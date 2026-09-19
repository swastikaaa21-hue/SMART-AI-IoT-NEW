"""
Tests for API endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "services" in data

    async def test_root_endpoint(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "SMART AI IoT Backend"
        assert "api" in data


@pytest.mark.asyncio
class TestAuthEndpoints:
    async def test_register_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "securepass123",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {
            "email": "dup@example.com",
            "password": "securepass123",
        }
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409

    async def test_login_success(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "password": "mypassword1"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "login@example.com", "password": "mypassword1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "bad@example.com", "password": "correctpass1"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "bad@example.com", "password": "wrongpass"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestDeviceEndpoints:
    async def test_list_devices_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/devices")
        assert response.status_code == 401  # Missing auth header


@pytest.mark.asyncio
class TestSystemEndpoints:
    async def test_get_system_config(self, client: AsyncClient):
        response = await client.get("/api/v1/system/config")
        assert response.status_code == 200
        data = response.json()
        assert "gemini_api_key" in data
        assert "mqtt_broker" in data
        assert "app_name" in data

    async def test_get_system_status(self, client: AsyncClient):
        response = await client.get("/api/v1/system/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "total_rooms" in data
        assert "total_devices" in data

    async def test_seed_system_data(self, client: AsyncClient):
        # Register and login user first
        await client.post(
            "/api/v1/auth/register",
            json={"email": "seeduser@example.com", "password": "mypassword1", "full_name": "Seed User"},
        )
        login_res = await client.post(
            "/api/v1/auth/login",
            data={"username": "seeduser@example.com", "password": "mypassword1"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        seed_res = await client.post("/api/v1/system/seed", headers=headers)
        assert seed_res.status_code == 200
        data = seed_res.json()
        assert data["status"] == "success"
        assert data["rooms_count"] >= 4
        assert data["devices_count"] >= 10

        # Verify rooms are visible
        rooms_res = await client.get("/api/v1/rooms", headers=headers)
        assert rooms_res.status_code == 200
        assert rooms_res.json()["total"] >= 4

        # Test command sending to dev-km-1 via exact ID
        cmd_res = await client.post(
            "/api/v1/commands/dev-km-1",
            headers=headers,
            json={"action": "turn_on"},
        )
        assert cmd_res.status_code == 200
        assert cmd_res.json()["status"] in ["sent", "failed"]

        # Test command sending via fuzzy alias (light_bedroom)
        fuzzy_cmd = await client.post(
            "/api/v1/commands/light_bedroom",
            headers=headers,
            json={"action": "turn_on"},
        )
        assert fuzzy_cmd.status_code == 200
        assert fuzzy_cmd.json()["status"] in ["sent", "failed"]

        # Test set_value command
        val_res = await client.post(
            "/api/v1/commands/dev-km-1",
            headers=headers,
            json={"action": "set_value", "value": 95},
        )
        assert val_res.status_code == 200
        assert val_res.json()["status"] in ["sent", "failed"]

        # Test update config
        update_cfg = await client.post(
            "/api/v1/system/config",
            headers=headers,
            json={"gemini_model": "gemini-3.5-flash-lite"},
        )
        assert update_cfg.status_code == 200
        assert update_cfg.json()["gemini_model"] == "gemini-3.5-flash-lite"

    async def test_ui_endpoints(self, client: AsyncClient):
        ui_res = await client.get("/ui")
        assert ui_res.status_code == 200
        assert "html" in ui_res.headers.get("content-type", "")

        app_res = await client.get("/app")
        assert app_res.status_code == 200
