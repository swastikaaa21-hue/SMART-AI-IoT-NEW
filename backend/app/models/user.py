from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    id = Column(String(100), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)
    full_name = Column(String(255), nullable=True, default="")
    avatar_url = Column(String(500), nullable=True)
    home_name = Column(String(255), nullable=True, default="My Smart Home")
    location = Column(String(255), nullable=True, default="")
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    rooms = relationship("Room", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    schedules = relationship("Schedule", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
