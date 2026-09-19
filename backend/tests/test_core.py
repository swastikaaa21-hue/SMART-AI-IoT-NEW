"""
Tests for core configuration and utilities.
"""

from __future__ import annotations

from app.core.config import Settings, settings
from app.core.constants import DeviceState, DeviceType, RoomType
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.utils.helpers import parse_mqtt_topic, slugify


class TestConfig:
    def test_settings_loaded(self):
        assert settings.APP_NAME == "SMART AI IoT Backend"
        assert settings.MQTT_PORT == 8883
        assert settings.API_V1_PREFIX == "/api/v1"

    def test_is_production(self):
        s = Settings(APP_ENV="production")
        assert s.is_production is True

    def test_cors_parsing(self):
        s = Settings(BACKEND_CORS_ORIGINS='["http://localhost:3000"]')
        assert "http://localhost:3000" in s.BACKEND_CORS_ORIGINS


class TestSecurity:
    def test_password_hashing(self):
        plain = "secure-password-123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed) is True
        assert verify_password("wrong-password", hashed) is False

    def test_jwt_token_cycle(self):
        subject = "user-123"
        token = create_access_token(subject)
        payload = decode_token(token)
        assert payload["sub"] == subject
        assert payload["type"] == "access"


class TestConstants:
    def test_device_states(self):
        assert DeviceState.ON.value == "on"
        assert DeviceState.OFF.value == "off"

    def test_device_types(self):
        assert DeviceType.LIGHT.value == "light"
        assert DeviceType.FAN.value == "fan"

    def test_room_types(self):
        assert RoomType.LIVING_ROOM.value == "living_room"
        assert RoomType.BEDROOM.value == "bedroom"


class TestHelpers:
    def test_parse_mqtt_topic(self):
        result = parse_mqtt_topic("home/living_room/esp32_light_01/status")
        assert result is not None
        assert result["room"] == "living_room"
        assert result["device_id"] == "esp32_light_01"
        assert result["action"] == "status"

    def test_parse_mqtt_topic_invalid(self):
        assert parse_mqtt_topic("invalid/topic") is None
        assert parse_mqtt_topic("") is None

    def test_slugify(self):
        assert slugify("Living Room") == "living_room"
        assert slugify("Master Bedroom!") == "master_bedroom"
