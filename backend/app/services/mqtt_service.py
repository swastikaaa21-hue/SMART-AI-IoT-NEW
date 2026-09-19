"""
MQTT service for HiveMQ Cloud integration.

Handles TLS-secured connection on port 8883, subscribes to device status topics,
publishes commands, and dispatches incoming messages to handlers.
"""

from __future__ import annotations

import asyncio
import json
import ssl
import sys
import threading
import time
from typing import Any, Callable, Coroutine

import aiomqtt

from app.core.config import settings
from app.core.constants import (
    MQTT_TOPIC_COMMAND,
    MQTT_TOPIC_STATUS_WILDCARD,
    MQTT_TOPIC_TELEMETRY_WILDCARD,
)
from app.core.logging import get_logger

logger = get_logger("mqtt_service")

# Type alias for message handler callbacks
MessageHandler = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]

# On Windows, aiomqtt (paho-mqtt) requires SelectorEventLoop because it uses
# add_reader()/add_writer() which ProactorEventLoop does not support.
# We run the MQTT client in a dedicated thread with its own SelectorEventLoop.
_IS_WINDOWS = sys.platform == "win32"


class MQTTService:
    """
    Async MQTT client for HiveMQ Cloud.

    Lifecycle:
    1. ``connect()`` establishes TLS connection and spawns listener task.
    2. ``publish_command()`` sends JSON payloads to device command topics.
    3. ``disconnect()`` gracefully tears down the connection.

    On Windows, the MQTT loop runs in a dedicated thread with a
    SelectorEventLoop to avoid ProactorEventLoop compatibility issues.
    """

    def __init__(self) -> None:
        self._client: aiomqtt.Client | None = None
        self._listener_task: asyncio.Task | None = None
        self._connected: bool = False
        self._status_handlers: list[MessageHandler] = []
        self._telemetry_handlers: list[MessageHandler] = []
        self._reconnect_interval: int = 5
        self._max_reconnect_interval: int = 60
        # Windows threading support
        self._mqtt_loop: asyncio.AbstractEventLoop | None = None
        self._mqtt_thread: threading.Thread | None = None
        # Reference to the main event loop (for scheduling handler callbacks)
        self._main_loop: asyncio.AbstractEventLoop | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def on_status(self, handler: MessageHandler) -> None:
        """Register a handler for device status messages."""
        self._status_handlers.append(handler)

    def on_telemetry(self, handler: MessageHandler) -> None:
        """Register a handler for device telemetry messages."""
        self._telemetry_handlers.append(handler)

    def _build_tls_context(self) -> ssl.SSLContext:
        """Build TLS context for HiveMQ Cloud connection."""
        tls_context = ssl.create_default_context()
        tls_context.check_hostname = True
        tls_context.verify_mode = ssl.CERT_REQUIRED
        return tls_context

    async def connect(self) -> None:
        """Establish connection to HiveMQ Cloud and start message listener."""
        if not settings.MQTT_BROKER:
            logger.warning("mqtt_broker_not_configured", msg="MQTT_BROKER is empty, skipping connection")
            return

        logger.info(
            "mqtt_connecting",
            broker=settings.MQTT_BROKER,
            port=settings.MQTT_PORT,
            client_id=settings.MQTT_CLIENT_ID,
        )

        self._main_loop = asyncio.get_running_loop()

        if _IS_WINDOWS:
            # Run MQTT in a dedicated thread with SelectorEventLoop
            self._mqtt_loop = asyncio.SelectorEventLoop()
            self._mqtt_thread = threading.Thread(
                target=self._run_mqtt_thread,
                name="mqtt-selector-loop",
                daemon=True,
            )
            self._mqtt_thread.start()
        else:
            self._listener_task = asyncio.create_task(self._connection_loop())

    def _run_mqtt_thread(self) -> None:
        """Entry point for the dedicated MQTT thread (Windows only)."""
        asyncio.set_event_loop(self._mqtt_loop)
        self._mqtt_loop.run_until_complete(self._connection_loop())

    async def _connection_loop(self) -> None:
        """Persistent connection loop with automatic reconnection."""
        reconnect_interval = self._reconnect_interval

        while True:
            try:
                tls_params = aiomqtt.TLSParameters(
                    ca_certs=None,
                    certfile=None,
                    keyfile=None,
                ) if settings.MQTT_TLS_ENABLED else None

                tls_context = self._build_tls_context() if settings.MQTT_TLS_ENABLED else None

                async with aiomqtt.Client(
                    hostname=settings.MQTT_BROKER,
                    port=settings.MQTT_PORT,
                    username=settings.MQTT_USERNAME,
                    password=settings.MQTT_PASSWORD,
                    identifier=settings.MQTT_CLIENT_ID,
                    tls_context=tls_context,
                    keepalive=settings.MQTT_KEEPALIVE,
                ) as client:
                    self._client = client
                    self._connected = True
                    reconnect_interval = self._reconnect_interval

                    logger.info("mqtt_connected", broker=settings.MQTT_BROKER)

                    # Subscribe to status and telemetry wildcard topics
                    await client.subscribe(MQTT_TOPIC_STATUS_WILDCARD, qos=1)
                    await client.subscribe(MQTT_TOPIC_TELEMETRY_WILDCARD, qos=1)

                    logger.info(
                        "mqtt_subscribed",
                        topics=[MQTT_TOPIC_STATUS_WILDCARD, MQTT_TOPIC_TELEMETRY_WILDCARD],
                    )

                    # Listen for messages
                    async for message in client.messages:
                        await self._handle_message(message)

            except aiomqtt.MqttError as exc:
                self._connected = False
                self._client = None
                logger.error(
                    "mqtt_connection_error",
                    error=str(exc),
                    reconnect_in=reconnect_interval,
                )
                await asyncio.sleep(reconnect_interval)
                reconnect_interval = min(
                    reconnect_interval * 2,
                    self._max_reconnect_interval,
                )
            except asyncio.CancelledError:
                logger.info("mqtt_listener_cancelled")
                self._connected = False
                self._client = None
                break
            except Exception as exc:
                self._connected = False
                self._client = None
                logger.exception("mqtt_unexpected_error", error=str(exc))
                await asyncio.sleep(reconnect_interval)

    async def _handle_message(self, message: aiomqtt.Message) -> None:
        """Route incoming MQTT messages to registered handlers."""
        topic = str(message.topic)
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("mqtt_invalid_payload", topic=topic, error=str(exc))
            return

        logger.debug("mqtt_message_received", topic=topic, payload=payload)

        # Route to appropriate handlers based on topic pattern
        if "/status" in topic:
            for handler in self._status_handlers:
                try:
                    if _IS_WINDOWS and self._main_loop and self._main_loop.is_running():
                        asyncio.run_coroutine_threadsafe(handler(topic, payload), self._main_loop)
                    else:
                        await handler(topic, payload)
                except Exception as exc:
                    logger.exception(
                        "mqtt_status_handler_error",
                        handler=handler.__name__,
                        error=str(exc),
                    )
        elif "/telemetry" in topic:
            for handler in self._telemetry_handlers:
                try:
                    if _IS_WINDOWS and self._main_loop and self._main_loop.is_running():
                        asyncio.run_coroutine_threadsafe(handler(topic, payload), self._main_loop)
                    else:
                        await handler(topic, payload)
                except Exception as exc:
                    logger.exception(
                        "mqtt_telemetry_handler_error",
                        handler=handler.__name__,
                        error=str(exc),
                    )

    async def publish_command(
        self,
        room_slug: str,
        device_id: str,
        state: str,
        extra_payload: dict[str, Any] | None = None,
    ) -> bool:
        """
        Publish a command to a device via MQTT.

        Args:
            room_slug: The room's slug identifier.
            device_id: The target device identifier.
            state: Desired state ("on" or "off").
            extra_payload: Additional key-value pairs to include.

        Returns:
            True if published successfully, False otherwise.
        """
        if not self._client or not self._connected:
            logger.error("mqtt_publish_failed", reason="not_connected")
            return False

        topic = MQTT_TOPIC_COMMAND.format(room=room_slug, device_id=device_id)
        payload: dict[str, Any] = {
            "state": state,
            "timestamp": int(time.time()),
        }
        if extra_payload:
            payload.update(extra_payload)

        try:
            await self._client.publish(
                topic,
                json.dumps(payload).encode("utf-8"),
                qos=1,
            )
            logger.info(
                "mqtt_command_published",
                topic=topic,
                payload=payload,
            )
            return True
        except aiomqtt.MqttError as exc:
            logger.error(
                "mqtt_publish_error",
                topic=topic,
                error=str(exc),
            )
            return False

    async def publish_raw(self, topic: str, payload: dict[str, Any]) -> bool:
        """Publish an arbitrary JSON payload to any MQTT topic."""
        if not self._client or not self._connected:
            logger.error("mqtt_publish_raw_failed", reason="not_connected")
            return False

        try:
            await self._client.publish(
                topic,
                json.dumps(payload).encode("utf-8"),
                qos=1,
            )
            logger.info("mqtt_raw_published", topic=topic)
            return True
        except aiomqtt.MqttError as exc:
            logger.error("mqtt_raw_publish_error", topic=topic, error=str(exc))
            return False

    async def disconnect(self) -> None:
        """Gracefully disconnect from the MQTT broker."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        self._connected = False
        self._client = None
        logger.info("mqtt_disconnected")


# Module-level singleton
mqtt_service = MQTTService()
