from datetime import datetime

import pytest

from app.models.cluster import Cluster
from app.models.scan_task import ScanTask as ScanTaskModel
from app.services.scan_service import ScanTaskManager


def _mk_cluster(db) -> Cluster:
    c = Cluster(
        name="c-scanmgr",
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
def test_scan_task_manager_core_flow(db_session):
    mgr = ScanTaskManager()
    c = _mk_cluster(db_session)

    # create task
    task = mgr.create_scan_task(
        db_session,
        c.id,
        task_type="database",
        task_name="t1",
        target_database="dbA",
        target_table=None,
    )
    assert task.task_id in mgr.active_tasks and mgr.get_task(task.task_id) is not None

    # add in-memory log
    mgr.add_log(task.task_id, "INFO", "mem-log-1")
    logs = mgr.get_task_logs(task.task_id)
    assert any(l.message == "mem-log-1" for l in logs)

    # request cancel (persists a log, but we only assert True)
    assert mgr.request_cancel(db_session, task.task_id) is True

    # update progress and verify DB
    mgr.update_task_progress(
        db_session, task.task_id, completed_items=2, total_items=5, status="running"
    )
    row = (
        db_session.query(ScanTaskModel)
        .filter(ScanTaskModel.task_id == task.task_id)
        .first()
    )
    assert row.completed_items == 2 and row.total_items == 5 and row.status == "running"

    # safe_update_progress ignores unknown fields and logs a WARN
    mgr.safe_update_progress(
        db_session, task.task_id, completed_items=3, unknown_field="x"
    )
    mem_logs = [l.message for l in mgr.get_task_logs(task.task_id)]
    assert any("safe_update_progress" in m for m in mem_logs)

    # complete task and verify persisted status
    mgr.complete_task(db_session, task.task_id, success=True)
    row2 = (
        db_session.query(ScanTaskModel)
        .filter(ScanTaskModel.task_id == task.task_id)
        .first()
    )
    assert (
        row2.status == "completed"
        and row2.end_time is not None
        and row2.duration is not None
    )
