import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_websocket_endpoint_invalid_json_then_disconnect(monkeypatch):
    import app.api.websocket as ws_api
    from fastapi import WebSocketDisconnect

    class _WS:
        def __init__(self):
            self.calls = 0

        async def receive_text(self):
            self.calls += 1
            if self.calls == 1:
                return "{invalid-json]"
            raise WebSocketDisconnect()

    sent = []
    subs = []

    async def fake_connect(ws, user_id):
        return True

    async def fake_subscribe(user_id, topics):
        subs.append(topics)

    async def fake_disconnect(ws):
        return None

    async def fake_send(ws, msg):
        sent.append(msg.to_dict())

    monkeypatch.setattr(ws_api, "websocket_manager", ws_api.websocket_manager)
    monkeypatch.setattr(ws_api.websocket_manager, "connect", fake_connect)
    monkeypatch.setattr(ws_api.websocket_manager, "subscribe", fake_subscribe)
    monkeypatch.setattr(ws_api.websocket_manager, "disconnect", fake_disconnect)
    monkeypatch.setattr(ws_api.websocket_manager, "_send_to_websocket", fake_send)

    ws = _WS()
    await ws_api.websocket_endpoint(ws, user_id="u1", topics="a,b")
    assert subs and subs[-1] == ["a", "b"]
    assert any(x.get("type") == "error" and x.get("data", {}).get("message") == "Invalid JSON format" for x in sent)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_websocket_endpoint_internal_error_then_disconnect(monkeypatch):
    import app.api.websocket as ws_api
    from fastapi import WebSocketDisconnect

    class _WS:
        def __init__(self):
            self.calls = 0

        async def receive_text(self):
            self.calls += 1
            if self.calls == 1:
                return "{}"  # valid JSON, will hit handle_client_message
            raise WebSocketDisconnect()

    sent = []

    async def fake_connect(ws, user_id):
        return True

    async def fake_disconnect(ws):
        return None

    async def fake_send(ws, msg):
        sent.append(msg.to_dict())

    async def boom(*a, **k):
        raise Exception("boom")

    monkeypatch.setattr(ws_api, "websocket_manager", ws_api.websocket_manager)
    monkeypatch.setattr(ws_api.websocket_manager, "connect", fake_connect)
    monkeypatch.setattr(ws_api.websocket_manager, "disconnect", fake_disconnect)
    monkeypatch.setattr(ws_api.websocket_manager, "_send_to_websocket", fake_send)
    monkeypatch.setattr(ws_api, "handle_client_message", boom)

    ws = _WS()
    await ws_api.websocket_endpoint(ws, user_id="u2", topics="")
    assert any(x.get("type") == "error" and x.get("data", {}).get("message") == "Internal server error" for x in sent)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_websocket_connect_rejected(monkeypatch):
    import app.api.websocket as ws_api

    class _WS:
        async def receive_text(self):
            return "{}"

    async def fake_connect(ws, user_id):
        return False  # refuse connection

    monkeypatch.setattr(ws_api, "websocket_manager", ws_api.websocket_manager)
    monkeypatch.setattr(ws_api.websocket_manager, "connect", fake_connect)

    ws = _WS()
    # Should return early without raising
    await ws_api.websocket_endpoint(ws, user_id="u3", topics="alpha")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_websocket_outer_exception(monkeypatch):
    import app.api.websocket as ws_api

    class _WS:
        async def receive_text(self):
            raise Exception("boom")

    async def fake_connect(ws, user_id):
        return True

    async def fake_disconnect(ws):
        return None

    monkeypatch.setattr(ws_api, "websocket_manager", ws_api.websocket_manager)
    monkeypatch.setattr(ws_api.websocket_manager, "connect", fake_connect)
    monkeypatch.setattr(ws_api.websocket_manager, "disconnect", fake_disconnect)

    ws = _WS()
    # Should hit outer exception handler and then disconnect
    await ws_api.websocket_endpoint(ws, user_id="u4", topics="")
