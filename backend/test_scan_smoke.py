import time
import types

import pytest


def test_cluster_scan_smoke(monkeypatch):
    # Lazy imports to avoid side effects
    from app.config.database import engine, Base, SessionLocal
    from app.models.cluster import Cluster
    from app.services.scan_service import scan_task_manager

    # Ensure schema exists
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    # Create a demo cluster (won't actually connect to real services)
    cluster = Cluster(
        name="SMOKE-CLUSTER",
        description="smoke",
        hive_host="localhost",
        hive_port=10000,
        hive_database="default",
        hive_metastore_url="mysql://user:pass@localhost:3306/hive",
        hdfs_namenode_url="http://localhost:9870",
        hdfs_user="hdfs",
        small_file_threshold=128 * 1024 * 1024,
        scan_enabled=True,
    )
    session.add(cluster)
    session.commit()
    session.refresh(cluster)

    # Patch MetaStore + scanner behaviors to avoid real connections
    import app.services.scan_service as scan_service_mod

    class DummyConnector:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get_databases(self):
            return ["db1", "db2"]

    monkeypatch.setattr(scan_service_mod, "MySQLHiveMetastoreConnector", DummyConnector)

    # Mock HybridTableScanner.scan_database_tables to return deterministic stats
    def fake_scan_database_tables(self, db, database_name, table_filter=None, max_tables=None, **kwargs):
        # pretend each DB has 2 tables and 10 files with 2 small files
        return {
            "database": database_name,
            "tables_scanned": 2,
            "successful_tables": 2,
            "failed_tables": 0,
            "partitioned_tables": 0,
            "total_partitions": 0,
            "total_files": 10,
            "total_small_files": 2,
            "scan_duration": 0.01,
            "avg_table_scan_time": 0.005,
            "hdfs_mode": "mock",
            "hdfs_connect_time": 0.0,
            "metastore_query_time": 0.0,
            "original_table_count": 2,
            "filtered_table_count": 2,
            "filtered_by_name": 0,
            "limited_by_count": 0,
            "errors": [],
        }

    import app.monitor.hybrid_table_scanner as scanner_mod
    monkeypatch.setattr(
        scanner_mod.HybridTableScanner, "scan_database_tables", fake_scan_database_tables
    )

    # Trigger a scan (in background thread)
    task_id = scan_task_manager.scan_cluster_with_progress(session, cluster.id, max_tables_per_db=2)

    # Wait for completion (max 5 seconds)
    deadline = time.time() + 5
    status = None
    while time.time() < deadline:
        task = scan_task_manager.get_task(task_id)
        if task and task.status in ("completed", "failed"):
            status = task.status
            break
        time.sleep(0.05)

    assert status == "completed", f"scan not completed, status={status}"

    # Validate progress consistency and no keyword error in logs
    logs = scan_task_manager.get_task_logs(task_id)
    all_msgs = "\n".join([l.message for l in logs])
    assert "unexpected keyword argument" not in all_msgs

    # Validate counters
    task = scan_task_manager.get_task(task_id)
    assert task.completed_items == task.total_items
    # From fake data: 2 DBs * 2 tables = 4 tables; 2 DBs * 10 files = 20 files; 2 DBs * 2 small = 4
    assert task.total_tables_scanned == 4
    assert task.total_files_found == 20
    assert task.total_small_files == 4

    # Cleanup: delete created scan task row then cluster
    from app.models.scan_task import ScanTask as ScanTaskModel
    db_task = session.query(ScanTaskModel).filter(ScanTaskModel.task_id == task_id).first()
    if db_task:
        session.delete(db_task)
        session.commit()
    session.delete(cluster)
    session.commit()
    session.close()
