import pytest
from datetime import datetime, timedelta


from app.models.cluster import Cluster
from app.models.table_metric import TableMetric


def _mk_cluster(db, name="c-scanapi") -> Cluster:
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
async def test_scan_tables_single_table_and_database(db_session, monkeypatch):
    import app.api.table_scanning as ts

    c = _mk_cluster(db_session)

    class _Scanner:
        def __init__(self, cluster):
            pass

        def scan_single_table(self, db, database_name, table_name, strict_real=True):
            return {"ok": True, "table": f"{database_name}.{table_name}"}

        def scan_database_tables(self, db, database_name, strict_real=True, max_tables=None):
            return [{"table_name": "t1"}, {"table_name": "t2"}]

    monkeypatch.setattr(ts, "HybridTableScanner", _Scanner)

    # single table path
    from app.schemas.table_metric import ScanRequest

    req = ScanRequest(cluster_id=c.id, database_name="dbA", table_name="tA")
    r1 = await ts.scan_tables(req, strict_real=False, db=db_session)
    assert r1["scanned_tables"] == 1 and r1["result"]["ok"] is True

    # single database path
    req2 = ScanRequest(cluster_id=c.id, database_name="dbB", table_name=None)
    r2 = await ts.scan_tables(req2, strict_real=True, db=db_session)
    assert r2["scanned_tables"] == 2 and r2["results"][0]["table_name"] == "t1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_tables_invalid_and_not_found(db_session):
    import app.api.table_scanning as ts
    from app.schemas.table_metric import ScanRequest
    from fastapi import HTTPException

    # cluster not found
    with pytest.raises(HTTPException) as ei:
        await ts.scan_tables(ScanRequest(cluster_id=9999, database_name="db", table_name="t"), db=db_session)
    assert ei.value.status_code == 404

    # invalid request (missing database_name) — current implementation wraps to 500
    c = _mk_cluster(db_session)
    with pytest.raises(HTTPException) as ei2:
        await ts.scan_tables(ScanRequest(cluster_id=c.id, database_name=None, table_name=None), db=db_session)
    assert ei2.value.status_code == 500


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_database_tables_and_real(db_session, monkeypatch):
    import app.api.table_scanning as ts

    c = _mk_cluster(db_session)

    class _Scanner:
        def __init__(self, cluster):
            pass

        def scan_database_tables(self, db, database_name, max_tables=None, strict_real=True):
            return [{"table_name": "t1"}]

    monkeypatch.setattr(ts, "HybridTableScanner", _Scanner)

    r1 = await ts.scan_database_tables(c.id, "dbX", strict_real=False, max_tables=0, db=db_session)
    assert r1["database_name"] == "dbX" and r1["scanned_tables"] == 1

    r2 = await ts.scan_database_tables_real(c.id, "dbX", max_tables=5, strict_real=True, db=db_session)
    assert r2["strict_real"] is True and r2["scanned_tables"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_partition_metrics_paths(db_session):
    import app.api.table_scanning as ts
    from fastapi import HTTPException

    c = _mk_cluster(db_session)

    # no table metric -> 404
    with pytest.raises(HTTPException) as ei:
        await ts.get_partition_metrics(cluster_id=c.id, database_name="dbM", table_name="tM", db=db_session)
    assert ei.value.status_code == 404

    # not partitioned -> 400
    tm = TableMetric(
        cluster_id=c.id,
        database_name="dbM",
        table_name="tM",
        total_files=10,
        small_files=1,
        total_size=100,
        avg_file_size=10.0,
        is_partitioned=0,
        partition_count=0,
        scan_time=datetime.utcnow(),
    )
    db_session.add(tm)
    db_session.commit()

    with pytest.raises(HTTPException) as ei2:
        await ts.get_partition_metrics(cluster_id=c.id, database_name="dbM", table_name="tM", db=db_session)
    assert ei2.value.status_code == 400

    # make it partitioned and return result
    tm.is_partitioned = 1
    tm.partition_count = 12
    db_session.commit()

    res = await ts.get_partition_metrics(cluster_id=c.id, database_name="dbM", table_name="tM", page=2, page_size=5, db=db_session)
    assert res["table_info"]["total_partitions"] == 12
    assert res["pagination"]["page"] == 2 and res["pagination"]["page_size"] == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_single_table_and_progress_and_logs(db_session, monkeypatch):
    import app.api.table_scanning as ts
    from app.schemas.scan_task import ScanTaskLog, ScanTaskProgress

    c = _mk_cluster(db_session)

    class _Scanner:
        def __init__(self, cluster):
            pass

        def scan_single_table(self, db, database_name, table_name, strict_real=True):
            return {"files": 10}

    monkeypatch.setattr(ts, "HybridTableScanner", _Scanner)

    r = await ts.scan_single_table(c.id, "dbZ", "tZ", strict_real=False, db=db_session)
    assert r["table_name"].endswith("dbZ.tZ") and r["strict_real"] is False

    # progress ok
    prog = ScanTaskProgress(
        task_id="tid-1",
        status="running",
        progress_percentage=0.5,
        completed_items=1,
        total_items=10,
        estimated_remaining_seconds=1.0,
        logs=[ScanTaskLog(timestamp=datetime.utcnow(), level="INFO", message="hi")],
    )
    monkeypatch.setattr(ts.scan_task_manager, "get_task_progress", lambda tid: prog, raising=False)
    pr = await ts.get_scan_task_progress("tid-1")
    assert pr.task_id == "tid-1" and pr.status == "running"

    # cluster overview
    monkeypatch.setattr(ts.scan_task_manager, "get_cluster_scan_overview", lambda cid: {"cluster_id": cid, "ok": True}, raising=False)
    ov = await ts.get_scan_progress(c.id)
    assert ov["cluster_id"] == c.id and ov["ok"] is True

    # logs
    log_items = [ScanTaskLog(timestamp=datetime.utcnow(), level="INFO", message="A")]
    monkeypatch.setattr(ts.scan_task_manager, "get_task_logs", lambda tid, limit=100, level=None: log_items)
    lg = await ts.get_scan_task_logs("tid-1", limit=1, level="INFO")
    assert lg["task_id"] == "tid-1" and lg["log_count"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_scan_task_progress_not_found(db_session, monkeypatch):
    import app.api.table_scanning as ts
    from fastapi import HTTPException

    monkeypatch.setattr(ts.scan_task_manager, "get_task_progress", lambda tid: None, raising=False)
    with pytest.raises(HTTPException) as ei:
        await ts.get_scan_task_progress("nope")
    # current implementation wraps into 500 on exception handling
    assert ei.value.status_code == 500


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_all_cluster_databases_with_progress(db_session, monkeypatch):
    import app.api.table_scanning as ts

    c = _mk_cluster(db_session)

    monkeypatch.setattr(ts.scan_task_manager, "create_cluster_scan_task", lambda cluster_id, strict_real, max_tables_per_db: "tid-x", raising=False)

    called = {"exec": False}

    async def fake_exec(task_id, cluster, strict_real, max_tables_per_db):
        called["exec"] = True

    monkeypatch.setattr(ts.scan_task_manager, "execute_cluster_scan", fake_exec, raising=False)

    resp = await ts.scan_all_cluster_databases_with_progress(c.id, strict_real=True, max_tables_per_db=3, db=db_session)
    assert resp["task_id"] == "tid-x" and resp["cluster_id"] == c.id
