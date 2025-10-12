"""
合并执行器模块
负责实际的文件合并操作执行
"""

import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from app.engines.connection_manager import HiveConnectionManager
from app.engines.validation_service import MergeTaskValidationService
from app.models.merge_task import MergeTask
from app.utils.merge_logger import MergeLogLevel, MergePhase, MergeTaskLogger
from app.utils.webhdfs_client import WebHDFSClient

logger = logging.getLogger(__name__)


class MergeTaskExecutor:
    """合并任务执行器"""

    def __init__(self, connection_manager: HiveConnectionManager):
        self.connection_manager = connection_manager
        self.validation_service = MergeTaskValidationService(connection_manager)
        self.progress_callback: Optional[Callable[[str, str], None]] = None

    def set_progress_callback(self, callback: Callable[[str, str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback

    def execute_merge(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        """执行合并任务"""
        merge_logger = MergeTaskLogger(task.id)
        start_time = time.time()

        try:
            # 更新任务状态为运行中
            task.status = "running"
            task.started_at = datetime.utcnow()
            self._update_task_progress(
                task, db_session, execution_phase="validation", progress_percentage=0
            )

            merge_logger.log(
                MergePhase.VALIDATION,
                MergeLogLevel.INFO,
                "Starting merge task execution",
            )
            self._report_progress(
                "validation",
                f"Starting merge for {task.database_name}.{task.table_name}",
            )

            # 验证任务
            validation_result = self.validation_service.validate_task(task)
            if not validation_result["valid"]:
                task.status = "failed"
                task.error_message = validation_result["message"]
                db_session.commit()
                return {
                    "success": False,
                    "message": validation_result["message"],
                    "duration": time.time() - start_time,
                }

            # 记录警告
            for warning in validation_result.get("warnings", []):
                merge_logger.log(MergePhase.VALIDATION, MergeLogLevel.WARNING, warning)

            self._update_task_progress(
                task, db_session, execution_phase="preparation", progress_percentage=20
            )

            # 执行统一的影子目录合并策略
            result = self._execute_unified_merge_impl(task, db_session, merge_logger)

            # 更新任务完成状态
            execution_time = time.time() - start_time
            if result["success"]:
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                self._update_task_progress(
                    task,
                    db_session,
                    execution_phase="completed",
                    progress_percentage=100,
                )
                merge_logger.log(
                    MergePhase.COMPLETION,
                    MergeLogLevel.INFO,
                    f"Merge completed successfully in {execution_time:.2f}s",
                )
            else:
                task.status = "failed"
                task.error_message = result.get("message", "Unknown error")
                merge_logger.log(
                    MergePhase.COMPLETION,
                    MergeLogLevel.ERROR,
                    f"Merge failed: {task.error_message}",
                )

            task.execution_time = execution_time
            db_session.commit()

            return result

        except Exception as e:
            logger.error(f"Merge execution failed: {e}")
            task.status = "failed"
            task.error_message = str(e)
            task.execution_time = time.time() - start_time
            db_session.commit()

            merge_logger.log(
                MergePhase.COMPLETION,
                MergeLogLevel.ERROR,
                f"Merge execution failed: {e}",
            )

            return {
                "success": False,
                "message": f"Execution failed: {str(e)}",
                "duration": task.execution_time,
            }

    def _execute_unified_merge_impl(
        self, task: MergeTask, db_session: Session, merge_logger: MergeTaskLogger
    ) -> Dict[str, Any]:
        """执行统一的影子目录合并策略"""
        try:
            self._report_progress("unified_merge", "Analyzing table structure...")
            self._update_task_progress(
                task,
                db_session,
                execution_phase="analyzing_table",
                progress_percentage=20,
            )

            # 获取表路径和格式信息
            table_path = self._get_table_path(task)
            if not table_path:
                raise RuntimeError(
                    f"Unable to determine table path for {task.database_name}.{task.table_name}"
                )

            storage_format = self._get_table_format(task)

            self._report_progress("unified_merge", "Creating shadow directory...")
            self._update_task_progress(
                task,
                db_session,
                execution_phase="creating_shadow",
                progress_percentage=40,
            )

            # 生成影子目录和备份目录路径
            ts = int(time.time())
            if task.partition_filter:
                # 分区表：为特定分区创建影子目录
                partition_path = self._resolve_partition_path(task, table_path)
                parent = (
                    "/".join(p for p in partition_path.rstrip("/").split("/")[:-1])
                    or "/"
                )
                partition_name = partition_path.split("/")[-1]
                shadow_path = f"{parent}/.shadow_{partition_name}_{ts}"
                backup_path = f"{parent}/.backup_{partition_name}_{ts}"
                target_path = partition_path
            else:
                # 非分区表：为整个表创建影子目录
                parent = (
                    "/".join(p for p in table_path.rstrip("/").split("/")[:-1]) or "/"
                )
                shadow_path = f"{parent}/.shadow_merge_{ts}"
                backup_path = f"{parent}/.backup_merge_{ts}"
                target_path = table_path

            merge_logger.log(
                MergePhase.EXECUTION,
                MergeLogLevel.INFO,
                f"Shadow directory: {shadow_path}, Target: {target_path}",
            )

            # 执行影子目录写入
            self._report_progress("unified_merge", "Writing to shadow directory...")
            self._update_task_progress(
                task,
                db_session,
                execution_phase="shadow_write",
                progress_percentage=60,
            )

            table_identifier = f"{task.database_name}.{task.table_name}"
            sql_shadow = f"INSERT OVERWRITE DIRECTORY '{shadow_path}'"
            if storage_format in ("PARQUET", "ORC"):
                sql_shadow += f" STORED AS {storage_format}"

            # 根据是否有分区过滤器构建查询
            if task.partition_filter:
                sql_shadow += (
                    f" SELECT * FROM {table_identifier} WHERE {task.partition_filter}"
                )
            else:
                sql_shadow += f" SELECT * FROM {table_identifier}"

            with self.connection_manager.get_hive_connection(
                task.database_name
            ) as conn:
                cursor = conn.cursor()
                # 设置压缩和优化参数
                try:
                    cursor.execute("SET hive.exec.compress.output=true")
                    cursor.execute(
                        "SET mapreduce.output.fileoutputformat.compress=true"
                    )
                    cursor.execute(
                        "SET mapreduce.output.fileoutputformat.compress.codec=org.apache.hadoop.io.compress.SnappyCodec"
                    )
                    if task.target_file_size is not None and task.target_file_size < 0:
                        cursor.execute("SET hive.exec.reducers.max=1")
                        cursor.execute("SET mapreduce.job.reduces=1")
                except Exception:
                    pass
                cursor.execute(sql_shadow)

            # 验证影子目录数据
            self._report_progress("unified_merge", "Validating shadow directory...")
            self._update_task_progress(
                task,
                db_session,
                execution_phase="validating_shadow",
                progress_percentage=80,
            )

            if not self._validate_shadow_directory(shadow_path):
                raise RuntimeError("Shadow directory validation failed")

            # 执行原子目录切换
            self._report_progress(
                "unified_merge", "Performing atomic directory swap..."
            )
            self._update_task_progress(
                task,
                db_session,
                execution_phase="atomic_swap",
                progress_percentage=90,
            )

            hdfs: WebHDFSClient = self.connection_manager.webhdfs_client

            # 原子切换：目标→备份，影子→目标
            ok1, msg1 = hdfs.move_file(target_path, backup_path)
            if not ok1:
                raise RuntimeError(f"Failed to backup target directory: {msg1}")

            ok2, msg2 = hdfs.move_file(shadow_path, target_path)
            if not ok2:
                # 回滚
                hdfs.move_file(backup_path, target_path)
                raise RuntimeError(f"Failed to move shadow to target: {msg2}")

            merge_logger.log(
                MergePhase.EXECUTION,
                MergeLogLevel.INFO,
                "Unified merge completed successfully",
            )

            return {
                "success": True,
                "message": "Unified merge completed successfully",
                "shadow_path": shadow_path,
                "backup_path": backup_path,
                "target_path": target_path,
                "sql_executed": sql_shadow,
            }

        except Exception as e:
            logger.error(f"Unified merge failed: {e}")
            merge_logger.log(
                MergePhase.EXECUTION, MergeLogLevel.ERROR, f"Unified merge failed: {e}"
            )

            # 尝试清理影子目录
            try:
                if "shadow_path" in locals():
                    hdfs: WebHDFSClient = self.connection_manager.webhdfs_client
                    hdfs.delete_file(shadow_path, recursive=True)
                    merge_logger.log(
                        MergePhase.ROLLBACK,
                        MergeLogLevel.INFO,
                        "Shadow directory cleaned up",
                    )
            except Exception as cleanup_error:
                merge_logger.log(
                    MergePhase.ROLLBACK,
                    MergeLogLevel.ERROR,
                    f"Failed to cleanup shadow directory: {cleanup_error}",
                )

            return {"success": False, "message": f"Unified merge failed: {str(e)}"}

    def _get_table_path(self, task: MergeTask) -> Optional[str]:
        """尝试从 MetaStore/Hive 获取表 LOCATION"""
        try:
            connector = getattr(self.connection_manager, "metastore_connector", None)
            if connector and hasattr(connector, "get_table_location"):
                if not getattr(connector, "_connection", None):
                    connector.connect()
                return connector.get_table_location(task.database_name, task.table_name)
        except Exception:
            pass
        # 兜底：DESCRIBE FORMATTED 解析 Location
        try:
            with self.connection_manager.get_hive_connection(
                task.database_name
            ) as conn:
                cur = conn.cursor()
                cur.execute(
                    f"DESCRIBE FORMATTED {task.database_name}.{task.table_name}"
                )
                for row in cur.fetchall():
                    try:
                        col = str(row[0] if len(row) > 0 else "")
                        val = str(row[1] if len(row) > 1 else "")
                        if col.strip().lower().startswith("location"):
                            return val.strip()
                    except Exception:
                        continue
        except Exception:
            return None
        return None

    def _get_table_format(self, task: MergeTask) -> str:
        """解析表存储格式：PARQUET/ORC/TEXTFILE（默认）"""
        try:
            with self.connection_manager.get_hive_connection(
                task.database_name
            ) as conn:
                cur = conn.cursor()
                cur.execute(
                    f"DESCRIBE FORMATTED {task.database_name}.{task.table_name}"
                )
                for row in cur.fetchall():
                    try:
                        col = str(row[0] if len(row) > 0 else "")
                        val = str(row[1] if len(row) > 1 else "")
                        if "InputFormat" in col:
                            low = val.lower()
                            if "parquet" in low:
                                return "PARQUET"
                            if "orc" in low:
                                return "ORC"
                            return "TEXTFILE"
                    except Exception:
                        continue
        except Exception:
            pass
        return "TEXTFILE"

    def _report_progress(self, phase: str, message: str):
        """报告执行进度"""
        if self.progress_callback:
            self.progress_callback(phase, message)
        logger.info(f"[{phase}] {message}")

    def _update_task_progress(
        self,
        task: MergeTask,
        db_session: Session,
        execution_phase: str = None,
        progress_percentage: float = None,
        estimated_remaining_time: int = None,
        processed_files_count: int = None,
        total_files_count: int = None,
        yarn_application_id: str = None,
        current_operation: str = None,
    ):
        """更新任务的详细进度信息到数据库"""
        try:
            if execution_phase is not None:
                task.execution_phase = execution_phase
            if progress_percentage is not None:
                task.progress_percentage = progress_percentage
            if estimated_remaining_time is not None:
                task.estimated_remaining_time = estimated_remaining_time
            if processed_files_count is not None:
                task.processed_files_count = processed_files_count
            if total_files_count is not None:
                task.total_files_count = total_files_count
            if yarn_application_id is not None:
                task.yarn_application_id = yarn_application_id
            if current_operation is not None:
                task.current_operation = current_operation

            db_session.commit()
            logger.debug(
                f"Updated task {task.id} progress: {execution_phase} - {progress_percentage}%"
            )
        except Exception as e:
            logger.error(f"Failed to update task progress: {e}")
            db_session.rollback()

    def _partition_filter_to_spec(self, partition_filter: str) -> Optional[str]:
        """将分区过滤器转换为分区规格"""
        try:
            # 简单实现：将 "year=2023 AND month=01" 转换为 "year=2023,month=01"
            # 这里需要根据实际情况调整
            import re

            matches = re.findall(r"(\w+)=([^\\s]+)", partition_filter)
            if matches:
                return ",".join([f"{key}='{value}'" for key, value in matches])
            return None
        except Exception:
            return None

    def _resolve_partition_path(self, task: MergeTask, table_path: str) -> str:
        """解析分区路径"""
        try:
            # 简单实现：从partition_filter中提取分区信息
            # 例如："dt='2023-12-01'" -> "dt=2023-12-01"
            import re

            matches = re.findall(r"(\w+)='([^']+)'", task.partition_filter)
            if matches:
                partition_spec = "/".join([f"{key}={value}" for key, value in matches])
                return f"{table_path.rstrip('/')}/{partition_spec}"
            else:
                # 如果解析失败，回退到表路径
                return table_path
        except Exception:
            return table_path

    def _validate_shadow_directory(self, shadow_path: str) -> bool:
        """验证影子目录数据"""
        try:
            hdfs: WebHDFSClient = self.connection_manager.webhdfs_client
            # 检查目录是否存在且包含文件
            status = hdfs.get_file_status(shadow_path)
            if status and status.get("type") == "DIRECTORY":
                # 检查目录是否包含数据文件
                files = hdfs.list_directory(shadow_path)
                return len(files) > 0
            return False
        except Exception as e:
            logger.warning(f"Shadow directory validation failed: {e}")
            return False
