import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
from app.database import get_db
from app.models import Device, SosAlert, SosStatusEnum, SosCategoryEnum
from app.schemas import (
    SosCreateRequest,
    SosBatchRequest,
    SosBatchResponse,
    SosResponse,
    SosStatusUpdateRequest,
)
from app.scoring import compute_db_priority_score, calculate_priority_score_pure
from app.websocket import ws_manager

router = APIRouter(prefix="/sos", tags=["Emergency SOS"])


async def _recompute_nearby_alerts(db: AsyncSession, lat: float, lon: float, exclude_id: uuid.UUID):
    """
    Finds existing active alerts within 500m and updates their corroboration count and priority score.
    This ensures that when a second SOS is triggered nearby, the existing alerts visibly re-rank!
    """
    find_nearby_sql = text("""
        SELECT id, category, created_at, ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon
        FROM sos_alerts
        WHERE ST_DWithin(
            location, 
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 
            500.0
        )
        AND id != :exclude_id
        AND status != 'resolved';
    """)
    res = await db.execute(find_nearby_sql, {"lat": lat, "lon": lon, "exclude_id": str(exclude_id)})
    nearby_rows = res.fetchall()

    for row in nearby_rows:
        new_score, count, loc_risk, breakdown = await compute_db_priority_score(
            db=db,
            lat=row.lat,
            lon=row.lon,
            category=row.category,
            created_at=row.created_at,
            exclude_alert_id=None,
        )
        update_sql = text("""
            UPDATE sos_alerts
            SET priority_score = :score, corroboration_count = :count
            WHERE id = :id;
        """)
        await db.execute(update_sql, {"score": new_score, "count": count, "id": row.id})


@router.post("", response_model=SosResponse, status_code=status.HTTP_201_CREATED)
async def create_sos_alert(
    request: SosCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Dispatches a real-time Emergency SOS alert.
    Calculates multi-factor priority score and broadcasts live across WebSocket.
    """
    now = datetime.now(timezone.utc)

    # Ensure device exists
    dev = await db.get(Device, request.device_id)
    if not dev:
        db.add(Device(id=request.device_id, app_version="2.0.0"))
        await db.flush()

    # Calculate initial priority score
    score, corrob_count, loc_risk, breakdown = await compute_db_priority_score(
        db=db,
        lat=request.lat,
        lon=request.lon,
        category=request.category,
        created_at=now,
    )

    alert_id = uuid.uuid4()
    point_geom = ST_SetSRID(ST_MakePoint(request.lon, request.lat), 4326)

    sos = SosAlert(
        id=alert_id,
        device_id=request.device_id,
        location=point_geom,
        message=request.message,
        category=request.category,
        priority_score=score,
        status=SosStatusEnum.SENT,
        created_at=now,
        sent_at=now,
        corroboration_count=corrob_count,
        is_relayed=False,
    )
    db.add(sos)
    await db.flush()

    # Recompute priority for other nearby alerts within 500m
    await _recompute_nearby_alerts(db, request.lat, request.lon, exclude_id=alert_id)
    await db.commit()

    response_data = SosResponse(
        id=alert_id,
        device_id=request.device_id,
        lat=request.lat,
        lon=request.lon,
        category=request.category,
        message=request.message,
        priority_score=score,
        status=SosStatusEnum.SENT,
        created_at=now,
        sent_at=now,
        corroboration_count=corrob_count,
        is_relayed=False,
        breakdown=breakdown,
    )

    # Broadcast over WebSocket
    await ws_manager.broadcast(
        message_type="sos",
        payload={
            "id": str(alert_id),
            "device_id": str(request.device_id),
            "lat": request.lat,
            "lon": request.lon,
            "category": request.category.value,
            "message": request.message,
            "priority_score": score,
            "status": "sent",
            "created_at": now.isoformat(),
            "corroboration_count": corrob_count,
            "is_relayed": False,
            "breakdown": breakdown,
        },
    )

    return response_data


@router.post("/batch", response_model=SosBatchResponse, status_code=status.HTTP_201_CREATED)
async def submit_sos_batch(
    batch: SosBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Sync-on-reconnect endpoint for offline queued alerts and mesh-relayed packets.
    Preserves exact offline creation timestamp for accurate decay and priority calculations.
    """
    if not batch.alerts:
        return SosBatchResponse(accepted=0, ids=[])

    now = datetime.now(timezone.utc)
    inserted_ids = []

    for alert in batch.alerts:
        created_time = alert.offline_created_at or now

        # Ensure device exists
        dev = await db.get(Device, alert.device_id)
        if not dev:
            db.add(Device(id=alert.device_id, app_version="2.0.0"))
            await db.flush()

        score, corrob_count, loc_risk, breakdown = await compute_db_priority_score(
            db=db,
            lat=alert.lat,
            lon=alert.lon,
            category=alert.category,
            created_at=created_time,
        )

        alert_id = uuid.uuid4()
        point_geom = ST_SetSRID(ST_MakePoint(alert.lon, alert.lat), 4326)

        sos = SosAlert(
            id=alert_id,
            device_id=alert.device_id,
            location=point_geom,
            message=alert.message,
            category=alert.category,
            priority_score=score,
            status=SosStatusEnum.SENT,
            created_at=created_time,
            sent_at=now,
            corroboration_count=corrob_count,
            is_relayed=alert.is_relayed or False,
        )
        db.add(sos)
        await db.flush()

        # Recompute nearby alerts
        await _recompute_nearby_alerts(db, alert.lat, alert.lon, exclude_id=alert_id)
        inserted_ids.append(alert_id)

        # Broadcast live
        await ws_manager.broadcast(
            message_type="sos",
            payload={
                "id": str(alert_id),
                "device_id": str(alert.device_id),
                "lat": alert.lat,
                "lon": alert.lon,
                "category": alert.category.value,
                "message": alert.message,
                "priority_score": score,
                "status": "sent",
                "created_at": created_time.isoformat(),
                "corroboration_count": corrob_count,
                "is_relayed": alert.is_relayed or False,
                "breakdown": breakdown,
            },
        )

    await db.commit()
    return SosBatchResponse(accepted=len(inserted_ids), ids=inserted_ids)


@router.get("", response_model=List[SosResponse])
async def get_sos_alerts(
    status_filter: Optional[SosStatusEnum] = Query(None, alias="status"),
    min_priority: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves all emergency SOS alerts sorted by dynamic priority score DESC.
    """
    where_clauses = []
    params = {"limit": limit}

    if status_filter:
        where_clauses.append("status = :status_filter")
        params["status_filter"] = status_filter.value

    if min_priority is not None:
        where_clauses.append("priority_score >= :min_priority")
        params["min_priority"] = min_priority

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    sql = text(f"""
        SELECT 
            id,
            device_id,
            ST_Y(location::geometry) AS lat,
            ST_X(location::geometry) AS lon,
            message,
            category,
            priority_score,
            status,
            created_at,
            sent_at,
            corroboration_count,
            is_relayed
        FROM sos_alerts
        {where_sql}
        ORDER BY priority_score DESC, created_at DESC
        LIMIT :limit;
    """)

    res = await db.execute(sql, params)
    rows = res.fetchall()

    return [
        SosResponse(
            id=row.id,
            device_id=row.device_id,
            lat=row.lat,
            lon=row.lon,
            message=row.message,
            category=row.category,
            priority_score=row.priority_score,
            status=row.status,
            created_at=row.created_at,
            sent_at=row.sent_at,
            corroboration_count=row.corroboration_count,
            is_relayed=row.is_relayed,
        )
        for row in rows
    ]


@router.patch("/{alert_id}/status", response_model=SosResponse)
async def update_sos_status(
    alert_id: uuid.UUID,
    update: SosStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Updates emergency status (e.g. acknowledged by responder or resolved).
    Broadcasts status change live to dashboard and field units.
    """
    sos = await db.get(SosAlert, alert_id)
    if not sos:
        raise HTTPException(status_code=404, detail="SOS Alert not found")

    sos.status = update.status
    await db.commit()
    await db.refresh(sos)

    # Get coords
    coord_sql = text("SELECT ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon FROM sos_alerts WHERE id = :id")
    c_res = await db.execute(coord_sql, {"id": str(alert_id)})
    c_row = c_res.fetchone()
    lat = c_row.lat if c_row else 23.3322
    lon = c_row.lon if c_row else 86.3652

    # Broadcast update
    await ws_manager.broadcast(
        message_type="sos_update",
        payload={
            "id": str(alert_id),
            "status": update.status.value,
        },
    )

    return SosResponse(
        id=sos.id,
        device_id=sos.device_id,
        lat=lat,
        lon=lon,
        message=sos.message,
        category=sos.category,
        priority_score=sos.priority_score,
        status=sos.status,
        created_at=sos.created_at,
        sent_at=sos.sent_at,
        corroboration_count=sos.corroboration_count,
        is_relayed=sos.is_relayed,
    )
