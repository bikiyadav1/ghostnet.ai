from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
from app.database import get_db
from app.models import Device, SignalReading
from app.schemas import ReadingsBatchRequest, ReadingsBatchResponse
from app.websocket import ws_manager

router = APIRouter(prefix="/readings", tags=["Readings"])


@router.post("", response_model=ReadingsBatchResponse, status_code=status.HTTP_201_CREATED)
async def submit_readings(
    batch: ReadingsBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts a batch of telemetry signal readings from mobile devices or simulators.
    Auto-registers unknown devices and broadcasts real-time updates over WebSocket.
    """
    if not batch.readings:
        return ReadingsBatchResponse(accepted=0)

    # Collect distinct device IDs
    device_ids = {r.device_id for r in batch.readings}

    # Ensure devices exist in DB
    existing_stmt = select(Device.id).where(Device.id.in_(device_ids))
    result = await db.execute(existing_stmt)
    existing_ids = set(result.scalars().all())

    new_device_ids = device_ids - existing_ids
    for d_id in new_device_ids:
        db.add(Device(id=d_id, app_version="2.0.0"))

    if new_device_ids:
        await db.flush()

    # Create SignalReading instances
    inserted_readings = []
    for r in batch.readings:
        point_geom = ST_SetSRID(ST_MakePoint(r.lon, r.lat), 4326)
        reading = SignalReading(
            device_id=r.device_id,
            location=point_geom,
            network_type=r.network_type,
            signal_dbm=r.signal_dbm,
            download_mbps=r.download_mbps,
            upload_mbps=r.upload_mbps,
            latency_ms=r.latency_ms,
            recorded_at=r.recorded_at,
        )
        db.add(reading)
        inserted_readings.append(r)

    await db.commit()

    # Broadcast to WebSocket clients
    for r in inserted_readings:
        await ws_manager.broadcast(
            message_type="reading",
            payload={
                "device_id": str(r.device_id),
                "lat": r.lat,
                "lon": r.lon,
                "signal_dbm": r.signal_dbm,
                "network_type": r.network_type.value,
                "recorded_at": r.recorded_at.isoformat(),
            },
        )

    return ReadingsBatchResponse(accepted=len(inserted_readings))
