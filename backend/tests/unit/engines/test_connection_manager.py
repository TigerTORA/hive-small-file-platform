"""
测试重构后的连接管理器模块
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.engines.connection_manager import HiveConnectionManager
from app.models.cluster import Cluster
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.utils.webhdfs_client import WebHDFSClient


class TestHiveConnectionManager:
    """测试 HiveConnectionManager 类"""

    @pytest.fixture
    def mock_cluster(self):
        """创建模拟集群配置"""
        cluster = Mock(spec=Cluster)
        cluster.id = 1
        cluster.name = "test-cluster"
        cluster.hive_host = "test-hive-host"
        cluster.hive_port = 10000
        cluster.hive_metastore_url = "postgresql://user:pass@host:5432/hive"
        cluster.hdfs_namenode_url = "hdfs://test-namenode:8020"
        cluster.hdfs_user = "hdfs"
        cluster.yarn_resource_manager_url = "http://rm:8088"
        return cluster

    @pytest.fixture
    def connection_manager(self, mock_cluster):
        """创建连接管理器实例"""
        with patch("app.engines.connection_manager.MySQLHiveMetastoreConnector"), patch(
            "app.engines.connection_manager.WebHDFSClient"
        ):
            return HiveConnectionManager(mock_cluster)

    def test_init_creates_clients(self, mock_cluster):
        """测试初始化时创建客户端"""
        with patch(
            "app.engines.connection_manager.MySQLHiveMetastoreConnector"
        ) as mock_metastore, patch(
            "app.engines.connection_manager.WebHDFSClient"
        ) as mock_webhdfs:

            manager = HiveConnectionManager(mock_cluster)

            # 验证创建了 MetaStore 连接器
            mock_metastore.assert_called_once_with(mock_cluster.hive_metastore_url)
            # 验证创建了 WebHDFS 客户端
            mock_webhdfs.assert_called_once_with(
                namenode_url=mock_cluster.hdfs_namenode_url, user=mock_cluster.hdfs_user
            )

            assert manager.cluster == mock_cluster
            assert hasattr(manager, "metastore_connector")
            assert hasattr(manager, "webhdfs_client")

    def test_get_metastore_connection(self, connection_manager):
        """测试获取 MetaStore 连接"""
        mock_conn = Mock()
        connection_manager.metastore_connector.get_connection.return_value = mock_conn

        result = connection_manager.get_metastore_connection()

        assert result == mock_conn
        connection_manager.metastore_connector.get_connection.assert_called_once()

    def test_get_webhdfs_client(self, connection_manager):
        """测试获取 WebHDFS 客户端"""
        result = connection_manager.get_webhdfs_client()

        assert result == connection_manager.webhdfs_client

    def test_test_metastore_connection_success(self, connection_manager):
        """测试 MetaStore 连接测试成功"""
        connection_manager.metastore_connector.test_connection.return_value = True

        result = connection_manager.test_metastore_connection()

        assert result is True
        connection_manager.metastore_connector.test_connection.assert_called_once()

    def test_test_metastore_connection_failure(self, connection_manager):
        """测试 MetaStore 连接测试失败"""
        connection_manager.metastore_connector.test_connection.side_effect = Exception(
            "Connection failed"
        )

        result = connection_manager.test_metastore_connection()

        assert result is False

    def test_test_hdfs_connection_success(self, connection_manager):
        """测试 HDFS 连接测试成功"""
        connection_manager.webhdfs_client.list_directory.return_value = []

        result = connection_manager.test_hdfs_connection()

        assert result is True
        connection_manager.webhdfs_client.list_directory.assert_called_once_with("/")

    def test_test_hdfs_connection_failure(self, connection_manager):
        """测试 HDFS 连接测试失败"""
        connection_manager.webhdfs_client.list_directory.side_effect = Exception(
            "HDFS connection failed"
        )

        result = connection_manager.test_hdfs_connection()

        assert result is False

    def test_cleanup_connections(self, connection_manager):
        """测试清理连接"""
        connection_manager.metastore_connector.close_connection = Mock()

        connection_manager.cleanup_connections()

        connection_manager.metastore_connector.close_connection.assert_called_once()

    def test_get_all_connections(self, connection_manager):
        """测试获取所有连接信息"""
        mock_metastore_conn = Mock()
        connection_manager.metastore_connector.get_connection.return_value = (
            mock_metastore_conn
        )

        connections = connection_manager.get_all_connections()

        assert "metastore" in connections
        assert "webhdfs" in connections
        assert connections["metastore"] == mock_metastore_conn
        assert connections["webhdfs"] == connection_manager.webhdfs_client

    def test_validate_all_connections_success(self, connection_manager):
        """测试验证所有连接成功"""
        connection_manager.test_metastore_connection = Mock(return_value=True)
        connection_manager.test_hdfs_connection = Mock(return_value=True)

        result = connection_manager.validate_all_connections()

        assert result["metastore"] is True
        assert result["hdfs"] is True
        assert result["all_connected"] is True

    def test_validate_all_connections_partial_failure(self, connection_manager):
        """测试验证连接部分失败"""
        connection_manager.test_metastore_connection = Mock(return_value=True)
        connection_manager.test_hdfs_connection = Mock(return_value=False)

        result = connection_manager.validate_all_connections()

        assert result["metastore"] is True
        assert result["hdfs"] is False
        assert result["all_connected"] is False

    @patch("app.engines.connection_manager.logger")
    def test_connection_error_logging(self, mock_logger, connection_manager):
        """测试连接错误日志记录"""
        connection_manager.metastore_connector.test_connection.side_effect = Exception(
            "Test error"
        )

        result = connection_manager.test_metastore_connection()

        assert result is False
        mock_logger.error.assert_called()

    def test_context_manager(self, mock_cluster):
        """测试上下文管理器功能"""
        with patch("app.engines.connection_manager.MySQLHiveMetastoreConnector"), patch(
            "app.engines.connection_manager.WebHDFSClient"
        ):

            manager = HiveConnectionManager(mock_cluster)
            manager.cleanup_connections = Mock()

            with manager as ctx_manager:
                assert ctx_manager == manager

            manager.cleanup_connections.assert_called_once()
