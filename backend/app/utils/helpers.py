"""
Shared helper functions.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone


def now_utc() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def unix_timestamp() -> int:
    """Return current Unix timestamp as integer."""
    return int(time.time())


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def parse_mqtt_topic(topic: str) -> dict[str, str] | None:
    """
    Parse an MQTT topic into components.

    Expected format: ``home/{room}/{device_id}/{action}``

    Returns dict with keys ``room``, ``device_id``, ``action``, or None if
    the topic does not match the expected pattern.
    """
    parts = topic.split("/")
    if len(parts) != 4 or parts[0] != "home":
        return None
    return {
        "room": parts[1],
        "device_id": parts[2],
        "action": parts[3],
    }


def clamp(value: int | float, min_val: int | float, max_val: int | float) -> int | float:
    """Clamp a numeric value between min_val and max_val."""
    return max(min_val, min(max_val, value))
