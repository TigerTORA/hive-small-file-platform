"""
Hive文件统计器
负责统计表和分区的文件数量
"""
import logging
import time
from typing import Any, Dict, Optional

from pyhive import hive
from sqlalchemy.orm import Session

from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.utils.merge_logger import MergeLogLevel, MergePhase, MergeTaskLogger
from app.utils.webhdfs_client import WebHDFSClient

logger = logging.getLogger(__name__)


class HiveFileCounter:
    """Hive文件统计器,用于精确统计表和分区的文件数量"""
    
    def __init__(
        self,
        cluster: Cluster,
        webhdfs_client: WebHDFSClient,
        hive_password: Optional[str] = None
    ):
        """
        初始化文件统计器
        
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
            logger.debug(
                f"Creating LDAP connection for user: {self.cluster.hive_username}"
            )

        return hive.Connection(**hive_conn_params)

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

    def _count_partition_files(self, partition_path: str) -> int:
        """
        统计分区目录下的文件数量(排除子目录)

        Args:
            partition_path: 分区HDFS路径

        Returns:
            文件数量
        """
        try:
            files = self.webhdfs_client.list_directory(partition_path)
            return len([f for f in files if not f.is_directory])
        except Exception as e:
            logger.warning(f"统计分区文件数失败: {e}")
            return 0

    def _wait_for_partition_data(
        self,
        database: str,
        table: str,
        partition_spec: str,
        timeout: int = 3600
    ):
        """
        轮询检查分区数据是否生成完成

        Args:
            database: 数据库名
            table: 表名
            partition_spec: 分区规格
            timeout: 超时时间(秒)

        Raises:
            Exception: 超时或检查失败
        """
        import time
        start = time.time()
        check_interval = 10  # 每10秒检查一次

        logger.info(f"开始等待分区数据生成: {partition_spec}, 超时={timeout}秒")

        while time.time() - start < timeout:
            try:
                partition_path = self._resolve_partition_path(database, table, partition_spec)
                if partition_path:
                    file_count = self._count_partition_files(partition_path)
                    if file_count > 0:
                        logger.info(f"临时分区数据已生成: {partition_path}, 文件数={file_count}")
                        return
                    else:
                        logger.debug(f"临时分区数据尚未生成,继续等待... ({int(time.time() - start)}秒)")
            except Exception as e:
                logger.debug(f"检查分区数据时出错,继续等待: {e}")

            time.sleep(check_interval)

        raise Exception(f"等待分区数据超时({timeout}秒): {partition_spec}")

    def _cleanup_temp_partition(
        self,
        database: str,
        table: str,
        temp_partition_spec: str,
        merge_logger
    ):
        """
        删除临时分区(失败时的清理操作)

        Args:
            database: 数据库名
            table: 表名
            temp_partition_spec: 临时分区规格
            merge_logger: 合并日志记录器
        """
        try:
            conn = self._create_hive_connection(database)
            cursor = conn.cursor()
            drop_sql = f"ALTER TABLE {table} DROP IF EXISTS PARTITION ({temp_partition_spec})"
            cursor.execute(drop_sql)
            cursor.close()
            conn.close()
            merge_logger.log(
                MergePhase.ROLLBACK,
                MergeLogLevel.INFO,
                f"已清理临时分区: {temp_partition_spec}"
            )
        except Exception as e:
            merge_logger.log(
                MergePhase.ROLLBACK,
                MergeLogLevel.WARNING,
                f"清理临时分区失败: {e}"
            )

