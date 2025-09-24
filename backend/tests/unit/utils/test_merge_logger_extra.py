import json

import pytest

from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.utils.merge_logger import MergeLogLevel, MergePhase, MergeTaskLogger


def _mk_task(db) -> MergeTask:
    c = Cluster(
        name="c-ml",
        description="",
        hive_host="localhost",
        hive_port=10000,
        hive_metastore_url="mysql://user:pass@localhost:3306/hive",
        hdfs_namenode_url="hdfs://localhost:9000",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    t = MergeTask(
        cluster_id=c.id,
        task_name="t-ml",
        database_name="db1",
        table_name="t1",
        merge_strategy="safe_merge",
        status="pending",
        use_ec=False,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.mark.unit
def test_merge_logger_flow_and_export(db_session):
    t = _mk_task(db_session)
    logger = MergeTaskLogger(t, db_session)

    logger.start_phase(MergePhase.CONNECTION_TEST, "连接测试", {"x": 1})
    logger.end_phase(MergePhase.CONNECTION_TEST, "连接完成", success=True)

    logger.log_sql_execution(
        "SELECT 1",
        MergePhase.DATA_VALIDATION,
        affected_rows=1,
        success=True,
    )
    logger.log_file_statistics(
        MergePhase.FILE_ANALYSIS, "db1.t1", files_before=10, files_after=2
    )
    logger.log_data_validation(MergePhase.DATA_VALIDATION, "count", 10, 10, True)
    logger.log_task_completion(True, 1234, {"files_saved": 8})

    js = logger.export_logs_to_json()
    body = json.loads(js)
    assert body["task_info"]["id"] == t.id
    assert isinstance(body["log_entries"], list) and len(body["log_entries"]) >= 4
    assert (
        body["summary"]["total_entries"] == len(body["log_entries"])
        or body["summary"]["total_entries"] >= 4
    )

    # DB TaskLog 已写入
    from app.models.task_log import TaskLog

    assert db_session.query(TaskLog).filter(TaskLog.task_id == t.id).count() >= 4
