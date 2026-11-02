from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, String, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"
    id = Column(String(100), primary_key=True)
    device_id = Column(String(100), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    power_watts = Column(Float, nullable=True)
    extra_data = Column(JSON, nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    device = relationship("Device", back_populates="telemetry_logs")
