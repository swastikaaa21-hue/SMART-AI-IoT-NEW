"""Schedule model for automation routines."""

from datetime import time
from sqlalchemy import Column, String, Boolean, Time, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class Schedule(Base):
    """Schedule/Routine for device automation."""
    __tablename__ = "schedules"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=False)
    action = Column(String, nullable=False)  # turn_on, turn_off, set_temperature, etc
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=True)  # nullable for one-time actions
    is_active = Column(Boolean, default=True)
    days = Column(String, default="1,2,3,4,5,6,7")  # comma-separated: 1=Mon, 7=Sun
    parameters = Column(Text, nullable=True)  # JSON string for AC temp, fan speed, etc
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Relationships
    room = relationship("Room", back_populates="schedules")
    device = relationship("Device", back_populates="schedules")
    user = relationship("User", back_populates="schedules")
