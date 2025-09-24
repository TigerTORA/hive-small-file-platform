from datetime import datetime, timedelta

import pytest

from app.models.cluster import Cluster
from app.models.table_metric import TableMetric


def _mk_cluster(db, name="c-trend") -> Cluster:
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
        scan_time=when,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@pytest.mark.unit
def test_table_file_counts_trends_up_and_down(client, db_session):
    now = datetime.now()
    c = _mk_cluster(db_session)

    # 表A：上升趋势（10 -> 15）
    _mk_metric(db_session, c.id, "db1", "t1", 10, now - timedelta(days=2))
    _mk_metric(db_session, c.id, "db1", "t1", 15, now - timedelta(days=1))

    # 表B：下降趋势（20 -> 10）
    _mk_metric(db_session, c.id, "db1", "t2", 20, now - timedelta(days=3))
    _mk_metric(db_session, c.id, "db1", "t2", 10, now - timedelta(hours=2))

    r = client.get("/api/v1/dashboard/table-file-counts")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) >= 2

    # 构造一个索引表方便断言
    by_table = {f"{x['database_name']}.{x['table_name']}": x for x in body}
    assert by_table["db1.t1"]["trend_7d"] >= 49.9  # 接近 +50.0
    assert by_table["db1.t2"]["trend_7d"] <= -49.9  # 接近 -50.0
