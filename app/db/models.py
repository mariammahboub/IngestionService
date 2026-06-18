from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint, Index
from app.db.session import Base


class SensorReadingModel(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String(128), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    reading = Column(Float, nullable=False)
    received_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("sensor_id", "timestamp", name="uq_sensor_timestamp"),
        Index("ix_sensor_id_timestamp", "sensor_id", "timestamp"),
    )