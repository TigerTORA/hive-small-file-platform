from datetime import datetime, timedelta

from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.models.scan_task import ScanTask
from app.models.scan_task_log import ScanTaskLogDB
from app.models.task_log import TaskLog


def seed_story_6_11_demo(session):
  cluster = Cluster(
      name="Story6.11 Demo Cluster",
      description="Seeded for Story 6.11 API tests",
      hive_host="localhost",
      hive_port=10000,
      hive_database="default",
      hive_metastore_url="mysql://user:pass@localhost:3306/hive",
      hdfs_namenode_url="http://localhost:9870/webhdfs/v1",
      hdfs_user="hdfs",
      status="active",
  )
  session.add(cluster)
  session.commit()
  session.refresh(cluster)

  start = datetime.utcnow() - timedelta(minutes=5)
  scan_task = ScanTask(
      task_id="TEST-STORY-6-11-SCAN",
      cluster_id=cluster.id,
      task_type="cluster",
      task_name="Story 6.11 Demo Scan",
      status="completed",
      total_items=10,
      completed_items=10,
      total_tables_scanned=10,
      total_files_found=123,
      total_small_files=34,
      start_time=start,
      end_time=start + timedelta(minutes=2),
      duration=120,
  )
  session.add(scan_task)
  session.commit()
  session.refresh(scan_task)

  session.add_all(
      [
          ScanTaskLogDB(
              scan_task_id=scan_task.id,
              level="INFO",
              message="开始扫描 Story 6.11 集群",
              database_name="demo_db",
              table_name=None,
          ),
          ScanTaskLogDB(
              scan_task_id=scan_task.id,
              level="INFO",
              message="扫描完成，发现 34 个小文件",
              database_name=None,
              table_name=None,
          ),
      ]
  )

  success_task = MergeTask(
      cluster_id=cluster.id,
      task_name="Story 6.11 Merge Success",
      database_name="demo_db",
      table_name="demo_orders",
      partition_filter="dt='2025-01-01'",
      target_file_size=256 * 1024 * 1024,
      target_storage_format="PARQUET",
      target_compression="SNAPPY",
      use_ec=False,
      status="success",
      files_before=180,
      files_after=6,
      size_saved=2 * 1024 * 1024 * 1024,
      started_time=start - timedelta(minutes=3),
      completed_time=start - timedelta(minutes=1),
  )
  failed_task = MergeTask(
      cluster_id=cluster.id,
      task_name="Story 6.11 Merge Failed",
      database_name="demo_db",
      table_name="demo_events",
      partition_filter="dt='2025-01-02'",
      target_file_size=256 * 1024 * 1024,
      target_storage_format="PARQUET",
      target_compression="SNAPPY",
      use_ec=False,
      status="failed",
      error_message="模拟失败：Hive 报错",
      files_before=200,
      files_after=None,
      size_saved=None,
      started_time=start - timedelta(minutes=2),
      completed_time=start - timedelta(minutes=1, seconds=30),
  )
  session.add_all([success_task, failed_task])
  session.commit()
  session.refresh(success_task)
  session.refresh(failed_task)

  session.add_all(
      [
          TaskLog(
              task_id=success_task.id,
              log_level="INFO",
              message="任务开始：准备合并 demo_db.demo_orders",
              phase="initialization",
              progress_percentage=0.0,
          ),
          TaskLog(
              task_id=success_task.id,
              log_level="INFO",
              message="任务成功完成",
              phase="completed",
              progress_percentage=100.0,
          ),
          TaskLog(
              task_id=failed_task.id,
              log_level="INFO",
              message="任务开始：准备合并 demo_db.demo_events",
              phase="initialization",
              progress_percentage=0.0,
          ),
          TaskLog(
              task_id=failed_task.id,
              log_level="ERROR",
              message="Hive 执行失败：权限不足",
              phase="merging",
              progress_percentage=45.0,
          ),
      ]
  )
  session.commit()

  return cluster, scan_task, success_task, failed_task


def test_story_6_11_endpoints(client, db_session):
  cluster, scan_task, success_task, failed_task = seed_story_6_11_demo(db_session)

  # 列出所有任务
  resp = client.get("/api/v1/tasks", params={"cluster_id": cluster.id})
  assert resp.status_code == 200
  data = resp.json()
  names = {item["task_name"] for item in data}
  assert "Story 6.11 Demo Scan" in names
  assert "Story 6.11 Merge Success" in names
  assert "Story 6.11 Merge Failed" in names

  # 验证扫描任务和日志
  scan_resp = client.get("/api/v1/scan-tasks/", params={"cluster_id": cluster.id})
  assert scan_resp.status_code == 200
  scan_tasks = scan_resp.json()
  assert any(task["task_name"] == "Story 6.11 Demo Scan" for task in scan_tasks)

  logs_resp = client.get(f"/api/v1/scan-tasks/{scan_task.task_id}/logs")
  assert logs_resp.status_code == 200
  logs = logs_resp.json()
  assert any("开始扫描" in log["message"] for log in logs)

  # 验证合并任务日志
  merge_logs = client.get(f"/api/v1/tasks/{success_task.id}/logs")
  assert merge_logs.status_code == 200
  merge_log_messages = [log["message"] for log in merge_logs.json()]
  assert any("任务成功完成" in msg for msg in merge_log_messages)

  failed_logs = client.get(f"/api/v1/tasks/{failed_task.id}/logs")
  assert failed_logs.status_code == 200
  assert any("Hive 执行失败" in log["message"] for log in failed_logs.json())
