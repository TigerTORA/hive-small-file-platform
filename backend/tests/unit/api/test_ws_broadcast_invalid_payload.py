import pytest


@pytest.mark.unit
def test_ws_broadcast_invalid_body_returns_422(client):
    # data 参数需要是 JSON 对象(dict)，传入列表将导致 422
    r = client.post(
        "/api/v1/ws/broadcast",
        params={"topic": "alpha", "message_type": "ping"},
        json=[1, 2, 3],
    )
    assert r.status_code == 422


@pytest.mark.unit
def test_ws_broadcast_empty_topic(client):
    # 空 topic 仍会进入代码，但语义上应可接受并返回 success（当前实现不校验）
    r = client.post(
        "/api/v1/ws/broadcast",
        params={"topic": "", "message_type": "ping"},
        json={"data": {"x": 1}},
    )
    assert r.status_code == 200
    assert r.json().get("status") == "success"
