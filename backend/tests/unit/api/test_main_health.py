import pytest


@pytest.mark.unit
def test_root_and_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json().get("message")

    h = client.get("/health")
    assert h.status_code == 200
    body = h.json()
    assert body.get("status") == "healthy"
    assert "server_config" in body

