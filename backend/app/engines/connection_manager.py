"""
连接管理器模块
负责管理Hive、HDFS、YARN等外部系统的连接
"""

import logging
from typing import List, Optional

from pyhive import hive

from app.models.cluster import Cluster
from app.monitor.hive_connector import HiveMetastoreConnector
from app.utils.encryption import decrypt_cluster_password
from app.utils.webhdfs_client import WebHDFSClient
from app.utils.yarn_monitor import YarnResourceManagerMonitor

logger = logging.getLogger(__name__)


class HiveConnectionManager:
    """Hive集群连接管理器"""

    def __init__(self, cluster: Cluster):
        self.cluster = cluster
        self.metastore_connector = HiveMetastoreConnector(cluster.hive_metastore_url)
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
        self.hive_password = self._init_hive_password()
        self._hive_connection = None

    def _init_hive_password(self) -> Optional[str]:
        """初始化Hive密码"""
        if not self.cluster.hive_password:
            return None

        # 解密失败时回退到明文，以兼容直接存放明文密码的环境
        try:
            return decrypt_cluster_password(self.cluster)
        except Exception:
            return self.cluster.hive_password

    def test_connections(self) -> bool:
        """测试所有连接"""
        try:
            # 测试MetaStore连接
            with self.metastore_connector as connector:
                connector.test_connection()

            # 测试HDFS连接
            if not self.webhdfs_client.test_connection():
                logger.error("HDFS connection test failed")
                return False

            # 测试Hive连接
            try:
                with self._create_hive_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            except Exception as e:
                logger.error(f"Hive connection test failed: {e}")
                return False

            logger.info("All connections tested successfully")
            return True

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def _create_hive_connection(self, database_name: str = None):
        """创建Hive连接"""
        try:
            connect_params = {
                "host": self.cluster.hive_host,
                "port": self.cluster.hive_port,
                "database": database_name or "default",
            }

            # 如果有认证信息，添加认证参数
            if self.cluster.auth_type == "LDAP" and self.cluster.hive_username:
                connect_params.update(
                    {
                        "username": self.cluster.hive_username,
                        "password": self.hive_password,
                        "auth": "LDAP",
                    }
                )

            return hive.Connection(**connect_params)

        except Exception as e:
            logger.error(f"Failed to create Hive connection: {e}")
            raise

    def get_hive_connection(self, database_name: str = None):
        """获取Hive连接（可复用）"""
        if self._hive_connection is None:
            self._hive_connection = self._create_hive_connection(database_name)
        return self._hive_connection

    def cleanup_connections(self):
        """清理所有连接"""
        try:
            if self._hive_connection:
                self._hive_connection.close()
                self._hive_connection = None

            if hasattr(self.webhdfs_client, "close"):
                self.webhdfs_client.close()

            logger.debug("Connections cleaned up successfully")

        except Exception as e:
            logger.error(f"Error cleaning up connections: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_connections()
