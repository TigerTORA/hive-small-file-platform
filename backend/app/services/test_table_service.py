"""
测试表生成服务 - 使用Python直接操作Hive和HDFS
"""

import asyncio
import json
import logging
import threading
import traceback
import uuid
from datetime import datetime
from time import monotonic
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.models.cluster import Cluster
from app.models.test_table_task import TestTableTask as TestTableTaskModel
from app.models.test_table_task_log import TestTableTaskLog
from app.schemas.test_table import (
    TestTableCreateRequest,
    TestTableDeleteRequest,
    TestTableTask,
    TestTableVerifyRequest,
    TestTableVerifyResult,
)
from app.services.websocket_service import websocket_manager

logger = logging.getLogger(__name__)


class TestTableService:
    """测试表生成服务"""

    def __init__(self):
        self._last_progress_log: Dict[Tuple[str, str], float] = {}

    def _log_task_event(
        self,
        db: Session,
        task_id: str,
        level: str,
        message: str,
        *,
        phase: Optional[str] = None,
        details: Optional[Any] = None,
        progress: Optional[float] = None,
    ) -> None:
        """Persist a structured log entry for a test-table task."""

        normalized_details: Optional[Any] = None
        if details is not None:
            try:
                json.dumps(details, ensure_ascii=False)
                normalized_details = details
            except TypeError:
                normalized_details = {"text": str(details)}

        entry = TestTableTaskLog(
            task_id=task_id,
            log_level=level.upper(),
            message=str(message),
            phase=phase,
            details=normalized_details,
            progress_percentage=progress,
        )

        try:
            db.add(entry)
            db.commit()
        except Exception as err:
            db.rollback()
            logger.warning(
                "Failed to persist test-table log for task %s: %s", task_id, err
            )

    def _should_emit_progress(
        self, task_id: str, phase: str, *, interval_seconds: float = 5.0
    ) -> bool:
        """Throttle progress日志，避免刷屏但保持稳定输出。"""

        key = (task_id, phase)
        now = monotonic()
        last = self._last_progress_log.get(key, 0.0)
        if now - last >= interval_seconds:
            self._last_progress_log[key] = now
            return True
        return False

    async def create_test_table(
        self, request: TestTableCreateRequest, db: Session
    ) -> TestTableTask:
        """创建测试表"""
        # 验证集群存在
        cluster = db.query(Cluster).filter(Cluster.id == request.cluster_id).first()
        if not cluster:
            raise ValueError(f"集群 {request.cluster_id} 不存在")

        # 创建任务记录
        task_id = str(uuid.uuid4())
        db_task = TestTableTaskModel(
            id=task_id,
            cluster_id=request.cluster_id,
            status="pending",
            config=json.dumps(request.config.dict(), ensure_ascii=False),
            created_time=datetime.utcnow(),
        )

        db.add(db_task)
        db.commit()
        db.refresh(db_task)

        # 启动后台任务
        force_recreate = getattr(request, "force_recreate", False)

        def run_task():
            asyncio.run(
                self._execute_create_task(task_id, request.cluster_id, force_recreate)
            )

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        return TestTableTask(**db_task.to_dict())

    async def _execute_create_task(
        self, task_id: str, cluster_id: int, force_recreate: bool
    ):
        """执行创建任务"""
        # 使用独立的数据库会话
        db = SessionLocal()
        connection_manager = None
        hive_conn = None
        hdfs_client = None

        try:
            task = (
                db.query(TestTableTaskModel)
                .filter(TestTableTaskModel.id == task_id)
                .first()
            )
            cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()

            if not task or not cluster:
                return

            task.status = "running"
            task.started_time = datetime.utcnow()
            task.last_heartbeat = datetime.utcnow()
            db.commit()
            await self._broadcast_task_update_from_db(task)

            config_dict = task.get_config_dict()
            self._log_task_event(
                db,
                task_id,
                "INFO",
                "开始执行测试表生成任务",
                phase="initialization",
                details={"config": config_dict},
                progress=task.progress_percentage,
            )

            # 阶段1: 初始化连接
            from app.engines.connection_manager import HiveConnectionManager

            task.current_phase = "initialization"
            task.current_operation = "初始化Hive和HDFS连接"
            task.progress_percentage = 10.0
            task.last_heartbeat = datetime.utcnow()
            db.commit()
            await self._broadcast_task_update_from_db(task)

            try:
                connection_manager = HiveConnectionManager(cluster)
                hive_conn = connection_manager.get_hive_connection()
                hdfs_client = connection_manager.webhdfs_client
                self._log_task_event(
                    db,
                    task_id,
                    "INFO",
                    "Hive/HDFS 连接创建成功",
                    phase="initialization",
                    details={
                        "hive_host": cluster.hive_host,
                        "hive_port": cluster.hive_port,
                        "hdfs_base_path": config_dict.get("hdfs_base_path"),
                    },
                    progress=task.progress_percentage,
                )
            except Exception as conn_err:
                self._log_task_event(
                    db,
                    task_id,
                    "ERROR",
                    f"建立Hive/HDFS连接失败: {conn_err}",
                    phase="initialization",
                )
                raise

            partition_count = config_dict.get("partition_count", 10)
            files_per_partition = config_dict.get("files_per_partition", 100)
            total_files = partition_count * files_per_partition
            files_created = 0
            files_failed = 0
            failure_samples: List[Dict[str, Any]] = []
            # 强制使用beeline模式进行数据生成
            generation_mode = "beeline"

            # 阶段2: 清理已存在的表和数据（如果需要）
            if force_recreate:
                task.current_phase = "cleanup"
                task.current_operation = "清理已存在的表和数据"
                task.progress_percentage = 20.0
                db.commit()
                await self._broadcast_task_update_from_db(task)

                cleanup_summary = await self._cleanup_existing_data(
                    hive_conn, hdfs_client, config_dict
                )
                level = "WARN" if cleanup_summary.get("errors") else "INFO"
                self._log_task_event(
                    db,
                    task_id,
                    level,
                    "清理历史表和数据完成",
                    phase="cleanup",
                    details=cleanup_summary,
                    progress=task.progress_percentage,
                )

            # 阶段3: 创建HDFS目录
            task.current_phase = "hdfs_setup"
            task.current_operation = "创建HDFS目录结构"
            task.progress_percentage = 20.0
            db.commit()
            await self._broadcast_task_update_from_db(task)
            self._log_task_event(
                db,
                task_id,
                "INFO",
                "准备HDFS目录结构",
                phase="hdfs_setup",
                details={
                    "base_path": config_dict.get(
                        "hdfs_base_path", "/user/test/small_files_test"
                    ),
                    "partition_count": partition_count,
                    "mode": generation_mode,
                },
                progress=task.progress_percentage,
            )

            # beeline模式: 跳过HDFS目录显式创建,由Hive在INSERT数据时自动生成
            self._log_task_event(
                db,
                task_id,
                "INFO",
                "使用Beeline模式，跳过HDFS目录显式创建，由Hive在INSERT数据时自动生成",
                phase="hdfs_setup",
                details={
                    "base_path": config_dict.get(
                        "hdfs_base_path", "/user/test/small_files_test"
                    )
                },
                progress=task.progress_percentage,
            )

            # 阶段4: 创建Hive表
            task.current_phase = "hive_table_creation"
            task.current_operation = "创建Hive表结构"
            task.progress_percentage = 40.0
            db.commit()
            await self._broadcast_task_update_from_db(task)
            self._log_task_event(
                db,
                task_id,
                "INFO",
                "开始创建Hive表",
                phase="hive_table_creation",
                details={
                    "database": config_dict.get("database_name", "test_db"),
                    "table": config_dict.get("table_name", "test_table"),
                },
                progress=task.progress_percentage,
            )

            await self._create_hive_table(hive_conn, config_dict)
            self._log_task_event(
                db,
                task_id,
                "INFO",
                "Hive表创建完成",
                phase="hive_table_creation",
                details={
                    "database": config_dict.get("database_name", "test_db"),
                    "table": config_dict.get("table_name", "test_table"),
                },
                progress=task.progress_percentage,
            )

            # 阶段5: 添加分区
            task.current_phase = "partition_creation"
            task.current_operation = "添加Hive表分区"
            task.progress_percentage = 55.0
            db.commit()
            await self._broadcast_task_update_from_db(task)

            partitions_added, partition_failures = await self._add_partitions(
                task,
                task_id,
                db,
                hive_conn,
                config_dict,
                generation_mode,
                partition_count,
            )
            self._log_task_event(
                db,
                task_id,
                "WARN" if partition_failures else "INFO",
                f"分区创建完成，成功 {partitions_added} 个，失败 {len(partition_failures)} 个",
                phase="partition_creation",
                details={
                    "expected_partitions": partition_count,
                    "added_partitions": partitions_added,
                    "failed_partitions": (
                        partition_failures[:5] if partition_failures else []
                    ),
                },
                progress=task.progress_percentage,
            )
            self._last_progress_log.pop((task_id, "partition_creation"), None)

            if partition_failures:
                failure_message = "分区创建阶段存在失败，任务终止"
                self._log_task_event(
                    db,
                    task_id,
                    "ERROR",
                    failure_message,
                    phase="partition_creation",
                    details={
                        "failed_partitions": partition_failures,
                    },
                )
                raise RuntimeError(failure_message)

            # 阶段6: 生成/加载数据文件
            task.current_phase = "data_generation"
            task.current_operation = f"写入 {total_files} 个测试文件"
            task.progress_percentage = 65.0
            db.commit()
            await self._broadcast_task_update_from_db(task)
            self._log_task_event(
                db,
                task_id,
                "INFO",
                "开始写入测试数据文件",
                phase="data_generation",
                details={
                    "partition_count": partition_count,
                    "files_per_partition": files_per_partition,
                    "expected_files": total_files,
                    "file_size_kb": config_dict.get("file_size_kb", 50),
                    "mode": generation_mode,
                },
                progress=task.progress_percentage,
            )

            # 统一使用beeline模式生成数据
            files_created, files_failed, failure_samples = (
                await self._generate_data_files_hive_insert(
                    task,
                    task_id,
                    db,
                    hive_conn,
                    config_dict,
                    total_files,
                )
            )

            if total_files > 0:
                task.current_operation = f"写入完成 {files_created}/{total_files}"
            if task.progress_percentage < 90.0:
                task.progress_percentage = 90.0
            db.commit()
            await self._broadcast_task_update_from_db(task)

            self._log_task_event(
                db,
                task_id,
                "WARN" if files_failed else "INFO",
                f"数据文件写入完成，成功 {files_created} 个，失败 {files_failed} 个",
                phase="data_generation",
                details={
                    "expected_files": total_files,
                    "successful_files": files_created,
                    "failed_files": files_failed,
                    "mode": generation_mode,
                    "sample_failures": failure_samples[:5] if failure_samples else [],
                },
                progress=task.progress_percentage,
            )
            self._last_progress_log.pop((task_id, "data_generation"), None)

            if files_failed or (total_files and files_created < total_files):
                failure_message = "数据写入阶段存在失败，任务终止"
                self._log_task_event(
                    db,
                    task_id,
                    "ERROR",
                    failure_message,
                    phase="data_generation",
                    details={
                        "successful_files": files_created,
                        "failed_files": files_failed,
                        "expected_files": total_files,
                        "mode": generation_mode,
                        "sample_failures": failure_samples,
                    },
                )
                raise RuntimeError(failure_message)

            # 阶段7: 验证结果
            task.current_phase = "verification"
            task.current_operation = "验证创建结果"
            task.progress_percentage = 95.0
            db.commit()
            await self._broadcast_task_update_from_db(task)

            file_size_kb = config_dict.get("file_size_kb", 50)
            total_size_mb = (files_created * file_size_kb) / 1024
            verification_details = {
                "expected_files": total_files,
                "successful_files": files_created,
                "failed_files": files_failed,
                "added_partitions": partitions_added,
                "file_size_kb": file_size_kb,
                "mode": generation_mode,
                "calculated_total_size_mb": round(total_size_mb, 2),
            }
            self._log_task_event(
                db,
                task_id,
                "INFO",
                "验证阶段完成",
                phase="verification",
                details=verification_details,
                progress=task.progress_percentage,
            )

            task.hdfs_files_created = files_created
            task.hive_partitions_added = partitions_added
            task.total_size_mb = total_size_mb

            # 完成
            task.status = "success"
            task.current_phase = "completed"
            task.current_operation = "创建完成"
            task.progress_percentage = 100.0
            task.completed_time = datetime.utcnow()
            db.commit()
            await self._broadcast_task_update_from_db(task)

            self._log_task_event(
                db,
                task_id,
                "INFO",
                "测试表生成任务成功完成",
                phase="completed",
                details={
                    **verification_details,
                    "completed_at": task.completed_time.isoformat(),
                },
                progress=task.progress_percentage,
            )

            # 自动触发单表扫描,使新表立即出现在表管理界面
            try:
                self._log_task_event(
                    db,
                    task_id,
                    "INFO",
                    "自动触发单表扫描",
                    phase="completed",
                    details={
                        "database": config_dict.get("database_name", "test_db"),
                        "table": config_dict.get("table_name", "test_table"),
                    },
                    progress=task.progress_percentage,
                )

                # 在后台线程中调用扫描API,不阻塞任务完成
                import threading
                import urllib.error
                import urllib.request

                def _trigger_scan():
                    try:
                        url = f"http://localhost:8000/api/v1/tables/scan-table/{cluster.id}/{config_dict.get('database_name', 'test_db')}/{config_dict.get('table_name', 'test_table')}"
                        req = urllib.request.Request(url, method="POST")
                        with urllib.request.urlopen(req, timeout=300) as response:
                            if response.status == 200:
                                logger.info(
                                    f"Auto scan triggered successfully for {config_dict.get('database_name')}.{config_dict.get('table_name')}"
                                )
                            else:
                                logger.warning(
                                    f"Auto scan returned status {response.status}"
                                )
                    except urllib.error.HTTPError as e:
                        logger.warning(f"Auto scan HTTP error: {e.code} - {e.reason}")
                    except Exception as e:
                        logger.warning(f"Auto scan request failed: {e}")

                threading.Thread(target=_trigger_scan, daemon=True).start()
            except Exception as scan_error:
                logger.warning(f"Auto scan after table creation failed: {scan_error}")
                # 扫描失败不影响任务成功状态

            if connection_manager:
                connection_manager.cleanup_connections()

        except Exception as e:
            logger.error(f"Test table creation failed: {e}")
            stacktrace = traceback.format_exc()
            try:
                task = (
                    db.query(TestTableTaskModel)
                    .filter(TestTableTaskModel.id == task_id)
                    .first()
                )
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    task.current_phase = task.current_phase or "error"
                    task.current_operation = f"执行失败: {e}"
                    task.completed_time = datetime.utcnow()
                    db.commit()
                    await self._broadcast_task_update_from_db(task)
                    self._log_task_event(
                        db,
                        task_id,
                        "ERROR",
                        f"任务执行失败: {e}",
                        phase=task.current_phase or "error",
                        details={
                            "error": str(e),
                            "stacktrace": stacktrace,
                        },
                    )
            except Exception:
                db.rollback()
        finally:
            if connection_manager:
                try:
                    connection_manager.cleanup_connections()
                except Exception as cleanup_err:
                    logger.warning(
                        "Failed to cleanup connections for test table task %s: %s",
                        task_id,
                        cleanup_err,
                    )
            db.close()

    async def _cleanup_existing_data(self, hive_conn, hdfs_client, config_dict):
        """清理已存在的表和数据"""
        database_name = config_dict.get("database_name", "test_db")
        table_name = config_dict.get("table_name", "test_table")
        hdfs_base_path = config_dict.get(
            "hdfs_base_path", "/user/test/small_files_test"
        )

        summary: Dict[str, Any] = {
            "database": database_name,
            "table": table_name,
            "hdfs_path": hdfs_base_path,
            "hive_table_dropped": False,
            "hdfs_deleted": False,
            "errors": [],
        }

        try:
            cursor = hive_conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {database_name}.{table_name}")
            cursor.close()
            summary["hive_table_dropped"] = True
        except Exception as e:
            logger.warning(f"Failed to drop Hive table: {e}")
            summary["errors"].append({"scope": "hive", "error": str(e)})

        try:
            hdfs_client.delete_directory(hdfs_base_path, recursive=True)
            summary["hdfs_deleted"] = True
        except Exception as e:
            logger.warning(f"Failed to delete HDFS directory: {e}")
            summary["errors"].append({"scope": "hdfs", "error": str(e)})

        return summary

    async def _create_hdfs_structure(self, hdfs_client, config_dict):
        """创建HDFS目录结构"""
        hdfs_base_path = config_dict.get(
            "hdfs_base_path", "/user/test/small_files_test"
        )
        partition_count = config_dict.get("partition_count", 10)

        # 创建主目录
        hdfs_client.create_directory(hdfs_base_path)

        # 创建分区目录
        created_dirs = 0
        for i in range(partition_count):
            partition_dir = f"{hdfs_base_path}/partition_{i:04d}"
            hdfs_client.create_directory(partition_dir)
            created_dirs += 1

        return created_dirs

    async def _generate_data_files_webhdfs(
        self,
        task: TestTableTaskModel,
        task_id: str,
        db: Session,
        hdfs_client,
        config_dict,
        total_files: int,
    ) -> tuple[int, int, List[Dict[str, Any]]]:
        """生成数据文件，并返回成功/失败统计."""

        hdfs_base_path = config_dict.get(
            "hdfs_base_path", "/user/test/small_files_test"
        )
        partition_count = config_dict.get("partition_count", 10)
        files_per_partition = config_dict.get("files_per_partition", 100)
        file_size_kb = config_dict.get("file_size_kb", 50)

        content_size_bytes = file_size_kb * 1024
        sample_line = "test_data_row_with_some_content_to_reach_target_size\n"
        lines_needed = max(1, content_size_bytes // len(sample_line.encode("utf-8")))
        file_content = sample_line * lines_needed

        files_created = 0
        files_failed = 0
        failure_samples: List[Dict[str, Any]] = []
        progress_start = 65.0
        progress_span = 25.0

        for partition_id in range(partition_count):
            partition_value = f"partition_{partition_id:04d}"
            partition_dir = f"{hdfs_base_path}/{partition_value}"

            created_in_partition = 0
            failed_in_partition: List[Dict[str, Any]] = []

            for file_id in range(files_per_partition):
                file_path = f"{partition_dir}/data_{file_id:06d}.txt"
                try:
                    hdfs_client.write_file(file_path, file_content.encode("utf-8"))
                    files_created += 1
                    created_in_partition += 1
                except Exception as e:
                    files_failed += 1
                    error_entry = {"file": file_path, "error": str(e)}
                    failed_in_partition.append(error_entry)
                    if len(failure_samples) < 20:
                        failure_samples.append(error_entry)
                    logger.warning(f"Failed to create file {file_path}: {e}")

                processed = files_created + files_failed
                if total_files > 0 and self._should_emit_progress(
                    task_id, "data_generation", interval_seconds=3.0
                ):
                    phase_ratio = min(1.0, processed / max(1, total_files))
                    task.progress_percentage = (
                        progress_start + phase_ratio * progress_span
                    )
                    task.current_operation = f"写入数据文件 {processed}/{total_files}"
                    db.commit()
                    await self._broadcast_task_update_from_db(task)
                    self._log_task_event(
                        db,
                        task_id,
                        "INFO",
                        "数据文件生成进度更新",
                        phase="data_generation",
                        details={
                            "processed_files": processed,
                            "total_files": total_files,
                            "current_partition": partition_value,
                        },
                        progress=task.progress_percentage,
                    )

            level = "WARN" if failed_in_partition else "INFO"
            self._log_task_event(
                db,
                task_id,
                level,
                f"分区 {partition_value} 数据写入完成，成功 {created_in_partition} 个，失败 {len(failed_in_partition)} 个",
                phase="data_generation",
                details={
                    "partition": partition_value,
                    "successful_files": created_in_partition,
                    "failed_files": len(failed_in_partition),
                    "errors": failed_in_partition[:5],
                },
            )

        return files_created, files_failed, failure_samples

    async def _create_hive_table(self, hive_conn, config_dict):
        """创建Hive表"""
        database_name = config_dict.get("database_name", "test_db")
        table_name = config_dict.get("table_name", "test_table")
        hdfs_base_path = config_dict.get(
            "hdfs_base_path", "/user/test/small_files_test"
        )

        cursor = hive_conn.cursor()

        # 创建数据库（如果不存在）
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")

        # 创建外部表
        create_table_sql = f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS {database_name}.{table_name} (
            data_content STRING
        )
        PARTITIONED BY (partition_id STRING)
        STORED AS TEXTFILE
        LOCATION '{hdfs_base_path}'
        """

        cursor.execute(create_table_sql)
        cursor.close()

    async def _add_partitions(
        self,
        task: TestTableTaskModel,
        task_id: str,
        db: Session,
        hive_conn,
        config_dict,
        generation_mode: str,
        partition_count: int,
    ) -> tuple[int, List[Dict[str, Any]]]:
        """添加分区，并返回成功数量与失败详情."""

        database_name = config_dict.get("database_name", "test_db")
        table_name = config_dict.get("table_name", "test_table")

        cursor = hive_conn.cursor()
        partitions_added = 0
        partition_failures: List[Dict[str, Any]] = []

        # beeline模式: 不指定LOCATION,使用Hive默认路径
        for partition_id in range(partition_count):
            partition_value = f"partition_{partition_id:04d}"
            add_partition_sql = f"""
            ALTER TABLE {database_name}.{table_name}
            ADD IF NOT EXISTS PARTITION (partition_id='{partition_value}')
            """

            try:
                cursor.execute(add_partition_sql)
                partitions_added += 1
            except Exception as e:
                logger.warning(f"Failed to add partition {partition_value}: {e}")
                error_entry: Dict[str, Any] = {
                    "partition": partition_value,
                    "error": str(e),
                }
                partition_failures.append(error_entry)
                self._log_task_event(
                    db,
                    task_id,
                    "WARN",
                    f"分区 {partition_value} 添加失败: {e}",
                    phase="partition_creation",
                    details=error_entry,
                )
            finally:
                processed_partitions = partitions_added + len(partition_failures)
                if partition_count > 0 and self._should_emit_progress(
                    task_id, "partition_creation", interval_seconds=4.0
                ):
                    phase_ratio = processed_partitions / partition_count
                    task.progress_percentage = 85.0 + min(1.0, phase_ratio) * 10.0
                    task.current_operation = (
                        f"添加分区 {processed_partitions}/{partition_count}"
                    )
                    db.commit()
                    await self._broadcast_task_update_from_db(task)
                    self._log_task_event(
                        db,
                        task_id,
                        "INFO",
                        "分区创建进度更新",
                        phase="partition_creation",
                        details={
                            "processed_partitions": processed_partitions,
                            "total_partitions": partition_count,
                            "last_partition": partition_value,
                        },
                        progress=task.progress_percentage,
                    )

        cursor.close()
        return partitions_added, partition_failures

    async def _generate_data_files_hive_insert(
        self,
        task: TestTableTaskModel,
        task_id: str,
        db: Session,
        hive_conn,
        config_dict,
        total_files: int,
    ) -> tuple[int, int, List[Dict[str, Any]]]:
        """通过 Hive LOAD DATA LOCAL 写入测试数据文件."""

        partition_count = config_dict.get("partition_count", 10)
        files_per_partition = config_dict.get("files_per_partition", 100)
        file_size_kb = config_dict.get("file_size_kb", 50)
        database_name = config_dict.get("database_name", "test_db")
        table_name = config_dict.get("table_name", "test_table")

        content_size_bytes = max(1, file_size_kb * 1024)

        files_created = 0
        files_failed = 0
        failure_samples: List[Dict[str, Any]] = []

        progress_start = 65.0
        progress_span = 25.0

        cursor = hive_conn.cursor()

        # 禁用Hive小文件自动合并,确保每次INSERT生成独立文件
        try:
            cursor.execute("SET hive.merge.mapfiles=false")
            cursor.execute("SET hive.merge.mapredfiles=false")
            cursor.execute("SET hive.merge.tezfiles=false")
            logger.info("已禁用Hive merge,每次INSERT将生成独立文件")
        except Exception as e:
            logger.warning(f"设置Hive merge参数失败,可能会导致文件被自动合并: {e}")

        # 强制每条记录独立INSERT,确保生成独立的小文件
        # 批量INSERT会导致Hive将多条记录写入同一文件,无法达成小文件测试目的
        try:
            for partition_id in range(partition_count):
                partition_value = f"partition_{partition_id:04d}"
                partition_literal = partition_value.replace("'", "''")

                created_in_partition = 0
                errors_in_partition: List[Dict[str, Any]] = []

                # 逐条插入:每条记录生成独立文件
                for file_id in range(files_per_partition):
                    metadata = (
                        f"partition={partition_value};file={file_id:06d};"
                        f"ts={datetime.utcnow().isoformat()}"
                    )
                    escaped_metadata = metadata.replace("'", "''")
                    filler_length = max(0, content_size_bytes - len(metadata))

                    if filler_length > 0:
                        content_expr = f"CONCAT('{escaped_metadata}', REPEAT('x', {filler_length}))"
                    else:
                        content_expr = f"'{escaped_metadata}'"

                    single_insert_sql = (
                        f"INSERT INTO TABLE {database_name}.{table_name} "
                        f"PARTITION (partition_id='{partition_literal}') "
                        f"VALUES ({content_expr})"
                    )

                    try:
                        cursor.execute(single_insert_sql)
                        files_created += 1
                        created_in_partition += 1
                    except Exception as single_err:
                        files_failed += 1
                        error_entry = {
                            "partition": partition_value,
                            "file_index": file_id,
                            "error": str(single_err),
                            "insert_sql": single_insert_sql,
                        }
                        errors_in_partition.append(error_entry)
                        if len(failure_samples) < 20:
                            failure_samples.append(error_entry)

                    processed = files_created + files_failed
                    if total_files > 0 and self._should_emit_progress(
                        task_id,
                        "data_generation",
                        interval_seconds=10.0,  # 降低日志频率
                    ):
                        phase_ratio = min(1.0, processed / max(1, total_files))
                        task.progress_percentage = (
                            progress_start + phase_ratio * progress_span
                        )
                        task.current_operation = (
                            f"写入测试文件 {min(processed, total_files)}/{total_files}"
                        )
                        db.commit()
                        await self._broadcast_task_update_from_db(task)
                        self._log_task_event(
                            db,
                            task_id,
                            "INFO",
                            "数据写入进度更新",
                            phase="data_generation",
                            details={
                                "processed_files": min(processed, total_files),
                                "total_files": total_files,
                                "current_partition": partition_value,
                            },
                            progress=task.progress_percentage,
                        )

                level = "WARN" if errors_in_partition else "INFO"
                self._log_task_event(
                    db,
                    task_id,
                    level,
                    f"分区 {partition_value} 数据插入完成，成功 {created_in_partition} 个，失败 {len(errors_in_partition)} 个",
                    phase="data_generation",
                    details={
                        "partition": partition_value,
                        "successful_files": created_in_partition,
                        "failed_files": len(errors_in_partition),
                        "errors": errors_in_partition[:5],
                    },
                )

            return files_created, files_failed, failure_samples
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def _update_heartbeat(self, task, db: Session):
        """更新任务心跳并提交"""
        task.last_heartbeat = datetime.utcnow()
        db.commit()

    def check_and_mark_timeout_tasks(self, db: Session, timeout_minutes: int = 30):
        """检测并标记超时任务 (无心跳超过阈值的运行中任务)"""
        from datetime import timedelta

        threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        # 查找超时任务: status=running 且 last_heartbeat < threshold (或为NULL)
        timeout_tasks = (
            db.query(TestTableTaskModel)
            .filter(TestTableTaskModel.status == "running")
            .filter(
                (TestTableTaskModel.last_heartbeat < threshold)
                | (TestTableTaskModel.last_heartbeat == None)
            )
            .all()
        )

        marked_count = 0
        for task in timeout_tasks:
            # 额外检查: 确保任务启动超过超时时间 (避免误杀刚启动的任务)
            if (
                task.started_time
                and (datetime.utcnow() - task.started_time).total_seconds()
                < timeout_minutes * 60
            ):
                continue

            task.status = "failed"
            task.completed_time = datetime.utcnow()
            task.error_message = f"任务执行超时 (超过 {timeout_minutes} 分钟无响应)"
            task.current_operation = "任务超时终止"

            self._log_task_event(
                db,
                task.id,
                "ERROR",
                f"任务因心跳超时被系统终止 (阈值: {timeout_minutes}分钟)",
                phase=task.current_phase or "unknown",
                details={
                    "last_heartbeat": (
                        str(task.last_heartbeat) if task.last_heartbeat else "NULL"
                    ),
                    "timeout_threshold_minutes": timeout_minutes,
                    "started_time": str(task.started_time),
                },
                progress=task.progress_percentage,
            )

            marked_count += 1
            logger.warning(
                f"Marked timeout task {task.id} as failed (last_heartbeat: {task.last_heartbeat})"
            )

        if marked_count > 0:
            db.commit()
            logger.info(f"Marked {marked_count} timeout tasks as failed")

        return marked_count

    async def _broadcast_task_update_from_db(self, task):
        """从数据库任务记录广播更新"""
        try:
            await websocket_manager.broadcast_task_update(
                {
                    "id": task.id,
                    "status": task.status,
                    "progress": task.progress_percentage,
                    "current_phase": task.current_phase,
                    "current_operation": task.current_operation,
                    "error_message": task.error_message,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast task update: {e}")

    def list_active_tasks(self, db: Session) -> list[TestTableTask]:
        """获取活跃任务列表"""
        db_tasks = (
            db.query(TestTableTaskModel)
            .order_by(TestTableTaskModel.created_time.desc())
            .limit(100)
            .all()
        )
        return [TestTableTask(**task.to_dict()) for task in db_tasks]

    def get_task(self, task_id: str, db: Session) -> Optional[TestTableTask]:
        """获取任务详情"""
        db_task = (
            db.query(TestTableTaskModel)
            .filter(TestTableTaskModel.id == task_id)
            .first()
        )
        if db_task:
            return TestTableTask(**db_task.to_dict())
        return None

    async def delete_test_table(
        self, request: TestTableDeleteRequest, db: Session
    ) -> Dict[str, str]:
        """删除测试表"""
        try:
            # 获取集群信息
            cluster = db.query(Cluster).filter(Cluster.id == request.cluster_id).first()
            if not cluster:
                return {"message": "错误", "error": f"集群 {request.cluster_id} 不存在"}

            # 建立连接
            from app.engines.connection_manager import HiveConnectionManager

            connection_manager = HiveConnectionManager(cluster)
            hive_conn = connection_manager.get_hive_connection()
            hdfs_client = connection_manager.webhdfs_client

            results = []

            # 删除Hive表
            try:
                cursor = hive_conn.cursor()
                drop_sql = (
                    f"DROP TABLE IF EXISTS {request.database_name}.{request.table_name}"
                )
                cursor.execute(drop_sql)
                cursor.close()
                results.append(
                    f"成功删除Hive表 {request.database_name}.{request.table_name}"
                )
            except Exception as e:
                results.append(f"删除Hive表失败: {str(e)}")

            # 删除HDFS数据
            if request.delete_hdfs_data:
                try:
                    # 尝试从数据库中查找对应任务配置以获取实际hdfs_base_path
                    task = (
                        db.query(TestTableTaskModel)
                        .filter(TestTableTaskModel.cluster_id == request.cluster_id)
                        .filter(
                            TestTableTaskModel.database_name == request.database_name
                        )
                        .filter(TestTableTaskModel.table_name == request.table_name)
                        .order_by(TestTableTaskModel.created_time.desc())
                        .first()
                    )

                    if task:
                        config_dict = task.get_config_dict()
                        table_path = config_dict.get(
                            "hdfs_base_path",
                            f"/user/test/small_files_test/{request.table_name}",
                        )
                    else:
                        # 回退方案: 尝试从Hive表元数据获取LOCATION,或使用默认路径
                        try:
                            cursor = hive_conn.cursor()
                            cursor.execute(
                                f"DESCRIBE FORMATTED {request.database_name}.{request.table_name}"
                            )
                            rows = cursor.fetchall()
                            cursor.close()

                            location = None
                            for row in rows:
                                if (
                                    len(row) >= 2
                                    and str(row[0]).strip().lower() == "location:"
                                ):
                                    location = str(row[1]).strip()
                                    break

                            if location and location.startswith("hdfs://"):
                                # 提取HDFS路径部分 (去除hdfs://nameservice/部分)
                                from urllib.parse import urlparse

                                parsed = urlparse(location)
                                table_path = parsed.path
                            else:
                                table_path = (
                                    location
                                    or f"/user/test/small_files_test/{request.table_name}"
                                )
                        except Exception:
                            table_path = (
                                f"/user/test/small_files_test/{request.table_name}"
                            )

                    # 尝试删除HDFS目录
                    hdfs_client.delete(table_path, recursive=True)
                    results.append(f"成功删除HDFS数据目录: {table_path}")
                except Exception as e:
                    results.append(f"删除HDFS数据失败: {str(e)}")

            return {"message": "删除操作完成", "details": results}

        except Exception as e:
            logger.error(f"删除测试表失败: {str(e)}")
            return {"message": "错误", "error": str(e)}

    async def verify_test_table(
        self, request: TestTableVerifyRequest, db: Session
    ) -> TestTableVerifyResult:
        """验证测试表"""
        try:
            # 获取集群信息
            cluster = db.query(Cluster).filter(Cluster.id == request.cluster_id).first()
            if not cluster:
                return TestTableVerifyResult(
                    table_exists=False,
                    partitions_count=0,
                    hdfs_files_count=0,
                    total_size_mb=0.0,
                    verification_passed=False,
                    issues=[f"集群 {request.cluster_id} 不存在"],
                )

            # 建立连接
            from app.engines.connection_manager import HiveConnectionManager

            connection_manager = HiveConnectionManager(cluster)
            hive_conn = connection_manager.get_hive_connection()
            hdfs_client = connection_manager.webhdfs_client

            issues = []
            table_exists = False
            partitions_count = 0
            hdfs_files_count = 0
            total_size_mb = 0.0
            data_rows_count = None

            # 检查表是否存在
            try:
                cursor = hive_conn.cursor()
                cursor.execute(
                    f"SHOW TABLES IN {request.database_name} LIKE '{request.table_name}'"
                )
                tables = cursor.fetchall()
                table_exists = len(tables) > 0
                cursor.close()

                if not table_exists:
                    issues.append(
                        f"表 {request.database_name}.{request.table_name} 不存在"
                    )

            except Exception as e:
                issues.append(f"检查表存在性失败: {str(e)}")

            # 如果表存在，检查分区
            if table_exists:
                try:
                    cursor = hive_conn.cursor()
                    cursor.execute(
                        f"SHOW PARTITIONS {request.database_name}.{request.table_name}"
                    )
                    partitions = cursor.fetchall()
                    partitions_count = len(partitions)
                    cursor.close()

                    if partitions_count == 0:
                        issues.append("表没有分区")

                except Exception as e:
                    issues.append(f"检查分区失败: {str(e)}")

                # 检查数据行数
                try:
                    cursor = hive_conn.cursor()
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {request.database_name}.{request.table_name}"
                    )
                    result = cursor.fetchone()
                    data_rows_count = result[0] if result else 0
                    cursor.close()

                except Exception as e:
                    issues.append(f"检查数据行数失败: {str(e)}")

            # 检查HDFS文件
            try:
                table_path = f"/user/test/small_files_test/{request.table_name}"
                try:
                    # 递归列出所有文件
                    files = hdfs_client.list(table_path, status=True)
                    hdfs_files_count = 0
                    total_size_bytes = 0

                    for file_info in files:
                        if file_info["type"] == "FILE" and file_info[
                            "pathSuffix"
                        ].endswith(".txt"):
                            hdfs_files_count += 1
                            total_size_bytes += file_info["length"]

                    total_size_mb = total_size_bytes / (1024 * 1024)

                    if hdfs_files_count == 0:
                        issues.append("HDFS中没有找到数据文件")

                except Exception as e:
                    issues.append(f"检查HDFS文件失败: {str(e)}")

            except Exception as e:
                issues.append(f"HDFS路径访问失败: {str(e)}")

            # 判断验证是否通过
            verification_passed = (
                table_exists
                and partitions_count > 0
                and hdfs_files_count > 0
                and len(issues) == 0
            )

            return TestTableVerifyResult(
                table_exists=table_exists,
                partitions_count=partitions_count,
                hdfs_files_count=hdfs_files_count,
                total_size_mb=total_size_mb,
                data_rows_count=data_rows_count,
                verification_passed=verification_passed,
                issues=issues,
            )

        except Exception as e:
            logger.error(f"验证测试表失败: {str(e)}")
            return TestTableVerifyResult(
                table_exists=False,
                partitions_count=0,
                hdfs_files_count=0,
                total_size_mb=0.0,
                verification_passed=False,
                issues=[f"验证过程出错: {str(e)}"],
            )


# 全局服务实例
test_table_service = TestTableService()
