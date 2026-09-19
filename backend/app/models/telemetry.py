from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, String, JSON, Uuid as UUID
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(100), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    power_watts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    device: Mapped["Device"] = relationship("Device", back_populates="telemetry_logs")
