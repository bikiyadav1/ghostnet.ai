import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
from app.database import get_db
from app.models import Device, CheckIn
from app.schemas import CheckInRequest, CheckInResponse
from app.websocket import ws_manager

router = APIRouter(prefix="/check-in", tags=["Check In"])


@router.post("", response_model=CheckInResponse, status_code=status.HTTP_201_CREATED)
async def submit_check_in(
    request: CheckInRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submits a one-tap 'I am Safe' / 'Needs Help' status check-in.
    Persisted to database and broadcasted across WebSocket.
    """
    now = datetime.now(timezone.utc)

    # Ensure device exists
    dev = await db.get(Device, request.device_id)
    if not dev:
        db.add(Device(id=request.device_id, app_version="2.0.0"))
        await db.flush()

    checkin_id = uuid.uuid4()
    point_geom = ST_SetSRID(ST_MakePoint(request.lon, request.lat), 4326)

    check_in = CheckIn(
        id=checkin_id,
        device_id=request.device_id,
        location=point_geom,
        status=request.status,
        created_at=now,
    )
    db.add(check_in)
    await db.commit()

    # Broadcast check-in
    await ws_manager.broadcast(
        message_type="check_in",
        payload={
            "id": str(checkin_id),
            "device_id": str(request.device_id),
            "status": request.status.value,
            "lat": request.lat,
            "lon": request.lon,
            "created_at": now.isoformat(),
        },
    )

    return CheckInResponse(
        id=checkin_id,
        device_id=request.device_id,
        status=request.status,
        created_at=now,
    )
