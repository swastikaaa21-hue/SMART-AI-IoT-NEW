from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class CommandLog(Base):
    __tablename__ = "command_logs"
    id = Column(String(100), primary_key=True)
    device_id = Column(String(100), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=True)
    source = Column(String(50), default="api", nullable=False)
    status = Column(String(30), default="sent", nullable=False)
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    device = relationship("Device", back_populates="command_logs")
