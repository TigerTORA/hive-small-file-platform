"""
HiveFileCounter单元测试

Story 6.10.1 - Task 3: 补充safe_hive_file_counter.py测试
测试策略: 单元测试为主,重点覆盖文件统计和HDFS操作逻辑
覆盖率目标: 0% → 80%

创建时间: 2025-10-13
预计时间: 4小时
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch, call
from typing import Optional

from app.engines.safe_hive_file_counter import HiveFileCounter
from app.models.cluster import Cluster
from app.utils.webhdfs_client import WebHDFSClient


class TestHiveFileCounter:
    """HiveFileCounter单元测试类"""

    # ==================== Fixtures ====================

    @pytest.fixture
    def mock_cluster(self):
        """模拟Cluster配置"""
        cluster = Mock(spec=Cluster)
        cluster.hive_host = "localhost"
        cluster.hive_port = 10000
        cluster.hive_database = "default"
        cluster.hdfs_namenode_url = "http://localhost:50070"
        cluster.auth_type = "NONE"
        cluster.hive_username = None
        cluster.small_file_threshold = 134217728  # 128MB
        return cluster

    @pytest.fixture
    def mock_webhdfs_client(self):
        """模拟WebHDFS客户端"""
        client = Mock(spec=WebHDFSClient)
        client.get_table_hdfs_stats = Mock(return_value={
            "success": True,
            "total_files": 100,
            "small_files_count": 50,
            "total_size": 1024 * 1024 * 1024
        })
        client.list_directory = Mock(return_value=[])
        return client

    @pytest.fixture
    def file_counter(self, mock_cluster, mock_webhdfs_client):
        """创建HiveFileCounter实例"""
        return HiveFileCounter(
            cluster=mock_cluster,
            webhdfs_client=mock_webhdfs_client,
            hive_password="test_password",
        )

    # ==================== 测试组1: 初始化 ====================

    def test_init_success(self, mock_cluster, mock_webhdfs_client):
        """TC-1.1: 正常初始化"""
        # When
        counter = HiveFileCounter(
            cluster=mock_cluster,
            webhdfs_client=mock_webhdfs_client,
            hive_password="test_pwd",
        )

        # Then
        assert counter.cluster == mock_cluster
        assert counter.webhdfs_client == mock_webhdfs_client
        assert counter.hive_password == "test_pwd"

    def test_init_without_password(self, mock_cluster, mock_webhdfs_client):
        """TC-1.2: 不带密码初始化"""
        # When
        counter = HiveFileCounter(
            cluster=mock_cluster,
            webhdfs_client=mock_webhdfs_client,
        )

        # Then
        assert counter.hive_password is None

    # ==================== 测试组2: _create_hive_connection ====================

    @patch('app.engines.safe_hive_file_counter.hive.Connection')
    def test_create_hive_connection_no_auth(self, mock_hive_conn, file_counter):
        """TC-2.1: 创建Hive连接(无认证)"""
        # Given
        mock_conn_instance = MagicMock()
        mock_hive_conn.return_value = mock_conn_instance

        # When
        result = file_counter._create_hive_connection("test_db")

        # Then
        mock_hive_conn.assert_called_once_with(
            host="localhost",
            port=10000,
            database="test_db"
        )
        assert result == mock_conn_instance

    @patch('app.engines.safe_hive_file_counter.hive.Connection')
    def test_create_hive_connection_ldap(self, mock_hive_conn, mock_cluster, mock_webhdfs_client):
        """TC-2.2: 创建Hive连接(LDAP认证)"""
        # Given
        mock_cluster.auth_type = "LDAP"
        mock_cluster.hive_username = "admin"
        counter = HiveFileCounter(
            mock_cluster, mock_webhdfs_client, hive_password="admin_pwd"
        )
        mock_conn_instance = MagicMock()
        mock_hive_conn.return_value = mock_conn_instance

        # When
        result = counter._create_hive_connection("prod_db")

        # Then
        mock_hive_conn.assert_called_once_with(
            host="localhost",
            port=10000,
            database="prod_db",
            username="admin",
            password="admin_pwd",
            auth="LDAP"
        )

    # ==================== 测试组3: _get_file_count ====================

    def test_get_file_count_success(self, file_counter):
        """TC-3.1: 成功获取文件数量"""
        # Given
        file_counter._get_table_location = Mock(return_value="hdfs://namenode:8020/user/hive/warehouse/test_db.db/user_logs")
        file_counter.webhdfs_client.get_table_hdfs_stats.return_value = {
            "success": True,
            "total_files": 150,
            "small_files_count": 80
        }

        # When
        result = file_counter._get_file_count("test_db", "user_logs")

        # Then
        assert result == 150
        file_counter._get_table_location.assert_called_once_with("test_db", "user_logs")

    def test_get_file_count_no_location(self, file_counter):
        """TC-3.2: 无法获取表位置"""
        # Given
        file_counter._get_table_location = Mock(return_value=None)

        # When
        result = file_counter._get_file_count("test_db", "user_logs")

        # Then
        assert result is None

    def test_get_file_count_webhdfs_failure(self, file_counter):
        """TC-3.3: WebHDFS统计失败,返回None"""
        # Given
        file_counter._get_table_location = Mock(return_value="hdfs://namenode:8020/user/hive/warehouse/test_db.db/user_logs")
        file_counter.webhdfs_client.get_table_hdfs_stats.return_value = {
            "success": False,
            "error": "HDFS connection failed"
        }

        # When
        result = file_counter._get_file_count("test_db", "user_logs")

        # Then
        assert result is None

    def test_get_file_count_exception(self, file_counter):
        """TC-3.4: 获取文件数量异常,回退到fallback"""
        # Given
        file_counter._get_table_location = Mock(side_effect=Exception("Connection error"))
        file_counter._get_file_count_fallback = Mock(return_value=None)

        # When
        result = file_counter._get_file_count("test_db", "user_logs")

        # Then
        assert result is None
        file_counter._get_file_count_fallback.assert_called_once()

    # ==================== 测试组4: _get_file_count_with_logging ====================

    def test_get_file_count_with_logging_success(self, file_counter):
        """TC-4.1: 带日志的文件数量获取成功"""
        # Given
        file_counter._get_table_location = Mock(return_value="hdfs://namenode:8020/user/hive/warehouse/test_db.db/user_logs")
        file_counter.webhdfs_client.get_table_hdfs_stats.return_value = {
            "success": True,
            "total_files": 200,
            "small_files_count": 100
        }
        mock_merge_logger = MagicMock()

        # When
        result = file_counter._get_file_count_with_logging(
            "test_db", "user_logs", None, mock_merge_logger
        )

        # Then
        assert result == 200
        assert mock_merge_logger.log_hdfs_operation.call_count == 2  # 一次开始,一次成功

    def test_get_file_count_with_logging_no_location(self, file_counter):
        """TC-4.2: 无法获取表位置"""
        # Given
        file_counter._get_table_location = Mock(return_value=None)
        mock_merge_logger = MagicMock()

        # When
        result = file_counter._get_file_count_with_logging(
            "test_db", "user_logs", None, mock_merge_logger
        )

        # Then
        assert result == 0
        mock_merge_logger.log.assert_called_once()

    def test_get_file_count_with_logging_webhdfs_failure(self, file_counter):
        """TC-4.3: WebHDFS统计失败(严格模式抛异常)"""
        # Given
        file_counter._get_table_location = Mock(return_value="hdfs://namenode:8020/user/hive/warehouse/test_db.db/user_logs")
        file_counter.webhdfs_client.get_table_hdfs_stats.return_value = {
            "success": False,
            "error": "Permission denied"
        }
        mock_merge_logger = MagicMock()

        # When & Then
        with pytest.raises(RuntimeError, match="WebHDFS 统计失败"):
            file_counter._get_file_count_with_logging(
                "test_db", "user_logs", None, mock_merge_logger
            )

    def test_get_file_count_with_logging_exception(self, file_counter):
        """TC-4.4: 获取过程中抛异常"""
        # Given
        file_counter._get_table_location = Mock(side_effect=Exception("Network error"))
        mock_merge_logger = MagicMock()

        # When & Then
        with pytest.raises(Exception, match="Network error"):
            file_counter._get_file_count_with_logging(
                "test_db", "user_logs", None, mock_merge_logger
            )

        # 验证错误日志被记录
        mock_merge_logger.log.assert_called()

    # ==================== 测试组5: _get_file_count_fallback ====================

    def test_get_file_count_fallback(self, file_counter):
        """TC-5.1: Fallback方法返回None"""
        # When
        result = file_counter._get_file_count_fallback("test_db", "user_logs", None)

        # Then
        assert result is None

    # ==================== 测试组6: _get_temp_table_file_count ====================

    def test_get_temp_table_file_count_success(self, file_counter):
        """TC-6.1: 成功获取临时表文件数量"""
        # Given
        file_counter._get_table_location = Mock(return_value="hdfs://namenode:8020/user/hive/warehouse/test_db.db/user_logs_temp")
        file_counter.webhdfs_client.get_table_hdfs_stats.return_value = {
            "success": True,
            "total_files": 10,
            "small_files_count": 0
        }

        # When
        result = file_counter._get_temp_table_file_count("test_db", "user_logs_temp")

        # Then
        assert result == 10

    def test_get_temp_table_file_count_no_location(self, file_counter):
        """TC-6.2: 无法获取临时表位置"""
        # Given
        file_counter._get_table_location = Mock(return_value=None)

        # When & Then
        with pytest.raises(RuntimeError, match="无法获取临时表HDFS位置"):
            file_counter._get_temp_table_file_count("test_db", "user_logs_temp")

    def test_get_temp_table_file_count_webhdfs_failure(self, file_counter):
        """TC-6.3: WebHDFS统计失败"""
        # Given
        file_counter._get_table_location = Mock(return_value="hdfs://namenode:8020/user/hive/warehouse/test_db.db/user_logs_temp")
        file_counter.webhdfs_client.get_table_hdfs_stats.return_value = {
            "success": False,
            "error": "HDFS timeout"
        }

        # When & Then
        with pytest.raises(RuntimeError, match="临时表文件统计失败"):
            file_counter._get_temp_table_file_count("test_db", "user_logs_temp")

    def test_get_temp_table_file_count_exception(self, file_counter):
        """TC-6.4: 获取过程中抛异常"""
        # Given
        file_counter._get_table_location = Mock(side_effect=Exception("Connection timeout"))

        # When & Then
        with pytest.raises(Exception, match="Connection timeout"):
            file_counter._get_temp_table_file_count("test_db", "user_logs_temp")

    # ==================== 测试组7: _count_partition_files ====================

    def test_count_partition_files_success(self, file_counter):
        """TC-7.1: 成功统计分区文件数"""
        # Given
        mock_file1 = Mock()
        mock_file1.is_directory = False
        mock_file2 = Mock()
        mock_file2.is_directory = False
        mock_dir = Mock()
        mock_dir.is_directory = True
        file_counter.webhdfs_client.list_directory.return_value = [mock_file1, mock_file2, mock_dir]

        # When
        result = file_counter._count_partition_files("/user/hive/warehouse/test_db.db/user_logs/dt=2024-01-01")

        # Then
        assert result == 2  # 只计数文件,不计数目录

    def test_count_partition_files_empty(self, file_counter):
        """TC-7.2: 分区目录为空"""
        # Given
        file_counter.webhdfs_client.list_directory.return_value = []

        # When
        result = file_counter._count_partition_files("/user/hive/warehouse/test_db.db/user_logs/dt=2024-01-01")

        # Then
        assert result == 0

    def test_count_partition_files_exception(self, file_counter):
        """TC-7.3: 统计失败返回0"""
        # Given
        file_counter.webhdfs_client.list_directory.side_effect = Exception("Permission denied")

        # When
        result = file_counter._count_partition_files("/user/hive/warehouse/test_db.db/user_logs/dt=2024-01-01")

        # Then
        assert result == 0

    # ==================== 测试组8: _wait_for_partition_data ====================

    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_partition_data_success(self, mock_time, mock_sleep, file_counter):
        """TC-8.1: 成功等待分区数据生成"""
        # Given
        mock_time.side_effect = [0, 5, 10]  # 模拟时间流逝
        file_counter._resolve_partition_path = Mock(return_value="/user/hive/warehouse/test_db.db/user_logs/dt=2024-01-01")
        file_counter._count_partition_files = Mock(return_value=5)

        # When
        file_counter._wait_for_partition_data("test_db", "user_logs", "dt='2024-01-01'", timeout=60)

        # Then - 应该成功返回,不抛异常
        assert file_counter._count_partition_files.call_count == 1

    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_partition_data_timeout(self, mock_time, mock_sleep, file_counter):
        """TC-8.2: 等待分区数据超时"""
        # Given
        # 模拟时间流逝超过timeout
        mock_time.side_effect = [0, 20, 40, 60, 80]
        file_counter._resolve_partition_path = Mock(return_value="/user/hive/warehouse/test_db.db/user_logs/dt=2024-01-01")
        file_counter._count_partition_files = Mock(return_value=0)  # 一直返回0(无文件)

        # When & Then
        with pytest.raises(Exception, match="等待分区数据超时"):
            file_counter._wait_for_partition_data("test_db", "user_logs", "dt='2024-01-01'", timeout=60)

    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_partition_data_resolve_error(self, mock_time, mock_sleep, file_counter):
        """TC-8.3: 解析分区路径失败,继续等待直到超时"""
        # Given
        mock_time.side_effect = [0, 20, 40, 60, 80]
        file_counter._resolve_partition_path = Mock(side_effect=Exception("Path not found"))

        # When & Then
        with pytest.raises(Exception, match="等待分区数据超时"):
            file_counter._wait_for_partition_data("test_db", "user_logs", "dt='2024-01-01'", timeout=60)

    # ==================== 测试组9: _cleanup_temp_partition ====================

    @patch('app.engines.safe_hive_file_counter.hive.Connection')
    def test_cleanup_temp_partition_success(self, mock_hive_conn, file_counter):
        """TC-9.1: 成功清理临时分区"""
        # Given
        mock_cursor = MagicMock()
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance
        mock_merge_logger = MagicMock()

        # When
        file_counter._cleanup_temp_partition(
            "test_db", "user_logs", "dt='2024-01-01_temp'", mock_merge_logger
        )

        # Then
        mock_cursor.execute.assert_called_once()
        assert "DROP IF EXISTS PARTITION" in mock_cursor.execute.call_args[0][0]
        mock_cursor.close.assert_called_once()
        mock_conn_instance.close.assert_called_once()
        # 验证成功日志
        success_logs = [call for call in mock_merge_logger.log.call_args_list if "已清理临时分区" in str(call)]
        assert len(success_logs) == 1

    @patch('app.engines.safe_hive_file_counter.hive.Connection')
    def test_cleanup_temp_partition_failure(self, mock_hive_conn, file_counter):
        """TC-9.2: 清理临时分区失败"""
        # Given
        mock_hive_conn.side_effect = Exception("Hive connection failed")
        mock_merge_logger = MagicMock()

        # When
        file_counter._cleanup_temp_partition(
            "test_db", "user_logs", "dt='2024-01-01_temp'", mock_merge_logger
        )

        # Then - 应该记录WARNING日志,不抛异常
        warning_logs = [call for call in mock_merge_logger.log.call_args_list if "清理临时分区失败" in str(call)]
        assert len(warning_logs) == 1


class TestHiveFileCounterEdgeCases:
    """HiveFileCounter边缘场景测试"""

    @pytest.fixture
    def mock_cluster(self):
        cluster = Mock(spec=Cluster)
        cluster.hive_host = "localhost"
        cluster.hive_port = 10000
        cluster.hive_database = "default"
        cluster.small_file_threshold = 134217728
        return cluster

    @pytest.fixture
    def mock_webhdfs_client(self):
        return Mock(spec=WebHDFSClient)

    # ==================== 边缘场景测试 ====================

    def test_init_with_none_threshold(self, mock_cluster, mock_webhdfs_client):
        """EC-1: 小文件阈值为None"""
        # Given
        mock_cluster.small_file_threshold = None

        # When
        counter = HiveFileCounter(mock_cluster, mock_webhdfs_client)

        # Then
        assert counter.cluster.small_file_threshold is None

    def test_get_file_count_with_partition_filter(self, mock_cluster, mock_webhdfs_client):
        """EC-2: 带分区过滤的文件统计"""
        # Given
        counter = HiveFileCounter(mock_cluster, mock_webhdfs_client)
        counter._get_table_location = Mock(return_value="hdfs://namenode:8020/user/hive/warehouse/test_db.db/user_logs")
        counter.webhdfs_client.get_table_hdfs_stats.return_value = {
            "success": True,
            "total_files": 50
        }

        # When
        result = counter._get_file_count("test_db", "user_logs", partition_filter="dt='2024-01-01'")

        # Then
        assert result == 50

    def test_count_partition_files_only_directories(self, mock_cluster, mock_webhdfs_client):
        """EC-3: 分区目录只包含子目录(无文件)"""
        # Given
        counter = HiveFileCounter(mock_cluster, mock_webhdfs_client)
        mock_dir1 = Mock()
        mock_dir1.is_directory = True
        mock_dir2 = Mock()
        mock_dir2.is_directory = True
        counter.webhdfs_client.list_directory.return_value = [mock_dir1, mock_dir2]

        # When
        result = counter._count_partition_files("/user/hive/warehouse/test_db.db/user_logs/dt=2024-01-01")

        # Then
        assert result == 0
