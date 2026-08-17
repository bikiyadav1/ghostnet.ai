import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.models import (
    NetworkTypeEnum,
    HelpPointTypeEnum,
    TowerSourceEnum,
    SosCategoryEnum,
    SosStatusEnum,
    CheckInStatusEnum,
)


class DeviceCreate(BaseModel):
    app_version: Optional[str] = "2.0.0"


class DeviceResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    app_version: Optional[str]

    class Config:
        from_attributes = True


class ReadingItem(BaseModel):
    device_id: uuid.UUID
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    network_type: NetworkTypeEnum
    signal_dbm: int = Field(..., ge=-140, le=-40)
    download_mbps: Optional[float] = 0.0
    upload_mbps: Optional[float] = 0.0
    latency_ms: Optional[int] = 0
    recorded_at: datetime


class ReadingsBatchRequest(BaseModel):
    readings: List[ReadingItem]


class ReadingsBatchResponse(BaseModel):
    accepted: int


class CoveragePointResponse(BaseModel):
    lat: float
    lon: float
    signal_dbm: int
    network_type: NetworkTypeEnum
    recorded_at: datetime


class HeatmapCellResponse(BaseModel):
    geohash: str
    avg_signal_dbm: float
    sample_count: int
    lat: Optional[float] = None
    lon: Optional[float] = None


class HelpPointResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: HelpPointTypeEnum
    lat: float
    lon: float
    distance_km: Optional[float] = None


class TowerResponse(BaseModel):
    id: uuid.UUID
    name: str
    lat: float
    lon: float
    operator: str
    source: TowerSourceEnum


# SOS Schemas for Phase 2
class SosCreateRequest(BaseModel):
    device_id: uuid.UUID
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    category: SosCategoryEnum = SosCategoryEnum.GENERAL
    message: Optional[str] = None


class SosBatchItem(BaseModel):
    device_id: uuid.UUID
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    category: SosCategoryEnum = SosCategoryEnum.GENERAL
    message: Optional[str] = None
    offline_created_at: Optional[datetime] = None
    is_relayed: Optional[bool] = False


class SosBatchRequest(BaseModel):
    alerts: List[SosBatchItem]


class SosBatchResponse(BaseModel):
    accepted: int
    ids: List[uuid.UUID]


class SosResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    lat: float
    lon: float
    category: SosCategoryEnum
    message: Optional[str]
    priority_score: float
    status: SosStatusEnum
    created_at: datetime
    sent_at: datetime
    corroboration_count: int
    is_relayed: bool
    breakdown: Optional[Dict[str, Any]] = None


class SosStatusUpdateRequest(BaseModel):
    status: SosStatusEnum


# Check-in Schemas for Phase 2
class CheckInRequest(BaseModel):
    device_id: uuid.UUID
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    status: CheckInStatusEnum = CheckInStatusEnum.SAFE


class CheckInResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    status: CheckInStatusEnum
    created_at: datetime


class WsMessage(BaseModel):
    type: str  # "reading" | "sos" | "prediction_update"
    payload: dict
