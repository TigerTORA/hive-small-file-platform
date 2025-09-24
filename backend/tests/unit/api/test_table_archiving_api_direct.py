from datetime import datetime, timedelta

import pytest

from app.models.cluster import Cluster
from app.models.table_metric import TableMetric


def _mk_cluster(db) -> Cluster:
    c = Cluster(
        name="c-arch",
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


def _mk_metric(db, cluster_id: int, dbn: str, tbl: str, status="active", is_cold=0):
    m = TableMetric(
        cluster_id=cluster_id,
        database_name=dbn,
        table_name=tbl,
        total_files=10,
        small_files=5,
        total_size=1024,
        avg_file_size=100.0,
        scan_time=datetime.utcnow() - timedelta(days=1),
        is_cold_data=is_cold,
        archive_status=status,
        last_access_time=datetime.utcnow() - timedelta(days=10) if is_cold else None,
        days_since_last_access=10 if is_cold else None,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cold_summary_and_list(db_session):
    import app.api.table_archiving as ta

    c = _mk_cluster(db_session)
    _mk_metric(db_session, c.id, "dbA", "t1", is_cold=1)
    _mk_metric(db_session, c.id, "dbA", "t2", is_cold=1)
    s = await ta.get_cold_data_summary(c.id, db_session)
    assert s["cold_data_summary"]["cold_table_count"] >= 2
    lst = await ta.get_cold_data_list(
        c.id,
        database_name=None,
        min_days_since_access=0,
        page=1,
        page_size=10,
        order_by="days_since_last_access",
        order_desc=True,
        db=db_session,
    )
    assert lst["pagination"]["total_count"] >= 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_cold_data_updates_flags(db_session, monkeypatch):
    import app.api.table_archiving as ta

    c = _mk_cluster(db_session)
    _mk_metric(db_session, c.id, "dbB", "t3", is_cold=0)

    class _Cold:
        def __init__(self, cluster):
            pass

        def scan_cold_data(self, threshold_days: int, database_filter=None):
            return {
                "cold_tables": [
                    {
                        "database_name": "dbB",
                        "table_name": "t3",
                        "last_access_time": datetime.utcnow() - timedelta(days=20),
                        "days_since_last_access": 20,
                    }
                ]
            }

    monkeypatch.setattr(ta, "SimpleColdDataScanner", _Cold)
    res = await ta.scan_cold_data(
        c.id,
        cold_days_threshold=15,
        cold_threshold_days=None,
        database_name=None,
        db=db_session,
    )
    assert res["scan_result"]["database_records_updated"] >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_archive_and_restore_table(db_session, monkeypatch):
    import app.api.table_archiving as ta

    c = _mk_cluster(db_session)
    m = _mk_metric(db_session, c.id, "dbC", "t4", status="active")

    class _Arc:
        def __init__(self, cluster):
            pass

        def archive_table(self, database_name, table_name, force=False):
            return {"archive_location": "/archive/dbC/t4"}

        def restore_table(self, database_name, table_name, archive_location):
            return {"restored": True}

    monkeypatch.setattr(ta, "SimpleArchiveEngine", _Arc)
    ar = await ta.archive_table(c.id, "dbC", "t4", False, db_session)
    assert ar["archive_result"]["archive_location"].endswith("/t4")

    # mark archived in DB to allow restore
    m.archive_status = "archived"
    m.archive_location = "/archive/dbC/t4"
    db_session.commit()
    rs = await ta.restore_table(c.id, "dbC", "t4", db_session)
    assert rs["restore_result"]["restored"] is True

    # mark archived again and list
    m.archive_status = "archived"
    m.archived_at = datetime.utcnow()
    db_session.commit()
    lst = await ta.list_archived_tables(
        c.id, database_name=None, page=1, page_size=10, db=db_session
    )
    assert lst["pagination"]["total_count"] >= 1

    stats = await ta.get_archive_statistics(c.id, days_range=7, db=db_session)
    assert "overall_statistics" in stats
