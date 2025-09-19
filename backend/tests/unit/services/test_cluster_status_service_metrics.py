import pytest
from datetime import datetime, timedelta

from app.models.cluster import Cluster
from app.services.cluster_status_service import ClusterStatusService
from app.models.cluster_status_history import ClusterStatusHistory


def _mk(db, name, status="active", health="unknown"):
    c = Cluster(
        name=name,
        description="",
        hive_host="localhost",
        hive_port=10000,
        hive_metastore_url="mysql://user:pass@localhost:3306/hive",
        hdfs_namenode_url="hdfs://localhost:9000",
        status=status,
        health_status=health,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.mark.unit
def test_status_history_and_metrics(db_session):
    svc = ClusterStatusService()
    c1 = _mk(db_session, "c1", status="active", health="healthy")
    c2 = _mk(db_session, "c2", status="inactive", health="unhealthy")

    # 写入若干历史记录（只需确保最近有一条）
    svc.record_status_change(db_session, c1.id, new_status="maintenance", reason="manual", message="maint")
    svc.record_status_change(db_session, c1.id, new_status="active", reason="manual", message="back")

    hist = svc.get_cluster_status_history(db_session, c1.id, limit=10)
    assert len(hist) >= 2
    assert isinstance(hist[0], ClusterStatusHistory)

    # 获取健康指标统计
    stats = svc.get_cluster_health_metrics(db_session, days=7)
    assert "status_distribution" in stats and "health_distribution" in stats
    # 应至少包含我们创建的两个状态/健康状态
    assert stats["status_distribution"].get("active", 0) >= 1
    assert stats["status_distribution"].get("inactive", 0) >= 1
    assert stats["health_distribution"].get("healthy", 0) >= 1
    assert stats["health_distribution"].get("unhealthy", 0) >= 1
    assert stats["recent_status_changes"] >= 1

