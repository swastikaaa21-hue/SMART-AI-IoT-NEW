"""
MQTT cross-event-loop behaviour.

The MQTT client lives on its own thread with its own loop on Windows, while the
database session factory and the WebSocket connections belong to the main loop.
These tests pin both directions of that boundary: inbound messages must be
handled on the main loop, and publishes must run on the loop that owns the
client, bounded by ``MQTT_PUBLISH_TIMEOUT``.
"""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable
from typing import Any

import pytest

from app.core.config import settings
from app.services.mqtt_service import MQTTService


class FakeMessage:
    """Stands in for ``aiomqtt.Message``; only topic and payload are read."""

    def __init__(self, topic: str, payload: Any) -> None:
        self.topic = topic
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()


class FakeClient:
    """Records publishes and the loop each one ran on."""

    def __init__(self, delay: float = 0.0) -> None:
        self.published: list[tuple[str, dict[str, Any], int]] = []
        self.loops: list[int] = []
        self._delay = delay

    async def publish(self, topic: str, payload: bytes, qos: int = 0) -> None:
        if self._delay:
            await asyncio.sleep(self._delay)
        self.loops.append(id(asyncio.get_running_loop()))
        self.published.append((topic, json.loads(payload), qos))


async def wait_until(
    predicate: Callable[[], bool],
    timeout: float = 3.0,
    reason: str = "condition",
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() > deadline:
            raise AssertionError(f"timed out waiting for {reason}")
        await asyncio.sleep(0.01)


def running_mqtt_loop() -> tuple[asyncio.AbstractEventLoop, threading.Thread]:
    """A second event loop on its own thread, standing in for the MQTT thread."""
    loop = asyncio.SelectorEventLoop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    return loop, thread


async def stop_loop(loop: asyncio.AbstractEventLoop, thread: threading.Thread) -> None:
    loop.call_soon_threadsafe(loop.stop)
    await asyncio.to_thread(thread.join, 5.0)
    loop.close()


async def test_status_handler_runs_on_the_main_loop() -> None:
    """The old code awaited handlers on the MQTT thread, so every WS send died."""
    service = MQTTService()
    main_loop = asyncio.get_running_loop()
    service._main_loop = main_loop

    seen: list[tuple[str, dict[str, Any], int]] = []

    async def handler(topic: str, payload: dict[str, Any]) -> None:
        seen.append((topic, payload, id(asyncio.get_running_loop())))

    service.on_status(handler)
    dispatcher = asyncio.create_task(service._dispatch_loop())
    try:
        await asyncio.to_thread(
            service._hand_off,
            FakeMessage("home/kamar/dev-km-1/status", {"state": "on", "timestamp": 1}),
        )
        await wait_until(lambda: bool(seen), reason="handler to run")

        topic, payload, loop_id = seen[0]
        assert topic == "home/kamar/dev-km-1/status"
        assert payload["state"] == "on"
        assert loop_id == id(main_loop)
    finally:
        dispatcher.cancel()


async def test_inbound_ordering_is_preserved() -> None:
    """One worker, not a task per message: `off` must never overtake `on`."""
    service = MQTTService()
    service._main_loop = asyncio.get_running_loop()

    order: list[str] = []

    async def handler(topic: str, payload: dict[str, Any]) -> None:
        if payload["state"] == "on":
            await asyncio.sleep(0.05)
        order.append(payload["state"])

    service.on_status(handler)
    dispatcher = asyncio.create_task(service._dispatch_loop())
    try:
        for state in ("on", "off"):
            await asyncio.to_thread(
                service._hand_off,
                FakeMessage("home/kamar/dev-km-1/status", {"state": state}),
            )
        await wait_until(lambda: len(order) == 2, reason="both messages")
        assert order == ["on", "off"]
    finally:
        dispatcher.cancel()


async def test_telemetry_and_unknown_topics_are_routed() -> None:
    service = MQTTService()
    service._main_loop = asyncio.get_running_loop()

    telemetry: list[str] = []
    status: list[str] = []

    async def on_telemetry(topic: str, payload: dict[str, Any]) -> None:
        telemetry.append(topic)

    async def on_status(topic: str, payload: dict[str, Any]) -> None:
        status.append(topic)

    service.on_telemetry(on_telemetry)
    service.on_status(on_status)
    dispatcher = asyncio.create_task(service._dispatch_loop())
    try:
        await asyncio.to_thread(
            service._hand_off,
            FakeMessage("home/kamar/dev-km-1/telemetry", {"temperature": 25.5}),
        )
        await asyncio.to_thread(service._hand_off, FakeMessage("home/kamar/dev-km-1/set", {}))
        await wait_until(lambda: bool(telemetry), reason="telemetry handler")
        await asyncio.sleep(0.05)

        assert telemetry == ["home/kamar/dev-km-1/telemetry"]
        assert status == []  # a `/set` echo is neither status nor telemetry
    finally:
        dispatcher.cancel()


async def test_invalid_payload_is_dropped_without_dispatch() -> None:
    service = MQTTService()
    service._main_loop = asyncio.get_running_loop()

    calls: list[str] = []

    async def handler(topic: str, payload: dict[str, Any]) -> None:
        calls.append(topic)

    service.on_status(handler)
    dispatcher = asyncio.create_task(service._dispatch_loop())
    try:
        await asyncio.to_thread(service._hand_off, FakeMessage("home/kamar/dev-1/status", b"{nope"))
        await asyncio.sleep(0.05)
        assert calls == []
        assert service._inbound.empty()
    finally:
        dispatcher.cancel()


async def test_saturated_queue_drops_instead_of_blocking() -> None:
    service = MQTTService()
    service._main_loop = asyncio.get_running_loop()
    service._inbound = asyncio.Queue(maxsize=1)

    service._enqueue_inbound("home/a/b/status", {"state": "on"})
    service._enqueue_inbound("home/a/b/status", {"state": "off"})  # must not raise

    assert service._inbound.qsize() == 1


async def test_a_failing_handler_does_not_stop_the_dispatcher() -> None:
    service = MQTTService()
    service._main_loop = asyncio.get_running_loop()

    received: list[str] = []

    async def broken(topic: str, payload: dict[str, Any]) -> None:
        raise RuntimeError("boom")

    async def fine(topic: str, payload: dict[str, Any]) -> None:
        received.append(topic)

    service.on_status(broken)
    service.on_status(fine)
    dispatcher = asyncio.create_task(service._dispatch_loop())
    try:
        await asyncio.to_thread(service._hand_off, FakeMessage("home/a/b/status", {"state": "on"}))
        await wait_until(lambda: bool(received), reason="second handler")
        assert not dispatcher.done()
    finally:
        dispatcher.cancel()


async def test_publish_runs_on_the_client_loop() -> None:
    """Awaiting the client from the main loop made aiomqtt's QoS-1 event cross loops."""
    service = MQTTService()
    client = FakeClient()
    service._client = client
    service._connected = True

    mqtt_loop, mqtt_thread = running_mqtt_loop()
    service._mqtt_loop = mqtt_loop
    main_loop = id(asyncio.get_running_loop())
    try:
        assert await service.publish_command("kamar", "dev-km-1", "on", {"brightness": 80}) is True

        topic, payload, qos = client.published[0]
        assert topic == "home/kamar/dev-km-1/set"
        assert payload["state"] == "on"
        assert payload["brightness"] == 80
        assert qos == 1
        assert client.loops == [id(mqtt_loop)]
        assert client.loops[0] != main_loop
    finally:
        await stop_loop(mqtt_loop, mqtt_thread)


async def test_publish_without_a_thread_loop_stays_local() -> None:
    """The non-Windows path has no second loop and must publish in place."""
    service = MQTTService()
    client = FakeClient()
    service._client = client
    service._connected = True

    assert await service.publish_raw("home/x/y/set", {"state": "off"}) is True
    assert client.loops == [id(asyncio.get_running_loop())]
    assert client.published[0][0] == "home/x/y/set"


async def test_publish_is_bounded_by_the_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stalled broker used to hang the request for aiomqtt's 10s default."""
    monkeypatch.setattr(settings, "MQTT_PUBLISH_TIMEOUT", 1)
    service = MQTTService()
    service._client = FakeClient(delay=30.0)
    service._connected = True

    mqtt_loop, mqtt_thread = running_mqtt_loop()
    service._mqtt_loop = mqtt_loop
    try:
        loop = asyncio.get_running_loop()
        started = loop.time()
        assert await service.publish_command("kamar", "dev-km-1", "on") is False
        elapsed = loop.time() - started
        assert elapsed < 3.0, f"publish took {elapsed:.2f}s, timeout not enforced"
    finally:
        await stop_loop(mqtt_loop, mqtt_thread)


async def test_publish_reports_disconnected_client() -> None:
    service = MQTTService()
    assert await service.publish_command("kamar", "dev-km-1", "on") is False


async def test_disconnect_stops_dispatcher_and_mqtt_thread() -> None:
    service = MQTTService()
    service._main_loop = asyncio.get_running_loop()

    mqtt_loop = asyncio.SelectorEventLoop()

    async def idle() -> None:
        """Stands in for `_connection_loop` so no broker is contacted."""
        await asyncio.sleep(30)

    def thread_body() -> None:
        asyncio.set_event_loop(mqtt_loop)
        try:
            service._mqtt_task = mqtt_loop.create_task(idle())
            mqtt_loop.run_until_complete(service._mqtt_task)
        except (RuntimeError, asyncio.CancelledError):
            pass
        finally:
            service._mqtt_task = None
            mqtt_loop.close()

    mqtt_thread = threading.Thread(target=thread_body, name="mqtt-test-loop", daemon=True)
    service._mqtt_loop = mqtt_loop
    service._mqtt_thread = mqtt_thread
    mqtt_thread.start()
    await wait_until(lambda: service._mqtt_task is not None, reason="connection task")

    service._dispatcher_task = asyncio.create_task(service._dispatch_loop())
    await service.disconnect()

    assert service._dispatcher_task is None
    assert service._mqtt_loop is None
    assert not mqtt_thread.is_alive()
    assert mqtt_loop.is_closed()
