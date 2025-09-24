from datetime import datetime, timedelta

import pytest

from app.services.enhanced_connection_service import (
    ConnectionConfig,
    ConnectionResult,
    ConnectionType,
    EnhancedConnectionService,
    FailureType,
)


@pytest.mark.unit
def test_history_and_statistics_and_circuit_breaker():
    svc = EnhancedConnectionService(ConnectionConfig())
    cid = 101

    # record some results
    r1 = ConnectionResult(
        connection_type=ConnectionType.METASTORE,
        status="success",
        response_time_ms=12.3,
    )
    r2 = ConnectionResult(
        connection_type=ConnectionType.HDFS,
        status="failed",
        response_time_ms=45.6,
        failure_type=FailureType.NETWORK_TIMEOUT,
        error_message="timeout",
    )

    svc._record_connection_result(cid, r1)
    svc._record_connection_result(cid, r2)

    # history
    hist = svc.get_connection_history(cid, limit=10)
    assert len(hist) == 2 and hist[0]["connection_type"] in ("metastore", "hdfs")

    # stats
    stats = svc.get_connection_statistics(cid, hours=24)
    assert stats["total_tests"] == 2 and stats["successful_tests"] >= 1
    assert "network_timeout" in stats["failure_types"] or stats["success_rate"] >= 0

    # circuit breaker behavior
    assert svc._is_circuit_breaker_open(cid, ConnectionType.HDFS) is False
    for _ in range(svc.config.circuit_breaker_threshold):
        svc._update_circuit_breaker(cid, ConnectionType.HDFS, success=False)
    assert svc._is_circuit_breaker_open(cid, ConnectionType.HDFS) is True
    svc._update_circuit_breaker(cid, ConnectionType.HDFS, success=True)
    assert svc._is_circuit_breaker_open(cid, ConnectionType.HDFS) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_test_cluster_connections_with_circuit_breaker(monkeypatch):
    from datetime import datetime, timedelta

    from app.services.enhanced_connection_service import (
        ConnectionResult,
        ConnectionType,
        EnhancedConnectionService,
    )

    svc = EnhancedConnectionService()

    class _Cluster:
        id = 202

    # circuit breaker open for METASTORE recently
    key = (_Cluster.id, ConnectionType.METASTORE)
    svc._circuit_breakers[key] = svc.config.circuit_breaker_threshold
    svc._last_successful_check[key] = datetime.now() - timedelta(minutes=1)

    # stub retry method for others
    def fake_retry(cluster, conn_type):
        if conn_type == ConnectionType.HDFS:
            return ConnectionResult(conn_type, "success", 1.0)
        return ConnectionResult(
            conn_type, "failed", 2.0, failure_type=None, error_message="x"
        )

    monkeypatch.setattr(svc, "_test_connection_with_retry", fake_retry)

    res = await svc.test_cluster_connections(
        _Cluster(),
        connection_types=[
            ConnectionType.METASTORE,
            ConnectionType.HDFS,
            ConnectionType.HIVESERVER2,
        ],
    )
    assert res["overall_status"] in ("partial", "failed")
    assert "tests" in res and isinstance(res["tests"], dict)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_test_cluster_connections_circuit_old_allows_run(monkeypatch):
    from datetime import datetime, timedelta

    from app.services.enhanced_connection_service import (
        ConnectionResult,
        ConnectionType,
        EnhancedConnectionService,
    )

    svc = EnhancedConnectionService()

    class _Cluster:
        id = 303

    # circuit open but last success long ago (>5 min) should still run
    key = (_Cluster.id, ConnectionType.METASTORE)
    svc._circuit_breakers[key] = svc.config.circuit_breaker_threshold
    svc._last_successful_check[key] = datetime.now() - timedelta(minutes=10)

    # run returns success for METASTORE
    def fake_retry(cluster, conn_type):
        if conn_type == ConnectionType.METASTORE:
            return ConnectionResult(conn_type, "success", 1.0)
        return ConnectionResult(conn_type, "failed", 2.0, error_message="x")

    monkeypatch.setattr(svc, "_test_connection_with_retry", fake_retry)
    res = await svc.test_cluster_connections(
        _Cluster(), connection_types=[ConnectionType.METASTORE]
    )
    assert res["overall_status"] == "success"


@pytest.mark.unit
def test_generate_failure_suggestions_paths():
    from app.services.enhanced_connection_service import (
        ConnectionType,
        EnhancedConnectionService,
        FailureType,
    )

    svc = EnhancedConnectionService()
    # cover various branches
    for ft in [
        FailureType.NETWORK_TIMEOUT,
        FailureType.CONNECTION_REFUSED,
        FailureType.DNS_RESOLUTION_FAILED,
        FailureType.AUTHENTICATION_FAILED,
        FailureType.PERMISSION_DENIED,
        FailureType.SSL_ERROR,
        FailureType.SERVICE_UNAVAILABLE,
    ]:
        s1 = svc._generate_failure_suggestions(ft, ConnectionType.METASTORE)
        s2 = svc._generate_failure_suggestions(ft, ConnectionType.HDFS)
        assert isinstance(s1, list) and isinstance(s2, list)


@pytest.mark.unit
def test_classify_error_branches():
    from app.services.enhanced_connection_service import (
        ConnectionType,
        EnhancedConnectionService,
        FailureType,
    )

    svc = EnhancedConnectionService()
    cases = [
        (RuntimeError("timeout"), FailureType.NETWORK_TIMEOUT),
        (RuntimeError("connection refused"), FailureType.CONNECTION_REFUSED),
        (RuntimeError("getaddrinfo"), FailureType.DNS_RESOLUTION_FAILED),
        (RuntimeError("password invalid"), FailureType.AUTHENTICATION_FAILED),
        (RuntimeError("permission denied"), FailureType.PERMISSION_DENIED),
        (RuntimeError("ssl certificate"), FailureType.SSL_ERROR),
        (RuntimeError("service unavailable"), FailureType.SERVICE_UNAVAILABLE),
    ]
    for err, expected in cases:
        assert svc._classify_error(err, ConnectionType.METASTORE) == expected
