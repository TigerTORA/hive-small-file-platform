import pytest


@pytest.mark.unit
def test_ws_stats_endpoint(client):
    r = client.get("/api/v1/ws/stats")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) >= {
        "total_connections",
        "total_users",
        "topic_subscriptions",
        "avg_connections_per_user",
    }


@pytest.mark.unit
def test_ws_broadcast_endpoint(client):
    # 由于当前无活跃连接，调用应成功并返回 success
    r = client.post(
        "/api/v1/ws/broadcast",
        params={"topic": "alpha", "message_type": "ping"},
        json={"data": {"x": 1}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "success"
    assert "stats" in body
