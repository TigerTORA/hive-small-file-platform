from datetime import datetime, timedelta

import pytest

from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.models.partition_metric import PartitionMetric
from app.models.table_metric import TableMetric


def _mk_cluster(db, name="c-dash") -> Cluster:
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
def test_dashboard_summary_and_top_tables_and_recent_tasks(client, db_session):
    c = _mk_cluster(db_session)
    now = datetime.now()

    # metrics
    m1 = TableMetric(
        cluster_id=c.id,
        database_name="db1",
        table_name="t1",
        total_files=100,
        small_files=60,
        total_size=100 * 1024 * 1024,
        scan_time=now,
    )
    m2 = TableMetric(
        cluster_id=c.id,
        database_name="db1",
        table_name="t2",
        total_files=50,
        small_files=10,
        total_size=50 * 1024 * 1024,
        scan_time=now,
    )
    db_session.add_all([m1, m2])
    db_session.commit()
    db_session.refresh(m1)
    db_session.refresh(m2)

    # summary
    r = client.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_tables"] >= 2 and body["total_files"] >= 150

    # top tables filtered by cluster
    r2 = client.get(
        "/api/v1/dashboard/top-tables", params={"cluster_id": c.id, "limit": 5}
    )
    assert r2.status_code == 200
    assert isinstance(r2.json(), list) and len(r2.json()) >= 1

    # recent tasks
    t = MergeTask(
        cluster_id=c.id,
        task_name="merge1",
        database_name="db1",
        table_name="t1",
        use_ec=False,
    )
    db_session.add(t)
    db_session.commit()
    r3 = client.get("/api/v1/dashboard/recent-tasks", params={"limit": 10})
    assert r3.status_code == 200 and isinstance(r3.json(), list)


@pytest.mark.unit
def test_dashboard_file_distribution_with_cluster(client, db_session):
    c = _mk_cluster(db_session, name="c-dist")
    now = datetime.now()

    # table + partitions in different ranges
    tm = TableMetric(
        cluster_id=c.id,
        database_name="dbx",
        table_name="tx",
        total_files=10,
        small_files=5,
        total_size=10 * 1024 * 1024,
        scan_time=now,
    )
    db_session.add(tm)
    db_session.commit()
    db_session.refresh(tm)

    # partition with small avg file (<1MB)
    p1 = PartitionMetric(
        table_metric_id=tm.id,
        partition_name="p1",
        partition_path="/p1",
        file_count=2,
        total_size=500 * 1024,
    )
    # partition with 1MB-128MB range
    p2 = PartitionMetric(
        table_metric_id=tm.id,
        partition_name="p2",
        partition_path="/p2",
        file_count=3,
        total_size=64 * 1024 * 1024,
    )
    db_session.add_all([p1, p2])
    db_session.commit()

    r = client.get("/api/v1/dashboard/file-distribution", params={"cluster_id": c.id})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) == 4
