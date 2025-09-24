import pytest


def _mk_cluster(db, name="c-more"):
    from app.models.cluster import Cluster

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
async def test_cluster_status_and_history_and_cache(db_session, monkeypatch):
    import app.api.clusters as clusters_api

    c = _mk_cluster(db_session)

    monkeypatch.setattr(
        clusters_api.cluster_status_service,
        "get_cluster_connection_summary",
        lambda db, cid: {"ok": True},
    )
    s = await clusters_api.get_cluster_status(c.id, db_session)
    assert s["ok"] is True

    class _Rec:
        id = 1
        from_status = "active"
        to_status = "active"
        reason = "r"
        message = "m"
        connection_test_result = {}

        class _D:
            def isoformat(self):
                return "t"

        created_at = _D()

    monkeypatch.setattr(
        clusters_api.cluster_status_service,
        "get_cluster_status_history",
        lambda db, cid, limit: [_Rec()],
    )
    h = await clusters_api.get_cluster_status_history(c.id, 5, db_session)
    assert h["total_records"] == 1 and h["cluster_id"] == c.id

    # clear cache
    called = {"clr": False}

    def fake_clear(cid):
        called["clr"] = True

    monkeypatch.setattr(
        clusters_api.cluster_status_service, "clear_connection_cache", fake_clear
    )
    cc = await clusters_api.clear_cluster_cache(c.id, db_session)
    assert called["clr"] is True and "cleared" in cc["message"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connection_history_and_statistics(db_session, monkeypatch):
    import app.api.clusters as clusters_api

    c = _mk_cluster(db_session)

    monkeypatch.setattr(
        clusters_api.enhanced_connection_service,
        "get_connection_history",
        lambda cid, limit: [{"status": "ok"}],
    )
    rh = await clusters_api.get_connection_history(c.id, 10, db_session)
    assert rh["total_records"] == 1

    monkeypatch.setattr(
        clusters_api.enhanced_connection_service,
        "get_connection_statistics",
        lambda cid, hours: {"success_rate": 1.0},
    )
    rs = await clusters_api.get_connection_statistics(c.id, 24, db_session)
    assert rs["success_rate"] == 1.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connection_tests(db_session, monkeypatch):
    import app.api.clusters as clusters_api

    c = _mk_cluster(db_session)

    # invalid types
    with pytest.raises(Exception):
        await clusters_api.test_cluster_connection_enhanced(
            c.id, ["bad"], False, db_session
        )

    # enhanced ok
    async def fake_test(db, cid, force_refresh, types=None):
        return {"overall_status": "ok", "tests": {}}

    monkeypatch.setattr(
        clusters_api.cluster_status_service, "test_cluster_connections", fake_test
    )
    eok = await clusters_api.test_cluster_connection_enhanced(
        c.id, ["metastore"], True, db_session
    )
    assert eok["test_mode"] == "enhanced" and eok["force_refresh"] is True

    # real mode
    rok = await clusters_api.test_cluster_connection(
        c.id, mode="real", force_refresh=False, db=db_session
    )
    assert rok["test_mode"] == "real" and "tests" in rok

    # mock mode
    class _Scanner:
        def __init__(self, cluster):
            pass

        def test_connections(self):
            return {
                "overall_status": "success",
                "tests": {
                    "metastore": {"status": "success"},
                    "hdfs": {"status": "success"},
                },
            }

    monkeypatch.setattr(clusters_api, "HybridTableScanner", _Scanner)
    mok = await clusters_api.test_cluster_connection(
        c.id, mode="mock", force_refresh=False, db=db_session
    )
    assert mok["overall_status"] in ("success", "failed") and "connections" in mok


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_cluster_status(db_session, monkeypatch):
    import app.api.clusters as clusters_api

    c = _mk_cluster(db_session)

    class _Rec:
        from_status = "active"
        to_status = "inactive"
        reason = "manual"
        message = "m"

        class _D:
            def isoformat(self):
                return "t"

        created_at = _D()

    monkeypatch.setattr(
        clusters_api.cluster_status_service,
        "record_status_change",
        lambda db, cid, new_status, reason, message: _Rec(),
    )
    r = await clusters_api.update_cluster_status(
        c.id, new_status="inactive", db=db_session
    )
    assert r["new_status"] == "inactive" and r["old_status"] == "active"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_all_cluster_tables_simple(db_session, monkeypatch):
    import app.api.clusters as clusters_api

    c = _mk_cluster(db_session)

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get_databases(self):
            return ["db1"]

    class _Scanner:
        def __init__(self, cluster):
            pass

        def scan_database_tables(self, db, db_name, table_filter=None, max_tables=None):
            return {
                "status": "completed",
                "tables_scanned": 1,
                "total_files": 10,
                "total_small_files": 2,
                "scan_duration": 0.1,
            }

    monkeypatch.setattr(clusters_api, "HybridTableScanner", _Scanner)
    from app.monitor import mysql_hive_connector as meta_mod

    monkeypatch.setattr(meta_mod, "MySQLHiveMetastoreConnector", lambda url: _Conn())

    res = await clusters_api.scan_all_cluster_tables(
        c.id, max_tables_per_db=2, db=db_session
    )
    assert res["cluster_id"] == c.id and "databases" in res
