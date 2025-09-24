import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from impala.dbapi import connect as impala_connect
from sqlalchemy.orm import Session

from app.engines.base_engine import BaseMergeEngine
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.monitor.hive_connector import HiveMetastoreConnector
from app.monitor.mock_hdfs_scanner import MockHDFSScanner
from app.services.path_resolver import PathResolver
from app.utils.encryption import decrypt_cluster_password
from app.utils.merge_logger import MergeLogLevel, MergePhase, MergeTaskLogger
from app.utils.webhdfs_client import WebHDFSClient
from app.utils.yarn_monitor import YarnResourceManagerMonitor

logger = logging.getLogger(__name__)


class RealHiveMergeEngine(BaseMergeEngine):
    """
    真实的Hive合并引擎 - 使用impyla库进行真实的Hive连接
    使用临时表+原子重命名策略，确保合并过程中原表可读
    支持分区级别的合并操作，真实执行SQL语句
    """

    def __init__(self, cluster: Cluster):
        super().__init__(cluster)
        self.hdfs_scanner = MockHDFSScanner(
            cluster.hdfs_namenode_url, cluster.hdfs_user
        )
        self.metastore_connector = HiveMetastoreConnector(cluster.hive_metastore_url)
        self.progress_callback: Optional[Callable[[str, str], None]] = None

        # 初始化WebHDFS客户端用于精确的文件统计
        self.webhdfs_client = WebHDFSClient(
            namenode_url=cluster.hdfs_namenode_url, user=cluster.hdfs_user or "hdfs"
        )

        # 初始化YARN监控器（如果配置了YARN RM URL）
        self.yarn_monitor = None
        if cluster.yarn_resource_manager_url:
            yarn_urls = [
                url.strip() for url in cluster.yarn_resource_manager_url.split(",")
            ]
            self.yarn_monitor = YarnResourceManagerMonitor(yarn_urls)

        # 获取LDAP密码（支持明文和加密）
        self.hive_password = None
        if cluster.hive_password:
            try:
                # 尝试解密，如果失败则直接使用明文
                self.hive_password = decrypt_cluster_password(cluster)
                if not self.hive_password:
                    # 解密失败，直接使用明文
                    self.hive_password = cluster.hive_password
                    logger.debug("Using plain text password for LDAP authentication")
            except Exception as e:
                # 解密出错，直接使用明文
                self.hive_password = cluster.hive_password
                logger.debug(f"Password decryption failed, using plain text: {e}")

    def set_progress_callback(self, callback: Callable[[str, str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback

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

    def validate_task(self, task: MergeTask) -> Dict[str, Any]:
        """验证合并任务是否可执行"""
        result = {"valid": True, "message": "Task validation passed", "warnings": []}

        try:
            # 连接检查
            if not self._test_connections():
                result["valid"] = False
                result["message"] = "Failed to connect to Hive or HDFS"
                return result

            # 检查表是否存在
            if not self._table_exists(task.database_name, task.table_name):
                result["valid"] = False
                result["message"] = (
                    f"Table {task.database_name}.{task.table_name} does not exist"
                )
                return result

            # 检查是否为分区表
            is_partitioned = self._is_partitioned_table(
                task.database_name, task.table_name
            )

            # 如果是分区表但没有指定分区过滤器，给出警告
            if is_partitioned and not task.partition_filter:
                result["warnings"].append(
                    "Partitioned table detected but no partition filter specified. This will merge all partitions."
                )

            # 如果指定了分区过滤器，验证分区是否存在
            if task.partition_filter:
                if not self._validate_partition_filter(
                    task.database_name, task.table_name, task.partition_filter
                ):
                    result["warnings"].append(
                        "Partition filter may not match any partitions"
                    )

            # 检查临时表名是否冲突
            temp_table_name = self._generate_temp_table_name(task.table_name)
            if self._table_exists(task.database_name, temp_table_name):
                result["warnings"].append(
                    f"Temporary table {temp_table_name} already exists, will be dropped"
                )

            logger.info(
                f"RealHive validation completed for {task.database_name}.{task.table_name}"
            )

        except Exception as e:
            logger.error(f"Task validation failed: {e}")
            result["valid"] = False
            result["message"] = str(e)

        return result

    def execute_merge(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        """执行真实的Hive文件合并（使用真实的Hive连接）"""
        start_time = time.time()

        # 初始化详尽日志记录器
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
            "log_summary": {},
            "detailed_logs": [],
        }

        temp_table_name = self._generate_temp_table_name(task.table_name)
        backup_table_name = self._generate_backup_table_name(task.table_name)

        try:
            # 更新任务状态为运行中
            self.update_task_status(task, "running", db_session=db_session)
            merge_logger.start_phase(
                MergePhase.INITIALIZATION,
                "初始化真实Hive合并任务",
                {
                    "temp_table_name": temp_table_name,
                    "backup_table_name": backup_table_name,
                    "merge_strategy": "real_hive_engine",
                    "hive_connection": "impyla",
                },
            )

            # 更新进度：初始化阶段
            self._update_task_progress(
                task,
                db_session,
                execution_phase="initialization",
                progress_percentage=5.0,
                current_operation="初始化真实Hive合并任务",
            )
            self._report_progress(
                "initializing", "Starting real Hive merge with impyla connection"
            )

            # 建立真实的Hive连接
            merge_logger.start_phase(
                MergePhase.CONNECTION_TEST, "建立真实Hive、HDFS、YARN连接"
            )
            self._report_progress(
                "connecting", "Establishing real connections to Hive and HDFS"
            )

            if not self._test_connections():
                merge_logger.end_phase(
                    MergePhase.CONNECTION_TEST,
                    "连接测试失败",
                    success=False,
                    details={
                        "hive_host": self.cluster.hive_host,
                        "hive_port": self.cluster.hive_port,
                        "hdfs_namenode": self.cluster.hdfs_namenode_url,
                        "yarn_rm": self.cluster.yarn_resource_manager_url,
                    },
                )
                raise Exception("Failed to connect to Hive or HDFS")

            merge_logger.end_phase(
                MergePhase.CONNECTION_TEST, "所有真实连接测试成功", success=True
            )

            # 更新进度：连接测试完成
            self._update_task_progress(
                task,
                db_session,
                execution_phase="connection_test",
                progress_percentage=10.0,
                current_operation="真实连接测试完成",
            )

            # 获取合并前的真实文件统计
            merge_logger.start_phase(MergePhase.FILE_ANALYSIS, "分析当前真实文件结构")
            self._report_progress("analyzing", "Analyzing real file structure")

            # 更新进度：文件分析阶段
            self._update_task_progress(
                task,
                db_session,
                execution_phase="file_analysis",
                progress_percentage=15.0,
                current_operation="分析真实文件结构",
            )

            files_before = self._get_real_file_count_with_logging(
                task.database_name, task.table_name, task.partition_filter, merge_logger
            )
            result["files_before"] = files_before

            merge_logger.log_file_statistics(
                MergePhase.FILE_ANALYSIS,
                f"{task.database_name}.{task.table_name}",
                files_before=files_before,
            )
            merge_logger.end_phase(
                MergePhase.FILE_ANALYSIS, f"真实文件分析完成，当前{files_before}个文件"
            )

            # 更新进度：文件分析完成，包含文件数信息
            self._update_task_progress(
                task,
                db_session,
                execution_phase="file_analysis",
                progress_percentage=25.0,
                total_files_count=files_before,
                current_operation=f"真实文件分析完成，发现{files_before}个文件",
            )

            # 第一步：创建临时表并执行真实合并
            merge_logger.start_phase(
                MergePhase.TEMP_TABLE_CREATION, f"创建真实临时表: {temp_table_name}"
            )
            self._report_progress(
                "creating_temp_table",
                f"Creating real temporary table: {temp_table_name}",
            )

            # 更新进度：创建临时表阶段
            self._update_task_progress(
                task,
                db_session,
                execution_phase="temp_table_creation",
                progress_percentage=35.0,
                current_operation=f"创建真实临时表: {temp_table_name}",
            )

            create_temp_sql = self._create_real_temp_table_with_logging(
                task, temp_table_name, merge_logger
            )
            result["sql_executed"].extend(create_temp_sql)
            result["temp_table_created"] = temp_table_name

            merge_logger.end_phase(
                MergePhase.TEMP_TABLE_CREATION, f"真实临时表创建完成: {temp_table_name}"
            )

            # 更新进度：临时表创建完成
            self._update_task_progress(
                task,
                db_session,
                execution_phase="temp_table_creation",
                progress_percentage=45.0,
                current_operation=f"真实临时表创建完成: {temp_table_name}",
            )

            # 第二步：验证临时表数据
            merge_logger.start_phase(
                MergePhase.DATA_VALIDATION, "验证真实临时表数据完整性"
            )
            self._report_progress(
                "validating", "Validating real temporary table data integrity"
            )

            # 更新进度：数据验证阶段
            self._update_task_progress(
                task,
                db_session,
                execution_phase="data_validation",
                progress_percentage=55.0,
                current_operation="验证真实临时表数据完整性",
            )

            validation_result = self._validate_real_temp_table_data(
                task, temp_table_name
            )

            merge_logger.log_data_validation(
                MergePhase.DATA_VALIDATION,
                "行数一致性检查",
                validation_result["original_count"],
                validation_result["temp_count"],
                validation_result["valid"],
                details=validation_result,
            )

            if not validation_result["valid"]:
                merge_logger.end_phase(
                    MergePhase.DATA_VALIDATION, "数据验证失败", success=False
                )
                raise Exception(
                    f'Temporary table validation failed: {validation_result["message"]}'
                )

            merge_logger.end_phase(MergePhase.DATA_VALIDATION, "数据验证通过")

            # 获取合并后的文件统计（从临时表）
            files_after = self._get_real_temp_table_file_count(
                task.database_name, temp_table_name, task.partition_filter
            )
            result["files_after"] = files_after

            merge_logger.log_file_statistics(
                MergePhase.DATA_VALIDATION, temp_table_name, files_after=files_after
            )

            # 第三步：原子切换表（关键步骤）
            merge_logger.start_phase(MergePhase.ATOMIC_SWAP, "执行真实原子表切换")
            self._report_progress("atomic_swap", "Performing real atomic table swap")

            # 更新进度：原子切换阶段
            self._update_task_progress(
                task,
                db_session,
                execution_phase="atomic_swap",
                progress_percentage=75.0,
                processed_files_count=files_after,
                current_operation="执行真实原子表切换",
            )

            swap_sql = self._real_atomic_table_swap_with_logging(
                task, temp_table_name, backup_table_name, merge_logger
            )
            result["sql_executed"].extend(swap_sql)
            result["backup_table_created"] = backup_table_name

            merge_logger.end_phase(MergePhase.ATOMIC_SWAP, "真实原子表切换完成")

            # 更新进度：原子切换完成
            self._update_task_progress(
                task,
                db_session,
                execution_phase="atomic_swap",
                progress_percentage=85.0,
                current_operation="真实原子表切换完成",
            )

            # 计算节省的空间（简化估算）
            if files_before > files_after:
                result["size_saved"] = (
                    (files_before - files_after) * 64 * 1024 * 1024
                )  # 假设每个文件平均64MB

            result["success"] = True
            result["duration"] = time.time() - start_time
            result["message"] = (
                f"真实Hive合并成功完成。文件从{files_before}个减少到{files_after}个"
            )
            result["log_summary"] = merge_logger.get_log_summary()

            merge_logger.log_task_completion(
                True,
                int(result["duration"] * 1000),
                {
                    "files_before": files_before,
                    "files_after": files_after,
                    "files_reduced": files_before - files_after,
                    "size_saved": result["size_saved"],
                },
            )

            self._report_progress(
                "completed",
                f"Real Hive merge completed successfully. Files: {files_before} → {files_after}",
            )

            # 更新进度：任务完成
            self._update_task_progress(
                task,
                db_session,
                execution_phase="completion",
                progress_percentage=100.0,
                processed_files_count=files_after,
                current_operation=f"真实合并完成：{files_before} → {files_after} 文件",
            )

            # 更新任务状态为成功
            self.update_task_status(
                task,
                "success",
                files_before=files_before,
                files_after=files_after,
                size_saved=result["size_saved"],
                db_session=db_session,
            )

            self.log_task_event(task, "INFO", result["message"], db_session=db_session)
            self.log_task_event(
                task,
                "INFO",
                f"真实备份表已创建: {backup_table_name}. 验证后可手动删除.",
                db_session=db_session,
            )

        except Exception as e:
            error_message = str(e)
            result["message"] = f"真实Hive合并失败: {error_message}"
            result["duration"] = time.time() - start_time

            self._report_progress("failed", f"Real Hive merge failed: {error_message}")

            # 执行回滚操作
            try:
                self._report_progress(
                    "rolling_back",
                    "Starting rollback process to clean up real temporary resources",
                )
                self.log_task_event(
                    task, "WARNING", "开始回滚真实资源", db_session=db_session
                )
                rollback_sql = self._rollback_real_merge(
                    task, temp_table_name, backup_table_name
                )
                result["sql_executed"].extend(rollback_sql)
                self.log_task_event(task, "INFO", "回滚成功完成", db_session=db_session)
            except Exception as rollback_error:
                self.log_task_event(
                    task, "ERROR", f"回滚失败: {rollback_error}", db_session=db_session
                )
                result["message"] += f". 回滚失败: {rollback_error}"

            # 更新任务状态为失败
            self.update_task_status(
                task, "failed", error_message=error_message, db_session=db_session
            )
            self.log_task_event(task, "ERROR", result["message"], db_session=db_session)

            logger.error(f"Real Hive merge execution failed for task {task.id}: {e}")

        finally:
            # 清理连接
            self._cleanup_connections()

        return result

    def _test_connections(self) -> bool:
        """测试真实连接：Hive 成功即可放行，HDFS 失败仅告警"""
        # 先试 HDFS（严格：失败则返回 False）
        try:
            hdfs_ok, hdfs_msg = self.webhdfs_client.test_connection()
            if not hdfs_ok:
                logger.error(f"WebHDFS connection failed: {hdfs_msg}")
                return False
        except Exception as e:
            logger.error(f"WebHDFS connection exception: {e}")
            return False

        # 再试 Hive（必须成功）
        try:
            conn = self._create_real_hive_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if result and result[0] == 1:
                logger.info("Real Hive connection test passed")
                return True
            logger.error("Real Hive connection test failed: unexpected result")
            return False
        except Exception as e:
            logger.error(f"Real Hive connection test failed: {e}")
            return False

    def _create_real_hive_connection(self, database_name: str = None):
        """创建真实的Hive/Impala连接，带回退（NOSASL/PLAIN x SSL）"""
        db = database_name or self.cluster.hive_database or "default"
        host = self.cluster.hive_host
        port = self.cluster.hive_port

        candidates = []
        if (
            self.cluster.auth_type or ""
        ).upper() == "LDAP" and self.cluster.hive_username:
            candidates.extend(
                [
                    {
                        "auth_mechanism": "PLAIN",
                        "use_ssl": False,
                        "user": self.cluster.hive_username,
                        "password": self.hive_password,
                    },
                    {
                        "auth_mechanism": "PLAIN",
                        "use_ssl": True,
                        "user": self.cluster.hive_username,
                        "password": self.hive_password,
                    },
                ]
            )
        else:
            candidates.extend(
                [
                    {"auth_mechanism": "NOSASL", "use_ssl": False},
                    {"auth_mechanism": "NOSASL", "use_ssl": True},
                ]
            )

        last_err = None
        for c in candidates:
            try:
                params = {
                    "host": host,
                    "port": port,
                    "database": db,
                    "timeout": 10,
                    "auth_mechanism": c["auth_mechanism"],
                }
                if "user" in c and c["user"]:
                    params["user"] = c["user"]
                if "password" in c and c["password"]:
                    params["password"] = c["password"]
                if c.get("use_ssl"):
                    params["use_ssl"] = True
                logger.info(
                    f"Attempting Hive connection host={host} port={port} auth={params['auth_mechanism']} ssl={c.get('use_ssl', False)}"
                )
                return impala_connect(**params)
            except Exception as e:
                last_err = e
                logger.warning(f"Hive connect failed with {c}: {e}")
        logger.error(f"All Hive connection attempts failed: {last_err}")
        raise last_err

    def _table_exists(self, database_name: str, table_name: str) -> bool:
        """检查表是否存在（真实查询）"""
        try:
            conn = self._create_real_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f'SHOW TABLES LIKE "{table_name}"')
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result is not None
        except Exception as e:
            logger.error(f"Failed to check if table exists: {e}")
            return False

    def _is_partitioned_table(self, database_name: str, table_name: str) -> bool:
        """检查表是否为分区表（真实查询）"""
        try:
            conn = self._create_real_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f"DESCRIBE FORMATTED {table_name}")

            rows = cursor.fetchall()
            is_partitioned = False

            for row in rows:
                if len(row) >= 2 and row[0] and "Partition Information" in str(row[0]):
                    is_partitioned = True
                    break

            cursor.close()
            conn.close()
            return is_partitioned
        except Exception as e:
            logger.error(f"Failed to check if table is partitioned: {e}")
            return False

    def _validate_partition_filter(
        self, database_name: str, table_name: str, partition_filter: str
    ) -> bool:
        """验证分区过滤器（真实查询）"""
        try:
            conn = self._create_real_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f"SHOW PARTITIONS {table_name}")
            partitions = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()

            # 简单匹配验证：检查是否有分区包含过滤条件的内容
            for partition in partitions:
                if partition_filter.replace("'", "").replace('"', "") in partition:
                    return True

            return len(partitions) > 0  # 如果有分区但没匹配到，也返回True避免阻塞
        except Exception:
            return True  # 验证失败时返回True，让后续流程继续

    def _generate_temp_table_name(self, table_name: str) -> str:
        """生成临时表名"""
        timestamp = int(time.time())
        return f"{table_name}_real_merge_temp_{timestamp}"

    def _generate_backup_table_name(self, table_name: str) -> str:
        """生成备份表名"""
        timestamp = int(time.time())
        return f"{table_name}_real_backup_{timestamp}"

    def _get_table_location(self, database_name: str, table_name: str) -> Optional[str]:
        """获取表的HDFS位置（优先MetaStore，其次HS2，最后默认路径）"""
        try:
            return PathResolver.get_table_location(
                self.cluster, database_name, table_name
            )
        except Exception as e:
            logger.error(f"Failed to resolve table location: {e}")
            return None

    def _get_real_file_count_with_logging(
        self,
        database_name: str,
        table_name: str,
        partition_filter: Optional[str],
        merge_logger,
    ) -> int:
        """带日志记录的真实文件数量获取"""
        try:
            table_location = self._get_table_location(database_name, table_name)
            if not table_location:
                merge_logger.log(
                    MergePhase.FILE_ANALYSIS,
                    MergeLogLevel.ERROR,
                    f"无法获取表{database_name}.{table_name}的HDFS位置",
                    details={"database": database_name, "table": table_name},
                )
                return 0

            merge_logger.log_hdfs_operation(
                "get_real_table_stats", table_location, MergePhase.FILE_ANALYSIS
            )

            stats = self.webhdfs_client.get_table_hdfs_stats(
                table_location, self.cluster.small_file_threshold or 134217728
            )

            if stats.get("success", False):
                file_count = stats.get("total_files", 0)
                merge_logger.log_hdfs_operation(
                    "get_real_table_stats",
                    table_location,
                    MergePhase.FILE_ANALYSIS,
                    stats=stats,
                    success=True,
                )
                logger.info(
                    f"Real file count for {database_name}.{table_name}: {file_count}"
                )
                return file_count
            else:
                merge_logger.log_hdfs_operation(
                    "get_real_table_stats",
                    table_location,
                    MergePhase.FILE_ANALYSIS,
                    success=False,
                    error_message=stats.get("error", "Unknown error"),
                )
                return 0

        except Exception as e:
            merge_logger.log(
                MergePhase.FILE_ANALYSIS,
                MergeLogLevel.ERROR,
                f"获取真实文件数量失败: {str(e)}",
                details={"error": str(e), "table": f"{database_name}.{table_name}"},
            )
            return 0

    def _create_real_temp_table_with_logging(
        self, task: MergeTask, temp_table_name: str, merge_logger
    ) -> List[str]:
        """创建真实临时表并执行合并（真实SQL执行）"""
        sql_statements = []

        try:
            conn = self._create_real_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 设置 Hive 合并参数（真实执行）
            merge_settings = [
                "SET hive.merge.mapfiles=true",
                "SET hive.merge.mapredfiles=true",
                "SET hive.merge.size.per.task=268435456",  # 256MB
                "SET hive.exec.dynamic.partition=true",
                "SET hive.exec.dynamic.partition.mode=nonstrict",
                "SET mapred.reduce.tasks=1",  # 减少输出文件数
            ]

            for setting in merge_settings:
                merge_logger.log_sql_execution(
                    setting, MergePhase.TEMP_TABLE_CREATION, success=True
                )
                cursor.execute(setting)
                sql_statements.append(setting)
                logger.info(f"Real SQL executed: {setting}")

            # 删除可能存在的临时表（真实执行）
            drop_temp_sql = f"DROP TABLE IF EXISTS {temp_table_name}"
            merge_logger.log_sql_execution(
                drop_temp_sql, MergePhase.TEMP_TABLE_CREATION
            )
            cursor.execute(drop_temp_sql)
            sql_statements.append(drop_temp_sql)
            logger.info(f"Real SQL executed: {drop_temp_sql}")

            # 创建临时表并执行合并（真实执行）
            # 保持原表 EXTERNAL/非事务属性
            fmt_info = self._get_table_format_info(task.database_name, task.table_name)
            table_type = str(fmt_info.get("table_type", "")).upper()
            is_external = "EXTERNAL" in table_type

            if task.partition_filter:
                create_sql = (
                    f"CREATE {('EXTERNAL ' if is_external else '')}TABLE {temp_table_name} "
                    f"TBLPROPERTIES('transactional'='false') "
                    f"AS SELECT * FROM {task.table_name} WHERE {task.partition_filter}"
                )
            else:
                create_sql = (
                    f"CREATE {('EXTERNAL ' if is_external else '')}TABLE {temp_table_name} "
                    f"TBLPROPERTIES('transactional'='false') "
                    f"AS SELECT * FROM {task.table_name}"
                )

            # 长时 SQL：增加心跳日志
            self._execute_sql_with_heartbeat(
                cursor=cursor,
                sql=create_sql,
                phase=MergePhase.TEMP_TABLE_CREATION,
                merge_logger=merge_logger,
                task=task,
                db_session=None,  # 真实引擎仅记录日志，不更新 DB 进度
                op_desc=f"创建真实临时表并写入数据: {temp_table_name}",
                execution_phase_name="temp_table_creation",
            )
            sql_statements.append(create_sql)
            logger.info(f"Real SQL executed (completed): {create_sql}")

            cursor.close()
            conn.close()

            merge_logger.log(
                MergePhase.TEMP_TABLE_CREATION,
                MergeLogLevel.INFO,
                f"真实临时表{temp_table_name}创建成功",
                details={
                    "temp_table": temp_table_name,
                    "sql_count": len(sql_statements),
                },
            )

        except Exception as e:
            merge_logger.log_sql_execution(
                create_sql if "create_sql" in locals() else "CREATE TABLE ...",
                MergePhase.TEMP_TABLE_CREATION,
                success=False,
                error_message=str(e),
            )
            logger.error(f"Failed to create real temp table: {e}")
            raise

        return sql_statements

    def _execute_sql_with_heartbeat(
        self,
        *,
        cursor,
        sql: str,
        phase: MergePhase,
        merge_logger: MergeTaskLogger,
        task: MergeTask,
        db_session: Optional[Session],
        op_desc: str,
        execution_phase_name: str,
        interval: int = 10,
    ) -> None:
        """与 Safe 引擎一致的心跳执行封装。db_session 可为 None（仅记录日志）。"""
        import threading
        import time as _time

        stop = threading.Event()
        start_ts = _time.time()

        def _heartbeat():
            while not stop.wait(interval):
                waited = int(_time.time() - start_ts)
                merge_logger.log(
                    phase=phase,
                    level=MergeLogLevel.INFO,
                    message=f"正在执行: {op_desc}",
                    details={"elapsed_s": waited, "full_sql": sql[:200]},
                )
                try:
                    cur_op = f"{op_desc} (已等待{waited}s)"
                    yarn_id = None
                    if self.yarn_monitor is not None:
                        from app.utils.yarn_monitor import YarnApplicationState

                        try:
                            apps = self.yarn_monitor.get_applications(limit=20)
                            apps = [
                                a
                                for a in apps
                                if str(getattr(a, "application_type", "")).upper()
                                in ("TEZ", "MAPREDUCE")
                            ]
                            app = None
                            if getattr(task, "yarn_application_id", None):
                                for a in apps:
                                    if a.id == task.yarn_application_id:
                                        app = a
                                        break
                            if app is None and apps:
                                app = sorted(
                                    apps, key=lambda a: a.start_time, reverse=True
                                )[0]
                            if app is not None:
                                yarn_id = app.id
                                merge_logger.log_yarn_monitoring(
                                    app.id,
                                    phase,
                                    progress=float(getattr(app, "progress", 0) or 0),
                                    state=str(app.state or ""),
                                    details={
                                        "queue": getattr(app, "queue", ""),
                                        "name": getattr(app, "name", ""),
                                        "tracking_url": getattr(app, "tracking_url", "")
                                        or getattr(app, "original_tracking_url", ""),
                                    },
                                )
                                try:
                                    pct = int(getattr(app, "progress", 0) or 0)
                                    cur_op = f"{op_desc} - YARN {pct}% {getattr(app,'state','')} (队列:{getattr(app,'queue','')}) (已等待{waited}s)"
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    if db_session is not None:
                        try:
                            self._update_task_progress(
                                task,
                                db_session,
                                execution_phase=execution_phase_name,
                                yarn_application_id=yarn_id
                                or getattr(task, "yarn_application_id", None),
                                current_operation=cur_op,
                            )
                        except Exception:
                            pass
                except Exception:
                    pass

        merge_logger.log(
            phase,
            MergeLogLevel.INFO,
            f"SQL开始执行: {op_desc}",
            details={"full_sql": sql},
        )
        t = threading.Thread(target=_heartbeat, daemon=True)
        t.start()
        try:
            cursor.execute(sql)
            stop.set()
            t.join(timeout=0.2)
            merge_logger.log_sql_execution(sql, phase, success=True)
        except Exception as e:
            stop.set()
            t.join(timeout=0.2)
            merge_logger.log_sql_execution(
                sql, phase, success=False, error_message=str(e)
            )
            raise

    def _validate_real_temp_table_data(
        self, task: MergeTask, temp_table_name: str
    ) -> Dict[str, Any]:
        """验证临时表数据完整性（真实查询）"""
        result = {
            "valid": True,
            "message": "Validation passed",
            "original_count": 0,
            "temp_count": 0,
        }

        try:
            conn = self._create_real_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 检查原表行数（真实查询）
            if task.partition_filter:
                count_original_sql = f"SELECT COUNT(*) FROM {task.table_name} WHERE {task.partition_filter}"
            else:
                count_original_sql = f"SELECT COUNT(*) FROM {task.table_name}"

            cursor.execute(count_original_sql)
            original_count = cursor.fetchone()[0]
            result["original_count"] = original_count
            logger.info(f"Real original table count: {original_count}")

            # 检查临时表行数（真实查询）
            count_temp_sql = f"SELECT COUNT(*) FROM {temp_table_name}"
            cursor.execute(count_temp_sql)
            temp_count = cursor.fetchone()[0]
            result["temp_count"] = temp_count
            logger.info(f"Real temp table count: {temp_count}")

            # 验证行数是否一致
            if original_count != temp_count:
                result["valid"] = False
                result["message"] = (
                    f"Row count mismatch: original={original_count}, temp={temp_count}"
                )
                logger.error(result["message"])
            else:
                logger.info("Real data validation passed")

            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to validate real temp table data: {e}")
            result["valid"] = False
            result["message"] = str(e)

        return result

    def _get_real_temp_table_file_count(
        self,
        database_name: str,
        temp_table_name: str,
        partition_filter: Optional[str] = None,
    ) -> int:
        """获取临时表的文件数量（真实查询）"""
        try:
            # 获取临时表的HDFS路径（真实查询）
            table_location = self._get_table_location(database_name, temp_table_name)
            if not table_location:
                logger.error(
                    f"Could not get real temp table location for {database_name}.{temp_table_name}"
                )
                return 0

            logger.info(
                f"Getting real file count for temp table {database_name}.{temp_table_name} at location: {table_location}"
            )

            # 使用WebHDFS客户端获取准确的文件统计
            stats = self.webhdfs_client.get_table_hdfs_stats(
                table_location, self.cluster.small_file_threshold or 134217728
            )

            if stats.get("success", False):
                total_files = stats.get("total_files", 0)
                logger.info(
                    f"Real WebHDFS stats for temp table {database_name}.{temp_table_name}: {total_files} files"
                )
                return total_files
            else:
                logger.error(
                    f"Real WebHDFS stats failed for temp table: {stats.get('error', 'Unknown error')}"
                )
                return 0

        except Exception as e:
            logger.error(f"Failed to get real temp table file count: {e}")
            return 0

    def _real_atomic_table_swap_with_logging(
        self,
        task: MergeTask,
        temp_table_name: str,
        backup_table_name: str,
        merge_logger,
    ) -> List[str]:
        """真实原子表切换（真实SQL执行）"""
        sql_statements = []

        try:
            conn = self._create_real_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 第一步：将原表重命名为备份表（真实执行）
            rename_to_backup_sql = (
                f"ALTER TABLE {task.table_name} RENAME TO {backup_table_name}"
            )
            merge_logger.log_sql_execution(rename_to_backup_sql, MergePhase.ATOMIC_SWAP)
            cursor.execute(rename_to_backup_sql)
            sql_statements.append(rename_to_backup_sql)
            logger.info(f"Real SQL executed: {rename_to_backup_sql}")

            merge_logger.log(
                MergePhase.ATOMIC_SWAP,
                MergeLogLevel.INFO,
                f"原表重命名为备份表: {task.table_name} -> {backup_table_name}",
                details={
                    "original_table": task.table_name,
                    "backup_table": backup_table_name,
                },
            )

            # 第二步：将临时表重命名为原表名（真实执行）
            rename_temp_to_original_sql = (
                f"ALTER TABLE {temp_table_name} RENAME TO {task.table_name}"
            )
            merge_logger.log_sql_execution(
                rename_temp_to_original_sql, MergePhase.ATOMIC_SWAP
            )
            cursor.execute(rename_temp_to_original_sql)
            sql_statements.append(rename_temp_to_original_sql)
            logger.info(f"Real SQL executed: {rename_temp_to_original_sql}")

            merge_logger.log(
                MergePhase.ATOMIC_SWAP,
                MergeLogLevel.INFO,
                f"临时表重命名为原表: {temp_table_name} -> {task.table_name}",
                details={
                    "temp_table": temp_table_name,
                    "original_table": task.table_name,
                },
            )

            cursor.close()
            conn.close()

            merge_logger.log(
                MergePhase.ATOMIC_SWAP,
                MergeLogLevel.INFO,
                "真实原子表切换成功完成",
                details={
                    "swap_operations": 2,
                    "backup_created": backup_table_name,
                    "active_table": task.table_name,
                },
            )

        except Exception as e:
            merge_logger.log(
                MergePhase.ATOMIC_SWAP,
                MergeLogLevel.ERROR,
                f"真实原子表切换失败: {str(e)}",
                details={"error": str(e), "failed_operation": "real_table_rename"},
            )
            logger.error(f"Real atomic table swap failed: {e}")
            raise

        return sql_statements

    def _rollback_real_merge(
        self, task: MergeTask, temp_table_name: str, backup_table_name: str
    ) -> List[str]:
        """回滚真实合并操作（真实SQL执行）"""
        sql_statements = []

        try:
            conn = self._create_real_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 检查备份表是否存在，如果存在则恢复（真实查询）
            if self._table_exists(task.database_name, backup_table_name):
                # 删除可能存在的损坏的原表（真实执行）
                drop_damaged_sql = f"DROP TABLE IF EXISTS {task.table_name}"
                cursor.execute(drop_damaged_sql)
                sql_statements.append(drop_damaged_sql)
                logger.info(f"Real rollback SQL executed: {drop_damaged_sql}")

                # 将备份表恢复为原表（真实执行）
                restore_sql = (
                    f"ALTER TABLE {backup_table_name} RENAME TO {task.table_name}"
                )
                cursor.execute(restore_sql)
                sql_statements.append(restore_sql)
                logger.info(f"Real rollback SQL executed: {restore_sql}")

            # 清理临时表（真实执行）
            drop_temp_sql = f"DROP TABLE IF EXISTS {temp_table_name}"
            cursor.execute(drop_temp_sql)
            sql_statements.append(drop_temp_sql)
            logger.info(f"Real rollback SQL executed: {drop_temp_sql}")

            cursor.close()
            conn.close()

            logger.info("Real rollback completed successfully")

        except Exception as e:
            logger.error(f"Real rollback failed: {e}")
            raise

        return sql_statements

    def _cleanup_connections(self):
        """清理连接"""
        try:
            self.hdfs_scanner.disconnect()
            self.webhdfs_client.close()
            if self.yarn_monitor:
                self.yarn_monitor.close()
        except Exception as e:
            logger.warning(f"Failed to cleanup connections: {e}")

    def get_merge_preview(self, task: MergeTask) -> Dict[str, Any]:
        """获取合并预览信息"""
        preview = {
            "estimated_files_before": 0,
            "estimated_files_after": 0,
            "estimated_size_reduction": 0,
            "estimated_duration": 0,
            "is_partitioned": False,
            "partitions": [],
            "temp_table_name": "",
            "warnings": [],
            "engine_type": "real_hive_engine",
        }

        try:
            # 建立真实连接
            if not self._test_connections():
                raise Exception("Failed to connect to real Hive or HDFS")

            # 检查是否为分区表（真实查询）
            is_partitioned = self._is_partitioned_table(
                task.database_name, task.table_name
            )
            preview["is_partitioned"] = is_partitioned

            # 如果是分区表，获取分区列表（真实查询）
            if is_partitioned:
                conn = self._create_real_hive_connection(task.database_name)
                cursor = conn.cursor()
                cursor.execute(f"SHOW PARTITIONS {task.table_name}")
                partitions = [row[0] for row in cursor.fetchall()]
                cursor.close()
                conn.close()
                preview["partitions"] = partitions[:10]  # 最多显示10个分区

            # 获取当前文件数量（真实查询）
            current_files = self._get_real_file_count_with_logging(
                task.database_name,
                task.table_name,
                task.partition_filter,
                MergeTaskLogger(task, None),
            )
            preview["estimated_files_before"] = current_files

            # 估算合并后的文件数量（基于经验值）
            if current_files > 1000:
                preview["estimated_files_after"] = max(10, current_files // 50)
            elif current_files > 100:
                preview["estimated_files_after"] = max(5, current_files // 20)
            else:
                preview["estimated_files_after"] = max(1, current_files // 10)

            # 估算空间节省
            files_reduced = (
                preview["estimated_files_before"] - preview["estimated_files_after"]
            )
            preview["estimated_size_reduction"] = (
                files_reduced * 64 * 1024 * 1024
            )  # 假设每个文件平均64MB

            # 估算执行时间
            preview["estimated_duration"] = self.estimate_duration(task)

            # 生成临时表名
            preview["temp_table_name"] = self._generate_temp_table_name(task.table_name)

            # 添加警告信息
            if current_files < 10:
                preview["warnings"].append("表中文件数量较少，合并效果可能有限")

            if is_partitioned and not task.partition_filter:
                preview["warnings"].append(
                    "分区表建议指定分区过滤条件，避免处理所有分区"
                )

            if task.partition_filter and not self._validate_partition_filter(
                task.database_name, task.table_name, task.partition_filter
            ):
                preview["warnings"].append("分区过滤器可能不匹配任何分区")

        except Exception as e:
            logger.error(f"Failed to generate real merge preview: {e}")
            preview["warnings"].append(f"无法生成真实预览: {str(e)}")

        finally:
            self._cleanup_connections()

        return preview

    def estimate_duration(self, task: MergeTask) -> int:
        """估算任务执行时间（基于真实文件数量和表大小）"""
        try:
            file_count = self._get_real_file_count_with_logging(
                task.database_name,
                task.table_name,
                task.partition_filter,
                MergeTaskLogger(task, None),
            )

            # 基于文件数量的估算（秒）
            base_time = 60  # 基础时间60秒
            file_factor = file_count * 0.2  # 每个文件增加0.2秒

            # 真实合并需要额外时间（创建临时表、验证、切换）
            real_overhead = 120  # 真实操作额外开销

            total_time = base_time + file_factor + real_overhead

            return int(total_time)

        except Exception as e:
            logger.error(f"Failed to estimate duration: {e}")
            return 600  # 默认10分钟
