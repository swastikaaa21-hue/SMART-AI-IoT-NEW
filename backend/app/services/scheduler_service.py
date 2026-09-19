"""Real-time scheduler service for automated device control."""

import asyncio
from datetime import datetime, time
from typing import Dict, Set
from app.core.logging import get_logger
from app.services.supabase_service import supabase_service
from app.services.device_manager import device_manager

logger = get_logger("scheduler_service")


class SchedulerService:
    """Manages scheduled device automation tasks."""

    def __init__(self):
        self._running = False
        self._task = None
        self._active_schedules: Set[str] = set()

    async def start(self):
        """Start the scheduler background task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("scheduler_started")

    async def stop(self):
        """Stop the scheduler background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("scheduler_stopped")

    async def _run_scheduler(self):
        """Main scheduler loop - checks schedules every minute."""
        while self._running:
            try:
                await self._check_schedules()
            except Exception as e:
                logger.error("scheduler_error", error=str(e))
            await asyncio.sleep(60)  # Check every minute

    async def _check_schedules(self):
        """Check and execute due schedules."""
        now = datetime.now()
        current_time = now.time()
        current_day = now.isoweekday()  # 1=Mon, 7=Sun

        # Get all active schedules from Supabase
        try:
            schedules = await supabase_service.get_all_schedules()
        except Exception as e:
            logger.warning("failed_to_fetch_schedules", error=str(e))
            return

        for schedule in schedules:
            if not schedule.get("is_active"):
                continue

            schedule_id = schedule.get("id")
            start_time_str = schedule.get("start_time")
            end_time_str = schedule.get("end_time")
            days_str = schedule.get("days", "1,2,3,4,5,6,7")

            # Check if today is in schedule days
            days = [int(d.strip()) for d in days_str.split(",") if d.strip().isdigit()]
            if current_day not in days:
                continue

            # Parse start time
            try:
                start_time = datetime.strptime(start_time_str, "%H:%M").time()
            except:
                continue

            # Check if it's time to turn ON
            if self._is_time_match(current_time, start_time):
                schedule_key = f"{schedule_id}_start"
                if schedule_key not in self._active_schedules:
                    await self._execute_schedule(schedule, "start")
                    self._active_schedules.add(schedule_key)
            else:
                self._active_schedules.discard(f"{schedule_id}_start")

            # Check if it's time to turn OFF (if end_time is set)
            if end_time_str:
                try:
                    end_time = datetime.strptime(end_time_str, "%H:%M").time()
                    if self._is_time_match(current_time, end_time):
                        schedule_key = f"{schedule_id}_end"
                        if schedule_key not in self._active_schedules:
                            await self._execute_schedule(schedule, "end")
                            self._active_schedules.add(schedule_key)
                    else:
                        self._active_schedules.discard(f"{schedule_id}_end")
                except:
                    pass

    def _is_time_match(self, current: time, target: time) -> bool:
        """Check if current time matches target time (minute precision)."""
        return current.hour == target.hour and current.minute == target.minute

    async def _execute_schedule(self, schedule: Dict, phase: str):
        """Execute a scheduled action."""
        device_id = schedule.get("device_id")
        action = schedule.get("action")
        schedule_name = schedule.get("name", "Unknown")

        # For end phase, always turn off
        if phase == "end":
            action = "turn_off"

        logger.info(
            "executing_schedule",
            schedule_name=schedule_name,
            device_id=device_id,
            action=action,
            phase=phase
        )

        try:
            # Parse parameters if available
            params = {}
            parameters_str = schedule.get("parameters")
            if parameters_str:
                import json
                try:
                    params = json.loads(parameters_str)
                except:
                    pass

            # Execute command
            await device_manager.send_command(
                device_id=device_id,
                action=action,
                source="scheduler",
                target_temperature=params.get("target_temperature"),
                ac_mode=params.get("ac_mode"),
                fan_speed=params.get("fan_speed"),
                timer_minutes=params.get("timer_minutes"),
            )
            logger.info("schedule_executed", schedule_name=schedule_name, device_id=device_id)
        except Exception as e:
            logger.error("schedule_execution_failed", schedule_name=schedule_name, error=str(e))


# Global singleton instance
scheduler_service = SchedulerService()
