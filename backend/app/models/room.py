from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, Text
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    room_type: Mapped[str] = mapped_column(String(50), nullable=False, default="living_room")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(100), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="rooms")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="room", cascade="all, delete-orphan", lazy="selectin")
    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="room", cascade="all, delete-orphan")
