import logging
import re
import socket
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from pyhive import hive
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.engines.base_engine import BaseMergeEngine
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.models.table_metric import TableMetric
from app.monitor.hive_connector import HiveMetastoreConnector
from app.services.path_resolver import PathResolver
from app.utils.encryption import decrypt_cluster_password
from app.utils.merge_logger import MergeLogLevel, MergePhase, MergeTaskLogger
from app.utils.webhdfs_client import WebHDFSClient
from app.utils.yarn_monitor import YarnResourceManagerMonitor

logger = logging.getLogger(__name__)


class SafeHiveMergeEngine(BaseMergeEngine):
    """
    安全的Hive合并引擎
    使用临时表+原子重命名的策略，确保合并过程中原表可读
    支持分区级别的合并操作
    """

    _FORMAT_KEYWORDS = {
        "PARQUET": ["parquet"],
        "ORC": ["orc"],
        "AVRO": ["avro"],
        "RCFILE": ["rcfile"],
    }

    _COMPRESSION_CODECS = {
        "SNAPPY": "org.apache.hadoop.io.compress.SnappyCodec",
        "GZIP": "org.apache.hadoop.io.compress.GzipCodec",
        "LZ4": "org.apache.hadoop.io.compress.Lz4Codec",
    }

    _PARQUET_COMPRESSION = {
        "SNAPPY": "SNAPPY",
        "GZIP": "GZIP",
        "LZ4": "LZ4",
        "NONE": "UNCOMPRESSED",
    }

    _ORC_COMPRESSION = {
        "SNAPPY": "SNAPPY",
        "GZIP": "ZLIB",
        "LZ4": "LZ4",
        "NONE": "NONE",
    }

    def __init__(self, cluster: Cluster):
        super().__init__(cluster)
        # 使用 WebHDFSClient 进行文件统计，移除对 HDFSScanner 的依赖
        self.hdfs_scanner = None
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

        # 解密LDAP密码
        self.hive_password = None
        if cluster.hive_password:
            # 解密失败时回退到明文，以兼容直接存放明文密码的环境
            try:
                self.hive_password = decrypt_cluster_password(cluster)
            except Exception:
                self.hive_password = None
            if not self.hive_password:
                self.hive_password = cluster.hive_password

    def set_progress_callback(self, callback: Callable[[str, str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback

    # 以下私有方法提供桩实现，便于测试用例通过 @patch 进行替换
    # 真实逻辑在 execute_merge 内部按策略路径实现
    def _execute_concatenate(
        self, task: MergeTask, db_session: Session
    ) -> Dict[str, Any]:  # pragma: no cover - 测试打桩
        return {"success": False, "message": "stub"}

    def _execute_insert_overwrite(
        self, task: MergeTask, db_session: Session
    ) -> Dict[str, Any]:  # pragma: no cover
        return {"success": False, "message": "stub"}

    def _execute_safe_merge(
        self, task: MergeTask, db_session: Session
    ) -> Dict[str, Any]:  # pragma: no cover
        return {"success": False, "message": "stub"}

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
            # 连接检查（严格：WebHDFS/Hive 任一失败则不可执行）
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

            # 存储/格式检查：禁止对不受支持的表进行合并（如 Hudi/Iceberg/Delta/ACID）
            fmt = self._get_table_format_info(task.database_name, task.table_name)
            if self._is_unsupported_table_type(fmt):
                result["valid"] = False
                result["message"] = self._unsupported_reason(fmt)
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
                f"SafeHive validation completed for {task.database_name}.{task.table_name}"
            )

        except Exception as e:
            logger.error(f"Task validation failed: {e}")
            result["valid"] = False
            result["message"] = str(e)

        return result

    def execute_merge(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        """执行安全文件合并（带详尽日志记录）"""
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

        # 运行期再次进行严格的表类型校验，避免误操作
        fmt = self._get_table_format_info(task.database_name, task.table_name)
        if self._is_unsupported_table_type(fmt):
            msg = self._unsupported_reason(fmt)
            self._report_progress("failed", msg)
            self.update_task_status(
                task, "failed", error_message=msg, db_session=db_session
            )
            return {
                "success": False,
                "files_before": 0,
                "files_after": 0,
                "size_saved": 0,
                "duration": time.time() - start_time,
                "message": msg,
                "sql_executed": [],
                "temp_table_created": "",
                "backup_table_created": "",
                "log_summary": {},
                "detailed_logs": [],
            }

        original_format = self._infer_storage_format_name(fmt)
        original_compression = self._infer_table_compression(fmt, original_format)
        target_format = (task.target_storage_format or original_format or "TEXTFILE").upper()
        if target_format not in {"PARQUET", "ORC", "TEXTFILE", "RCFILE", "AVRO"}:
            target_format = original_format or "TEXTFILE"
        compression_pref = task.target_compression.upper() if task.target_compression else None
        if compression_pref in {"", "DEFAULT"}:
            compression_pref = None

        if task.partition_filter and (task.target_storage_format or task.target_compression):
            merge_logger.log(
                MergePhase.INITIALIZATION,
                MergeLogLevel.WARNING,
                "分区合并暂不支持修改输出格式或压缩设置，已忽略相关选项",
                details={"code": "W110"},
            )
            target_format = original_format or target_format
            compression_pref = None
        elif target_format != original_format or compression_pref:
            merge_logger.log(
                MergePhase.INITIALIZATION,
                MergeLogLevel.INFO,
                "应用自定义输出格式/压缩设置",
                details={
                    "code": "M104",
                    "original_format": original_format,
                    "target_format": target_format,
                    "original_compression": original_compression,
                    "target_compression": compression_pref or "SNAPPY",
                },
            )

        base_compression = (original_compression or "").upper()
        if base_compression in {"", "DEFAULT"}:
            base_compression = None
        job_compression = None
        if compression_pref == "KEEP":
            job_compression = base_compression
        elif compression_pref:
            job_compression = compression_pref
        else:
            job_compression = base_compression or "SNAPPY"

        # 如果指定了分区过滤器，优先按分区级别执行合并（不进行整表原子切换）
        if task.partition_filter:
            try:
                # 连接测试
                if not self._test_connections():
                    raise Exception("Failed to connect to Hive or HDFS")

                # 预统计：分区文件数
                part_path = self._resolve_partition_path(
                    task.database_name, task.table_name, task.partition_filter
                )
                files_before = None
                files_after = None
                if part_path:
                    try:
                        stats_before = self.webhdfs_client.scan_directory_stats(
                            part_path, self.cluster.small_file_threshold or 134217728
                        )
                        files_before = int(getattr(stats_before, "total_files", 0) or 0)
                    except Exception:
                        files_before = None

                spec = self._partition_filter_to_spec(task.partition_filter)
                if not spec:
                    raise Exception(
                        f"Unsupported partition_filter: {task.partition_filter}"
                    )

                # 路径一：CONCATENATE（原地合并）
                if (task.merge_strategy or "concatenate") == "concatenate":
                    merge_logger.start_phase(
                        MergePhase.TEMP_TABLE_CREATION, "分区级合并（CONCATENATE）"
                    )
                    conn = self._create_hive_connection(task.database_name)
                    cursor = conn.cursor()
                    sql = (
                        f"ALTER TABLE {task.table_name} PARTITION ({spec}) CONCATENATE"
                    )
                    merge_logger.log_sql_execution(sql, MergePhase.TEMP_TABLE_CREATION)
                    cursor.execute(sql)
                    cursor.close()
                    conn.close()
                    merge_logger.end_phase(
                        MergePhase.TEMP_TABLE_CREATION, "分区 CONCATENATE 完成"
                    )
                else:
                    # 路径二：INSERT OVERWRITE 单分区（重写分区数据，控制 reducer 数减少文件数）
                    merge_logger.start_phase(
                        MergePhase.TEMP_TABLE_CREATION, "分区级合并（INSERT OVERWRITE）"
                    )
                    nonpart_cols, part_cols = self._get_table_columns(
                        task.database_name, task.table_name
                    )
                    if not nonpart_cols:
                        raise Exception("Failed to get table columns")
                    conn = self._create_hive_connection(task.database_name)
                    cursor = conn.cursor()
                    settings = [
                        "SET hive.merge.mapfiles=true",
                        "SET hive.merge.mapredfiles=true",
                        "SET hive.exec.dynamic.partition.mode=nonstrict",
                        "SET hive.tez.auto.reducer.parallelism=false",
                        "SET mapred.reduce.tasks=1",
                    ]
                    for st in settings:
                        merge_logger.log_sql_execution(
                            st, MergePhase.TEMP_TABLE_CREATION, success=True
                        )
                        cursor.execute(st)
                    # 静态分区覆盖：分区列不出现在 SELECT 列表
                    cols_expr = ", ".join([f"`{c}`" for c in nonpart_cols])
                    insert_sql = (
                        f"INSERT OVERWRITE TABLE {task.table_name} PARTITION ({spec}) "
                        f"SELECT {cols_expr} FROM {task.table_name} WHERE {task.partition_filter} DISTRIBUTE BY 1"
                    )
                    merge_logger.log_sql_execution(
                        insert_sql, MergePhase.TEMP_TABLE_CREATION
                    )
                    cursor.execute(insert_sql)
                    cursor.close()
                    conn.close()
                    merge_logger.end_phase(
                        MergePhase.TEMP_TABLE_CREATION, "分区 INSERT OVERWRITE 完成"
                    )

                # 统计合并后文件数
                if part_path:
                    try:
                        stats_after = self.webhdfs_client.scan_directory_stats(
                            part_path, self.cluster.small_file_threshold or 134217728
                        )
                        files_after = int(getattr(stats_after, "total_files", 0) or 0)
                    except Exception:
                        files_after = None

                # 汇总结果
                result["success"] = True
                result["duration"] = time.time() - start_time
                result["message"] = (
                    f"Partition-level merge completed via "
                    f"{(task.merge_strategy or 'concatenate').upper()} for ({spec})"
                )
                result["files_before"] = files_before
                result["files_after"] = files_after
                result["size_saved"] = 0

                # 更新任务状态
                self._update_task_progress(
                    task,
                    db_session,
                    execution_phase="completion",
                    progress_percentage=100.0,
                    processed_files_count=files_after if files_after is not None else 0,
                    current_operation=f"分区合并完成: PARTITION ({spec})",
                )
                self.update_task_status(
                    task,
                    "success",
                    files_before=(
                        files_before if isinstance(files_before, int) else None
                    ),
                    files_after=files_after if isinstance(files_after, int) else None,
                    size_saved=0,
                    db_session=db_session,
                )
                self.log_task_event(
                    task,
                    "INFO",
                    result["message"],
                    db_session=db_session,
                    details={
                        "phase": "completion",
                        "code": "M900",
                        "partition_spec": spec,
                        "files_before": files_before,
                        "files_after": files_after,
                    },
                )
                return result
            except Exception as e:
                # 若分区级失败，直接失败（不做整表替代）
                result["message"] = f"Partition-level merge failed: {e}"
                result["duration"] = time.time() - start_time
                self._report_progress("failed", result["message"])
                self.update_task_status(
                    task, "failed", error_message=str(e), db_session=db_session
                )
                self.log_task_event(
                    task,
                    "ERROR",
                    result["message"],
                    db_session=db_session,
                    details={
                        "phase": "completion",
                        "code": "E900",
                        "partition_spec": spec,
                    },
                )
                return result

        try:
            # 更新任务状态为运行中
            self.update_task_status(task, "running", db_session=db_session)
            merge_logger.start_phase(
                MergePhase.INITIALIZATION,
                "初始化安全合并任务",
                {
                    "temp_table_name": temp_table_name,
                    "backup_table_name": backup_table_name,
                    "merge_strategy": "safe_hive_engine",
                },
            )

            # 更新进度：初始化阶段
            self._update_task_progress(
                task,
                db_session,
                execution_phase="initialization",
                progress_percentage=5.0,
                current_operation="初始化安全合并任务",
            )
            self._report_progress(
                "initializing", "Starting safe merge with temporary table strategy"
            )

            # 建立连接
            merge_logger.start_phase(
                MergePhase.CONNECTION_TEST, "建立Hive、HDFS、YARN连接"
            )
            self._report_progress(
                "connecting", "Establishing connections to Hive and HDFS"
            )

            if not self._test_connections(
                merge_logger=merge_logger, task=task, db_session=db_session
            ):
                merge_logger.end_phase(
                    MergePhase.CONNECTION_TEST,
                    "连接测试失败",
                    success=False,
                    details={
                        "hive_host": self.cluster.hive_host,
                        "hdfs_namenode": self.cluster.hdfs_namenode_url,
                        "yarn_rm": self.cluster.yarn_resource_manager_url,
                    },
                )
                raise Exception("Failed to connect to Hive or HDFS")

            merge_logger.end_phase(
                MergePhase.CONNECTION_TEST, "所有连接测试成功", success=True
            )

            # 更新进度：连接测试完成
            self._update_task_progress(
                task,
                db_session,
                execution_phase="connection_test",
                progress_percentage=10.0,
                current_operation="连接测试完成",
            )

            # 获取合并前的文件统计
            merge_logger.start_phase(MergePhase.FILE_ANALYSIS, "分析当前文件结构")
            self._report_progress("analyzing", "Analyzing current file structure")

            # 更新进度：文件分析阶段
            self._update_task_progress(
                task,
                db_session,
                execution_phase="file_analysis",
                progress_percentage=15.0,
                current_operation="分析当前文件结构",
            )

            files_before = self._get_file_count_with_logging(
                task.database_name, task.table_name, task.partition_filter, merge_logger
            )
            result["files_before"] = files_before

            merge_logger.log_file_statistics(
                MergePhase.FILE_ANALYSIS,
                f"{task.database_name}.{task.table_name}",
                files_before=files_before,
            )
            merge_logger.end_phase(
                MergePhase.FILE_ANALYSIS,
                f"文件分析完成，当前{files_before if files_before is not None else '未知'}个文件",
            )

            # 更新进度：文件分析完成，包含文件数信息
            self._update_task_progress(
                task,
                db_session,
                execution_phase="file_analysis",
                progress_percentage=25.0,
                total_files_count=files_before,
                current_operation=f"文件分析完成，发现{files_before if files_before is not None else '未知'}个文件",
            )

            # 第一步：创建临时表
            merge_logger.start_phase(
                MergePhase.TEMP_TABLE_CREATION, f"创建临时表: {temp_table_name}"
            )
            self._report_progress(
                "creating_temp_table", f"Creating temporary table: {temp_table_name}"
            )

            # 更新进度：创建临时表阶段
            self._update_task_progress(
                task,
                db_session,
                execution_phase="temp_table_creation",
                progress_percentage=35.0,
                current_operation=f"创建临时表: {temp_table_name}",
            )

            create_temp_sql = self._create_temp_table_with_logging(
                task,
                temp_table_name,
                merge_logger,
                db_session,
                target_format,
                job_compression,
                original_format,
                original_compression,
            )
            result["sql_executed"].extend(create_temp_sql)
            result["temp_table_created"] = temp_table_name

            merge_logger.end_phase(
                MergePhase.TEMP_TABLE_CREATION, f"临时表创建完成: {temp_table_name}"
            )

            # 更新进度：临时表创建完成
            self._update_task_progress(
                task,
                db_session,
                execution_phase="temp_table_creation",
                progress_percentage=45.0,
                current_operation=f"临时表创建完成: {temp_table_name}",
            )

            # 第二步：验证临时表数据
            merge_logger.start_phase(MergePhase.DATA_VALIDATION, "验证临时表数据完整性")
            self._report_progress(
                "validating", "Validating temporary table data integrity"
            )

            # 更新进度：数据验证阶段
            self._update_task_progress(
                task,
                db_session,
                execution_phase="data_validation",
                progress_percentage=55.0,
                current_operation="验证临时表数据完整性",
            )

            validation_result = self._validate_temp_table_data(task, temp_table_name)

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
            files_after = self._get_temp_table_file_count(
                task.database_name, temp_table_name, task.partition_filter
            )
            result["files_after"] = files_after

            merge_logger.log_file_statistics(
                MergePhase.DATA_VALIDATION, temp_table_name, files_after=files_after
            )

            # 第三步：切换为新数据
            # 读取原表 External/Location 信息，用于决定切换策略
            fmt_info_after = self._get_table_format_info(
                task.database_name, task.table_name
            )
            table_type_after = str(fmt_info_after.get("table_type", "")).upper()
            is_external = "EXTERNAL" in table_type_after
            original_location = (
                self._get_table_location(task.database_name, task.table_name) or ""
            )
            parent_dir = (
                "/".join([p for p in original_location.rstrip("/").split("/")[:-1]])
                if original_location
                else ""
            )
            # 直接读取临时表LOCATION，作为影子目录来源
            temp_location = (
                self._get_table_location(task.database_name, temp_table_name) or ""
            )
            if is_external and original_location and temp_location:
                merge_logger.start_phase(MergePhase.ATOMIC_SWAP, "外部表目录切换")
                self._report_progress(
                    "atomic_swap", "Swapping external table directory"
                )
                self._update_task_progress(
                    task,
                    db_session,
                    execution_phase="atomic_swap",
                    progress_percentage=75.0,
                    processed_files_count=files_after,
                    current_operation="执行外部表目录切换",
                )
                hdfs: WebHDFSClient = self.webhdfs_client
                ts_id = int(time.time())
                # 首选：备份到 .merge_shadow 根
                shadow_root = f"{parent_dir}/.merge_shadow" if parent_dir else ""
                backup_dir = f"{shadow_root}/backup_{ts_id}"
                ok1, msg1 = self._hdfs_rename_with_fallback(
                    src=original_location,
                    dst=backup_dir,
                    merge_logger=merge_logger,
                    phase=MergePhase.ATOMIC_SWAP,
                    task=task,
                    db_session=db_session,
                )
                if not ok1:
                    # 二级回退：退到父目录 .merge_backup_<ts>
                    alt_backup_dir = f"{parent_dir}/.merge_backup_{ts_id}" if parent_dir else ""
                    if alt_backup_dir:
                        ok1b, msg1b = self._hdfs_rename_with_fallback(
                            src=original_location,
                            dst=alt_backup_dir,
                            merge_logger=merge_logger,
                            phase=MergePhase.ATOMIC_SWAP,
                            task=task,
                            db_session=db_session,
                        )
                        if ok1b:
                            backup_dir = alt_backup_dir
                        else:
                            raise RuntimeError(f"备份原目录失败: {msg1} ; fallback: {msg1b}")
                    else:
                        raise RuntimeError(f"备份原目录失败: {msg1}")

                ok2, msg2 = self._hdfs_rename_with_fallback(
                    src=temp_location,
                    dst=original_location,
                    merge_logger=merge_logger,
                    phase=MergePhase.ATOMIC_SWAP,
                    task=task,
                    db_session=db_session,
                )
                if not ok2:
                    # 回滚：尝试把备份恢复回原路径（也使用回退）
                    self._hdfs_rename_with_fallback(
                        src=backup_dir,
                        dst=original_location,
                        merge_logger=merge_logger,
                        phase=MergePhase.ATOMIC_SWAP,
                        task=task,
                        db_session=db_session,
                    )
                    raise RuntimeError(f"切换影子目录失败: {msg2}")
                # 删除临时表元数据
                try:
                    conn = self._create_hive_connection(task.database_name)
                    cur = conn.cursor()
                    cur.execute(f"DROP TABLE IF EXISTS {temp_table_name}")
                    cur.close()
                    conn.close()
                except Exception:
                    pass
                result["backup_table_created"] = backup_dir
                merge_logger.end_phase(MergePhase.ATOMIC_SWAP, "外部表目录切换完成")
                self._update_task_progress(
                    task,
                    db_session,
                    execution_phase="atomic_swap",
                    progress_percentage=85.0,
                    current_operation="外部表目录切换完成",
                )
            else:
                # 非外部表：重命名表对象
                merge_logger.start_phase(MergePhase.ATOMIC_SWAP, "执行原子表切换")
                self._report_progress("atomic_swap", "Performing atomic table swap")
                self._update_task_progress(
                    task,
                    db_session,
                    execution_phase="atomic_swap",
                    progress_percentage=75.0,
                    processed_files_count=files_after,
                    current_operation="执行原子表切换",
                )
                swap_sql = self._atomic_table_swap_with_logging(
                    task, temp_table_name, backup_table_name, merge_logger
                )
                result["sql_executed"].extend(swap_sql)
                result["backup_table_created"] = backup_table_name
                merge_logger.end_phase(MergePhase.ATOMIC_SWAP, "原子表切换完成")
                self._update_task_progress(
                    task,
                    db_session,
                    execution_phase="atomic_swap",
                    progress_percentage=85.0,
                    current_operation="原子表切换完成",
                )

            # 切换完成后，重新统计一次目标表文件数，确保展示准确
            try:
                files_after_actual = self._get_file_count_with_logging(
                    task.database_name,
                    task.table_name,
                    task.partition_filter,
                    merge_logger,
                )
                if isinstance(files_after_actual, int):
                    files_after = files_after_actual
                    result["files_after"] = files_after
            except Exception as _:
                pass

            base_compression = (original_compression or "").upper()
            if base_compression in {"", "DEFAULT"}:
                base_compression = None
            effective_meta_compression = None
            if job_compression == "KEEP":
                effective_meta_compression = base_compression
            elif job_compression:
                effective_meta_compression = job_compression

            if (
                effective_format := target_format
            ) and (
                effective_format != original_format
                or effective_meta_compression is not None
            ):
                self._update_active_table_format(
                    task.database_name,
                    task.table_name,
                    effective_format,
                    effective_meta_compression,
                    merge_logger,
                )

            # 计算节省的空间（简化估算）
            if (
                isinstance(files_before, int)
                and isinstance(files_after, int)
                and files_before > files_after
            ):
                result["size_saved"] = (
                    (files_before - files_after) * 64 * 1024 * 1024
                )  # 假设每个文件平均64MB

            result["success"] = True
            result["duration"] = time.time() - start_time
            result["message"] = (
                f"Safe merge completed successfully. Files reduced from "
                f"{files_before if files_before is not None else 'NaN'} to {files_after if files_after is not None else 'NaN'}"
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
                f"Safe merge completed successfully. Files: {files_before if files_before is not None else 'NaN'} → {files_after if files_after is not None else 'NaN'}",
            )

            # 更新进度：任务完成
            self._update_task_progress(
                task,
                db_session,
                execution_phase="completion",
                progress_percentage=100.0,
                processed_files_count=files_after,
                current_operation=f"合并完成：{files_before if files_before is not None else 'NaN'} → {files_after if files_after is not None else 'NaN'} 文件",
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

            self.log_task_event(
                task,
                "INFO",
                result["message"],
                db_session=db_session,
                details={
                    "phase": "completion",
                    "code": "M900",
                    "files_before": files_before,
                    "files_after": files_after,
                },
            )
            self.log_task_event(
                task,
                "INFO",
                f"Backup table created: {backup_table_name}. Drop it after verification.",
                db_session=db_session,
                details={
                    "phase": "completion",
                    "code": "M901",
                    "backup_table": backup_table_name,
                },
            )

        except Exception as e:
            error_message = str(e)
            result["message"] = f"Safe merge failed: {error_message}"
            result["duration"] = time.time() - start_time

            self._report_progress("failed", f"Safe merge failed: {error_message}")

            # 执行回滚操作
            try:
                self._report_progress(
                    "rolling_back",
                    "Starting rollback process to clean up temporary resources",
                )
                self.log_task_event(
                    task,
                    "WARNING",
                    "Starting rollback process",
                    db_session=db_session,
                    details={"phase": "rollback", "code": "W801"},
                )
                rollback_sql = self._rollback_merge(
                    task, temp_table_name, backup_table_name
                )
                result["sql_executed"].extend(rollback_sql)
                self.log_task_event(
                    task,
                    "INFO",
                    "Rollback completed successfully",
                    db_session=db_session,
                    details={"phase": "rollback", "code": "M802"},
                )
            except Exception as rollback_error:
                self.log_task_event(
                    task,
                    "ERROR",
                    f"Rollback failed: {rollback_error}",
                    db_session=db_session,
                    details={
                        "phase": "rollback",
                        "code": "E803",
                        "error": str(rollback_error),
                    },
                )
                result["message"] += f". Rollback failed: {rollback_error}"

            # 更新任务状态为失败
            self.update_task_status(
                task, "failed", error_message=error_message, db_session=db_session
            )
            self.log_task_event(
                task,
                "ERROR",
                result["message"],
                db_session=db_session,
                details={"phase": "completion", "code": "E900"},
            )

            logger.error(f"Safe merge execution failed for task {task.id}: {e}")

        finally:
            # 清理连接
            self._cleanup_connections()

        return result

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
        }

        try:
            # 建立连接
            if not self._test_connections():
                raise Exception("Failed to connect to Hive or HDFS")

            # 检查是否为分区表
            is_partitioned = self._is_partitioned_table(
                task.database_name, task.table_name
            )
            preview["is_partitioned"] = is_partitioned

            # 如果是分区表，获取分区列表
            if is_partitioned:
                partitions = self._get_table_partitions(
                    task.database_name, task.table_name
                )
                preview["partitions"] = partitions[:10]  # 最多显示10个分区

            # 获取当前文件数量
            current_files = self._get_file_count(
                task.database_name, task.table_name, task.partition_filter
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
            logger.error(f"Failed to generate merge preview: {e}")
            preview["warnings"].append(f"无法生成预览: {str(e)}")

        finally:
            self._cleanup_connections()

        return preview

    def estimate_duration(self, task: MergeTask) -> int:
        """估算任务执行时间（基于文件数量和表大小）"""
        try:
            file_count = self._get_file_count(
                task.database_name, task.table_name, task.partition_filter
            )

            # 基于文件数量的估算（秒）
            base_time = 60  # 基础时间60秒
            file_factor = file_count * 0.2  # 每个文件增加0.2秒

            # 安全合并需要额外时间（创建临时表、验证、切换）
            safety_overhead = 120  # 安全操作额外开销

            total_time = base_time + file_factor + safety_overhead

            return int(total_time)

        except Exception as e:
            logger.error(f"Failed to estimate duration: {e}")
            return 600  # 默认10分钟

    def _test_connections(
        self,
        *,
        merge_logger: Optional[MergeTaskLogger] = None,
        task: Optional[MergeTask] = None,
        db_session: Optional[Session] = None,
        timeout_sec: int = 10,
    ) -> bool:
        """测试连接：输出更详细的日志并增加心跳，Hive 必须成功。

        过程：
        1) WebHDFS 自检（失败仅告警）
        2) Hive TCP 探测（3s 超时）
        3) HiveServer2 连接 + SELECT 1（超时 + 心跳日志）
        """
        # 1) HDFS/HttpFS（不作为阻塞条件）
        try:
            if merge_logger:
                merge_logger.log(
                    MergePhase.CONNECTION_TEST,
                    MergeLogLevel.INFO,
                    "开始测试 WebHDFS 连接",
                    details={"namenode": self.cluster.hdfs_namenode_url},
                )
            ok, msg = self.webhdfs_client.test_connection()
            if not ok:
                logger.error(f"WebHDFS test failed: {msg}")
                if merge_logger:
                    merge_logger.log_hdfs_operation(
                        "connect",
                        self.cluster.hdfs_namenode_url,
                        MergePhase.CONNECTION_TEST,
                        success=False,
                        error_message=str(msg),
                    )
                return False
            else:
                if merge_logger:
                    merge_logger.log_hdfs_operation(
                        "connect",
                        self.cluster.hdfs_namenode_url,
                        MergePhase.CONNECTION_TEST,
                        stats={"ok": True},
                        success=True,
                    )
        except Exception as e:
            logger.error(f"WebHDFS test exception: {e}")
            if merge_logger:
                merge_logger.log(
                    MergePhase.CONNECTION_TEST,
                    MergeLogLevel.ERROR,
                    f"WebHDFS 测试异常: {e}",
                    details={"namenode": self.cluster.hdfs_namenode_url},
                )
            return False

        # 2) Hive（必须成功）
        try:
            hive_conn_params = {
                "host": self.cluster.hive_host,
                "port": self.cluster.hive_port,
                "database": self.cluster.hive_database or "default",
            }
            if (
                self.cluster.auth_type or ""
            ).upper() == "LDAP" and self.cluster.hive_username:
                hive_conn_params["username"] = self.cluster.hive_username
                if self.hive_password:
                    hive_conn_params["password"] = self.hive_password
                hive_conn_params["auth"] = "LDAP"
                logger.info(
                    f"Using LDAP authentication for user: {self.cluster.hive_username}"
                )

            # 2.1 TCP 快速探测（3s）
            if merge_logger:
                merge_logger.log(
                    MergePhase.CONNECTION_TEST,
                    MergeLogLevel.INFO,
                    f"测试 Hive TCP 连接: {hive_conn_params['host']}:{hive_conn_params['port']}",
                    details={
                        "host": hive_conn_params["host"],
                        "port": hive_conn_params["port"],
                    },
                )
            try:
                with socket.create_connection(
                    (hive_conn_params["host"], hive_conn_params["port"]), timeout=3
                ):
                    pass
            except Exception as se:
                if merge_logger:
                    merge_logger.log(
                        MergePhase.CONNECTION_TEST,
                        MergeLogLevel.ERROR,
                        f"Hive TCP 连接失败: {se}",
                        details={
                            "host": hive_conn_params["host"],
                            "port": hive_conn_params["port"],
                        },
                    )
                logger.error(f"Hive TCP connectivity failed: {se}")
                return False

            # 2.2 HS2 连接 + SELECT 1（超时 + 心跳）
            if merge_logger:
                merge_logger.start_phase(
                    MergePhase.CONNECTION_TEST, "连接 HiveServer2 并校验查询"
                )

            done_flag = {"ok": False, "err": None}

            def _connect_and_query():
                try:
                    conn = hive.Connection(**hive_conn_params)
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchall()
                    cursor.close()
                    conn.close()
                    done_flag["ok"] = True
                except Exception as ie:
                    done_flag["err"] = ie

            th = threading.Thread(target=_connect_and_query, daemon=True)
            th.start()

            waited = 0
            while th.is_alive() and waited < timeout_sec:
                if merge_logger and task and db_session:
                    merge_logger.log(
                        MergePhase.CONNECTION_TEST,
                        MergeLogLevel.INFO,
                        "正在连接 HiveServer2 ...",
                        details={"elapsed_s": waited},
                    )
                    try:
                        self._update_task_progress(
                            task,
                            db_session,
                            execution_phase="connection_test",
                            current_operation=f"连接 HiveServer2 中 (已等待{waited}s)",
                        )
                    except Exception:
                        pass
                waited += 2
                th.join(timeout=2)

            if th.is_alive():
                if merge_logger:
                    merge_logger.end_phase(
                        MergePhase.CONNECTION_TEST,
                        f"HiveServer2 连接超时({timeout_sec}s)",
                        success=False,
                    )
                logger.error("Hive connection test timeout")
                return False

            if done_flag["ok"] and not done_flag["err"]:
                if merge_logger:
                    merge_logger.end_phase(
                        MergePhase.CONNECTION_TEST, "Hive 连接与校验通过", success=True
                    )
                logger.info("Hive connection test passed")
                return True
            else:
                err = done_flag["err"]
                if merge_logger:
                    merge_logger.end_phase(
                        MergePhase.CONNECTION_TEST,
                        f"Hive 校验失败: {err}",
                        success=False,
                    )
                logger.error(f"Hive connection test failed: {err}")
                return False
        except Exception as e:
            logger.error(f"Hive connection test failed: {e}")
            return False

    def _get_table_location(self, database_name: str, table_name: str) -> Optional[str]:
        """获取表的HDFS位置（优先MetaStore，其次HS2，最后默认路径）"""
        try:
            return PathResolver.get_table_location(
                self.cluster, database_name, table_name
            )
        except Exception as e:
            logger.error(f"Failed to resolve table location: {e}")
            return None

    def _create_hive_connection(self, database_name: str = None):
        """创建Hive连接（支持LDAP认证）"""
        hive_conn_params = {
            "host": self.cluster.hive_host,
            "port": self.cluster.hive_port,
            "database": database_name or self.cluster.hive_database or "default",
        }

        # 如果配置了LDAP认证
        if self.cluster.auth_type == "LDAP" and self.cluster.hive_username:
            hive_conn_params["username"] = self.cluster.hive_username
            if self.hive_password:
                hive_conn_params["password"] = self.hive_password
            hive_conn_params["auth"] = "LDAP"
            logger.debug(
                f"Creating LDAP connection for user: {self.cluster.hive_username}"
            )

        return hive.Connection(**hive_conn_params)

    def _cleanup_connections(self):
        """清理连接"""
        try:
            if self.hdfs_scanner:
                self.hdfs_scanner.disconnect()
            self.webhdfs_client.close()
            if self.yarn_monitor:
                self.yarn_monitor.close()
        except Exception as e:
            logger.warning(f"Failed to cleanup connections: {e}")

    def _table_exists(self, database_name: str, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f'SHOW TABLES LIKE "{table_name}"')
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result is not None
        except Exception:
            return False

    def _is_partitioned_table(self, database_name: str, table_name: str) -> bool:
        """检查表是否为分区表"""
        try:
            conn = self._create_hive_connection(database_name)
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

    def _get_table_partitions(self, database_name: str, table_name: str) -> List[str]:
        """获取表的分区列表"""
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f"SHOW PARTITIONS {table_name}")
            partitions = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return partitions
        except Exception as e:
            logger.error(f"Failed to get table partitions: {e}")
            return []

    def _get_table_format_info(
        self, database_name: str, table_name: str
    ) -> Dict[str, Any]:
        """获取表的格式/属性信息，用于安全校验。
        返回：{'input_format': str, 'serde_lib': str, 'storage_handler': str, 'tblproperties': {k:v}}
        """
        info: Dict[str, Any] = {
            "input_format": "",
            "output_format": "",
            "serde_lib": "",
            "storage_handler": "",
            "tblproperties": {},
            "table_type": "",
        }
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            # 读取格式信息
            cursor.execute(f"DESCRIBE FORMATTED {table_name}")
            rows = cursor.fetchall()
            for row in rows:
                if not row or len(row) < 2:
                    continue
                k = str(row[0]).strip()
                v = str(row[1]).strip() if row[1] is not None else ""
                if "InputFormat" in k:
                    info["input_format"] = v
                elif "OutputFormat" in k:
                    info["output_format"] = v
                elif "SerDe Library" in k:
                    info["serde_lib"] = v
                elif "Storage Handler" in k:
                    info["storage_handler"] = v
                elif "Table Type" in k or k.lower().startswith("type"):
                    # values like EXTERNAL_TABLE / MANAGED_TABLE
                    info["table_type"] = v
            # 读取表属性
            try:
                cursor.execute(f"SHOW TBLPROPERTIES {table_name}")
                props = cursor.fetchall()
                for pr in props:
                    # 常见返回为 (key, value)
                    if len(pr) >= 2:
                        info["tblproperties"][str(pr[0]).strip()] = str(pr[1]).strip()
            except Exception:
                pass
            cursor.close()
            conn.close()
        except Exception:
            pass
        return info

    def _infer_storage_format_name(self, fmt: Dict[str, Any]) -> str:
        input_fmt = str(fmt.get("input_format", "")).lower()
        serde = str(fmt.get("serde_lib", "")).lower()
        for fmt_name, keywords in self._FORMAT_KEYWORDS.items():
            if any(keyword in input_fmt for keyword in keywords):
                return fmt_name
            if any(keyword in serde for keyword in keywords):
                return fmt_name
        return "TEXTFILE"

    def _infer_table_compression(
        self, fmt: Dict[str, Any], storage_format: str
    ) -> str:
        props = {
            str(k).lower(): str(v).upper()
            for k, v in fmt.get("tblproperties", {}).items()
        }
        if storage_format == "ORC":
            value = props.get("orc.compress") or props.get("orc.default.compress")
            if value:
                return value.upper()
            return "ZLIB"
        if storage_format == "PARQUET":
            value = props.get("parquet.compression")
            if value:
                return value.upper()
            return "SNAPPY"
        if storage_format == "TEXTFILE":
            value = props.get("compression") or props.get("fileoutputformat.compress")
            if value:
                return value.upper()
            codec = props.get("mapreduce.output.fileoutputformat.compress.codec")
            if codec:
                codec = codec.rsplit('.', 1)[-1]
                return codec.upper()
            return "NONE"
        return "DEFAULT"

    def _apply_output_settings(
        self,
        cursor,
        merge_logger,
        sql_statements: List[str],
        storage_format: str,
        compression: Optional[str],
    ) -> None:
        if not compression:
            return
        codec = compression.upper()
        if codec in {"DEFAULT", ""}:
            return
        if codec == "KEEP":
            return

        def _exec(setting: str) -> None:
            merge_logger.log(
                MergePhase.TEMP_TABLE_CREATION,
                MergeLogLevel.INFO,
                f"SQL开始执行: {setting}",
                details={"full_sql": setting},
            )
            cursor.execute(setting)
            merge_logger.log_sql_execution(
                setting, MergePhase.TEMP_TABLE_CREATION, success=True
            )
            sql_statements.append(setting)

        if codec == "NONE":
            _exec("SET hive.exec.compress.output=false")
            _exec("SET mapreduce.output.fileoutputformat.compress=false")
        else:
            codec_class = self._COMPRESSION_CODECS.get(codec)
            if codec_class:
                _exec("SET hive.exec.compress.output=true")
                _exec("SET mapreduce.output.fileoutputformat.compress=true")
                _exec(
                    f"SET mapreduce.output.fileoutputformat.compress.codec={codec_class}"
                )
        if storage_format == "ORC":
            target = self._ORC_COMPRESSION.get(codec, self._ORC_COMPRESSION.get("NONE"))
            if target:
                _exec(f"SET hive.exec.orc.default.compress={target}")
        elif storage_format == "PARQUET":
            target = self._PARQUET_COMPRESSION.get(
                codec, self._PARQUET_COMPRESSION.get("NONE")
            )
            if target:
                _exec(f"SET parquet.compression={target}")

    def _update_active_table_format(
        self,
        database_name: str,
        table_name: str,
        storage_format: str,
        compression: Optional[str],
        merge_logger,
    ) -> None:
        comp = (compression or "").upper()
        if comp in {"DEFAULT", ""}:
            comp = None
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f"ALTER TABLE {table_name} SET FILEFORMAT {storage_format}")
            merge_logger.log_sql_execution(
                f"ALTER TABLE {table_name} SET FILEFORMAT {storage_format}",
                MergePhase.COMPLETION,
                success=True,
            )
            if comp and comp != "KEEP":
                props = {}
                if storage_format == "ORC":
                    mapped = self._ORC_COMPRESSION.get(comp)
                    if mapped:
                        props["orc.compress"] = mapped
                elif storage_format == "PARQUET":
                    mapped = self._PARQUET_COMPRESSION.get(comp)
                    if mapped:
                        props["parquet.compression"] = mapped
                elif storage_format in {"TEXTFILE", "AVRO", "RCFILE"}:
                    if comp == "NONE":
                        props["compression"] = "UNCOMPRESSED"
                    else:
                        props["compression"] = comp
                for key, value in props.items():
                    cursor.execute(
                        f"ALTER TABLE {table_name} SET TBLPROPERTIES('{key}'='{value}')"
                    )
                    merge_logger.log_sql_execution(
                        f"ALTER TABLE {table_name} SET TBLPROPERTIES('{key}'='{value}')",
                        MergePhase.COMPLETION,
                        success=True,
                    )
            cursor.close()
            conn.close()
        except Exception as exc:  # pragma: no cover - metadata updates best effort
            merge_logger.log(
                MergePhase.COMPLETION,
                MergeLogLevel.WARNING,
                f"更新表文件格式/压缩信息失败: {exc}",
                details={"code": "W902"},
            )

    def _is_unsupported_table_type(self, fmt: Dict[str, Any]) -> bool:
        """识别不受支持的表类型（Hudi/Iceberg/Delta/ACID等）"""
        input_fmt = str(fmt.get("input_format", "")).lower()
        serde_lib = str(fmt.get("serde_lib", "")).lower()
        storage_handler = str(fmt.get("storage_handler", "")).lower()
        props = {
            str(k).lower(): str(v).lower()
            for k, v in fmt.get("tblproperties", {}).items()
        }

        # Hudi 检测：handler/serde/input 或 hoodie.* 属性
        if (
            "hudi" in input_fmt
            or "hudi" in serde_lib
            or "hudi" in storage_handler
            or any(k.startswith("hoodie.") for k in props.keys())
        ):
            return True
        # Iceberg 检测
        if (
            "iceberg" in input_fmt
            or "iceberg" in storage_handler
            or "iceberg" in serde_lib
        ):
            return True
        # Delta 检测
        if "delta" in input_fmt or "delta" in storage_handler or "delta" in serde_lib:
            return True
        # ACID 事务表：必须 transactional=true 或 storage handler 含 acid
        if props.get("transactional") == "true" or "acid" in storage_handler:
            return True
        return False

    def _unsupported_reason(self, fmt: Dict[str, Any]) -> str:
        input_fmt = str(fmt.get("input_format", "")).lower()
        serde_lib = str(fmt.get("serde_lib", "")).lower()
        storage_handler = str(fmt.get("storage_handler", "")).lower()
        props = {
            str(k).lower(): str(v).lower()
            for k, v in fmt.get("tblproperties", {}).items()
        }

        if (
            "hudi" in input_fmt
            or "hudi" in serde_lib
            or "hudi" in storage_handler
            or any(k.startswith("hoodie.") for k in props.keys())
        ):
            return "目标表为 Hudi 表，当前合并引擎不支持对 Hudi 表执行合并，请使用 Hudi 自带的压缩/合并机制（如 compaction/cluster）"
        if (
            "iceberg" in input_fmt
            or "iceberg" in storage_handler
            or "iceberg" in serde_lib
        ):
            return "目标表为 Iceberg 表，当前合并引擎不支持该表的合并操作"
        if "delta" in input_fmt or "delta" in storage_handler or "delta" in serde_lib:
            return "目标表为 Delta 表，当前合并引擎不支持该表的合并操作"
        if props.get("transactional") == "true" or "acid" in storage_handler:
            return "目标表为 ACID/事务表，当前合并引擎不支持该表的合并操作"
        return "目标表类型不受支持，已阻止合并操作"

    def _get_table_columns(
        self, database_name: str, table_name: str
    ) -> (List[str], List[str]):
        """获取表的字段列表（非分区列、分区列）"""
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f"DESCRIBE FORMATTED {table_name}")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            nonpart: List[str] = []
            parts: List[str] = []
            in_part = False
            for row in rows:
                if not row or len(row) < 1:
                    continue
                first = str(row[0]).strip()
                if not first:
                    continue
                if first.startswith("#"):
                    if "Partition Information" in first:
                        in_part = True
                    continue
                if first.lower() == "col_name" or first.lower().startswith("name"):
                    continue
                # 过滤非字段行（如详细信息）
                if ":" in first:
                    # 进入详细信息部分
                    break
                if in_part:
                    parts.append(first)
                else:
                    nonpart.append(first)
            # 去掉可能的空白/无效项
            nonpart = [c for c in nonpart if c and c != "col_name"]
            parts = [c for c in parts if c and c != "col_name"]
            return nonpart, parts
        except Exception:
            return [], []

    def _partition_filter_to_spec(self, partition_filter: str) -> Optional[str]:
        """将 WHERE 风格的分区过滤转换为 PARTITION 规范，例如:
        "dt='2024-01-01' AND region='cn'" -> "dt='2024-01-01', region='cn'"
        仅支持等值 AND 组合。
        """
        if not partition_filter:
            return None
        # 标准化 AND 分隔为逗号（不区分大小写）
        normalized = re.sub(
            r"\s+and\s+", ",", partition_filter.strip(), flags=re.IGNORECASE
        )
        parts = [p.strip() for p in normalized.split(",") if p.strip()]
        specs = []
        for p in parts:
            if "=" not in p:
                return None
            k, v = p.split("=", 1)
            k = k.strip()
            v = v.strip()
            # 如果值没有引号且不是纯数字，补充单引号
            if not (v.startswith("'") or v.startswith('"')):
                if re.fullmatch(r"[0-9]+", v):
                    pass
                else:
                    v = f"'{v}'"
            specs.append(f"{k}={v}")
        return ", ".join(specs) if specs else None

    def _resolve_partition_path(
        self, database_name: str, table_name: str, partition_filter: str
    ) -> Optional[str]:
        """根据分区过滤器解析分区在 HDFS 的路径（在表根路径下拼接spec）。"""
        try:
            root = self._get_table_location(database_name, table_name)
            if not root:
                return None
            # 规范化为路径: key=value/key2=value2
            normalized = re.sub(
                r"\s+and\s+", "/", partition_filter.strip(), flags=re.IGNORECASE
            )
            normalized = normalized.replace(",", "/").replace(" ", "")
            normalized = normalized.replace("'", "").replace('"', "")
            if not normalized:
                return None
            return root.rstrip("/") + "/" + normalized
        except Exception:
            return None

    def _validate_partition_filter(
        self, database_name: str, table_name: str, partition_filter: str
    ) -> bool:
        """验证分区过滤器"""
        try:
            partitions = self._get_table_partitions(database_name, table_name)

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
        return f"{table_name}_merge_temp_{timestamp}"

    def _generate_backup_table_name(self, table_name: str) -> str:
        """生成备份表名"""
        timestamp = int(time.time())
        return f"{table_name}_backup_{timestamp}"

    def _create_temp_table(self, task: MergeTask, temp_table_name: str) -> List[str]:
        """创建临时表并执行合并"""
        sql_statements = []

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 设置 Hive 合并参数
            merge_settings = [
                "SET hive.merge.mapfiles=true",
                "SET hive.merge.mapredfiles=true",
                "SET hive.merge.size.per.task=268435456",  # 256MB
                "SET hive.exec.dynamic.partition=true",
                "SET hive.exec.dynamic.partition.mode=nonstrict",
                "SET mapred.reduce.tasks=1",  # 减少输出文件数
            ]

            for setting in merge_settings:
                cursor.execute(setting)
                sql_statements.append(setting)

            # 删除可能存在的临时表
            drop_temp_sql = f"DROP TABLE IF EXISTS {temp_table_name}"
            cursor.execute(drop_temp_sql)
            sql_statements.append(drop_temp_sql)

            # 创建临时表并执行合并
            if task.partition_filter:
                create_sql = f"""
                CREATE TABLE {temp_table_name} 
                AS SELECT * FROM {task.table_name} 
                WHERE {task.partition_filter}
                """
            else:
                create_sql = f"""
                CREATE TABLE {temp_table_name} 
                AS SELECT * FROM {task.table_name}
                """

            cursor.execute(create_sql)
            sql_statements.append(create_sql)

            cursor.close()
            conn.close()

            logger.info(f"Temporary table {temp_table_name} created successfully")

        except Exception as e:
            logger.error(f"Failed to create temporary table: {e}")
            raise

        return sql_statements

    def _validate_temp_table_data(
        self, task: MergeTask, temp_table_name: str
    ) -> Dict[str, Any]:
        """验证临时表数据完整性"""
        result = {
            "valid": True,
            "message": "Validation passed",
            "original_count": 0,
            "temp_count": 0,
        }

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 检查原表行数
            if task.partition_filter:
                count_original_sql = f"SELECT COUNT(*) FROM {task.table_name} WHERE {task.partition_filter}"
            else:
                count_original_sql = f"SELECT COUNT(*) FROM {task.table_name}"

            cursor.execute(count_original_sql)
            original_count = cursor.fetchone()[0]
            result["original_count"] = original_count

            # 检查临时表行数
            count_temp_sql = f"SELECT COUNT(*) FROM {temp_table_name}"
            cursor.execute(count_temp_sql)
            temp_count = cursor.fetchone()[0]
            result["temp_count"] = temp_count

            # 验证行数是否一致
            if original_count != temp_count:
                result["valid"] = False
                result["message"] = (
                    f"Row count mismatch: original={original_count}, temp={temp_count}"
                )

            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to validate temp table data: {e}")
            result["valid"] = False
            result["message"] = str(e)

        return result

    def _atomic_table_swap(
        self, task: MergeTask, temp_table_name: str, backup_table_name: str
    ) -> List[str]:
        """原子性地交换表"""
        sql_statements = []

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 第一步：将原表重命名为备份表
            rename_to_backup_sql = (
                f"ALTER TABLE {task.table_name} RENAME TO {backup_table_name}"
            )
            cursor.execute(rename_to_backup_sql)
            sql_statements.append(rename_to_backup_sql)

            # 第二步：将临时表重命名为原表名
            rename_temp_to_original_sql = (
                f"ALTER TABLE {temp_table_name} RENAME TO {task.table_name}"
            )
            cursor.execute(rename_temp_to_original_sql)
            sql_statements.append(rename_temp_to_original_sql)

            cursor.close()
            conn.close()

            logger.info(
                f"Atomic table swap completed: {task.table_name} -> {backup_table_name}, {temp_table_name} -> {task.table_name}"
            )

        except Exception as e:
            logger.error(f"Failed to perform atomic table swap: {e}")
            raise

        return sql_statements

    def _hdfs_rename_with_fallback(
        self,
        *,
        src: str,
        dst: str,
        merge_logger: MergeTaskLogger,
        phase: MergePhase,
        task: MergeTask,
        db_session: Session,
    ) -> tuple[bool, str]:
        """先尝试 WebHDFS rename，失败则回退 HS2 dfs -mv。

        返回: (ok, message)
        """
        ok = False
        last_msg = ""
        # 1) WebHDFS 优先
        try:
            ok, msg = self.webhdfs_client.move_file(src, dst)
            if ok:
                merge_logger.log_hdfs_operation(
                    "rename", src, phase, success=True, stats={"to": dst}
                )
                return True, ""
            last_msg = str(msg)
            merge_logger.log_hdfs_operation(
                "rename", src, phase, success=False, error_message=str(msg)
            )
        except Exception as e:
            last_msg = str(e)
            merge_logger.log_hdfs_operation(
                "rename", src, phase, success=False, error_message=str(e)
            )

        # 2) 回退 HS2 dfs -mv
        try:
            conn = self._create_hive_connection(task.database_name)
            cur = conn.cursor()
            cur.execute(f"dfs -mv {src} {dst}")
            try:
                cur.close(); conn.close()
            except Exception:
                pass
            merge_logger.log_hdfs_operation(
                "rename",
                src,
                phase,
                success=True,
                stats={"to": dst, "fallback": "hs2-dfs-mv"},
            )
            # 刷新当前操作提示（非关键）
            try:
                self._update_task_progress(
                    task,
                    db_session,
                    current_operation=f"目录移动(回退HS2): {src} -> {dst}",
                )
            except Exception:
                pass
            return True, ""
        except Exception as e2:
            merge_logger.log_hdfs_operation(
                "rename",
                src,
                phase,
                success=False,
                error_message=f"hs2-dfs-mv failed: {e2}",
            )
            return False, f"WebHDFS failed: {last_msg}; HS2 failed: {e2}"

    def _rollback_merge(
        self, task: MergeTask, temp_table_name: str, backup_table_name: str
    ) -> List[str]:
        """回滚合并操作"""
        sql_statements = []

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 检查备份表是否存在，如果存在则恢复
            if self._table_exists(task.database_name, backup_table_name):
                # 删除可能存在的损坏的原表
                drop_damaged_sql = f"DROP TABLE IF EXISTS {task.table_name}"
                cursor.execute(drop_damaged_sql)
                sql_statements.append(drop_damaged_sql)

                # 将备份表恢复为原表
                restore_sql = (
                    f"ALTER TABLE {backup_table_name} RENAME TO {task.table_name}"
                )
                cursor.execute(restore_sql)
                sql_statements.append(restore_sql)

            # 清理临时表
            drop_temp_sql = f"DROP TABLE IF EXISTS {temp_table_name}"
            cursor.execute(drop_temp_sql)
            sql_statements.append(drop_temp_sql)

            cursor.close()
            conn.close()

            logger.info("Rollback completed successfully")

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise

        return sql_statements

    def _get_file_count(
        self,
        database_name: str,
        table_name: str,
        partition_filter: Optional[str] = None,
    ) -> Optional[int]:
        """获取表的文件数量（使用WebHDFS精确统计）"""
        try:
            # 获取表的HDFS路径
            table_location = self._get_table_location(database_name, table_name)
            if not table_location:
                logger.error(
                    f"Could not get table location for {database_name}.{table_name}"
                )
                return None

            logger.info(
                f"Getting file count for table {database_name}.{table_name} at location: {table_location}"
            )

            # 使用WebHDFS客户端获取准确的文件统计
            stats = self.webhdfs_client.get_table_hdfs_stats(
                table_location, self.cluster.small_file_threshold or 134217728
            )

            if stats.get("success", False):
                total_files = stats.get("total_files", 0)
                logger.info(
                    f"WebHDFS stats for {database_name}.{table_name}: {total_files} files, "
                    f"{stats.get('small_files_count', 0)} small files"
                )
                return total_files
            else:
                logger.error(
                    f"WebHDFS stats failed: {stats.get('error', 'Unknown error')}"
                )
                return None

        except Exception as e:
            logger.error(f"Failed to get file count using WebHDFS: {e}")
            # 如果WebHDFS失败，使用备用方法
            return self._get_file_count_fallback(
                database_name, table_name, partition_filter
            )

    def _get_temp_table_file_count(
        self,
        database_name: str,
        temp_table_name: str,
        partition_filter: Optional[str] = None,
    ) -> Optional[int]:
        """获取临时表的文件数量（使用WebHDFS精确统计）"""
        try:
            # 获取临时表的HDFS路径
            table_location = self._get_table_location(database_name, temp_table_name)
            if not table_location:
                logger.error(
                    f"Could not get temp table location for {database_name}.{temp_table_name}"
                )
                raise RuntimeError("无法获取临时表HDFS位置")

            logger.info(
                f"Getting file count for temp table {database_name}.{temp_table_name} at location: {table_location}"
            )

            # 使用WebHDFS客户端获取准确的文件统计
            stats = self.webhdfs_client.get_table_hdfs_stats(
                table_location, self.cluster.small_file_threshold or 134217728
            )

            if stats.get("success", False):
                total_files = stats.get("total_files", 0)
                logger.info(
                    f"WebHDFS stats for temp table {database_name}.{temp_table_name}: {total_files} files"
                )
                return total_files
            else:
                logger.error(
                    f"WebHDFS stats failed for temp table: {stats.get('error', 'Unknown error')}"
                )
                raise RuntimeError(
                    f"临时表文件统计失败: {stats.get('error','Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Failed to get temp table file count: {e}")
            raise

    def _get_file_count_fallback(
        self,
        database_name: str,
        table_name: str,
        partition_filter: Optional[str] = None,
    ) -> Optional[int]:
        """获取文件数量的备用方法"""
        try:
            # 简单估算：基于表大小和平均文件大小
            # 在实际环境中可以通过其他方式获取更准确的文件数量
            return None  # 统计失败不再估算，交由前端显示 NaN
        except Exception as e:
            logger.error(f"Fallback file count method failed: {e}")
            return 0

    def _get_file_count_with_logging(
        self,
        database_name: str,
        table_name: str,
        partition_filter: Optional[str],
        merge_logger,
    ) -> int:
        """带日志记录的文件数量获取"""
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
                "get_table_stats", table_location, MergePhase.FILE_ANALYSIS
            )

            stats = self.webhdfs_client.get_table_hdfs_stats(
                table_location, self.cluster.small_file_threshold or 134217728
            )

            if stats.get("success", False):
                file_count = stats.get("total_files", 0)
                merge_logger.log_hdfs_operation(
                    "get_table_stats",
                    table_location,
                    MergePhase.FILE_ANALYSIS,
                    stats=stats,
                    success=True,
                )
                return file_count
            else:
                merge_logger.log_hdfs_operation(
                    "get_table_stats",
                    table_location,
                    MergePhase.FILE_ANALYSIS,
                    success=False,
                    error_message=stats.get("error", "Unknown error"),
                )
                # 严格模式：统计失败视为致命错误
                raise RuntimeError(
                    f"WebHDFS 统计失败: {stats.get('error', 'Unknown error')}"
                )

        except Exception as e:
            merge_logger.log(
                MergePhase.FILE_ANALYSIS,
                MergeLogLevel.ERROR,
                f"获取文件数量失败: {str(e)}",
                details={"error": str(e), "table": f"{database_name}.{table_name}"},
            )
            # 严格模式：异常直接上抛
            raise

    def _create_temp_table_with_logging(
        self,
        task: MergeTask,
        temp_table_name: str,
        merge_logger,
        db_session: Session,
        target_format: str,
        job_compression: Optional[str],
        original_format: str,
        original_compression: str,
    ) -> List[str]:
        """带详细日志记录的临时表创建"""
        sql_statements = []

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 设置 Hive 合并参数
            merge_settings = [
                "SET hive.merge.mapfiles=true",
                "SET hive.merge.mapredfiles=true",
                "SET hive.merge.size.per.task=268435456",  # 256MB
                "SET hive.exec.dynamic.partition=true",
                "SET hive.exec.dynamic.partition.mode=nonstrict",
                # 关键：禁止 Tez 自动并行，配合单 reducer 强制减少输出文件数
                "SET hive.tez.auto.reducer.parallelism=false",
                "SET mapred.reduce.tasks=1",  # 减少输出文件数
            ]

            for setting in merge_settings:
                # 设置项较快，直接记录执行成功
                merge_logger.log(
                    MergePhase.TEMP_TABLE_CREATION,
                    MergeLogLevel.INFO,
                    f"SQL开始执行: {setting}",
                    details={"full_sql": setting},
                )
                cursor.execute(setting)
                merge_logger.log_sql_execution(
                    setting, MergePhase.TEMP_TABLE_CREATION, success=True
                )
                sql_statements.append(setting)

            self._apply_output_settings(
                cursor,
                merge_logger,
                sql_statements,
                target_format,
                job_compression,
            )

            # 删除可能存在的临时表
            drop_temp_sql = f"DROP TABLE IF EXISTS {temp_table_name}"
            merge_logger.log(
                MergePhase.TEMP_TABLE_CREATION,
                MergeLogLevel.INFO,
                f"SQL开始执行: {drop_temp_sql}",
                details={"full_sql": drop_temp_sql},
            )
            cursor.execute(drop_temp_sql)
            merge_logger.log_sql_execution(
                drop_temp_sql, MergePhase.TEMP_TABLE_CREATION, success=True
            )
            sql_statements.append(drop_temp_sql)

            # 创建临时表并执行合并
            # 读取原表是否为 EXTERNAL（用于保持表类型与路径）
            fmt_info = self._get_table_format_info(task.database_name, task.table_name)
            table_type = str(fmt_info.get("table_type", "")).upper()
            is_external = "EXTERNAL" in table_type
            original_location = (
                self._get_table_location(task.database_name, task.table_name) or ""
            )
            # 影子目录：在原父目录下使用固定根 ".merge_shadow"，并在其下创建按时间戳命名的子目录
            # 例如：hdfs://.../parent/.merge_shadow/<ts>
            ts_id = int(time.time())
            # 将影子目录切回原父目录，避免 /warehouse 路径的 HttpFS 限制
            parent_dir = (
                "/".join([p for p in original_location.rstrip("/").split("/")[:-1]])
                if original_location
                else ""
            )
            shadow_root = f"{parent_dir}/.merge_shadow" if parent_dir else ""
            shadow_dir = f"{shadow_root}/{ts_id}" if shadow_root else ""

            # 外部表：预创建影子目标目录，优先通过 HS2 执行 dfs，失败再回退 WebHDFS
            if is_external and shadow_dir:
                hs2_ok = False
                try:
                    try:
                        # 先确保根目录存在并开放权限，再创建本次会话的子目录
                        cursor.execute(f"dfs -mkdir -p {shadow_root}")
                        cursor.execute(f"dfs -chmod 777 {shadow_root}")
                        cursor.execute(f"dfs -mkdir -p {shadow_dir}")
                        cursor.execute(f"dfs -chmod 777 {shadow_dir}")
                        hs2_ok = True
                        merge_logger.log(
                            MergePhase.TEMP_TABLE_CREATION,
                            MergeLogLevel.INFO,
                            f"HS2 已创建影子目录并授权: {shadow_dir}",
                        )
                    except Exception as e:
                        merge_logger.log(
                            MergePhase.TEMP_TABLE_CREATION,
                            MergeLogLevel.WARNING,
                            f"HS2 创建影子目录失败，回退 WebHDFS: {e}",
                        )
                    if not hs2_ok:
                        # 先确保根目录存在
                        ok_root, msg_root = self.webhdfs_client.create_directory(
                            shadow_root, permission="777"
                        )
                        if not ok_root and "File exists" not in str(msg_root):
                            raise RuntimeError(f"创建影子根目录失败: {msg_root}")
                        merge_logger.log_hdfs_operation(
                            "mkdir",
                            shadow_root,
                            MergePhase.TEMP_TABLE_CREATION,
                            success=ok_root,
                            error_message=None if ok_root else str(msg_root),
                        )
                        # 再创建本次使用的子目录
                        ok_mkdir, msg_mkdir = self.webhdfs_client.create_directory(
                            shadow_dir, permission="777"
                        )
                        if not ok_mkdir and "File exists" not in str(msg_mkdir):
                            raise RuntimeError(f"创建影子目录失败: {msg_mkdir}")
                        merge_logger.log_hdfs_operation(
                            "mkdir",
                            shadow_dir,
                            MergePhase.TEMP_TABLE_CREATION,
                            success=ok_mkdir,
                            error_message=None if ok_mkdir else str(msg_mkdir),
                        )
                except Exception as e:
                    merge_logger.log_hdfs_operation(
                        "mkdir",
                        shadow_dir,
                        MergePhase.TEMP_TABLE_CREATION,
                        success=False,
                        error_message=str(e),
                    )
                    raise

            effective_format = target_format or original_format or "TEXTFILE"

            if is_external:
                fmt_clause = ""
                if effective_format in {"PARQUET", "ORC", "AVRO", "RCFILE"}:
                    fmt_clause = f" STORED AS {effective_format}"
                # 1) 预创建影子目录（上方已 mkdir），2) 写入影子目录
                insert_dir_sql = f"INSERT OVERWRITE DIRECTORY '{shadow_dir}'{fmt_clause} SELECT * FROM {task.table_name}"
                # 3) 创建外部临时表映射影子目录
                create_like_sql = f"CREATE EXTERNAL TABLE {temp_table_name} LIKE {task.table_name} LOCATION '{shadow_dir}'"

                self._apply_output_settings(
                    cursor,
                    merge_logger,
                    sql_statements,
                    effective_format,
                    job_compression,
                )

                # 执行：先写目录（长时 SQL 心跳），再建映射表
                self._execute_sql_with_heartbeat(
                    cursor=cursor,
                    sql=insert_dir_sql,
                    phase=MergePhase.TEMP_TABLE_CREATION,
                    merge_logger=merge_logger,
                    task=task,
                    db_session=db_session,
                    op_desc=f"写入影子目录: {shadow_dir}",
                    execution_phase_name="temp_table_creation",
                )
                sql_statements.append(insert_dir_sql)
                merge_logger.log_sql_execution(
                    create_like_sql, MergePhase.TEMP_TABLE_CREATION
                )
                cursor.execute(create_like_sql)
                sql_statements.append(create_like_sql)
                if effective_format and effective_format != original_format:
                    alter_temp_fmt = (
                        f"ALTER TABLE {temp_table_name} SET FILEFORMAT {effective_format}"
                    )
                    merge_logger.log_sql_execution(
                        alter_temp_fmt, MergePhase.TEMP_TABLE_CREATION
                    )
                    cursor.execute(alter_temp_fmt)
                    sql_statements.append(alter_temp_fmt)
                if job_compression and job_compression not in {None, "KEEP"}:
                    mapped_prop = None
                    if effective_format == "ORC":
                        mapped_prop = self._ORC_COMPRESSION.get(
                            job_compression, self._ORC_COMPRESSION.get("NONE")
                        )
                        if mapped_prop:
                            tbl_sql = (
                                f"ALTER TABLE {temp_table_name} SET TBLPROPERTIES('orc.compress'='{mapped_prop}')"
                            )
                            cursor.execute(tbl_sql)
                            merge_logger.log_sql_execution(
                                tbl_sql, MergePhase.TEMP_TABLE_CREATION
                            )
                            sql_statements.append(tbl_sql)
                    elif effective_format == "PARQUET":
                        mapped_prop = self._PARQUET_COMPRESSION.get(
                            job_compression, self._PARQUET_COMPRESSION.get("NONE")
                        )
                        if mapped_prop:
                            tbl_sql = (
                                f"ALTER TABLE {temp_table_name} SET TBLPROPERTIES('parquet.compression'='{mapped_prop}')"
                            )
                            cursor.execute(tbl_sql)
                            merge_logger.log_sql_execution(
                                tbl_sql, MergePhase.TEMP_TABLE_CREATION
                            )
                            sql_statements.append(tbl_sql)
            else:
                # 非外部表：保留 CTAS 临时表
                storage_clause = (
                    f" STORED AS {effective_format}"
                    if effective_format in {"PARQUET", "ORC", "AVRO", "RCFILE"}
                    else ""
                )
                properties = ["'transactional'='false'"]
                effective_compression = job_compression
                if effective_compression == "KEEP":
                    effective_compression = None
                if effective_compression and effective_compression != "NONE":
                    if effective_format == "ORC":
                        mapped = self._ORC_COMPRESSION.get(
                            effective_compression, self._ORC_COMPRESSION.get("SNAPPY")
                        )
                        if mapped:
                            properties.append(f"'orc.compress'='{mapped}'")
                    elif effective_format == "PARQUET":
                        mapped = self._PARQUET_COMPRESSION.get(
                            effective_compression, self._PARQUET_COMPRESSION.get("SNAPPY")
                        )
                        if mapped:
                            properties.append(f"'parquet.compression'='{mapped}'")
                elif effective_compression == "NONE":
                    if effective_format == "ORC":
                        properties.append("'orc.compress'='NONE'")
                    elif effective_format == "PARQUET":
                        properties.append("'parquet.compression'='UNCOMPRESSED'")
                props_clause = f" TBLPROPERTIES({', '.join(properties)})"
                select_sql = (
                    f"SELECT * FROM {task.table_name} WHERE {task.partition_filter} DISTRIBUTE BY 1"
                    if task.partition_filter
                    else f"SELECT * FROM {task.table_name} DISTRIBUTE BY 1"
                )
                create_sql = (
                    f"CREATE TABLE {temp_table_name}{storage_clause}{props_clause} AS {select_sql}"
                )
                # 长时 SQL：增加心跳日志
                self._execute_sql_with_heartbeat(
                    cursor=cursor,
                    sql=create_sql,
                    phase=MergePhase.TEMP_TABLE_CREATION,
                    merge_logger=merge_logger,
                    task=task,
                    db_session=db_session,
                    op_desc=f"创建临时表并写入数据: {temp_table_name}",
                    execution_phase_name="temp_table_creation",
                )
                sql_statements.append(create_sql)

            cursor.close()
            conn.close()

            merge_logger.log(
                MergePhase.TEMP_TABLE_CREATION,
                MergeLogLevel.INFO,
                f"临时表{temp_table_name}创建成功",
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
        db_session: Session,
        op_desc: str,
        execution_phase_name: str,
        interval: int = 10,
    ) -> None:
        """执行可能耗时较长的 SQL，期间定时输出心跳日志并刷新当前操作。

        - 在执行前记录“开始执行”日志
        - 执行结束后记录“执行成功/失败”日志
        - 执行期间每 `interval` 秒输出一次 INFO 心跳，包含已等待时长
        - 同步更新任务 `current_operation`，避免前端长时间静默
        """
        import threading

        stop = threading.Event()
        start_ts = time.time()

        def _heartbeat():
            i = 0
            while not stop.wait(interval):
                i += 1
                waited = int(time.time() - start_ts)
                merge_logger.log(
                    phase=phase,
                    level=MergeLogLevel.INFO,
                    message=f"正在执行: {op_desc}",
                    details={"elapsed_s": waited, "full_sql": sql[:200]},
                )
                # 仅刷新当前操作，避免误导性的进度上涨
                try:
                    cur_op = f"{op_desc} (已等待{waited}s)"
                    yarn_id = None
                    # 附带 YARN 应用心跳（如果配置了 RM）
                    if self.yarn_monitor is not None:
                        try:
                            # 拉取更宽的范围，包含 RUNNING/ACCEPTED/SUBMITTED，避免 RM 还未进入 RUNNING 时拿不到应用
                            apps = self.yarn_monitor.get_applications(limit=20)
                            apps = [
                                a
                                for a in apps
                                if str(getattr(a, "application_type", "")).upper()
                                in ("TEZ", "MAPREDUCE")
                            ]
                            # 选择最新启动的应用，优先匹配已记录的ID
                            app = None
                            if task.yarn_application_id:
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
                                # 记录 YARN 监控日志
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
                                # 把进度拼进 current_operation，便于用户识别
                                try:
                                    pct = int(getattr(app, "progress", 0) or 0)
                                    cur_op = f"{op_desc} - YARN {pct}% {getattr(app,'state','')} (队列:{getattr(app,'queue','')}) (已等待{waited}s)"
                                except Exception:
                                    pass
                        except Exception:
                            # 监控失败不影响主流程
                            pass

                    self._update_task_progress(
                        task,
                        db_session,
                        execution_phase=execution_phase_name,
                        yarn_application_id=yarn_id or task.yarn_application_id,
                        current_operation=cur_op,
                    )
                except Exception:
                    pass

        # 记录开始
        merge_logger.log(
            phase,
            MergeLogLevel.INFO,
            f"SQL开始执行: {op_desc}",
            details={"full_sql": sql},
        )
        hb = threading.Thread(target=_heartbeat, daemon=True)
        hb.start()
        try:
            cursor.execute(sql)
            stop.set()
            hb.join(timeout=0.2)
            merge_logger.log_sql_execution(sql, phase, success=True)
        except Exception as e:
            stop.set()
            hb.join(timeout=0.2)
            merge_logger.log_sql_execution(
                sql, phase, success=False, error_message=str(e)
            )
            raise

    def _atomic_table_swap_with_logging(
        self,
        task: MergeTask,
        temp_table_name: str,
        backup_table_name: str,
        merge_logger,
    ) -> List[str]:
        """带详细日志记录的原子表切换"""
        sql_statements = []

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 第一步：将原表重命名为备份表
            rename_to_backup_sql = (
                f"ALTER TABLE {task.table_name} RENAME TO {backup_table_name}"
            )
            merge_logger.log_sql_execution(rename_to_backup_sql, MergePhase.ATOMIC_SWAP)
            cursor.execute(rename_to_backup_sql)
            sql_statements.append(rename_to_backup_sql)

            merge_logger.log(
                MergePhase.ATOMIC_SWAP,
                MergeLogLevel.INFO,
                f"原表重命名为备份表: {task.table_name} -> {backup_table_name}",
                details={
                    "original_table": task.table_name,
                    "backup_table": backup_table_name,
                },
            )

            # 第二步：将临时表重命名为原表名
            rename_temp_to_original_sql = (
                f"ALTER TABLE {temp_table_name} RENAME TO {task.table_name}"
            )
            merge_logger.log_sql_execution(
                rename_temp_to_original_sql, MergePhase.ATOMIC_SWAP
            )
            cursor.execute(rename_temp_to_original_sql)
            sql_statements.append(rename_temp_to_original_sql)

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
                "原子表切换成功完成",
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
                f"原子表切换失败: {str(e)}",
                details={"error": str(e), "failed_operation": "table_rename"},
            )
            raise

        return sql_statements
