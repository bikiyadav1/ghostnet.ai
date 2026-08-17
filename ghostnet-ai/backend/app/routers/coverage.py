from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import pygeohash as pgh
from app.database import get_db
from app.schemas import CoveragePointResponse, HeatmapCellResponse

router = APIRouter(prefix="/coverage", tags=["Coverage"])


@router.get("", response_model=List[CoveragePointResponse])
async def get_coverage(
    bbox: Optional[str] = Query(
        None,
        description="Bounding box in format 'minLon,minLat,maxLon,maxLat'",
        example="86.0,23.0,86.8,23.6",
    ),
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns individual signal reading points filtered by bounding box.
    Uses PostGIS GIST spatial index for ultra-fast response (<300ms).
    """
    where_clause = ""
    params = {"limit": limit}

    if bbox:
        try:
            coords = [float(c.strip()) for c in bbox.split(",")]
            if len(coords) != 4:
                raise ValueError
            min_lon, min_lat, max_lon, max_lat = coords
            where_clause = "WHERE location && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)"
            params.update({
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat,
            })
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid bbox format. Expected 'minLon,minLat,maxLon,maxLat'",
            )

    sql_query = text(f"""
        SELECT 
            ST_Y(location::geometry) AS lat,
            ST_X(location::geometry) AS lon,
            signal_dbm,
            network_type,
            recorded_at
        FROM signal_readings
        {where_clause}
        ORDER BY recorded_at DESC
        LIMIT :limit;
    """)

    result = await db.execute(sql_query, params)
    rows = result.fetchall()

    return [
        CoveragePointResponse(
            lat=row.lat,
            lon=row.lon,
            signal_dbm=row.signal_dbm,
            network_type=row.network_type,
            recorded_at=row.recorded_at,
        )
        for row in rows
    ]


@router.get("/heatmap", response_model=List[HeatmapCellResponse])
async def get_coverage_heatmap(
    bbox: Optional[str] = Query(
        None,
        description="Bounding box in format 'minLon,minLat,maxLon,maxLat'",
        example="86.0,23.0,86.8,23.6",
    ),
    precision: int = Query(6, ge=4, le=8, description="Geohash precision"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregated signal strength by Geohash cell across the specified bounding box.
    Optimized for fast rendering of heatmap tiles and coverage density.
    """
    where_clause = ""
    params = {"precision": precision}

    if bbox:
        try:
            coords = [float(c.strip()) for c in bbox.split(",")]
            if len(coords) != 4:
                raise ValueError
            min_lon, min_lat, max_lon, max_lat = coords
            where_clause = "WHERE location && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)"
            params.update({
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat,
            })
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid bbox format. Expected 'minLon,minLat,maxLon,maxLat'",
            )

    # Fast spatial query retrieving points
    sql_query = text(f"""
        SELECT 
            ST_Y(location::geometry) AS lat,
            ST_X(location::geometry) AS lon,
            signal_dbm
        FROM signal_readings
        {where_clause};
    """)

    result = await db.execute(sql_query, params)
    rows = result.fetchall()

    # Aggregate in Python / Geohash buckets
    cells = {}
    for row in rows:
        gh = pgh.encode(row.lat, row.lon, precision=precision)
        if gh not in cells:
            cells[gh] = {
                "total_signal": 0,
                "count": 0,
            }
        cells[gh]["total_signal"] += row.signal_dbm
        cells[gh]["count"] += 1

    heatmap_cells = []
    for gh, data in cells.items():
        center_lat, center_lon = pgh.decode(gh)
        avg_dbm = data["total_signal"] / data["count"]
        heatmap_cells.append(
            HeatmapCellResponse(
                geohash=gh,
                avg_signal_dbm=round(avg_dbm, 2),
                sample_count=data["count"],
                lat=round(center_lat, 6),
                lon=round(center_lon, 6),
            )
        )

    return heatmap_cells
