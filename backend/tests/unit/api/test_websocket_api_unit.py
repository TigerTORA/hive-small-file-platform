import asyncio
import json

import pytest

from app.api import websocket as ws_api
from app.services.websocket_service import WebSocketManager, WebSocketMessage


class DummyWS:
    pass


@pytest.fixture()
def patched_manager(monkeypatch):
    mgr = WebSocketManager()
    # replace the manager used inside api.websocket
    monkeypatch.setattr(ws_api, "websocket_manager", mgr)
    return mgr


@pytest.fixture()
def capture_send(monkeypatch):
    calls = []

    async def fake_send(_ws, message: WebSocketMessage):
        calls.append(message.to_dict())

    monkeypatch.setattr(ws_api.websocket_manager, "_send_to_websocket", fake_send)
    return calls


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_subscribe_unsubscribe(patched_manager, capture_send):
    ws = DummyWS()
    await ws_api.handle_client_message(
        ws, "u1", {"type": "subscribe", "data": {"topics": ["a", "b"]}}
    )
    assert capture_send[-1]["type"] == "subscription_confirmed"
    assert set(capture_send[-1]["data"]["topics"]) == {"a", "b"}

    await ws_api.handle_client_message(
        ws, "u1", {"type": "unsubscribe", "data": {"topics": ["a"]}}
    )
    assert capture_send[-1]["type"] == "unsubscription_confirmed"
    assert capture_send[-1]["data"]["topics"] == ["a"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_ping_and_get_status(patched_manager, capture_send):
    ws = DummyWS()
    await ws_api.handle_client_message(
        ws, "u1", {"type": "ping", "data": {"timestamp": "t"}}
    )
    assert capture_send[-1]["type"] == "pong"
    assert capture_send[-1]["data"]["timestamp"] == "t"

    await ws_api.handle_client_message(ws, "u1", {"type": "get_status", "data": {}})
    assert capture_send[-1]["type"] == "status_response"
    assert set(capture_send[-1]["data"].keys()) >= {
        "total_connections",
        "total_users",
        "topic_subscriptions",
        "avg_connections_per_user",
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_unknown_message_type(patched_manager, capture_send):
    ws = DummyWS()
    await ws_api.handle_client_message(ws, "u1", {"type": "unknown_type", "data": {}})
    assert capture_send[-1]["type"] == "error"
    assert "Unknown message type" in capture_send[-1]["data"]["message"]
