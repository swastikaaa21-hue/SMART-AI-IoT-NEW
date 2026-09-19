from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, Text, JSON, Uuid as UUID
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class CommandLog(Base):
    __tablename__ = "command_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(100), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="api", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="sent", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    device: Mapped["Device"] = relationship("Device", back_populates="command_logs")
