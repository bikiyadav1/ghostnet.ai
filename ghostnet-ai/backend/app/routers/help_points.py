from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.schemas import HelpPointResponse

router = APIRouter(prefix="/help-points", tags=["Help Points"])


@router.get("", response_model=List[HelpPointResponse])
async def get_nearby_help_points(
    lat: float = Query(..., ge=-90.0, le=90.0, description="User latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="User longitude"),
    radius_km: float = Query(25.0, ge=0.5, le=200.0, description="Search radius in kilometers"),
    type_filter: Optional[str] = Query(None, description="Optional type filter (hospital, police, shelter, safe_zone)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Finds nearest emergency help points (hospitals, police stations, shelters, safe zones)
    using PostGIS ST_DWithin and ST_Distance indexed queries.
    """
    radius_meters = radius_km * 1000.0
    type_clause = ""
    params = {
        "lon": lon,
        "lat": lat,
        "radius_meters": radius_meters,
    }

    if type_filter:
        type_clause = "AND type = :type_filter"
        params["type_filter"] = type_filter

    sql_query = text(f"""
        SELECT 
            id,
            name,
            type,
            ST_Y(location::geometry) AS lat,
            ST_X(location::geometry) AS lon,
            ROUND((ST_Distance(location, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) / 1000.0)::numeric, 2) AS distance_km
        FROM help_points
        WHERE ST_DWithin(location, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_meters)
        {type_clause}
        ORDER BY distance_km ASC
        LIMIT 50;
    """)

    result = await db.execute(sql_query, params)
    rows = result.fetchall()

    return [
        HelpPointResponse(
            id=row.id,
            name=row.name,
            type=row.type,
            lat=row.lat,
            lon=row.lon,
            distance_km=float(row.distance_km),
        )
        for row in rows
    ]
