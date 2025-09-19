import pytest
from unittest.mock import patch, MagicMock

from app.api.websocket import handle_client_message


class DummyWS:
    """不直接使用 websocket_manager._send_to_websocket 的底层，实现仅作为占位。"""
    pass


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_subscribe_unsubscribe_and_ping(monkeypatch):
    sent = []

    async def fake_send(_ws, message):
        sent.append(message)

    with patch("app.api.websocket.websocket_manager.subscribe") as sub, \
         patch("app.api.websocket.websocket_manager.unsubscribe") as unsub, \
         patch("app.api.websocket.websocket_manager._send_to_websocket", side_effect=fake_send):
        ws = DummyWS()

        # subscribe
        await handle_client_message(ws, "u1", {"type": "subscribe", "data": {"topics": ["a", "b"]}})
        assert sub.called
        assert sent[-1].type == "subscription_confirmed"

        # unsubscribe
        await handle_client_message(ws, "u1", {"type": "unsubscribe", "data": {"topics": ["a"]}})
        assert unsub.called
        assert sent[-1].type == "unsubscription_confirmed"

        # ping
        await handle_client_message(ws, "u1", {"type": "ping", "data": {"timestamp": 123}})
        assert sent[-1].type == "pong"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_get_status_and_unknown():
    sent = []

    async def fake_send(_ws, message):
        sent.append(message)

    with patch("app.api.websocket.websocket_manager.get_connection_stats", return_value={"ok": 1}), \
         patch("app.api.websocket.websocket_manager._send_to_websocket", side_effect=fake_send):
        ws = DummyWS()

        # get_status
        await handle_client_message(ws, "u1", {"type": "get_status", "data": {}})
        assert sent[-1].type == "status_response"
        assert sent[-1].data == {"ok": 1}

        # unknown type
        await handle_client_message(ws, "u1", {"type": "xxx", "data": {}})
        assert sent[-1].type == "error"
