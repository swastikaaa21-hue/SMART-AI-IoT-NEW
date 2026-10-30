"""Schedule model for automation routines."""

from sqlalchemy import Column, String, Boolean, Time, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.session import Base


class Schedule(Base):
    """Schedule/Routine for device automation."""
    __tablename__ = "schedules"

    id = Column(String(100), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    room_id = Column(String(100), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    device_id = Column(String(100), ForeignKey("devices.device_id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False, default="turn_on")
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=True)
    is_active = Column(Boolean, default=True)
    days = Column(String(50), default="1,2,3,4,5,6,7")
    parameters = Column(Text, nullable=True)
    user_id = Column(String(100), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    room = relationship("Room", back_populates="schedules")
    device = relationship("Device", back_populates="schedules")
    user = relationship("User", back_populates="schedules")
