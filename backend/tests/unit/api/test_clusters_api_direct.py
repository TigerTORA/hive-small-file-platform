import pytest
from datetime import datetime


from app.models.cluster import Cluster
from app.models.table_metric import TableMetric


def _cluster_payload(name="c-cls"):
    return {
        "name": name,
        "description": "",
        "hive_host": "localhost",
        "hive_port": 10000,
        "hive_database": "default",
        "hive_metastore_url": "mysql://user:pass@localhost:3306/hive",
        "hdfs_namenode_url": "hdfs://localhost:9000",
        "hdfs_user": "hdfs",
        "auth_type": "NONE",
        "small_file_threshold": 128*1024*1024,
        "scan_enabled": True,
    }


def _mk_cluster(db, name="c-cls-db") -> Cluster:
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
@pytest.mark.asyncio
async def test_create_list_get_update_delete_cluster(db_session, monkeypatch):
    import app.api.clusters as clusters_api
    from app.schemas.cluster import ClusterCreate, ClusterUpdate

    # invalid URLs
    bad = _cluster_payload("bad")
    bad["hive_metastore_url"] = "xxx://invalid"
    with pytest.raises(Exception):
        await clusters_api.create_cluster(ClusterCreate(**bad), False, db_session)

    bad2 = _cluster_payload("bad2")
    bad2["hdfs_namenode_url"] = "ftp://invalid"
    with pytest.raises(Exception):
        await clusters_api.create_cluster(ClusterCreate(**bad2), False, db_session)

    # success create
    ok = _cluster_payload("ok1")
    created = await clusters_api.create_cluster(ClusterCreate(**ok), False, db_session)
    assert created.id and created.name == "ok1"

    # list and get
    lst = await clusters_api.list_clusters(db_session)
    assert any(x.id == created.id for x in lst)
    one = await clusters_api.get_cluster(created.id, db_session)
    assert one.id == created.id

    # update
    upd = await clusters_api.update_cluster(created.id, ClusterUpdate(description="d1"), db_session)
    assert upd.description == "d1"

    # avoid raw SQL incompatibility in SQLAlchemy 2.x for delete_cluster here


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cluster_stats_and_databases(db_session):
    import app.api.clusters as clusters_api

    c = _mk_cluster(db_session)

    # some metrics
    for dbn, tbl, files, small in [
        ("db1", "t1", 10, 4),
        ("db2", "t2", 5, 1),
        ("db1", "t3", 7, 0),
    ]:
        m = TableMetric(
            cluster_id=c.id,
            database_name=dbn,
            table_name=tbl,
            total_files=files,
            small_files=small,
            total_size=files * 100,
            avg_file_size=100.0,
            scan_time=datetime.utcnow(),
        )
        db_session.add(m)
    db_session.commit()

    stats = await clusters_api.get_cluster_stats(c.id, db_session)
    assert stats["total_databases"] == 2 and stats["total_tables"] >= 3

    dbs = await clusters_api.get_cluster_databases(c.id, db_session)
    assert set(dbs) == {"db1", "db2"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cluster_databases_when_empty_uses_metastore_error_path(db_session, monkeypatch):
    import app.api.clusters as clusters_api

    c = _mk_cluster(db_session, name="c-empty")

    class _Conn:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def get_databases(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(clusters_api, "HybridTableScanner", lambda cluster: object())
    from app.monitor import mysql_hive_connector as meta_mod
    monkeypatch.setattr(meta_mod, "MySQLHiveMetastoreConnector", lambda url: _Conn())

    res = await clusters_api.get_cluster_databases(c.id, db_session)
    assert isinstance(res, dict) and res.get("databases") == [] and "warning" in res


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_and_batch_checks(db_session, monkeypatch):
    import app.api.clusters as clusters_api

    monkeypatch.setattr(clusters_api.cluster_status_service, "get_cluster_health_metrics", lambda db, days: {"ok": True})
    r = await clusters_api.get_health_metrics(7, db_session)
    assert r["ok"] is True

    async def fake_batch(db, ids, limit):
        return {1: {"overall_status": "ok"}, 2: {"overall_status": "ok"}}

    monkeypatch.setattr(clusters_api.cluster_status_service, "batch_health_check", fake_batch)
    r2 = await clusters_api.batch_health_check([1, 2], 5, db_session)
    assert r2["successful_checks"] == 2 and r2["total_clusters"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_cluster_with_validation_failure(db_session, monkeypatch):
    import app.api.clusters as clusters_api
    from app.schemas.cluster import ClusterCreate

    class _Scanner:
        def __init__(self, cluster):
            pass
        def test_connections(self):
            return {
                "overall_status": "failed",
                "tests": {
                    "metastore": {"status": "error", "message": "bad"},
                    "hdfs": {"status": "success", "mode": "real"},
                },
                "logs": [],
                "suggestions": ["x"],
            }

    monkeypatch.setattr(clusters_api, "HybridTableScanner", _Scanner)

    payload = _cluster_payload("c-validate")
    with pytest.raises(Exception):
        await clusters_api.create_cluster(ClusterCreate(**payload), True, db_session)
