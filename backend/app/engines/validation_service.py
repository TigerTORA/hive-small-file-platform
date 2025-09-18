"""
验证服务模块
负责合并任务的验证、表检查、格式验证等
"""

import logging
import re
from typing import Any, Dict, List, Optional

from app.engines.connection_manager import HiveConnectionManager
from app.models.merge_task import MergeTask

logger = logging.getLogger(__name__)


class MergeTaskValidationService:
    """合并任务验证服务"""

    def __init__(self, connection_manager: HiveConnectionManager):
        self.connection_manager = connection_manager

    def validate_task(self, task: MergeTask) -> Dict[str, Any]:
        """验证合并任务是否可执行"""
        result = {"valid": True, "message": "Task validation passed", "warnings": []}

        try:
            # 连接检查
            if not self.connection_manager.test_connections():
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

            return result

        except Exception as e:
            logger.error(f"Task validation failed: {e}")
            result["valid"] = False
            result["message"] = f"Validation error: {str(e)}"
            return result

    def _table_exists(self, database_name: str, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            with self.connection_manager.get_hive_connection(database_name) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False

    def _is_partitioned_table(self, database_name: str, table_name: str) -> bool:
        """检查表是否为分区表"""
        try:
            with self.connection_manager.metastore_connector as connector:
                result = connector.get_table_info(database_name, table_name)
                return result.get("is_partitioned", False)
        except Exception as e:
            logger.error(f"Error checking partition status: {e}")
            return False

    def _get_table_partitions(self, database_name: str, table_name: str) -> List[str]:
        """获取表的分区列表"""
        try:
            with self.connection_manager.get_hive_connection(database_name) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SHOW PARTITIONS {database_name}.{table_name}")
                partitions = [row[0] for row in cursor.fetchall()]
                return partitions
        except Exception as e:
            logger.error(f"Error getting table partitions: {e}")
            return []

    def _get_table_format_info(
        self, database_name: str, table_name: str
    ) -> Dict[str, Any]:
        """获取表格式信息"""
        try:
            with self.connection_manager.metastore_connector as connector:
                return connector.get_table_format_info(database_name, table_name)
        except Exception as e:
            logger.error(f"Error getting table format info: {e}")
            return {}

    def _is_unsupported_table_type(self, fmt: Dict[str, Any]) -> bool:
        """检查是否为不支持的表类型"""
        input_format = fmt.get("input_format", "").lower()
        serde_lib = fmt.get("serde_lib", "").lower()

        # Hudi表检测
        if (
            "hudi" in input_format
            or "hudi" in serde_lib
            or "org.apache.hudi" in input_format
            or "org.apache.hudi" in serde_lib
        ):
            return True

        # Iceberg表检测
        if (
            "iceberg" in input_format
            or "iceberg" in serde_lib
            or "org.apache.iceberg" in input_format
            or "org.apache.iceberg" in serde_lib
        ):
            return True

        # Delta Lake表检测
        if (
            "delta" in input_format
            or "delta" in serde_lib
            or "io.delta" in input_format
            or "io.delta" in serde_lib
        ):
            return True

        # ACID事务表检测
        table_props = fmt.get("table_properties", {})
        if table_props.get("transactional", "").lower() == "true":
            return True

        return False

    def _unsupported_reason(self, fmt: Dict[str, Any]) -> str:
        """获取不支持的原因"""
        input_format = fmt.get("input_format", "").lower()
        serde_lib = fmt.get("serde_lib", "").lower()

        if "hudi" in input_format or "hudi" in serde_lib:
            return "Hudi tables are not supported for concatenate merge"

        if "iceberg" in input_format or "iceberg" in serde_lib:
            return "Iceberg tables are not supported for concatenate merge"

        if "delta" in input_format or "delta" in serde_lib:
            return "Delta Lake tables are not supported for concatenate merge"

        table_props = fmt.get("table_properties", {})
        if table_props.get("transactional", "").lower() == "true":
            return "ACID transactional tables are not supported for concatenate merge"

        return "Unsupported table format detected"

    def _validate_partition_filter(
        self, database_name: str, table_name: str, partition_filter: str
    ) -> bool:
        """验证分区过滤器是否有效"""
        try:
            # 简单的分区过滤器验证：检查是否有匹配的分区
            partitions = self._get_table_partitions(database_name, table_name)
            if not partitions:
                return False

            # 使用正则表达式验证分区过滤器
            # 这里假设分区过滤器格式如：year=2023/month=01
            filter_pattern = partition_filter.replace("=", "=").replace("/", "/")
            for partition in partitions:
                if filter_pattern in partition:
                    return True

            return False

        except Exception as e:
            logger.error(f"Error validating partition filter: {e}")
            return False

    def get_table_columns(
        self, database_name: str, table_name: str
    ) -> tuple[List[str], List[str]]:
        """获取表的列信息"""
        try:
            with self.connection_manager.get_hive_connection(database_name) as conn:
                cursor = conn.cursor()
                cursor.execute(f"DESCRIBE {database_name}.{table_name}")
                columns = []
                partition_columns = []
                is_partition_section = False

                for row in cursor.fetchall():
                    col_name = row[0].strip()
                    if col_name == "":
                        continue
                    if "# Partition Information" in row[0]:
                        is_partition_section = True
                        continue
                    if is_partition_section:
                        if col_name != "col_name":  # Skip header
                            partition_columns.append(col_name)
                    else:
                        columns.append(col_name)

                return columns, partition_columns

        except Exception as e:
            logger.error(f"Error getting table columns: {e}")
            return [], []
