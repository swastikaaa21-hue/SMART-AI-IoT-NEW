from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class Room(Base):
    __tablename__ = "rooms"
    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)
    room_type = Column(String(50), nullable=False, default="living_room")
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    owner_id = Column(String(100), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    owner = relationship("User", back_populates="rooms")
    devices = relationship("Device", back_populates="room", cascade="all, delete-orphan", lazy="selectin")
    schedules = relationship("Schedule", back_populates="room", cascade="all, delete-orphan")
