from datetime import datetime
from types import SimpleNamespace

import pytest

from app.models.cluster import Cluster
from app.models.table_metric import TableMetric


def _mk_cluster(db, name="c-tables") -> Cluster:
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


def _mk_metric(db, cluster_id: int, dbn: str, tbl: str, files: int, when: datetime):
    m = TableMetric(
        cluster_id=cluster_id,
        database_name=dbn,
        table_name=tbl,
        total_files=files,
        small_files=max(0, files // 2),
        total_size=files * 1024,
        avg_file_size=(files * 1024) / max(files, 1),
        scan_time=when,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tables_metrics_and_small_files(db_session, monkeypatch):
    import app.api.tables as tables_mod

    c = _mk_cluster(db_session)
    now = datetime.now()
    _mk_metric(db_session, c.id, "db1", "t1", 10, now)
    _mk_metric(db_session, c.id, "db1", "t2", 20, now)

    metrics = await tables_mod.get_table_metrics(
        cluster_id=c.id, database_name=None, db=db_session
    )
    assert isinstance(metrics, list) and len(metrics) == 2

    summary = await tables_mod.get_small_file_summary(cluster_id=c.id, db=db_session)
    assert summary["total_tables"] >= 2
    assert summary["total_files"] >= 30
    assert summary["total_small_files"] >= 15
    assert isinstance(summary["avg_file_size"], float)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tables_list_databases_and_tables(db_session, monkeypatch):
    import app.api.tables as tables_mod

    c = _mk_cluster(db_session)

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get_databases(self):
            return ["db1", "db2"]

        def get_tables(self, database_name):
            return [{"table_name": "t1", "table_path": "/wh/db1/t1"}]

    monkeypatch.setattr(tables_mod, "MySQLHiveMetastoreConnector", lambda url: _Conn())

    resp = await tables_mod.get_databases(c.id, db_session)
    assert resp["databases"] == ["db1", "db2"]

    resp2 = await tables_mod.get_tables(c.id, "db1", db_session)
    assert resp2["database"] == "db1" and len(resp2["tables"]) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tables_partition_metrics_with_stub_scanner(db_session, monkeypatch):
    import app.api.tables as tables_mod

    c = _mk_cluster(db_session)

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get_table_partitions_count(self, dbn, tbl):
            return 2

        def get_table_partitions_paged(self, dbn, tbl, offset, page_size):
            return [
                {
                    "partition_name": "dt=2024-01-01",
                    "partition_path": "/wh/db1/t1/dt=2024-01-01",
                },
                {
                    "partition_name": "dt=2024-01-02",
                    "partition_path": "/wh/db1/t1/dt=2024-01-02",
                },
            ]

    class _Web:
        def __init__(self, *a, **k):
            pass

        def scan_directory_stats(self, path, small_file_threshold):
            return SimpleNamespace(
                total_files=10,
                small_files_count=5,
                total_size=1024,
                average_file_size=100.0,
            )

        def close(self):
            pass

    monkeypatch.setattr(tables_mod, "MySQLHiveMetastoreConnector", lambda url: _Conn())
    monkeypatch.setattr(tables_mod, "WebHDFSClient", _Web)

    resp = await tables_mod.get_partition_metrics(
        cluster_id=c.id,
        database_name="db1",
        table_name="t1",
        page=1,
        page_size=10,
        concurrency=2,
        db=db_session,
    )
    assert resp["total"] == 2 and len(resp["items"]) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tables_archive_endpoints_stubbed(db_session, monkeypatch):
    import app.api.tables as tables_mod

    c = _mk_cluster(db_session)

    class _Arc:
        def __init__(self, cluster, root="/archive"):
            pass

        def archive_table(self, db, dn, tn, force):
            return {"archived": True}

        def restore_table(self, db, dn, tn):
            return {"restored": True}

        def get_archive_status(self, db, dn, tn):
            return {"status": "archived"}

        def list_archived_tables(self, db, limit):
            return {"items": []}

        def get_archive_statistics(self, db):
            return {"tables": 0}

    monkeypatch.setattr(tables_mod, "SimpleArchiveEngine", _Arc)

    r1 = await tables_mod.archive_table(
        c.id, "db1", "t1", False, "/archive", db_session
    )
    assert r1["archive_result"]["archived"] is True
    r2 = await tables_mod.restore_table(c.id, "db1", "t1", db_session)
    assert r2["restore_result"]["restored"] is True
    r3 = await tables_mod.get_archive_status(c.id, "db1", "t1", db_session)
    assert r3["table_status"]["status"] == "archived"
    r4 = await tables_mod.list_archived_tables(c.id, 10, db_session)
    assert r4["items"] == []
    r5 = await tables_mod.get_archive_statistics(c.id, db_session)
    assert r5["tables"] == 0
