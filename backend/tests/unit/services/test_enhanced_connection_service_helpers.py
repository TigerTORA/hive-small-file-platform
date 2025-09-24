import math

import pytest

from app.services.enhanced_connection_service import (
    ConnectionResult,
    ConnectionType,
    EnhancedConnectionService,
    FailureType,
)


@pytest.mark.unit
def test_classify_error_various_types():
    svc = EnhancedConnectionService()
    c = ConnectionType.HDFS

    assert svc._classify_error(Exception("timed out"), c) == FailureType.NETWORK_TIMEOUT
    assert (
        svc._classify_error(Exception("connection refused"), c)
        == FailureType.CONNECTION_REFUSED
    )
    assert (
        svc._classify_error(Exception("getaddrinfo failed"), c)
        == FailureType.DNS_RESOLUTION_FAILED
    )
    assert (
        svc._classify_error(Exception("authentication failed"), c)
        == FailureType.AUTHENTICATION_FAILED
    )
    assert (
        svc._classify_error(Exception("permission denied"), c)
        == FailureType.PERMISSION_DENIED
    )
    assert svc._classify_error(Exception("ssl handshake"), c) == FailureType.SSL_ERROR
    assert (
        svc._classify_error(Exception("service unavailable"), c)
        == FailureType.SERVICE_UNAVAILABLE
    )
    assert (
        svc._classify_error(Exception("totally unknown"), c)
        == FailureType.UNKNOWN_ERROR
    )


@pytest.mark.unit
def test_generate_failure_suggestions_contains_generic_and_specific():
    svc = EnhancedConnectionService()
    # pick one combination and check representative suggestions
    sugg = svc._generate_failure_suggestions(
        FailureType.NETWORK_TIMEOUT, ConnectionType.METASTORE
    )
    assert any("检查网络连接" in s for s in sugg)
    assert any("Hive MetaStore" in s for s in sugg)


@pytest.mark.unit
def test_connection_statistics_empty_history():
    svc = EnhancedConnectionService()
    stats = svc.get_connection_statistics(cluster_id=1, hours=24)
    assert stats["total_tests"] == 0
    assert stats["success_rate"] == 0
    assert stats["average_response_time_ms"] == 0
    assert stats["failure_types"] == {}


@pytest.mark.unit
def test_record_history_and_statistics():
    svc = EnhancedConnectionService()
    cid = 42

    # two successes and one failure
    svc._record_connection_result(
        cid,
        ConnectionResult(
            connection_type=ConnectionType.METASTORE,
            status="success",
            response_time_ms=100,
        ),
    )
    svc._record_connection_result(
        cid,
        ConnectionResult(
            connection_type=ConnectionType.HDFS,
            status="success",
            response_time_ms=200,
        ),
    )
    svc._record_connection_result(
        cid,
        ConnectionResult(
            connection_type=ConnectionType.HIVESERVER2,
            status="failed",
            response_time_ms=50,
            failure_type=FailureType.CONNECTION_REFUSED,
            error_message="refused",
        ),
    )

    stats = svc.get_connection_statistics(cid, hours=48)
    assert stats["total_tests"] == 3
    assert stats["successful_tests"] == 2
    assert math.isclose(stats["success_rate"], round(2 / 3 * 100, 2))
    assert math.isclose(stats["average_response_time_ms"], round((100 + 200) / 2, 2))
    assert stats["failure_types"].get(FailureType.CONNECTION_REFUSED.value) == 1
    assert stats["period_hours"] == 48
