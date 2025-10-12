"""
Hive分区路径解析器
负责分区路径的解析、查询和规格格式转换
"""

import logging
import re
from typing import Dict, List, Optional

from pyhive import hive

from app.models.cluster import Cluster
from app.utils.webhdfs_client import WebHDFSClient

logger = logging.getLogger(__name__)


class HivePartitionPathResolver:
    """Hive分区路径解析器,负责分区路径相关的所有操作"""

    def __init__(
        self,
        cluster: Cluster,
        webhdfs_client: WebHDFSClient,
        hive_password: Optional[str] = None,
    ):
        """
        初始化分区路径解析器

        Args:
            cluster: 集群配置对象
            webhdfs_client: WebHDFS客户端实例
            hive_password: 解密后的Hive密码(可选)
        """
        self.cluster = cluster
        self.webhdfs_client = webhdfs_client
        self.hive_password = hive_password

    def _create_hive_connection(self, database_name: str = None):
        """创建Hive连接(支持LDAP认证)"""
        hive_conn_params = {
            "host": self.cluster.hive_host,
            "port": self.cluster.hive_port,
            "database": database_name or self.cluster.hive_database or "default",
        }

        if self.cluster.auth_type == "LDAP" and self.cluster.hive_username:
            hive_conn_params["username"] = self.cluster.hive_username
            if self.hive_password:
                hive_conn_params["password"] = self.hive_password
            hive_conn_params["auth"] = "LDAP"

        return hive.Connection(**hive_conn_params)

    def _get_table_location(self, database_name: str, table_name: str) -> Optional[str]:
        """获取表的HDFS位置"""
        from app.services.path_resolver import PathResolver

        try:
            return PathResolver.get_table_location(
                self.cluster, database_name, table_name
            )
        except Exception as e:
            logger.error(f"Failed to resolve table location: {e}")
            return None

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

    def partition_filter_to_spec(self, partition_filter: str) -> Optional[str]:
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

    def split_or_partition_filter(self, partition_filter: str) -> List[str]:
        """
        将包含OR条件的partition_filter拆分成多个单分区条件
        例如: (partition_id='p1' OR partition_id='p2') -> ['partition_id=\'p1\'', 'partition_id=\'p2\'']
        """
        if not partition_filter or "or" not in partition_filter.lower():
            return [partition_filter] if partition_filter else []

        # 移除外层括号
        cleaned = partition_filter.strip()
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = cleaned[1:-1].strip()

        # 使用正则分割OR (忽略大小写)
        parts = re.split(r"\s+or\s+", cleaned, flags=re.IGNORECASE)
        return [part.strip() for part in parts if part.strip()]

    def validate_partition_filter(
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

    def parse_partition_spec(self, partition_spec: str) -> Dict[str, str]:
        """
        解析分区规格字符串为键值对字典

        Examples:
            partition_id='partition_0000' -> {'partition_id': 'partition_0000'}
            dt='2024-01-01' AND hour='12' -> {'dt': '2024-01-01', 'hour': '12'}
        """
        result = {}
        # 匹配 key='value' 或 key="value"
        pattern = r"(\w+)\s*=\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, partition_spec, re.IGNORECASE)
        for key, value in matches:
            result[key] = value
        return result

    def format_partition_spec(self, partition_kv: Dict[str, str]) -> str:
        """
        格式化分区键值对为分区规格字符串

        Examples:
            {'partition_id': 'temp_0000_123'} -> "partition_id='temp_0000_123'"
            {'dt': '2024-01-01', 'hour': '12'} -> "dt='2024-01-01', hour='12'"
        """
        parts = [f"{key}='{value}'" for key, value in partition_kv.items()]
        return ", ".join(parts)

    def generate_temp_partition_kv(
        self, partition_kv: Dict[str, str], ts: int
    ) -> Dict[str, str]:
        """
        生成临时分区键值对

        Examples:
            {'partition_id': 'partition_0000'}, 123 -> {'partition_id': 'temp_0000_123'}
            {'dt': '2024-01-01'}, 456 -> {'dt': 'temp_20240101_456'}
        """
        temp_kv = {}
        for key, value in partition_kv.items():
            # 提取原始分区值(移除可能的前缀和特殊字符)
            clean_value = (
                value.replace("partition_", "").replace("-", "").replace(":", "")
            )
            temp_value = f"temp_{clean_value}_{ts}"
            temp_kv[key] = temp_value
        return temp_kv

    def get_partition_hdfs_path(
        self, database_name: str, table_name: str, partition_filter: str
    ) -> Optional[str]:
        """
        通过SHOW PARTITIONS和WebHDFS查询获取分区的真实HDFS路径
        适用于外部表和管理表，支持非标准目录结构
        """
        try:
            # 1. 从partition_filter提取分区值
            # 例如: partition_id='partition_0000' -> partition_0000
            match = re.search(r"['\"]([^'\"]+)['\"]", partition_filter)
            if not match:
                logger.warning(f"无法从partition_filter提取分区值: {partition_filter}")
                return self._resolve_partition_path_fallback(
                    database_name, table_name, partition_filter
                )

            partition_value = match.group(1)  # 例如: partition_0000

            # 2. 获取表的HDFS根路径
            root_location = self._get_table_location(database_name, table_name)
            if not root_location:
                return None

            # 移除hdfs://nameservice前缀,WebHDFS只需要路径部分
            clean_root = root_location
            if root_location.startswith("hdfs://"):
                parts = root_location.split("/", 3)
                if len(parts) > 3:
                    clean_root = "/" + parts[3]

            # 3. 通过WebHDFS列举表目录,查找匹配的分区目录
            hdfs = self.webhdfs_client
            try:
                file_statuses = hdfs.list_directory(clean_root)
                if not file_statuses:
                    logger.warning(f"表目录为空: {root_location}")
                    return self._resolve_partition_path_fallback(
                        database_name, table_name, partition_filter
                    )

                # 查找包含分区值的目录 - 优先匹配标准Hive格式 (key=value)
                # 从partition_filter提取分区键名,例如: partition_id='partition_0000' -> partition_id
                # 移除可能的括号
                partition_key = partition_filter.split("=")[0].strip().strip("()")
                standard_format = f"{partition_key}={partition_value}"
                logger.info(
                    f"查找分区目录: partition_key={partition_key}, partition_value={partition_value}, standard_format={standard_format}"
                )

                # 首先查找标准格式的分区目录
                for file_info in file_statuses:
                    if file_info.is_directory and standard_format in file_info.path:
                        logger.info(
                            f"通过WebHDFS找到分区路径(标准格式): {file_info.path}"
                        )
                        return file_info.path

                # 如果没找到标准格式,尝试匹配只包含分区值的目录(非标准格式)
                for file_info in file_statuses:
                    # 确保不会误匹配到标准格式的一部分
                    path_suffix = file_info.path.split("/")[-1]
                    if file_info.is_directory and path_suffix == partition_value:
                        logger.info(
                            f"通过WebHDFS找到分区路径(非标准格式): {file_info.path}"
                        )
                        return file_info.path

                logger.warning(
                    f"未找到匹配分区值 '{partition_value}' 的目录(标准格式:{standard_format})"
                )
                return self._resolve_partition_path_fallback(
                    database_name, table_name, partition_filter
                )

            except Exception as hdfs_e:
                import traceback

                logger.warning(f"WebHDFS查询分区目录失败: {hdfs_e}")
                logger.warning(f"异常堆栈: {traceback.format_exc()}")
                return self._resolve_partition_path_fallback(
                    database_name, table_name, partition_filter
                )

        except Exception as e:
            import traceback

            logger.warning(f"Failed to get partition HDFS path via WebHDFS: {e}")
            logger.warning(f"外层异常堆栈: {traceback.format_exc()}")
            # 回退到简单拼接方法
            return self._resolve_partition_path_fallback(
                database_name, table_name, partition_filter
            )

    def resolve_partition_path(
        self, database_name: str, table_name: str, partition_filter: str
    ) -> Optional[str]:
        """根据分区过滤器解析分区在 HDFS 的路径 - 兼容方法,调用新实现"""
        logger.info(
            f"resolve_partition_path被调用: database={database_name}, table={table_name}, filter={partition_filter}"
        )
        result = self.get_partition_hdfs_path(
            database_name, table_name, partition_filter
        )
        logger.info(f"resolve_partition_path返回: {result}")
        return result

    def _resolve_partition_path_fallback(
        self, database_name: str, table_name: str, partition_filter: str
    ) -> Optional[str]:
        """根据分区过滤器解析分区在 HDFS 的路径（在表根路径下拼接spec）- 回退方法"""
        try:
            root = self._get_table_location(database_name, table_name)
            if not root:
                return None

            # 移除hdfs://nameservice前缀,只保留路径部分
            if root.startswith("hdfs://"):
                # hdfs://nameservice1/user/test/path -> /user/test/path
                parts = root.split("/", 3)
                if len(parts) > 3:
                    root = "/" + parts[3]

            # 规范化为路径: key=value/key2=value2
            # 例如: partition_id='partition_0000' -> partition_id=partition_0000
            normalized = partition_filter.strip()
            # 移除外层括号
            normalized = normalized.strip("()")
            # 替换AND为路径分隔符
            normalized = re.sub(r"\s+and\s+", "/", normalized, flags=re.IGNORECASE)
            # 移除空格和引号
            normalized = normalized.replace(" ", "").replace("'", "").replace('"', "")

            if not normalized:
                return None

            logger.info(
                f"_resolve_partition_path_fallback: root={root}, normalized={normalized}"
            )
            return root.rstrip("/") + "/" + normalized
        except Exception as e:
            logger.error(f"_resolve_partition_path_fallback failed: {e}")
            return None
