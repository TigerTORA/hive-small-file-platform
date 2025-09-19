import pytest
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.models.scan_task import ScanTask as ScanTaskModel
from app.models.scan_task_log import ScanTaskLogDB


def _mk_cluster(db, name="c-tables2") -> Cluster:
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


def _mk_metric(db, cluster_id: int, dbn: str, tbl: str, total_files: int, small_files: int, total_size: int, avg_file_size: float, scan_time: datetime, is_cold=0, days=0):
    m = TableMetric(
        cluster_id=cluster_id,
        database_name=dbn,
        table_name=tbl,
        total_files=total_files,
        small_files=small_files,
        total_size=total_size,
        avg_file_size=avg_file_size,
        is_partitioned=0,
        partition_count=0,
        table_path=f"/wh/{dbn}/{tbl}",
        scan_time=scan_time,
        is_cold_data=is_cold,
        days_since_last_access=days,
        last_access_time=scan_time - timedelta(days=days) if is_cold else None,
    )
    db.add(m); db.commit(); db.refresh(m)
    return m


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_small_file_ratios(db_session):
    import app.api.tables as tables_mod
    import app.engines.safe_hive_engine as safe_eng_mod
    c = _mk_cluster(db_session)
    now = datetime.now()
    _mk_metric(db_session, c.id, "db1", "t1", 100, 90, 1000, 10, now)
    _mk_metric(db_session, c.id, "db1", "t2", 50, 10, 500, 10, now)
    res = await tables_mod.analyze_small_file_ratios(c.id, db_session)
    assert res["summary"]["total_tables"] >= 2
    assert isinstance(res["recommendations"], list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_table_partitions_and_stats(db_session, monkeypatch):
    import app.api.tables as tables_mod
    import app.engines.safe_hive_engine as safe_eng_mod
    c = _mk_cluster(db_session)

    class _Eng:
        def __init__(self, cluster):
            pass
        def _table_exists(self, dbn, tbl):
            return True
        def _is_partitioned_table(self, dbn, tbl):
            return True
        def _get_table_partitions(self, dbn, tbl):
            return ["year=2024/month=01", "year=2024/month=02"]
        def _get_file_count(self, dbn, tbl, part=None):
            return 120

    monkeypatch.setattr(safe_eng_mod, "SafeHiveMergeEngine", _Eng)
    parts = await tables_mod.get_table_partitions(c.id, "db1", "t1", db_session)
    assert parts["is_partitioned"] is True and parts["partition_count"] == 2

    stats1 = await tables_mod.get_partition_file_stats(c.id, "db1", "t1", partition_spec=None, db=db_session)
    assert stats1["file_stats"]["total_files"] == 120

    stats2 = await tables_mod.get_partition_file_stats(c.id, "db1", "t1", partition_spec="year=2024", db=db_session)
    assert stats2["partition_spec"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_connections_and_scan_all_databases(db_session, monkeypatch):
    import app.api.tables as tables_mod
    import app.engines.safe_hive_engine as safe_eng_mod
    c = _mk_cluster(db_session)

    class _Scanner:
        def __init__(self, cluster):
            pass
        def test_connections(self):
            return {"ok": True}
        def scan_database_tables(self, db, database_name, table_filter=None, max_tables=None):
            return {"tables_scanned": 1, "total_files": 10, "total_small_files": 5}

    class _Conn:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def get_databases(self):
            return ["db1", "db2"]

    monkeypatch.setattr(tables_mod, "HybridTableScanner", _Scanner)
    monkeypatch.setattr(tables_mod, "MySQLHiveMetastoreConnector", lambda url: _Conn())

    r1 = await tables_mod.test_cluster_connections(c.id, db_session)
    assert r1["connections"]["ok"] is True

    r2 = await tables_mod.test_cluster_connections_real(c.id, db_session)
    assert r2["connections"]["ok"] is True

    r3 = await tables_mod.scan_all_databases(c.id, 5, db_session)
    assert r3["summary"]["total_databases"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cold_data_endpoints_and_scan_progress(db_session, monkeypatch):
    import app.api.tables as tables_mod
    from app.services import scan_service as scan_service_mod

    c = _mk_cluster(db_session)

    # cold data scanner stubs
    class _Cold:
        def __init__(self, cluster, threshold=90):
            pass
        def scan_cold_tables(self, db, database_name=None):
            return {"tables": 1}
        def get_cold_data_summary(self, db):
            return {"count": 0}

    monkeypatch.setattr(tables_mod, "SimpleColdDataScanner", _Cold)

    r1 = await tables_mod.scan_cold_data(c.id, 30, None, db_session)
    assert r1["status"] == "completed"
    r2 = await tables_mod.get_cold_data_summary(c.id, db_session)
    assert "count" in r2

    # cold data list requires some metrics with is_cold_data=1
    now = datetime.now()
    _mk_metric(db_session, c.id, "dbx", "t1", 10, 5, 1000, 100, now, is_cold=1, days=10)
    lst = await tables_mod.get_cold_data_list(c.id, 1, 10, db_session)
    assert lst["total"] >= 1 and lst["page"] == 1

    # scan progress (persisted path)
    t = ScanTaskModel(cluster_id=c.id, task_type="cluster", task_name="t", status="running")
    db_session.add(t); db_session.commit(); db_session.refresh(t)
    ts = datetime.utcnow()
    db_session.add(ScanTaskLogDB(scan_task_id=t.id, timestamp=ts, level="INFO", message="x", database_name="d", table_name="tb"))
    db_session.commit()

    # no in-memory task
    monkeypatch.setattr(scan_service_mod.scan_task_manager, "get_task", lambda task_id: None)
    pr = await tables_mod.get_scan_task_progress(t.task_id, db_session)
    assert pr.task_id == t.task_id and len(pr.logs) >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_database_tables_modes_and_single_table(db_session, monkeypatch):
    import app.api.tables as tables_mod

    c = _mk_cluster(db_session)

    class _Scanner2:
        def __init__(self, cluster):
            self.hive_connector = SimpleNamespace(connect=lambda: True, disconnect=lambda: None)
            self.hdfs_scanner = SimpleNamespace(connect=lambda: True, disconnect=lambda: None)
        def scan_database_tables(self, db, database_name, table_filter=None, max_tables=None, strict_real=False):
            return {"tables_scanned": 1, "total_files": 10, "total_small_files": 5}
        def _initialize_hdfs_scanner(self):
            return None
        def scan_table(self, db, database_name, table_info):
            return {"ok": True, "table": table_info.get("table_name")}

    class _Conn2:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def get_tables(self, database_name):
            return [{"table_name": "tA", "table_path": "/wh/dbA/tA"}]

    monkeypatch.setattr(tables_mod, "HybridTableScanner", _Scanner2)
    monkeypatch.setattr(tables_mod, "MySQLHiveMetastoreConnector", lambda url: _Conn2())

    # mock mode
    r1 = await tables_mod.scan_database_tables(c.id, "dbA", table_filter=None, db=db_session)
    assert r1["status"] == "completed" and r1["scan_result"]["tables_scanned"] == 1

    # real mode
    r2 = await tables_mod.scan_database_tables_real(c.id, "dbA", table_filter=None, max_tables=3, strict_real=True, db=db_session)
    assert r2["scan_result"]["total_files"] == 10

    # single table
    r3 = await tables_mod.scan_single_table(c.id, "dbA", "tA", db_session)
    assert r3["table_name"] == "tA" and r3["status"] == "completed"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_table_info_and_partitions_list(db_session, monkeypatch):
    import app.api.tables as tables_mod
    import app.engines.safe_hive_engine as safe_eng_mod
    c = _mk_cluster(db_session)

    class _Eng2:
        def __init__(self, cluster):
            pass
        def _table_exists(self, dbn, tbl):
            return True
        def _is_partitioned_table(self, dbn, tbl):
            return True
        def _get_table_partitions(self, dbn, tbl):
            return ["dt=2024-01-01", "dt=2024-01-02"]
        def _get_table_format_info(self, dbn, tbl):
            return {"input_format": "org.apache.hadoop.mapred.TextInputFormat", "serde_lib": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe", "table_properties": {}}
        def _is_unsupported_table_type(self, fmt):
            return False
        def _unsupported_reason(self, fmt):
            return None

    monkeypatch.setattr(safe_eng_mod, "SafeHiveMergeEngine", _Eng2)

    info = await tables_mod.get_table_info(c.id, "dbA", "tB", db_session)
    assert info["merge_supported"] is True and info["partition_count"] == 2

    parts_list = await tables_mod.get_table_partitions_list(c.id, "dbA", "tB", db_session)
    assert len(parts_list["partitions"]) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_merge_preview_and_table_info_non_partitioned(db_session, monkeypatch):
    import app.api.tables as tables_mod
    import app.engines.safe_hive_engine as safe_eng_mod
    from app.models.cluster import Cluster

    c = _mk_cluster(db_session)

    class _Eng3:
        def __init__(self, cluster):
            pass
        def get_merge_preview(self, task):
            return {"estimated_files_after": 10}
        def _table_exists(self, dbn, tbl):
            return True
        def _is_partitioned_table(self, dbn, tbl):
            return False
        def _get_table_format_info(self, dbn, tbl):
            return {"input_format": "org.apache.hadoop.mapred.TextInputFormat", "serde_lib": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe", "table_properties": {}}
        def _is_unsupported_table_type(self, fmt):
            return False
        def _unsupported_reason(self, fmt):
            return None

    monkeypatch.setattr(safe_eng_mod, "SafeHiveMergeEngine", _Eng3)

    prev = await tables_mod.get_merge_preview(c.id, "dbA", "tX", partition_filter=None, db=db_session)
    assert prev["preview"]["estimated_files_after"] == 10

    info = await tables_mod.get_table_info(c.id, "dbA", "tX", db_session)
    assert info["is_partitioned"] is False and info["partition_count"] == 0
