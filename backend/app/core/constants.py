"""
Application-wide constants.

Centralised string literals, topic patterns, and enumerations used across
the entire backend so nothing is hard-coded in business logic.
"""

from __future__ import annotations

from enum import Enum


# ── MQTT Topic Patterns ──────────────────────────────────────
MQTT_TOPIC_COMMAND = "home/{room}/{device_id}/set"
MQTT_TOPIC_STATUS = "home/{room}/{device_id}/status"
MQTT_TOPIC_STATUS_WILDCARD = "home/+/+/status"
MQTT_TOPIC_TELEMETRY = "home/{room}/{device_id}/telemetry"
MQTT_TOPIC_TELEMETRY_WILDCARD = "home/+/+/telemetry"


# ── Device States ────────────────────────────────────────────
class DeviceState(str, Enum):
    ON = "on"
    OFF = "off"


# ── Device Types ─────────────────────────────────────────────
class DeviceType(str, Enum):
    LIGHT = "light"
    FAN = "fan"
    AC = "ac"
    TV = "tv"
    PROJECTOR = "projector"
    SENSOR = "sensor"
    RELAY = "relay"
    DOOR_LOCK = "door_lock"
    CAMERA = "camera"
    CURTAIN = "curtain"
    SPEAKER = "speaker"
    THERMOSTAT = "thermostat"
    OTHER = "other"


# ── Room Types ───────────────────────────────────────────────
class RoomType(str, Enum):
    LIVING_ROOM = "living_room"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    GARAGE = "garage"
    GARDEN = "garden"
    OFFICE = "office"
    HALLWAY = "hallway"
    STUDIO = "studio"
    MEETING_ROOM = "meeting_room"
    OTHER = "other"


# ── Command Actions ─────────────────────────────────────────
class CommandAction(str, Enum):
    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"
    TOGGLE = "toggle"
    SET_VALUE = "set_value"
    GET_STATUS = "get_status"


# ── AI Intent Types ─────────────────────────────────────────
class AIIntent(str, Enum):
    CONTROL_DEVICE = "control_device"
    QUERY_STATUS = "query_status"
    QUERY_TELEMETRY = "query_telemetry"
    LIST_DEVICES = "list_devices"
    GENERAL_CHAT = "general_chat"
    SCHEDULE_TASK = "schedule_task"


# ── WebSocket Event Types ───────────────────────────────────
class WSEventType(str, Enum):
    DEVICE_STATUS_UPDATE = "device_status_update"
    DEVICE_COMMAND_SENT = "device_command_sent"
    TELEMETRY_UPDATE = "telemetry_update"
    AI_RESPONSE = "ai_response"
    CONNECTION_ACK = "connection_ack"
    ERROR = "error"


# ── API Limits ───────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
