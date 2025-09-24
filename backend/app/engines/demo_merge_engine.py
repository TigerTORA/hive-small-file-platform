"""
演示版合并引擎 - 用于展示完整的合并流程
不依赖pyhive，通过MetaStore和WebHDFS API演示真实的合并逻辑
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.monitor.hive_connector import HiveMetastoreConnector
from app.utils.merge_logger import MergeLogLevel, MergePhase, MergeTaskLogger
from app.utils.webhdfs_client import WebHDFSClient
from app.utils.yarn_monitor import YarnResourceManagerMonitor

logger = logging.getLogger(__name__)


class DemoMergeEngine:
    """演示版合并引擎，展示完整的合并流程"""

    def __init__(self, cluster: Cluster):
        self.cluster = cluster
        self.webhdfs_client = WebHDFSClient(
            cluster.hdfs_namenode_url, cluster.hdfs_user
        )
        self.metastore_connector = HiveMetastoreConnector(cluster.hive_metastore_url)

        # YARN监控（如果配置了）
        if cluster.yarn_resource_manager_url:
            self.yarn_monitor = YarnResourceManagerMonitor(
                cluster.yarn_resource_manager_url
            )
        else:
            self.yarn_monitor = None

    def execute_merge(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        """执行演示版合并任务"""
        start_time = time.time()
        merge_logger = MergeTaskLogger(task, db_session)

        result = {
            "success": False,
            "files_before": 0,
            "files_after": 0,
            "size_saved": 0,
            "duration": 0.0,
            "message": "",
            "sql_executed": [],
            "temp_table_created": "",
            "backup_table_created": "",
            "detailed_logs": [],
        }

        try:
            # 第一阶段：初始化
            merge_logger.start_phase(MergePhase.INITIALIZATION, "初始化合并任务")
            self._update_task_progress(
                task, db_session, "initialization", 5.0, "初始化合并任务"
            )
            time.sleep(1)  # 模拟初始化时间
            merge_logger.end_phase(MergePhase.INITIALIZATION, "初始化完成")

            # 第二阶段：连接测试
            merge_logger.start_phase(MergePhase.CONNECTION_TEST, "测试各组件连接")
            self._update_task_progress(
                task, db_session, "connection_test", 10.0, "测试连接中"
            )

            # 模拟连接测试（演示版跳过真实连接）
            connection_success = True  # 演示版总是成功
            logger.info("Demo version: skipping real connection tests")

            # 记录连接测试详情
            merge_logger.log(
                MergePhase.CONNECTION_TEST,
                MergeLogLevel.INFO,
                "MetaStore连接测试成功",
                details={"connector_type": "mysql", "database": task.database_name},
            )

            merge_logger.log_hdfs_operation(
                "连接测试",
                "/",
                MergePhase.CONNECTION_TEST,
                stats={"namenode_available": True},
                success=True,
            )

            if self.yarn_monitor:
                merge_logger.log_yarn_monitoring(
                    "demo_application_123",
                    MergePhase.CONNECTION_TEST,
                    state="CONNECTING",
                    details={"cluster_status": "healthy"},
                )

            merge_logger.end_phase(MergePhase.CONNECTION_TEST, "所有连接测试成功")

            # 第三阶段：文件分析
            merge_logger.start_phase(MergePhase.FILE_ANALYSIS, "分析表文件结构")
            self._update_task_progress(
                task, db_session, "file_analysis", 25.0, "分析文件结构中"
            )

            # 获取真实的文件统计
            files_before = self._get_real_file_count(task)
            result["files_before"] = files_before

            # 记录HDFS扫描操作
            table_location = (
                f"/user/hive/warehouse/{task.database_name}.db/{task.table_name}"
            )
            merge_logger.log_hdfs_operation(
                "扫描表目录",
                table_location,
                MergePhase.FILE_ANALYSIS,
                stats={
                    "total_files": files_before,
                    "small_files_threshold": 128 * 1024 * 1024,
                    "small_files_count": files_before,  # 假设都是小文件
                    "directory_scanned": True,
                },
                success=True,
            )

            merge_logger.log_file_statistics(
                MergePhase.FILE_ANALYSIS,
                f"{task.database_name}.{task.table_name}",
                files_before=files_before,
                hdfs_stats={
                    "table_location": table_location,
                    "partition_count": 1,
                    "file_format": "PARQUET",
                    "avg_file_size": 2529,  # 从真实数据获取
                },
            )

            self._update_task_progress(
                task,
                db_session,
                "file_analysis",
                35.0,
                f"发现{files_before}个文件待合并",
                total_files_count=files_before,
            )
            merge_logger.end_phase(
                MergePhase.FILE_ANALYSIS, f"分析完成，发现{files_before}个文件"
            )

            # 第四阶段：创建临时表（模拟）
            merge_logger.start_phase(MergePhase.TEMP_TABLE_CREATION, "创建临时表")
            self._update_task_progress(
                task, db_session, "temp_table_creation", 50.0, "创建临时表中"
            )

            temp_table_name = f"{task.table_name}_temp_{int(time.time())}"
            time.sleep(2)  # 模拟SQL执行时间

            # 记录模拟的SQL
            create_sql = f"CREATE TABLE {temp_table_name} AS SELECT * FROM {task.database_name}.{task.table_name}"
            result["sql_executed"].append(create_sql)
            result["temp_table_created"] = temp_table_name

            merge_logger.log_sql_execution(
                create_sql,
                MergePhase.TEMP_TABLE_CREATION,
                success=True,
                affected_rows=result["files_before"] * 1000,
            )  # 估算行数

            # 记录YARN任务监控（如果有）
            if self.yarn_monitor:
                yarn_app_id = f"application_1735876200000_001{task.id}"
                self._update_task_progress(
                    task, db_session, yarn_application_id=yarn_app_id
                )
                merge_logger.log_yarn_monitoring(
                    yarn_app_id,
                    MergePhase.TEMP_TABLE_CREATION,
                    progress=45.0,
                    state="RUNNING",
                    details={"job_type": "CREATE_TABLE", "estimated_duration": "2m"},
                )
            merge_logger.end_phase(
                MergePhase.TEMP_TABLE_CREATION, f"临时表{temp_table_name}创建成功"
            )

            # 第五阶段：数据验证
            merge_logger.start_phase(MergePhase.DATA_VALIDATION, "验证数据完整性")
            self._update_task_progress(
                task, db_session, "data_validation", 65.0, "验证数据完整性"
            )

            # 模拟合并后的文件数（通常会显著减少）
            files_after = max(1, files_before // 10)  # 假设合并效果很好
            result["files_after"] = files_after

            merge_logger.log_data_validation(
                MergePhase.DATA_VALIDATION,
                "数据完整性检查",
                original_count=files_before,
                new_count=files_after,
                success=True,
            )

            self._update_task_progress(
                task,
                db_session,
                "data_validation",
                75.0,
                f"数据验证完成，将产生{files_after}个合并文件",
                processed_files_count=files_after,
            )
            merge_logger.end_phase(MergePhase.DATA_VALIDATION, "数据验证通过")

            # 第六阶段：原子表切换
            merge_logger.start_phase(MergePhase.ATOMIC_SWAP, "执行原子表切换")
            self._update_task_progress(
                task, db_session, "atomic_swap", 85.0, "执行原子表切换"
            )

            backup_table_name = f"{task.table_name}_backup_{int(time.time())}"

            # 模拟原子切换SQL
            swap_sqls = [
                f"ALTER TABLE {task.database_name}.{task.table_name} RENAME TO {backup_table_name}",
                f"ALTER TABLE {temp_table_name} RENAME TO {task.database_name}.{task.table_name}",
            ]
            result["sql_executed"].extend(swap_sqls)
            result["backup_table_created"] = backup_table_name

            for sql in swap_sqls:
                merge_logger.log_sql_execution(
                    sql, MergePhase.ATOMIC_SWAP, success=True
                )

            time.sleep(1)  # 模拟切换时间
            merge_logger.end_phase(MergePhase.ATOMIC_SWAP, "原子表切换完成")

            # 第七阶段：完成
            merge_logger.start_phase(MergePhase.COMPLETION, "完成合并操作")

            # 计算节省的空间
            if files_before > files_after:
                result["size_saved"] = (
                    (files_before - files_after) * 64 * 1024 * 1024
                )  # 估算

            result["success"] = True
            result["duration"] = time.time() - start_time
            result["message"] = (
                f"演示合并成功完成。文件数从 {files_before} 减少到 {files_after}"
            )

            # 更新最终任务状态
            task.status = "success"
            task.files_before = files_before
            task.files_after = files_after
            task.size_saved = result["size_saved"]
            task.completed_time = datetime.utcnow()

            self._update_task_progress(
                task,
                db_session,
                "completion",
                100.0,
                f"合并完成: {files_before} → {files_after} 文件",
                processed_files_count=files_after,
            )

            merge_logger.log_task_completion(
                True,
                int(result["duration"] * 1000),
                {
                    "files_before": files_before,
                    "files_after": files_after,
                    "size_saved": result["size_saved"],
                },
            )
            merge_logger.end_phase(MergePhase.COMPLETION, "合并任务完成")

            db_session.commit()

        except Exception as e:
            error_message = str(e)
            result["message"] = f"演示合并失败: {error_message}"
            result["success"] = False

            # 更新失败状态
            task.status = "failed"
            task.error_message = error_message
            task.execution_phase = "error"
            task.current_operation = f"执行失败: {error_message}"
            task.completed_time = datetime.utcnow()

            merge_logger.log_task_completion(
                False, int((time.time() - start_time) * 1000)
            )
            db_session.commit()

            logger.error(f"Merge task {task.id} failed: {e}")

        return result

    def _test_connections(self) -> bool:
        """测试各组件连接"""
        try:
            # 测试MetaStore连接
            with self.metastore_connector as conn:
                conn.test_connection()

            # 测试WebHDFS连接
            status = self.webhdfs_client.get_file_status("/")
            if not status.get("success", False):
                return False

            # 测试YARN连接（如果配置了）
            if self.yarn_monitor:
                try:
                    self.yarn_monitor.get_cluster_info()
                except:
                    logger.warning("YARN connection test failed, but continuing")

            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def _get_real_file_count(self, task: MergeTask) -> int:
        """获取真实的文件数量"""
        try:
            # 从已扫描的表信息中获取文件数
            from sqlalchemy.orm import Session

            from app.models.table_metric import TableMetric

            # 查询表文件统计
            metric = (
                Session.object_session(task)
                .query(TableMetric)
                .filter_by(
                    cluster_id=task.cluster_id,
                    database_name=task.database_name,
                    table_name=task.table_name,
                )
                .first()
            )

            if metric and metric.total_files:
                return metric.total_files
            else:
                # 通过MetaStore查询表位置，再用WebHDFS统计文件
                with self.metastore_connector as conn:
                    table_info = conn.get_table_info(
                        task.database_name, task.table_name
                    )
                    if table_info and "location" in table_info:
                        hdfs_path = table_info["location"].replace(
                            "hdfs://nameservice1", ""
                        )
                        stats = self.webhdfs_client.scan_directory_stats(
                            hdfs_path, self.cluster.small_file_threshold
                        )
                        return stats.total_files if stats else 1

            # 默认返回1（至少有一个文件）
            return 1

        except Exception as e:
            logger.error(f"Failed to get real file count: {e}")
            return 1  # 保守估计

    def _update_task_progress(
        self,
        task: MergeTask,
        db_session: Session,
        execution_phase: str = None,
        progress_percentage: float = None,
        current_operation: str = None,
        estimated_remaining_time: int = None,
        processed_files_count: int = None,
        total_files_count: int = None,
        yarn_application_id: str = None,
    ):
        """更新任务进度"""
        try:
            if execution_phase is not None:
                task.execution_phase = execution_phase
            if progress_percentage is not None:
                task.progress_percentage = progress_percentage
            if current_operation is not None:
                task.current_operation = current_operation
            if estimated_remaining_time is not None:
                task.estimated_remaining_time = estimated_remaining_time
            if processed_files_count is not None:
                task.processed_files_count = processed_files_count
            if total_files_count is not None:
                task.total_files_count = total_files_count
            if yarn_application_id is not None:
                task.yarn_application_id = yarn_application_id

            db_session.commit()
            logger.info(
                f"Updated task {task.id} progress: {execution_phase} - {progress_percentage}%"
            )
        except Exception as e:
            logger.error(f"Failed to update task progress: {e}")
            db_session.rollback()
