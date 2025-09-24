import asyncio
import json
from typing import Dict

import pytest

from app.models.cluster import Cluster
from app.models.cluster_status_history import ClusterStatusHistory
from app.services.cluster_status_service import ClusterStatusService


def _make_cluster(db, name="c1") -> Cluster:
    c = Cluster(
        name=name,
        description="",
        hive_host="localhost",
        hive_port=10000,
        hive_metastore_url="mysql://user:pass@localhost:3306/hive",
        hdfs_namenode_url="hdfs://localhost:9000",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.mark.unit
def test_cache_and_get_cached_result_basic():
    svc = ClusterStatusService()
    # 未命中
    assert svc.get_connection_status_cached(1, "metastore") is None

    # 只有一个服务 -> _get_cached_cluster_test_result 应为 None
    svc.cache_connection_status(1, "metastore", "success", {"response_time_ms": 10})
    assert svc._get_cached_cluster_test_result(1) is None

    # 两个关键服务具备 -> 可构造整体缓存结果
    svc.cache_connection_status(1, "hdfs", "unknown", {"response_time_ms": 20})
    cached = svc._get_cached_cluster_test_result(1)
    assert cached and cached.get("cached") is True
    assert cached["tests"]["metastore"]["status"] == "success"
    assert cached["tests"]["hdfs"]["status"] == "unknown"
    # 存在 unknown，整体状态从 success 变为 partial
    assert cached["overall_status"] in ("partial", "success")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_cluster_connections_success_path(db_session, monkeypatch):
    svc = ClusterStatusService()
    c = _make_cluster(db_session, name="c-success")

    fake_result: Dict = {
        "overall_status": "partial",
        "tests": {
            "metastore": {"status": "success", "response_time_ms": 10},
            "hdfs": {
                "status": "failed",
                "response_time_ms": 20,
                "failure_type": "network_timeout",
            },
        },
        "logs": [],
        "suggestions": [],
    }

    async def fake_test_cluster_connections(self, cluster, conn_types=None):
        return fake_result

    # patch增强连接服务
    # 直接打到 cluster_status_service 模块中的引用
    monkeypatch.setattr(
        "app.services.cluster_status_service.enhanced_connection_service",
        type("X", (), {"test_cluster_connections": fake_test_cluster_connections})(),
        raising=False,
    )

    res = await svc.test_cluster_connections(db_session, c.id, force_refresh=True)
    assert res == fake_result

    # 缓存写入
    ms = svc.get_connection_status_cached(c.id, "metastore")
    hdfs = svc.get_connection_status_cached(c.id, "hdfs")
    assert ms and ms["status"] == "success"
    assert hdfs and hdfs["status"] == "failed"

    # 健康状态映射 partial -> degraded
    db_session.refresh(c)
    assert c.health_status == "degraded"
    assert c.last_health_check is not None

    # 产生一条状态变更历史（unknown -> degraded）
    histories = (
        db_session.query(ClusterStatusHistory)
        .filter(ClusterStatusHistory.cluster_id == c.id)
        .all()
    )
    assert len(histories) >= 1
    assert "degraded" in (histories[-1].message or "")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_cluster_connections_error_path(db_session, monkeypatch):
    svc = ClusterStatusService()
    c = _make_cluster(db_session, name="c-error")

    async def fake_raise(self, *args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "app.services.cluster_status_service.enhanced_connection_service",
        type("X", (), {"test_cluster_connections": fake_raise})(),
        raising=False,
    )

    res = await svc.test_cluster_connections(db_session, c.id, force_refresh=True)
    assert res["overall_status"] == "failed"
    assert "boom" in res["error"]

    # 三个服务均缓存为 error
    for s in ("metastore", "hdfs", "hiveserver2"):
        cached = svc.get_connection_status_cached(c.id, s)
        assert cached and cached["status"] == "error"

    db_session.refresh(c)
    assert c.health_status == "unhealthy"


@pytest.mark.unit
def test_get_cluster_connection_summary(db_session):
    svc = ClusterStatusService()
    c = _make_cluster(db_session, name="c-summary")

    # 预置缓存，仅 metastore/hdfs
    svc.cache_connection_status(c.id, "metastore", "success", {})
    svc.cache_connection_status(c.id, "hdfs", "failed", {})

    summary = svc.get_cluster_connection_summary(db_session, c.id)
    assert summary["cluster_id"] == c.id
    assert summary["cluster_name"] == c.name
    assert summary["connections"]["metastore"]["cached"] is True
    assert summary["connections"]["hdfs"]["cached"] is True
    # 未缓存的 hiveserver2 -> unknown/cached=False
    assert summary["connections"]["hiveserver2"]["cached"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_health_check_mixed_results(db_session, monkeypatch):
    svc = ClusterStatusService()
    c1 = _make_cluster(db_session, name="c1")
    c2 = _make_cluster(db_session, name="c2")

    async def fake_self_test(db, cluster_id, *_, **__):
        if cluster_id == c1.id:
            return {"overall_status": "success", "tests": {}}
        raise RuntimeError("err2")

    # 打补丁到实例方法以避免真实调用
    monkeypatch.setattr(svc, "test_cluster_connections", fake_self_test)

    result = await svc.batch_health_check(db_session, [c1.id, c2.id], parallel_limit=2)
    assert result[c1.id]["overall_status"] == "success"
    assert result[c2.id]["overall_status"] == "error"
