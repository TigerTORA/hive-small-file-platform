from datetime import datetime, timedelta

import pytest

from app.models.cluster import Cluster
from app.models.scan_task import ScanTask
from app.models.scan_task_log import ScanTaskLogDB


def _mk_cluster(db, name="c-scan") -> Cluster:
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


def _mk_task(db, cluster_id=1, task_id="task-1", status="running") -> ScanTask:
    t = ScanTask(
        cluster_id=cluster_id,
        task_id=task_id,
        task_type="database",
        task_name=f"scan-{task_id}",
        status=status,
        start_time=datetime.utcnow() - timedelta(minutes=5),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.mark.unit
def test_list_and_get_scan_tasks(client, db_session):
    c = _mk_cluster(db_session)
    _mk_task(db_session, cluster_id=c.id, task_id="task-2", status="success")
    _mk_task(db_session, cluster_id=c.id, task_id="task-3", status="failed")

    r = client.get("/api/v1/scan-tasks/", params={"cluster_id": c.id})
    assert r.status_code == 200 and len(r.json()) >= 2

    tid = r.json()[0]["task_id"]
    g = client.get(f"/api/v1/scan-tasks/{tid}")
    assert g.status_code == 200 and g.json()["task_id"]


@pytest.mark.unit
def test_scan_task_logs_persisted_and_memory_merge(client, db_session, monkeypatch):
    from app.services import scan_service as scan_service_mod

    c = _mk_cluster(db_session)
    t = _mk_task(db_session, cluster_id=c.id, task_id="task-logs", status="running")
    # create persisted log
    row = ScanTaskLogDB(
        scan_task_id=t.id,
        timestamp=datetime.utcnow() - timedelta(minutes=1),
        level="INFO",
        message="persisted",
        database_name="db1",
        table_name="t1",
    )
    db_session.add(row)
    db_session.commit()

    # memory log newer
    from app.schemas.scan_task import ScanTaskLog

    mem_log = ScanTaskLog(
        timestamp=datetime.utcnow(),
        level="INFO",
        message="mem",
        database_name="db1",
        table_name="t1",
    )
    monkeypatch.setattr(
        scan_service_mod.scan_task_manager, "get_task_logs", lambda task_id: [mem_log]
    )

    r = client.get(f"/api/v1/scan-tasks/{t.task_id}/logs")
    assert r.status_code == 200
    msgs = [x["message"] for x in r.json()]
    assert "persisted" in msgs and "mem" in msgs


@pytest.mark.unit
def test_cancel_scan_task(client, db_session, monkeypatch):
    from app.services import scan_service as scan_service_mod

    c = _mk_cluster(db_session)
    t = _mk_task(db_session, cluster_id=c.id, task_id="task-cancel", status="running")

    called = {"ok": False}

    def fake_cancel(db, task_id):
        called["ok"] = True

    monkeypatch.setattr(
        scan_service_mod.scan_task_manager, "request_cancel", fake_cancel
    )

    r = client.post(f"/api/v1/scan-tasks/{t.task_id}/cancel")
    assert r.status_code == 200 and called["ok"] is True
