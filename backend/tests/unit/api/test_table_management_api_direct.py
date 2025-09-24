from datetime import datetime, timedelta

import pytest

from app.models.cluster import Cluster
from app.models.table_metric import TableMetric


def _mk_cluster(db) -> Cluster:
    c = Cluster(
        name="c-mgr",
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


def _mk_metric(
    db, cluster_id: int, dbn: str, tbl: str, when: datetime, files=10, small=5
):
    m = TableMetric(
        cluster_id=cluster_id,
        database_name=dbn,
        table_name=tbl,
        total_files=files,
        small_files=small,
        total_size=files * 1024,
        avg_file_size=100.0,
        scan_time=when,
        is_cold_data=0,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@pytest.mark.unit
@pytest.mark.asyncio
async def test_table_management_endpoints_direct(db_session):
    import app.api.table_management as tm

    c = _mk_cluster(db_session)
    now = datetime.now()
    _mk_metric(db_session, c.id, "dbx", "t1", now - timedelta(hours=2))
    _mk_metric(
        db_session, c.id, "dbx", "t1", now - timedelta(hours=1), files=12, small=6
    )
    _mk_metric(db_session, c.id, "dbx", "t2", now)

    # metrics
    ms = await tm.get_table_metrics(cluster_id=c.id, database_name=None, db=db_session)
    assert len(ms) >= 2

    # small files summary
    sm = await tm.get_small_file_summary(
        cluster_id=c.id, database_name="dbx", db=db_session
    )
    assert sm["total_tables"] >= 1

    # databases
    dbs = await tm.get_databases(c.id, db_session)
    assert dbs["databases"] == ["dbx"]

    # tables
    tbls = await tm.get_tables(c.id, "dbx", db_session)
    assert "t1" in tbls["tables"]

    # detail
    detail = await tm.get_table_detail(c.id, "dbx", "t1", db_session)
    assert detail["file_metrics"]["total_files"] >= 10

    # history
    hist = await tm.get_table_scan_history(c.id, "dbx", "t1", 10, db_session)
    assert hist["scan_count"] >= 2
