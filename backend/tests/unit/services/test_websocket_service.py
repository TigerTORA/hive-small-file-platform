import asyncio
import json
from typing import List, Tuple

import pytest

from app.services.websocket_service import (
    WebSocketManager,
    WebSocketMessage,
    RealTimeNotificationService,
)


class FakeWebSocket:
    """A minimal async-compatible fake WebSocket for unit tests."""

    def __init__(self, name: str = "ws", raise_on_send: bool = False):
        self.name = name
        self.accepted = False
        self.raise_on_send = raise_on_send
        self.sent_texts: List[str] = []

    async def accept(self):
        self.accepted = True

    async def send_text(self, text: str):
        if self.raise_on_send:
            raise RuntimeError(f"send failure on {self.name}")
        self.sent_texts.append(text)

    def last_payload(self):
        return json.loads(self.sent_texts[-1]) if self.sent_texts else None


@pytest.mark.unit
def test_message_to_dict_has_timestamp():
    m = WebSocketMessage(type="test", data={"x": 1})
    d = m.to_dict()
    assert d["type"] == "test"
    assert d["data"] == {"x": 1}
    assert isinstance(d.get("timestamp"), str) and len(d["timestamp"]) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_and_disconnect_flow():
    mgr = WebSocketManager()
    ws = FakeWebSocket("u1-ws")

    ok = await mgr.connect(ws, user_id="u1")
    assert ok is True
    assert ws.accepted is True
    assert "u1" in mgr.active_connections
    assert ws in mgr.active_connections["u1"]
    assert mgr.connection_metadata.get(ws, {}).get("user_id") == "u1"

    # connect sends an initial connection_established message
    payload = ws.last_payload()
    assert payload and payload["type"] == "connection_established"

    await mgr.disconnect(ws)
    assert "u1" not in mgr.active_connections
    assert "u1" not in mgr.subscriptions
    assert ws not in mgr.connection_metadata


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscribe_unsubscribe_and_stats():
    mgr = WebSocketManager()
    ws1, ws2 = FakeWebSocket("u1-ws"), FakeWebSocket("u2-ws")

    await mgr.connect(ws1, user_id="u1")
    await mgr.connect(ws2, user_id="u2")

    await mgr.subscribe("u1", ["t1", "t2"])  # u1 -> t1, t2
    await mgr.subscribe("u2", ["t2"])          # u2 -> t2

    stats = mgr.get_connection_stats()
    assert stats["total_connections"] == 2
    assert stats["total_users"] == 2
    assert stats["topic_subscriptions"]["t2"] == 2
    # avg is computed as total_connections / max(total_users, 1)
    assert stats["avg_connections_per_user"] == 1.0

    # Unsubscribe u1 from t1; it should disappear from topic stats
    await mgr.unsubscribe("u1", ["t1"])
    stats2 = mgr.get_connection_stats()
    assert "t1" not in stats2["topic_subscriptions"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_broadcast_to_topic_sends_only_to_subscribers_and_disconnects_on_error():
    mgr = WebSocketManager()
    ok1, ok2 = FakeWebSocket("u1-ok"), FakeWebSocket("u2-ok")
    bad = FakeWebSocket("u3-bad", raise_on_send=True)

    await mgr.connect(ok1, user_id="u1")
    await mgr.connect(ok2, user_id="u2")
    await mgr.connect(bad, user_id="u3")

    await mgr.subscribe("u1", ["alpha"])  # subscribed
    await mgr.subscribe("u2", ["beta"])   # not subscribed to alpha
    await mgr.subscribe("u3", ["alpha"])  # subscribed but will raise on send

    msg = WebSocketMessage(type="foo", data={"hello": 123})
    await mgr.broadcast_to_topic("alpha", msg)

    # ok1 should receive the broadcast (plus the initial connect message)
    assert len(ok1.sent_texts) >= 2
    assert ok1.last_payload()["type"] == "foo"

    # ok2 subscribed to beta only; its last payload should still be connection_established
    assert ok2.last_payload()["type"] == "connection_established"

    # bad socket should have been disconnected after failure
    assert "u3" not in mgr.active_connections or bad not in mgr.active_connections.get("u3", set())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_to_user_success_and_missing_user():
    mgr = WebSocketManager()
    ws1, ws2 = FakeWebSocket("u1-1"), FakeWebSocket("u1-2")

    await mgr.connect(ws1, user_id="u1")
    await mgr.connect(ws2, user_id="u1")

    msg = WebSocketMessage(type="bar", data={"v": 1})
    ok = await mgr.send_to_user("u1", msg)
    assert ok is True
    # both u1 sockets should have received the message (in addition to connection messages)
    assert any(json.loads(t)["type"] == "bar" for t in ws1.sent_texts)
    assert any(json.loads(t)["type"] == "bar" for t in ws2.sent_texts)

    # non-existent user
    ok_missing = await mgr.send_to_user("uX", msg)
    assert ok_missing is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_to_user_partial_failure_still_true_and_disconnects_bad_ws():
    mgr = WebSocketManager()
    good = FakeWebSocket("good")
    bad = FakeWebSocket("bad", raise_on_send=True)
    await mgr.connect(good, user_id="u1")
    await mgr.connect(bad, user_id="u1")

    msg = WebSocketMessage(type="ping", data={})
    ok = await mgr.send_to_user("u1", msg)
    # at least one succeeded -> True
    assert ok is True
    # bad should be disconnected
    assert bad not in mgr.active_connections.get("u1", set())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_realtime_notification_service_topics_and_types(monkeypatch):
    mgr = WebSocketManager()
    svc = RealTimeNotificationService(mgr)

    calls: List[Tuple[str, WebSocketMessage]] = []

    async def fake_broadcast(topic: str, message: WebSocketMessage):
        calls.append((topic, message))

    monkeypatch.setattr(mgr, "broadcast_to_topic", fake_broadcast)

    # trigger each notification path
    await svc.notify_connection_status_changed(1, "c1", {"overall_status": "success", "tests": {}, "suggestions": []})
    await svc.notify_health_check_completed(1, "healthy", {"d": 1})
    await svc.notify_scan_progress(1, 99, 0.5, current_table="db.tbl")
    await svc.notify_task_status_changed(77, "merge", "running", progress=0.1)
    await svc.notify_cluster_stats_updated(1, {"x": 2})

    topics = [t for t, _ in calls]
    types = [m.type for _, m in calls]

    # verify topics routing
    assert topics == [
        "cluster_status",  # connection_status
        "health_check",    # health_update
        "scan_progress",   # scan_progress
        "task_updates",    # task_update
        "cluster_status",  # cluster_stats
    ]

    # verify message types
    assert types == [
        "connection_status",
        "health_update",
        "scan_progress",
        "task_update",
        "cluster_stats",
    ]

