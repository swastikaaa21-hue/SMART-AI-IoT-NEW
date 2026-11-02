from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class Device(Base):
    __tablename__ = "devices"
    id = Column(String(100), primary_key=True)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    device_type = Column(String(50), nullable=False, default="LIGHT")
    room_id = Column(String(100), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    state = Column(String(10), default="off", nullable=False)
    brightness = Column(Integer, nullable=True, default=100)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    target_temperature = Column(Float, nullable=True, default=24.0)
    ac_mode = Column(String(20), nullable=True, default="cool")
    fan_speed = Column(String(20), nullable=True, default="auto")
    timer_minutes = Column(Integer, nullable=True, default=0)
    extra_metadata = Column(JSON, nullable=True, default=dict)
    is_online = Column(Boolean, default=False, nullable=False)
    firmware_version = Column(String(50), nullable=True, default="1.0.0")
    description = Column(Text, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    room = relationship("Room", back_populates="devices")
    telemetry_logs = relationship("TelemetryLog", back_populates="device", cascade="all, delete-orphan", lazy="selectin")
    command_logs = relationship("CommandLog", back_populates="device", cascade="all, delete-orphan", lazy="selectin")
    schedules = relationship("Schedule", back_populates="device", cascade="all, delete-orphan")
