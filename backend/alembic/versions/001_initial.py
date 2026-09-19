"""Initial schema - all tables

Revision ID: 001_initial
Revises: None
Create Date: 2026-09-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import JSON, Uuid as UUID

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("is_superuser", sa.Boolean, default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- rooms ---
    op.create_table(
        "rooms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("room_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- devices ---
    op.create_table(
        "devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=False),
        sa.Column(
            "room_id",
            UUID(as_uuid=True),
            sa.ForeignKey("rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(10), default="off", nullable=False),
        sa.Column("brightness", sa.Integer, nullable=True),
        sa.Column("temperature", sa.Float, nullable=True),
        sa.Column("humidity", sa.Float, nullable=True),
        sa.Column("extra_metadata", JSON, nullable=True),
        sa.Column("is_online", sa.Boolean, default=False, nullable=False),
        sa.Column("firmware_version", sa.String(50), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- telemetry_logs ---
    op.create_table(
        "telemetry_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "device_id",
            sa.String(100),
            sa.ForeignKey("devices.device_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("temperature", sa.Float, nullable=True),
        sa.Column("humidity", sa.Float, nullable=True),
        sa.Column("power_watts", sa.Float, nullable=True),
        sa.Column("extra_data", JSON, nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )

    # --- command_logs ---
    op.create_table(
        "command_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "device_id",
            sa.String(100),
            sa.ForeignKey("devices.device_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("payload", JSON, nullable=True),
        sa.Column("source", sa.String(50), default="api", nullable=False),
        sa.Column("status", sa.String(30), default="sent", nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )

    # --- chat_sessions ---
    op.create_table(
        "chat_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), default="New Chat", nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- chat_messages ---
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("function_call", sa.Text, nullable=True),
        sa.Column("function_response", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("command_logs")
    op.drop_table("telemetry_logs")
    op.drop_table("devices")
    op.drop_table("rooms")
    op.drop_table("users")
