from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False, default="LIGHT")
    room_id: Mapped[str] = mapped_column(String(100), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    state: Mapped[str] = mapped_column(String(10), default="off", nullable=False)
    brightness: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=100)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=24.0)
    ac_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="cool")
    fan_speed: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="auto")
    timer_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    firmware_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="1.0.0")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    room: Mapped["Room"] = relationship("Room", back_populates="devices")
    telemetry_logs: Mapped[list["TelemetryLog"]] = relationship("TelemetryLog", back_populates="device", cascade="all, delete-orphan", lazy="selectin")
    command_logs: Mapped[list["CommandLog"]] = relationship("CommandLog", back_populates="device", cascade="all, delete-orphan", lazy="selectin")
    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="device", cascade="all, delete-orphan")
