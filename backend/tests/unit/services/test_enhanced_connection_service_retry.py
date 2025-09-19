import pytest


@pytest.mark.unit
def test_retry_timeout_and_unsupported(monkeypatch):
    from app.services.enhanced_connection_service import EnhancedConnectionService, ConnectionConfig, ConnectionType, FailureType, FutureTimeoutError

    cfg = ConnectionConfig(timeout_seconds=0.01, max_retries=1, retry_delay=0)
    svc = EnhancedConnectionService(cfg)

    class _Fut:
        def __init__(self, exc):
            self._exc = exc
        def result(self, timeout=None):
            raise self._exc

    # timeout path
    monkeypatch.setattr(svc.executor, "submit", lambda func, cluster: _Fut(FutureTimeoutError()))
    r = svc._test_connection_with_retry(object(), ConnectionType.METASTORE)
    assert r.status == "timeout" and r.failure_type == FailureType.NETWORK_TIMEOUT

    # unsupported type path -> failed
    r2 = svc._test_connection_with_retry(object(), "bad_type")  # type: ignore
    assert r2.status == "failed"


@pytest.mark.unit
def test_retry_then_success(monkeypatch):
    from app.services.enhanced_connection_service import EnhancedConnectionService, ConnectionConfig, ConnectionType, ConnectionResult

    cfg = ConnectionConfig(timeout_seconds=0.1, max_retries=1, retry_delay=0)
    svc = EnhancedConnectionService(cfg)

    seq = [
        ConnectionResult(ConnectionType.HDFS, "failed", 1.0, error_message="e"),
        ConnectionResult(ConnectionType.HDFS, "success", 2.0),
    ]

    class _Fut:
        def __init__(self, res):
            self._res = res
        def result(self, timeout=None):
            return self._res

    def fake_submit(func, cluster):
        return _Fut(seq.pop(0))

    monkeypatch.setattr(svc.executor, "submit", fake_submit)
    res = svc._test_connection_with_retry(object(), ConnectionType.HDFS)
    assert res.status == "success" and res.attempt_count >= 1
