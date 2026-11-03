from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.db.session import Base


class IRCode(Base):
    """Stores learned IR frequency codes for remote control buttons."""
    __tablename__ = "ir_codes"
    
    id = Column(String(100), primary_key=True)
    device_id = Column(String(100), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True)
    button_name = Column(String(100), nullable=False)  # e.g., "power", "vol_up", "ch_up"
    button_label = Column(String(100), nullable=True)  # Display name
    ir_frequency = Column(Text, nullable=False)  # Raw IR frequency data from sensor
    protocol = Column(String(50), nullable=True)  # e.g., "NEC", "RC5", "SONY"
    raw_data = Column(Text, nullable=True)  # Additional raw timing data if needed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<IRCode {self.device_id}:{self.button_name}>"
