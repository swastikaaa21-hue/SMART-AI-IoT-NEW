from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default="")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    home_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default="My Smart Home")
    location: Mapped[str | None] = mapped_column(String(255), nullable=True, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    rooms: Mapped[list["Room"]] = relationship("Room", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
