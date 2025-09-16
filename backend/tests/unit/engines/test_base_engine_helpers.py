from typing import Dict, Any

from app.engines.base_engine import BaseMergeEngine
from app.models.merge_task import MergeTask
from app.models.cluster import Cluster


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


def test_update_task_status_without_db_session():
    engine = _FakeEngine(_make_cluster())
    task = MergeTask(
        cluster_id=1,
        task_name="t",
        table_name="tbl",
        database_name="db",
        merge_strategy="safe_merge",
    )

    engine.update_task_status(task, "running")
    assert task.status == "running"

    engine.update_task_status(task, "success", files_before=10, files_after=2, size_saved=123)
    assert task.status == "success"
    assert task.files_before == 10
    assert task.files_after == 2
    assert task.size_saved == 123


def test_log_task_event_without_db_session(caplog):
    engine = _FakeEngine(_make_cluster())
    task = MergeTask(
        cluster_id=1,
        task_name="t2",
        table_name="tbl",
        database_name="db",
        merge_strategy="safe_merge",
    )
    with caplog.at_level("INFO"):
        engine.log_task_event(task, "INFO", "hello")
    assert any("hello" in r.message for r in caplog.records)

