"""
安全的Hive合并引擎(重构版 - 混合架构)
使用组合模式调用专用管理器,同时保留核心业务逻辑方法
"""
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.engines.base_engine import BaseMergeEngine
from app.engines.safe_hive_atomic_swap import HiveAtomicSwapManager
from app.engines.safe_hive_file_counter import HiveFileCounter
from app.engines.safe_hive_metadata_manager import HiveMetadataManager
from app.engines.hive_partition_path_resolver import HivePartitionPathResolver
from app.engines.hive_partition_merge_executor import HivePartitionMergeExecutor
from app.engines.safe_hive_temp_table import HiveTempTableManager
from app.engines.safe_hive_utils import HiveEngineUtils
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.monitor.hive_connector import HiveMetastoreConnector
from app.utils.encryption import decrypt_cluster_password
from app.utils.merge_logger import MergeLogLevel, MergePhase, MergeTaskLogger
from app.utils.webhdfs_client import WebHDFSClient
from app.utils.yarn_monitor import YarnResourceManagerMonitor

logger = logging.getLogger(__name__)


class SafeHiveMergeEngine(BaseMergeEngine):
    """
    安全的Hive合并引擎(重构版)
    通过组合模式使用各个专用管理器,保持代码模块化
    同时保留核心业务方法以确保向后兼容
    """

    def __init__(self, cluster: Cluster):
        super().__init__(cluster)
        
        # 解密LDAP密码
        self.hive_password = None
        if cluster.hive_password:
            try:
                self.hive_password = decrypt_cluster_password(cluster)
            except Exception:
                self.hive_password = None
            if not self.hive_password:
                self.hive_password = cluster.hive_password

        # 初始化WebHDFS客户端
        self.webhdfs_client = WebHDFSClient(
            namenode_url=cluster.hdfs_namenode_url,
            user=cluster.hdfs_user or "hdfs"
        )

        # 初始化YARN监控器
        self.yarn_monitor = None
        if cluster.yarn_resource_manager_url:
            yarn_urls = [
                url.strip() for url in cluster.yarn_resource_manager_url.split(",")
            ]
            self.yarn_monitor = YarnResourceManagerMonitor(yarn_urls)

        # 初始化各个管理器
        self.metadata_manager = HiveMetadataManager(cluster, self.hive_password)
        self.file_counter = HiveFileCounter(cluster, self.webhdfs_client, self.hive_password)
        self.path_resolver = HivePartitionPathResolver(cluster, self.webhdfs_client, self.hive_password)
        self.temp_table_manager = HiveTempTableManager(cluster, self.hive_password)
        self.atomic_swap_manager = HiveAtomicSwapManager(
            cluster,
            self.webhdfs_client,
            self.yarn_monitor,
            self.hive_password,
            extract_error_detail_func=HiveEngineUtils.extract_error_detail,
            update_task_progress_func=self._update_task_progress,
        )

        # 初始化合并执行器(需要在其他管理器之后,因为它依赖这些管理器)
        self.partition_merge_executor = HivePartitionMergeExecutor(self)

        # 保留的实例变量
        self.metastore_connector = HiveMetastoreConnector(cluster.hive_metastore_url)
        self.progress_callback: Optional[Callable[[str, str], None]] = None
        self.hdfs_scanner = None  # 兼容性保留

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
        current_operation: str = None,
        yarn_application_id: str = None,
    ):
        """更新任务进度信息"""
        try:
            if execution_phase is not None:
                task.execution_phase = execution_phase
            if progress_percentage is not None:
                task.progress_percentage = min(99.0, max(0.0, progress_percentage))
            if estimated_remaining_time is not None:
                task.estimated_remaining_time = estimated_remaining_time
            if processed_files_count is not None:
                task.processed_files_count = processed_files_count
            if total_files_count is not None:
                task.total_files_count = total_files_count
            if current_operation is not None:
                task.current_operation = current_operation
            if yarn_application_id is not None:
                task.yarn_application_id = yarn_application_id

            db_session.commit()
            db_session.refresh(task)
        except Exception:
            db_session.rollback()

    # ==================== 委托方法 (使用新的管理器) ====================
    
    def _extract_error_detail(self, exc: Exception) -> str:
        """提取错误详情 - 委托给工具类"""
        return HiveEngineUtils.extract_error_detail(exc)

    def _create_hive_connection(self, database_name: str = None):
        """创建Hive连接 - 委托给元数据管理器"""
        return self.metadata_manager._create_hive_connection(database_name)

    def _cleanup_connections(self):
        """清理连接 - 委托给元数据管理器"""
        return self.metadata_manager._cleanup_connections()

    def _table_exists(self, database_name: str, table_name: str) -> bool:
        """检查表是否存在 - 委托给元数据管理器"""
        return self.metadata_manager._table_exists(database_name, table_name)

    def _is_partitioned_table(self, database_name: str, table_name: str) -> bool:
        """检查是否为分区表 - 委托给元数据管理器"""
        return self.metadata_manager._is_partitioned_table(database_name, table_name)

    def _get_table_location(self, database_name: str, table_name: str) -> Optional[str]:
        """获取表位置 - 委托给元数据管理器"""
        return self.metadata_manager._get_table_location(database_name, table_name)

    def _get_table_partitions(self, database_name: str, table_name: str) -> List[str]:
        """获取表分区列表 - 委托给元数据管理器"""
        return self.metadata_manager._get_table_partitions(database_name, table_name)

    def _get_table_format_info(self, database_name: str, table_name: str) -> Dict[str, Any]:
        """获取表格式信息 - 委托给元数据管理器"""
        return self.metadata_manager._get_table_format_info(database_name, table_name)

    def _infer_storage_format_name(self, fmt: Dict[str, Any]) -> str:
        """推断存储格式名称 - 委托给元数据管理器"""
        return self.metadata_manager._infer_storage_format_name(fmt)

    def _infer_table_compression(self, fmt: Dict[str, Any], storage_format: str) -> str:
        """推断表压缩格式 - 委托给元数据管理器"""
        return self.metadata_manager._infer_table_compression(fmt, storage_format)

    def _is_unsupported_table_type(self, fmt: Dict[str, Any]) -> bool:
        """检查是否为不支持的表类型 - 委托给元数据管理器"""
        return self.metadata_manager._is_unsupported_table_type(fmt)

    def _unsupported_reason(self, fmt: Dict[str, Any]) -> str:
        """获取不支持的原因 - 委托给元数据管理器"""
        return self.metadata_manager._unsupported_reason(fmt)

    def _get_table_columns(self, database_name: str, table_name: str):
        """获取表列信息 - 委托给元数据管理器"""
        return self.metadata_manager._get_table_columns(database_name, table_name)

    def _get_partition_columns(self, database: str, table: str) -> list[str]:
        """获取分区列 - 委托给元数据管理器"""
        return self.metadata_manager._get_partition_columns(database, table)

    def _list_all_partitions(self, database: str, table: str) -> list[str]:
        """列出所有分区 - 委托给元数据管理器"""
        return self.metadata_manager._list_all_partitions(database, table)

    def _parse_table_schema_from_show_create(self, database: str, table: str) -> Dict[str, Any]:
        """解析表结构 - 委托给元数据管理器"""
        return self.metadata_manager._parse_table_schema_from_show_create(database, table)

    def _get_format_classes(self, storage_format: str) -> tuple:
        """获取格式类 - 委托给工具类"""
        return HiveEngineUtils.get_format_classes(storage_format)

    def _apply_output_settings(self, cursor, merge_logger, sql_statements: List[str], storage_format: str, compression: Optional[str]):
        """应用输出设置 - 委托给元数据管理器"""
        return self.metadata_manager._apply_output_settings(cursor, merge_logger, sql_statements, storage_format, compression)

    def _update_active_table_format(self, database_name: str, table_name: str, storage_format: str, compression: Optional[str], merge_logger):
        """更新活动表格式 - 委托给元数据管理器"""
        return self.metadata_manager._update_active_table_format(database_name, table_name, storage_format, compression, merge_logger)

    # 分区路径解析相关方法(委托给path_resolver)
    def _partition_filter_to_spec(self, partition_filter: str) -> Optional[str]:
        """分区过滤器转换 - 委托给路径解析器"""
        return self.path_resolver.partition_filter_to_spec(partition_filter)

    def _split_or_partition_filter(self, partition_filter: str) -> List[str]:
        """分割OR分区过滤器 - 委托给路径解析器"""
        return self.path_resolver.split_or_partition_filter(partition_filter)

    def _validate_partition_filter(self, database_name: str, table_name: str, partition_filter: str) -> bool:
        """验证分区过滤器 - 委托给路径解析器"""
        return self.path_resolver.validate_partition_filter(database_name, table_name, partition_filter)

    def _parse_partition_spec(self, partition_spec: str) -> Dict[str, str]:
        """解析分区规格 - 委托给路径解析器"""
        return self.path_resolver.parse_partition_spec(partition_spec)

    def _format_partition_spec(self, partition_kv: Dict[str, str]) -> str:
        """格式化分区规格 - 委托给路径解析器"""
        return self.path_resolver.format_partition_spec(partition_kv)

    def _generate_temp_partition_kv(self, partition_kv: Dict[str, str], ts: int) -> Dict[str, str]:
        """生成临时分区KV - 委托给路径解析器"""
        return self.path_resolver.generate_temp_partition_kv(partition_kv, ts)

    def _get_partition_hdfs_path(self, database_name: str, table_name: str, partition_filter: str) -> Optional[str]:
        """获取分区HDFS路径 - 委托给路径解析器"""
        return self.path_resolver.get_partition_hdfs_path(database_name, table_name, partition_filter)

    def _resolve_partition_path(self, database_name: str, table_name: str, partition_filter: str) -> Optional[str]:
        """解析分区路径 - 委托给路径解析器"""
        return self.path_resolver.resolve_partition_path(database_name, table_name, partition_filter)

    def _resolve_partition_path_fallback(self, database_name: str, table_name: str, partition_spec: str) -> Optional[str]:
        """解析分区路径(回退) - 委托给路径解析器"""
        return self.path_resolver._resolve_partition_path_fallback(database_name, table_name, partition_spec)

    # 分区合并执行相关方法(委托给partition_merge_executor)
    def _get_non_partition_columns(self, database: str, table: str) -> str:
        """获取非分区列 - 委托给合并执行器"""
        return self.partition_merge_executor._get_non_partition_columns(database, table)

    def _execute_partition_native_merge(self, task, merge_logger, progress_tracker):
        """执行分区原生合并 - 委托给合并执行器"""
        return self.partition_merge_executor.execute_partition_native_merge(task, merge_logger, progress_tracker)

    def _execute_single_partition_native_merge(self, task, partition_spec: str, merge_logger, progress_tracker):
        """执行单分区原生合并 - 委托给合并执行器"""
        return self.partition_merge_executor.execute_single_partition_native_merge(task, partition_spec, merge_logger, progress_tracker)

    def _execute_full_table_dynamic_partition_merge(self, task, merge_logger, db_session):
        """执行整表动态分区合并 - 委托给合并执行器"""
        return self.partition_merge_executor.execute_full_table_dynamic_partition_merge(task, merge_logger, db_session)

    # 临时表管理相关方法
    def _generate_temp_table_name(self, table_name: str) -> str:
        """生成临时表名 - 委托给临时表管理器"""
        return self.temp_table_manager._generate_temp_table_name(table_name)

    def _generate_backup_table_name(self, table_name: str) -> str:
        """生成备份表名 - 委托给临时表管理器"""
        return self.temp_table_manager._generate_backup_table_name(table_name)

    def _create_temp_table(self, task: MergeTask, temp_table_name: str) -> List[str]:
        """创建临时表 - 委托给临时表管理器"""
        return self.temp_table_manager._create_temp_table(task, temp_table_name)

    def _create_temp_table_with_logging(self, task, temp_table_name, merge_logger, db_session):
        """创建临时表(带日志) - 委托给临时表管理器"""
        return self.temp_table_manager._create_temp_table_with_logging(task, temp_table_name, merge_logger, db_session)

    def _validate_temp_table_data(self, task, temp_table_name, merge_logger):
        """验证临时表数据 - 委托给临时表管理器"""
        return self.temp_table_manager._validate_temp_table_data(task, temp_table_name, merge_logger)

    # 原子交换相关方法
    def _test_connections(self, merge_logger=None, task=None, db_session=None) -> bool:
        """测试连接 - 委托给原子交换管理器"""
        return self.atomic_swap_manager._test_connections(merge_logger, task, db_session)

    def _execute_sql_with_heartbeat(self, **kwargs):
        """执行SQL(带心跳) - 委托给原子交换管理器"""
        return self.atomic_swap_manager._execute_sql_with_heartbeat(**kwargs)

    def _atomic_table_swap(self, task, temp_table_name, backup_table_name):
        """原子表交换 - 委托给原子交换管理器"""
        return self.atomic_swap_manager._atomic_table_swap(task, temp_table_name, backup_table_name)

    def _atomic_table_swap_with_logging(self, task, temp_table_name, backup_table_name, merge_logger):
        """原子表交换(带日志) - 委托给原子交换管理器"""
        return self.atomic_swap_manager._atomic_table_swap_with_logging(task, temp_table_name, backup_table_name, merge_logger)

    def _atomic_swap_table_location(self, task, temp_table_name, merge_logger, db_session):
        """原子交换表位置 - 委托给原子交换管理器"""
        return self.atomic_swap_manager._atomic_swap_table_location(task, temp_table_name, merge_logger, db_session)

    def _hdfs_rename_with_fallback(self, src_path, dest_path, merge_logger, phase):
        """HDFS重命名(带回退) - 委托给原子交换管理器"""
        return self.atomic_swap_manager._hdfs_rename_with_fallback(src_path, dest_path, merge_logger, phase)

    def _rollback_merge(self, task, backup_table_name, merge_logger):
        """回滚合并 - 委托给原子交换管理器"""
        return self.atomic_swap_manager._rollback_merge(task, backup_table_name, merge_logger)

    # 文件统计相关方法
    def _get_file_count(self, database_name: str, table_name: str, partition_filter: Optional[str] = None) -> int:
        """获取文件数量 - 委托给文件计数器"""
        return self.file_counter._get_file_count(database_name, table_name, partition_filter)

    def _get_file_count_with_logging(self, database_name, table_name, partition_filter, merge_logger, phase):
        """获取文件数量(带日志) - 委托给文件计数器"""
        return self.file_counter._get_file_count_with_logging(database_name, table_name, partition_filter, merge_logger, phase)

    def _get_file_count_fallback(self, database_name, table_name, partition_filter):
        """获取文件数量(回退) - 委托给文件计数器"""
        return self.file_counter._get_file_count_fallback(database_name, table_name, partition_filter)

    def _get_temp_table_file_count(self, database_name, temp_table_name, partition_filter, merge_logger):
        """获取临时表文件数量 - 委托给文件计数器"""
        return self.file_counter._get_temp_table_file_count(database_name, temp_table_name, partition_filter, merge_logger)

    def _count_partition_files(self, partition_path: str) -> int:
        """统计分区文件 - 委托给文件计数器"""
        return self.file_counter._count_partition_files(partition_path)

    def _wait_for_partition_data(self, partition_path, merge_logger, timeout):
        """等待分区数据 - 委托给文件计数器"""
        return self.file_counter._wait_for_partition_data(partition_path, merge_logger, timeout)

    def _cleanup_temp_partition(self, temp_partition_path, merge_logger):
        """清理临时分区 - 委托给文件计数器"""
        return self.file_counter._cleanup_temp_partition(temp_partition_path, merge_logger)

    # ==================== 核心业务方法 (暂时保留原实现) ====================
    # 这些方法从备份文件中复制,待后续逐步重构

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

            # 存储/格式检查
            fmt = self._get_table_format_info(task.database_name, task.table_name)
            if self._is_unsupported_table_type(fmt):
                result["valid"] = False
                result["message"] = self._unsupported_reason(fmt)
                return result

            # 检查是否为分区表
            is_partitioned = self._is_partitioned_table(
                task.database_name, task.table_name
            )

            # 分区表警告
            if is_partitioned and not task.partition_filter:
                result["warnings"].append(
                    "Partitioned table detected but no partition filter specified. This will merge all partitions."
                )

            # 验证分区过滤器
            if task.partition_filter:
                if not self._validate_partition_filter(
                    task.database_name, task.table_name, task.partition_filter
                ):
                    result["warnings"].append(
                        "Partition filter may not match any partitions"
                    )

            # 检查临时表名冲突
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

    # execute_merge, get_merge_preview, estimate_duration 等核心方法
    # 需要从备份文件中完整复制,这里暂时用stub代替
    def execute_merge(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        """执行合并 - 需要从备份文件复制完整实现"""
        raise NotImplementedError("需要从备份文件复制execute_merge的完整实现")

    def get_merge_preview(self, task: MergeTask) -> Dict[str, Any]:
        """获取合并预览 - 需要从备份文件复制完整实现"""
        raise NotImplementedError("需要从备份文件复制get_merge_preview的完整实现")

    def estimate_duration(self, task: MergeTask) -> int:
        """估算耗时"""
        return 300  # 默认5分钟

    # 测试桩方法
    def _execute_concatenate(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        return {"success": False, "message": "stub"}

    def _execute_insert_overwrite(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        return {"success": False, "message": "stub"}

    def _execute_safe_merge(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        return {"success": False, "message": "stub"}
