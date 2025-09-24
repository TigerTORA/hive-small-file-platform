from datetime import datetime

import pytest

from app.models.cluster import Cluster
from app.models.merge_task import MergeTask


def _mk_cluster(db, name="c-task") -> Cluster:
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


def _mk_task(
    db, cluster_id: int, name="t1", status="pending", fb=None, fa=None, ss=None
) -> MergeTask:
    t = MergeTask(
        cluster_id=cluster_id,
        task_name=name,
        database_name="db1",
        table_name="t",
        merge_strategy="safe_merge",
        status=status,
        files_before=fb,
        files_after=fa,
        size_saved=ss,
        use_ec=False,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.mark.unit
def test_list_create_get_and_cluster_tasks(client, db_session):
    c = _mk_cluster(db_session)
    _mk_task(db_session, c.id, name="t1")
    _mk_task(db_session, c.id, name="t2", status="success", fb=10, fa=2, ss=1024)

    # list
    r = client.get("/api/v1/tasks/", params={"cluster_id": c.id, "limit": 10})
    assert r.status_code == 200 and len(r.json()) >= 2

    # create
    payload = {
        "cluster_id": c.id,
        "task_name": "t3",
        "database_name": "db1",
        "table_name": "t",
        "merge_strategy": "safe_merge",
    }
    r2 = client.post("/api/v1/tasks/", json=payload)
    assert r2.status_code == 200 and r2.json()["task_name"] == "t3"

    # get by id
    tid = r2.json()["id"]
    r3 = client.get(f"/api/v1/tasks/{tid}")
    assert r3.status_code == 200 and r3.json()["id"] == tid

    # tasks by cluster
    r4 = client.get(f"/api/v1/tasks/cluster/{c.id}")
    assert r4.status_code == 200 and len(r4.json()) >= 3

    # list by status filter
    r5 = client.get("/api/v1/tasks/", params={"status": "success", "limit": 50})
    assert r5.status_code == 200
    assert all(t["status"] == "success" for t in r5.json())

    # get not found
    r6 = client.get("/api/v1/tasks/999999")
    assert r6.status_code == 404


@pytest.mark.unit
def test_task_stats(client, db_session):
    c = _mk_cluster(db_session)
    _mk_task(db_session, c.id, status="success", fb=10, fa=4, ss=2048)
    _mk_task(db_session, c.id, status="failed")

    r = client.get("/api/v1/tasks/stats", params={"cluster_id": c.id})
    assert r.status_code == 200
    body = r.json()
    assert body["total_tasks"] >= 2
    assert body["completed_tasks"] >= 1
    assert body["total_files_saved"] >= 6
    assert body["total_size_saved"] >= 2048


@pytest.mark.unit
def test_execute_task_and_cancel(client, db_session, monkeypatch):

    c = _mk_cluster(db_session)
    t = _mk_task(db_session, c.id, status="pending")

    class _FakeEngine:
        def execute_merge(self, task, db):
            task.status = "success"
            db.commit()
            return {"ok": 1}

        def get_merge_preview(self, task):
            return {"preview": True}

    import app.engines.engine_factory as eng_factory_mod

    monkeypatch.setattr(
        eng_factory_mod.MergeEngineFactory,
        "get_engine",
        lambda cluster, engine_type=None: _FakeEngine(),
    )
    from app.api import tasks as tasks_mod

    monkeypatch.setattr(tasks_mod.settings, "DEMO_MODE", False)

    r = client.post(f"/api/v1/tasks/{t.id}/execute")
    assert r.status_code == 200
    assert r.json()["status"] in ("success", "failed")

    # executing again should be 400 (already success or running)
    r_again = client.post(f"/api/v1/tasks/{t.id}/execute")
    assert r_again.status_code == 400

    # cancel only when running -> expect 400 if not running
    r2 = client.post(f"/api/v1/tasks/{t.id}/cancel")
    assert r2.status_code in (200, 400)

    # set running then cancel
    t.status = "running"
    db_session.commit()
    r3 = client.post(f"/api/v1/tasks/{t.id}/cancel")
    assert r3.status_code == 200


@pytest.mark.unit
def test_task_preview(client, db_session, monkeypatch):

    c = _mk_cluster(db_session)
    t = _mk_task(db_session, c.id, status="pending")

    class _FakeEngine2:
        def get_merge_preview(self, task):
            return {"files_before": 10, "files_after": 2}

    import app.engines.engine_factory as eng_factory_mod

    monkeypatch.setattr(
        eng_factory_mod.MergeEngineFactory,
        "get_engine",
        lambda cluster, engine_type=None: _FakeEngine2(),
    )

    r = client.get(f"/api/v1/tasks/{t.id}/preview")
    assert r.status_code == 200
    assert r.json()["preview"]["files_before"] == 10


@pytest.mark.unit
def test_execute_and_logs_not_found_404(client):
    # execute nonexistent task
    r = client.post("/api/v1/tasks/999999/execute")
    assert r.status_code == 404

    # logs for nonexistent task
    r2 = client.get("/api/v1/tasks/999999/logs")
    assert r2.status_code == 404


@pytest.mark.unit
def test_task_preview_cluster_not_found_404(client, db_session):
    c = _mk_cluster(db_session)
    t = _mk_task(db_session, c.id, status="pending")
    # make cluster invalid
    t.cluster_id = 999999
    db_session.commit()
    r = client.get(f"/api/v1/tasks/{t.id}/preview")
    assert r.status_code == 404


@pytest.mark.unit
def test_task_stats_global(client, db_session):
    c = _mk_cluster(db_session)
    _mk_task(db_session, c.id, status="success", fb=6, fa=3, ss=512)
    r = client.get("/api/v1/tasks/stats")
    assert r.status_code == 200
    body = r.json()
    assert "total_tasks" in body and "status_distribution" in body


@pytest.mark.unit
def test_execute_task_error_path(client, db_session, monkeypatch):
    c = _mk_cluster(db_session)
    t = _mk_task(db_session, c.id, status="pending")

    class _ErrEngine:
        def execute_merge(self, task, db):
            raise RuntimeError("boom")

    import app.engines.engine_factory as eng_factory_mod

    monkeypatch.setattr(
        eng_factory_mod.MergeEngineFactory,
        "get_engine",
        lambda cluster, engine_type=None: _ErrEngine(),
    )
    from app.api import tasks as tasks_mod

    monkeypatch.setattr(tasks_mod.settings, "DEMO_MODE", False)

    r = client.post(f"/api/v1/tasks/{t.id}/execute")
    assert r.status_code == 200 and r.json()["status"] == "failed"
