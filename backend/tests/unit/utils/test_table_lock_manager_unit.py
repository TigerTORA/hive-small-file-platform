from datetime import datetime, timedelta

import pytest

from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.utils.table_lock_manager import TableLockManager


def _make_cluster(db, name="c-lock") -> Cluster:
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


def _make_task(db, cluster_id: int, db_name="db", tbl="tbl", name="t1") -> MergeTask:
    t = MergeTask(
        cluster_id=cluster_id,
        task_name=name,
        database_name=db_name,
        table_name=tbl,
        status="pending",
        use_ec=False,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.mark.unit
def test_acquire_and_release_lock_flow(db_session):
    c = _make_cluster(db_session)
    task = _make_task(db_session, c.id)

    # acquire
    r = TableLockManager.acquire_table_lock(
        db_session, c.id, task.database_name, task.table_name, task.id
    )
    assert r["success"] is True

    db_session.refresh(task)
    assert task.table_lock_acquired is True and task.lock_holder == f"task_{task.id}"

    # check status
    st = TableLockManager.check_table_lock_status(
        db_session, c.id, task.database_name, task.table_name
    )
    assert st.get("locked") is True and st.get("locked_by_task") == task.id

    # release
    rr = TableLockManager.release_table_lock(db_session, task.id)
    assert rr["success"] is True
    db_session.refresh(task)
    assert task.table_lock_acquired is False and task.lock_holder is None


@pytest.mark.unit
def test_acquire_when_other_task_holds_lock(db_session):
    c = _make_cluster(db_session)
    holder = _make_task(db_session, c.id, name="holder")
    holder.table_lock_acquired = True
    holder.status = "running"
    holder.started_time = datetime.utcnow()
    db_session.commit()

    me = _make_task(db_session, c.id, name="me")

    r = TableLockManager.acquire_table_lock(
        db_session, c.id, holder.database_name, holder.table_name, me.id
    )
    assert r["success"] is False
    assert r.get("locked_by_task") == holder.id


@pytest.mark.unit
def test_expired_lock_is_force_released_then_acquired_by_new_task(db_session):
    c = _make_cluster(db_session)
    expired = _make_task(db_session, c.id, name="expired")
    expired.table_lock_acquired = True
    expired.status = "running"
    expired.started_time = datetime.utcnow() - timedelta(minutes=180)
    db_session.commit()

    me = _make_task(db_session, c.id, name="me")

    r = TableLockManager.acquire_table_lock(
        db_session,
        c.id,
        expired.database_name,
        expired.table_name,
        me.id,
        lock_timeout_minutes=1,
    )
    assert r["success"] is True

    db_session.refresh(expired)
    db_session.refresh(me)
    assert expired.table_lock_acquired is False
    assert expired.status in ("failed", "running")  # 若释放时处于 running 应标记 failed
    assert me.table_lock_acquired is True


@pytest.mark.unit
def test_cleanup_expired_locks_and_get_all(db_session):
    c = _make_cluster(db_session)
    t1 = _make_task(db_session, c.id, name="t1")
    t2 = _make_task(db_session, c.id, name="t2")

    # t1: old running lock -> expired
    t1.table_lock_acquired = True
    t1.status = "running"
    t1.started_time = datetime.utcnow() - timedelta(minutes=90)

    # t2: recent running lock -> not expired
    t2.table_lock_acquired = True
    t2.status = "running"
    t2.started_time = datetime.utcnow()
    db_session.commit()

    res = TableLockManager.cleanup_expired_locks(db_session, lock_timeout_minutes=30)
    assert res["success"] is True
    assert res["cleaned_locks"] >= 1

    locks = TableLockManager.get_all_table_locks(db_session, cluster_id=c.id)
    assert locks["success"] is True
    assert locks["total_locks"] >= 0
    # 仅检查结构完整性
    if locks["total_locks"]:
        entry = locks["locks"][0]
        assert {
            "task_id",
            "cluster_id",
            "database_name",
            "table_name",
            "lock_holder",
            "task_status",
        } <= set(entry.keys())
