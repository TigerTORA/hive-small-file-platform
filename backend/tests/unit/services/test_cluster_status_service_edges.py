from datetime import datetime, timedelta

import pytest

from app.models.cluster import Cluster
from app.services.cluster_status_service import ClusterStatusService


def _mk_cluster(db, name="c-edge") -> Cluster:
    c = Cluster(
        name=name,
        description="",
        hive_host="localhost",
        hive_port=10000,
        hive_metastore_url="mysql://user:pass@localhost:3306/hive",
        hdfs_namenode_url="hdfs://localhost:9000",
    )
    db.add(c); db.commit(); db.refresh(c)
    return c


@pytest.mark.unit
def test_record_status_change_invalid_cluster_raises(db_session):
    svc = ClusterStatusService()
    with pytest.raises(ValueError):
        svc.record_status_change(db_session, 9999, new_status="active")


@pytest.mark.unit
def test_update_health_status_invalid_cluster_false(db_session):
    svc = ClusterStatusService()
    assert svc.update_health_status(db_session, 9999, "healthy") is False


@pytest.mark.unit
def test_connection_cache_put_get_and_expire(db_session):
    svc = ClusterStatusService()
    c = _mk_cluster(db_session)
    svc.cache_connection_status(c.id, "metastore", "success", {"ok": 1})
    cached = svc.get_connection_status_cached(c.id, "metastore")
    assert cached and cached["status"] == "success"

    # 过期：将时间回拨
    svc._connection_cache[c.id]["metastore"]["timestamp"] = datetime.now() - timedelta(seconds=999)
    svc._cache_ttl = 1
    assert svc.get_connection_status_cached(c.id, "metastore") is None


@pytest.mark.unit
def test_get_cluster_connection_summary_invalid_cluster_raises(db_session):
    svc = ClusterStatusService()
    with pytest.raises(ValueError):
        svc.get_cluster_connection_summary(db_session, 9999)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_cluster_connections_invalid_cluster_raises(db_session):
    svc = ClusterStatusService()
    with pytest.raises(ValueError):
        await svc.test_cluster_connections(db_session, 9999)

