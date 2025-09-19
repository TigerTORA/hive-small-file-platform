import pytest

from app.engines.safe_hive_engine_refactored import SafeHiveMergeEngine
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask


def _mk_cluster() -> Cluster:
    return Cluster(
        name="c",
        description="",
        hive_host="localhost",
        hive_port=10000,
        hive_metastore_url="mysql://user:pass@localhost:3306/hive",
        hdfs_namenode_url="hdfs://localhost:9000",
    )


@pytest.mark.unit
def test_safe_engine_pass_through(monkeypatch, db_session):
    c = _mk_cluster()
    t = MergeTask(
        cluster_id=1,
        task_name="t",
        database_name="db",
        table_name="tbl",
        merge_strategy="safe_merge",
    )

    eng = SafeHiveMergeEngine(c)

    class _Val:
        def validate_task(self, task):
            return {"valid": True}

    class _Exec:
        def __init__(self):
            self._cb = None
        def set_progress_callback(self, cb):
            self._cb = cb
        def execute_merge(self, task, db):
            return {"done": True}

    class _Prog:
        def get_merge_preview(self, task):
            return {"preview": True}
        def estimate_duration(self, task):
            return 42

    called_cleanup = {"ok": False}

    class _ConnMgr:
        def cleanup_connections(self):
            called_cleanup["ok"] = True

    # 注入替身
    eng.validation_service = _Val()
    eng.executor = _Exec()
    eng.progress_tracker = _Prog()
    eng.connection_manager = _ConnMgr()

    assert eng.validate_task(t)["valid"] is True
    assert eng.execute_merge(t, db_session)["done"] is True
    assert eng.get_merge_preview(t)["preview"] is True
    assert eng.estimate_duration(t) == 42

    with eng:
        pass
    assert called_cleanup["ok"] is True

