import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography
from app.database import Base


class NetworkTypeEnum(str, enum.Enum):
    TWO_G = "2G"
    THREE_G = "3G"
    FOUR_G = "4G"
    FIVE_G = "5G"
    NONE = "none"


class TowerSourceEnum(str, enum.Enum):
    OFFICIAL = "official"
    INFERRED = "inferred"


class HelpPointTypeEnum(str, enum.Enum):
    HOSPITAL = "hospital"
    POLICE = "police"
    SHELTER = "shelter"
    SAFE_ZONE = "safe_zone"


class SosCategoryEnum(str, enum.Enum):
    MEDICAL = "medical"
    DISASTER = "disaster"
    SECURITY = "security"
    GENERAL = "general"


class SosStatusEnum(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class CheckInStatusEnum(str, enum.Enum):
    SAFE = "safe"
    NEEDS_HELP = "needs_help"


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    app_version = Column(String(50), nullable=True, default="2.0.0")


class SignalReading(Base):
    __tablename__ = "signal_readings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)
    location = Column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)
    network_type = Column(Enum(NetworkTypeEnum, name="network_type_enum"), nullable=False)
    signal_dbm = Column(Integer, nullable=False)
    download_mbps = Column(Float, nullable=True, default=0.0)
    upload_mbps = Column(Float, nullable=True, default=0.0)
    latency_ms = Column(Integer, nullable=True, default=0)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("idx_signal_readings_location_gist", "location", postgresql_using="gist"),
        Index("idx_signal_readings_recorded_at", "recorded_at"),
    )


class Tower(Base):
    __tablename__ = "towers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    location = Column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)
    operator = Column(String(100), nullable=False)
    source = Column(Enum(TowerSourceEnum, name="tower_source_enum"), default=TowerSourceEnum.OFFICIAL, nullable=False)

    __table_args__ = (
        Index("idx_towers_location_gist", "location", postgresql_using="gist"),
    )


class DeadZone(Base):
    __tablename__ = "dead_zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cell_geohash = Column(String(12), nullable=False, index=True)
    predicted_score = Column(Float, nullable=False)
    predicted_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    confidence = Column(Float, nullable=False, default=1.0)


class HelpPoint(Base):
    __tablename__ = "help_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(Enum(HelpPointTypeEnum, name="help_point_type_enum"), nullable=False)
    location = Column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)

    __table_args__ = (
        Index("idx_help_points_location_gist", "location", postgresql_using="gist"),
    )


class SosAlert(Base):
    __tablename__ = "sos_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)
    location = Column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)
    message = Column(Text, nullable=True)
    category = Column(Enum(SosCategoryEnum, name="sos_category_enum"), nullable=False, default=SosCategoryEnum.GENERAL)
    priority_score = Column(Float, nullable=False, default=0.5)
    status = Column(Enum(SosStatusEnum, name="sos_status_enum"), nullable=False, default=SosStatusEnum.SENT)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    corroboration_count = Column(Integer, default=0, nullable=False)
    is_relayed = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("idx_sos_alerts_location_gist", "location", postgresql_using="gist"),
        Index("idx_sos_alerts_priority", "priority_score"),
        Index("idx_sos_alerts_created_at", "created_at"),
    )


class CheckIn(Base):
    __tablename__ = "check_ins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)
    location = Column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)
    status = Column(Enum(CheckInStatusEnum, name="checkin_status_enum"), nullable=False, default=CheckInStatusEnum.SAFE)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_check_ins_location_gist", "location", postgresql_using="gist"),
    )
