from typing import Any, Dict

from app.engines.base_engine import BaseMergeEngine
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask


class _FakeEngine(BaseMergeEngine):
    def validate_task(self, task: MergeTask) -> Dict[str, Any]:
        return {"valid": True}

    def execute_merge(self, task: MergeTask, db_session):
        return {"success": True}

    def get_merge_preview(self, task: MergeTask) -> Dict[str, Any]:
        return {"files_before": 0, "files_after": 0}

    def estimate_duration(self, task: MergeTask) -> int:
        return 0


def _make_cluster() -> Cluster:
    return Cluster(
        id=1,
        name="c",
        hive_metastore_url="mysql://u:p@localhost:3306/hive",
        hdfs_namenode_url="hdfs://nn:9000",
        hive_host="localhost",
        hive_port=10000,
    )


def test_build_table_path_simple():
    engine = _FakeEngine(_make_cluster())
    p = engine._build_table_path("dbx", "t1")
    assert p.endswith("/dbx.db/t1")


def test_log_task_event_with_db_session(db_session):
    engine = _FakeEngine(_make_cluster())
    task = MergeTask(
        cluster_id=1,
        task_name="t3",
        table_name="tbl",
        database_name="db",
        merge_strategy="safe_merge",
        use_ec=False,
    )
    db_session.add(task)
    db_session.commit()

    # 有 db_session 分支
    engine.log_task_event(task, "INFO", "hi-db", db_session=db_session)
    # 简要校验 DB 中是否已 flush（存在 TaskLog 记录）
    from app.models.task_log import TaskLog

    cnt = db_session.query(TaskLog).filter(TaskLog.task_id == task.id).count()
    assert cnt >= 1
