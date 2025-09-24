import pytest


@pytest.mark.unit
def test_test_error_endpoint(client, monkeypatch):
    # 屏蔽向 sentry 发送
    import app.api.errors as errors_mod

    monkeypatch.setattr(
        errors_mod,
        "sentry_sdk",
        type("S", (), {"capture_exception": lambda *_: None})(),
    )

    r = client.get("/api/v1/errors/test-error")
    assert r.status_code == 500
    assert r.json()["detail"].startswith("Test error captured by Sentry")


@pytest.mark.unit
def test_test_manual_error_endpoint(client, monkeypatch):
    import app.api.errors as errors_mod

    monkeypatch.setattr(
        errors_mod,
        "sentry_sdk",
        type("S", (), {"capture_message": (lambda *a, **kw: None)})(),
    )

    r = client.get("/api/v1/errors/test-manual-error")
    assert r.status_code == 200
    assert r.json()["message"].startswith("Manual error message")
