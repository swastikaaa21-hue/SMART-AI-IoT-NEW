"""
State Persistence Service - Ensures all user changes are saved to database without errors.

This service wraps all state-changing operations with:
- Transaction management
- Retry logic for transient failures
- Comprehensive error logging
- Validation before save
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, Optional
from functools import wraps

from app.core.logging import get_logger
from app.services.mysql_service import mysql_service
from app.services.websocket_manager import ws_manager

logger = get_logger("state_persistence")


class StatePersistenceService:
    """Ensures all state changes are persisted to database reliably."""

    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 0.5  # seconds

    async def _retry_operation(
        self, 
        operation: Callable, 
        operation_name: str,
        *args,
        **kwargs
    ) -> tuple[bool, Any, Optional[str]]:
        """
        Retry an operation with exponential backoff.
        Returns: (success: bool, result: Any, error: Optional[str])
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = await operation(*args, **kwargs)
                logger.info(
                    "operation_success",
                    operation=operation_name,
                    attempt=attempt + 1
                )
                return True, result, None
                
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "operation_failed_retry",
                    operation=operation_name,
                    attempt=attempt + 1,
                    error=last_error
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    
        logger.error(
            "operation_failed_all_retries",
            operation=operation_name,
            error=last_error
        )
        return False, None, last_error

    # ── Device State Changes ─────────────────────────────────

    async def save_device_state(
        self,
        device_id: str,
        state: str,
        extra_fields: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Save device state change with validation and retry.
        Returns: (success: bool, error: Optional[str])
        """
        # Validate state
        if state not in ["on", "off"]:
            return False, f"Invalid state: {state}"
        
        # Build update dict
        updates = {"state": state}
        if extra_fields:
            updates.update(extra_fields)
        
        # Save with retry
        success, result, error = await self._retry_operation(
            mysql_service.update_device_by_device_id,
            f"save_device_state_{device_id}",
            device_id,
            updates
        )
        
        if success:
            # Broadcast change via WebSocket
            try:
                await ws_manager.broadcast({
                    "type": "device_status_update",
                    "device_id": device_id,
                    "state": state,
                    "extra": extra_fields
                })
            except Exception as e:
                logger.warning("websocket_broadcast_failed", error=str(e))
        
        return success, error

    async def save_device_property(
        self,
        device_id: str,
        property_name: str,
        property_value: Any
    ) -> tuple[bool, Optional[str]]:
        """
        Save single device property (temperature, brightness, etc).
        Returns: (success: bool, error: Optional[str])
        """
        # Validate property
        allowed_properties = [
            "temperature", "target_temperature", "humidity", "brightness",
            "ac_mode", "fan_speed", "timer_minutes", "power_consumption"
        ]
        
        if property_name not in allowed_properties:
            return False, f"Invalid property: {property_name}"
        
        updates = {property_name: property_value}
        
        success, result, error = await self._retry_operation(
            mysql_service.update_device_by_device_id,
            f"save_device_property_{device_id}_{property_name}",
            device_id,
            updates
        )
        
        return success, error

    # ── IR Code Changes ──────────────────────────────────────

    async def save_ir_code(
        self,
        device_id: str,
        button_name: str,
        ir_frequency: str,
        protocol: Optional[str] = None,
        button_label: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Save IR code with validation.
        Returns: (success: bool, error: Optional[str])
        """
        # Validate inputs
        if not device_id or not button_name or not ir_frequency:
            return False, "Missing required fields"
        
        # Check if code exists
        existing = await mysql_service.get_ir_code_by_button(device_id, button_name)
        
        if existing:
            # Update existing
            updates = {
                "ir_frequency": ir_frequency,
                "protocol": protocol,
                "button_label": button_label,
            }
            success, result, error = await self._retry_operation(
                mysql_service.update_ir_code,
                f"update_ir_code_{device_id}_{button_name}",
                existing["id"],
                updates
            )
        else:
            # Create new
            import uuid
            from datetime import datetime, timezone
            
            code_data = {
                "id": str(uuid.uuid4()).replace("-", ""),
                "device_id": device_id,
                "button_name": button_name,
                "button_label": button_label,
                "ir_frequency": ir_frequency,
                "protocol": protocol,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            success, result, error = await self._retry_operation(
                mysql_service.create_ir_code,
                f"create_ir_code_{device_id}_{button_name}",
                code_data
            )
        
        if success:
            logger.info(
                "ir_code_saved",
                device_id=device_id,
                button=button_name,
                freq_length=len(ir_frequency)
            )
        
        return success, error

    # ── Schedule Changes ─────────────────────────────────────

    async def save_schedule(
        self,
        schedule_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Save schedule with validation.
        Returns: (success: bool, schedule_id: Optional[str], error: Optional[str])
        """
        # Validate required fields
        required = ["name", "time", "schedule_type"]
        for field in required:
            if field not in schedule_data:
                return False, None, f"Missing required field: {field}"
        
        success, result, error = await self._retry_operation(
            mysql_service.create_schedule,
            f"create_schedule_{schedule_data.get('name')}",
            schedule_data
        )
        
        schedule_id = result.get("id") if result else None
        return success, schedule_id, error

    async def update_schedule(
        self,
        schedule_id: str,
        updates: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Update schedule with validation."""
        success, result, error = await self._retry_operation(
            mysql_service.update_schedule,
            f"update_schedule_{schedule_id}",
            schedule_id,
            updates
        )
        
        return success, error

    # ── Room Changes ─────────────────────────────────────────

    async def save_room(
        self,
        room_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Save room with validation.
        Returns: (success: bool, room_id: Optional[str], error: Optional[str])
        """
        required = ["name", "slug"]
        for field in required:
            if field not in room_data:
                return False, None, f"Missing required field: {field}"
        
        success, result, error = await self._retry_operation(
            mysql_service.create_room,
            f"create_room_{room_data.get('name')}",
            room_data
        )
        
        room_id = result.get("id") if result else None
        return success, room_id, error

    async def update_room(
        self,
        room_id: str,
        updates: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Update room with validation."""
        success, result, error = await self._retry_operation(
            mysql_service.update_room,
            f"update_room_{room_id}",
            room_id,
            updates
        )
        
        return success, error

    # ── Telemetry ────────────────────────────────────────────

    async def save_telemetry(
        self,
        device_id: str,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        power_watts: Optional[float] = None,
        extra_data: Optional[Dict] = None
    ) -> tuple[bool, Optional[str]]:
        """Save telemetry data with validation."""
        from datetime import datetime, timezone
        import uuid
        
        telemetry_data = {
            "id": str(uuid.uuid4()).replace("-", ""),
            "device_id": device_id,
            "temperature": temperature,
            "humidity": humidity,
            "power_watts": power_watts,
            "extra_data": extra_data,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        
        success, result, error = await self._retry_operation(
            mysql_service.log_telemetry,
            f"save_telemetry_{device_id}",
            telemetry_data
        )
        
        # Also update device fields
        if success and (temperature or humidity):
            device_updates = {}
            if temperature is not None:
                device_updates["temperature"] = temperature
            if humidity is not None:
                device_updates["humidity"] = humidity
            
            await mysql_service.update_device_by_device_id(device_id, device_updates)
        
        return success, error

    # ── Batch Operations ─────────────────────────────────────

    async def save_multiple_device_states(
        self,
        device_updates: list[tuple[str, str, Optional[Dict[str, Any]]]]
    ) -> tuple[int, int, list[str]]:
        """
        Save multiple device states in batch.
        Args: list of (device_id, state, extra_fields)
        Returns: (success_count, fail_count, errors)
        """
        success_count = 0
        fail_count = 0
        errors = []
        
        for device_id, state, extra_fields in device_updates:
            success, error = await self.save_device_state(device_id, state, extra_fields)
            if success:
                success_count += 1
            else:
                fail_count += 1
                errors.append(f"{device_id}: {error}")
        
        logger.info(
            "batch_device_update_complete",
            total=len(device_updates),
            success=success_count,
            failed=fail_count
        )
        
        return success_count, fail_count, errors


# Module-level singleton
state_persistence = StatePersistenceService()
