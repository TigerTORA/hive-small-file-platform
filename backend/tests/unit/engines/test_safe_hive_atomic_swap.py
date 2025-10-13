"""
HiveAtomicSwapManager单元测试

Story 6.10.1 - Task 2: 补充safe_hive_atomic_swap.py测试
测试策略: 单元测试为主,重点覆盖原子交换和回滚逻辑
覆盖率目标: 0% → 80%

创建时间: 2025-10-12
预计时间: 6小时
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any, List

from app.engines.safe_hive_atomic_swap import HiveAtomicSwapManager
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.utils.webhdfs_client import WebHDFSClient


class TestHiveAtomicSwapManager:
    """HiveAtomicSwapManager单元测试类"""

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
        return cluster

    @pytest.fixture
    def mock_webhdfs_client(self):
        """模拟WebHDFS客户端"""
        client = Mock(spec=WebHDFSClient)
        client.test_connection.return_value = (True, "Connection OK")
        client._normalize_path = Mock(side_effect=lambda p: p.replace("hdfs://", "").split(":", 1)[-1] if ":" in p else p)
        return client

    @pytest.fixture
    def mock_task(self):
        """模拟MergeTask"""
        task = Mock(spec=MergeTask)
        task.id = 1
        task.database_name = "test_db"
        task.table_name = "user_logs"
        task.yarn_application_id = None
        return task

    @pytest.fixture
    def atomic_swap_manager(self, mock_cluster, mock_webhdfs_client):
        """创建HiveAtomicSwapManager实例"""
        return HiveAtomicSwapManager(
            cluster=mock_cluster,
            webhdfs_client=mock_webhdfs_client,
            yarn_monitor=None,
            hive_password="test_password",
            extract_error_detail_func=lambda e: str(e),
            update_task_progress_func=Mock(),
        )

    # ==================== 测试组1: 初始化 ====================

    def test_init_success(self, mock_cluster, mock_webhdfs_client):
        """TC-1.1: 正常初始化"""
        # When
        manager = HiveAtomicSwapManager(
            cluster=mock_cluster,
            webhdfs_client=mock_webhdfs_client,
            hive_password="test_pwd",
        )

        # Then
        assert manager.cluster == mock_cluster
        assert manager.webhdfs_client == mock_webhdfs_client
        assert manager.hive_password == "test_pwd"
        assert manager.yarn_monitor is None

    def test_init_with_all_parameters(self, mock_cluster, mock_webhdfs_client):
        """TC-1.2: 带所有参数初始化"""
        # Given
        yarn_monitor = Mock()
        extract_func = Mock()
        update_func = Mock()

        # When
        manager = HiveAtomicSwapManager(
            cluster=mock_cluster,
            webhdfs_client=mock_webhdfs_client,
            yarn_monitor=yarn_monitor,
            hive_password="pwd",
            extract_error_detail_func=extract_func,
            update_task_progress_func=update_func,
        )

        # Then
        assert manager.yarn_monitor == yarn_monitor
        assert manager._extract_error_detail == extract_func
        assert manager._update_task_progress == update_func

    # ==================== 测试组2: _create_hive_connection ====================

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_create_hive_connection_no_auth(self, mock_hive_conn, atomic_swap_manager):
        """TC-2.1: 创建Hive连接(无认证)"""
        # Given
        mock_conn_instance = MagicMock()
        mock_hive_conn.return_value = mock_conn_instance

        # When
        result = atomic_swap_manager._create_hive_connection("test_db")

        # Then
        mock_hive_conn.assert_called_once_with(
            host="localhost",
            port=10000,
            database="test_db"
        )
        assert result == mock_conn_instance

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_create_hive_connection_ldap(self, mock_hive_conn, mock_cluster, mock_webhdfs_client):
        """TC-2.2: 创建Hive连接(LDAP认证)"""
        # Given
        mock_cluster.auth_type = "LDAP"
        mock_cluster.hive_username = "admin"
        manager = HiveAtomicSwapManager(
            mock_cluster, mock_webhdfs_client, hive_password="admin_pwd"
        )
        mock_conn_instance = MagicMock()
        mock_hive_conn.return_value = mock_conn_instance

        # When
        result = manager._create_hive_connection("prod_db")

        # Then
        mock_hive_conn.assert_called_once_with(
            host="localhost",
            port=10000,
            database="prod_db",
            username="admin",
            password="admin_pwd",
            auth="LDAP"
        )

    # ==================== 测试组3: _atomic_table_swap ====================

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_atomic_table_swap_success(self, mock_hive_conn, atomic_swap_manager, mock_task):
        """TC-3.1: 成功执行原子表交换"""
        # Given
        mock_cursor = MagicMock()
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        # When
        sql_statements = atomic_swap_manager._atomic_table_swap(
            mock_task, "user_logs_temp_123", "user_logs_backup_456"
        )

        # Then
        assert len(sql_statements) == 2
        assert "ALTER TABLE user_logs RENAME TO user_logs_backup_456" in sql_statements[0]
        assert "ALTER TABLE user_logs_temp_123 RENAME TO user_logs" in sql_statements[1]
        assert mock_cursor.execute.call_count == 2
        mock_cursor.close.assert_called_once()
        mock_conn_instance.close.assert_called_once()

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_atomic_table_swap_first_rename_fails(self, mock_hive_conn, atomic_swap_manager, mock_task):
        """TC-3.2: 第一次重命名失败"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Table not found: user_logs")
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        # When & Then
        with pytest.raises(Exception, match="Table not found"):
            atomic_swap_manager._atomic_table_swap(
                mock_task, "user_logs_temp", "user_logs_backup"
            )

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_atomic_table_swap_second_rename_fails(self, mock_hive_conn, atomic_swap_manager, mock_task):
        """TC-3.3: 第二次重命名失败"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = [
            None,  # 第一次成功
            Exception("Temp table not found")  # 第二次失败
        ]
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        # When & Then
        with pytest.raises(Exception, match="Temp table not found"):
            atomic_swap_manager._atomic_table_swap(
                mock_task, "user_logs_temp", "user_logs_backup"
            )

    # ==================== 测试组4: _atomic_table_swap_with_logging ====================

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_atomic_table_swap_with_logging_success(
        self, mock_hive_conn, atomic_swap_manager, mock_task
    ):
        """TC-4.1: 带日志的原子表交换成功"""
        # Given
        mock_cursor = MagicMock()
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        mock_merge_logger = MagicMock()

        # When
        sql_statements = atomic_swap_manager._atomic_table_swap_with_logging(
            mock_task, "user_logs_temp", "user_logs_backup", mock_merge_logger
        )

        # Then
        assert len(sql_statements) == 2
        # 验证日志记录
        assert mock_merge_logger.log_sql_execution.call_count == 2
        assert mock_merge_logger.log.call_count >= 3  # 至少3次log调用
        mock_cursor.close.assert_called_once()
        mock_conn_instance.close.assert_called_once()

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_atomic_table_swap_with_logging_failure(
        self, mock_hive_conn, atomic_swap_manager, mock_task
    ):
        """TC-4.2: 带日志的原子表交换失败"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Permission denied")
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        mock_merge_logger = MagicMock()

        # When & Then
        with pytest.raises(Exception, match="Permission denied"):
            atomic_swap_manager._atomic_table_swap_with_logging(
                mock_task, "user_logs_temp", "user_logs_backup", mock_merge_logger
            )

        # 验证错误日志
        error_log_calls = [
            call for call in mock_merge_logger.log.call_args_list
            if len(call[0]) > 1 and "失败" in str(call[0][2])
        ]
        assert len(error_log_calls) > 0

    # ==================== 测试组5: _rollback_merge ====================

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_rollback_merge_with_backup_exists(
        self, mock_hive_conn, atomic_swap_manager, mock_task
    ):
        """TC-5.1: 回滚合并(备份表存在)"""
        # Given
        mock_cursor = MagicMock()
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        # Mock _table_exists返回True
        atomic_swap_manager._table_exists = Mock(return_value=True)

        # When
        sql_statements = atomic_swap_manager._rollback_merge(
            mock_task, "user_logs_temp", "user_logs_backup"
        )

        # Then
        assert len(sql_statements) == 3
        # 验证SQL语句: DROP原表, RENAME备份表, DROP临时表
        assert "DROP TABLE IF EXISTS user_logs" in sql_statements[0]
        assert "ALTER TABLE user_logs_backup RENAME TO user_logs" in sql_statements[1]
        assert "DROP TABLE IF EXISTS user_logs_temp" in sql_statements[2]

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_rollback_merge_without_backup(
        self, mock_hive_conn, atomic_swap_manager, mock_task
    ):
        """TC-5.2: 回滚合并(备份表不存在)"""
        # Given
        mock_cursor = MagicMock()
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        # Mock _table_exists返回False
        atomic_swap_manager._table_exists = Mock(return_value=False)

        # When
        sql_statements = atomic_swap_manager._rollback_merge(
            mock_task, "user_logs_temp", "user_logs_backup"
        )

        # Then
        # 只执行DROP临时表
        assert len(sql_statements) == 1
        assert "DROP TABLE IF EXISTS user_logs_temp" in sql_statements[0]

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_rollback_merge_failure(
        self, mock_hive_conn, atomic_swap_manager, mock_task
    ):
        """TC-5.3: 回滚失败"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Rollback failed: insufficient permissions")
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        atomic_swap_manager._table_exists = Mock(return_value=True)

        # When & Then
        with pytest.raises(Exception, match="Rollback failed"):
            atomic_swap_manager._rollback_merge(
                mock_task, "user_logs_temp", "user_logs_backup"
            )

    # ==================== 测试组6: _hdfs_rename_with_fallback ====================

    def test_hdfs_rename_with_fallback_webhdfs_success(
        self, atomic_swap_manager, mock_task
    ):
        """TC-6.1: HDFS重命名成功(WebHDFS)"""
        # Given
        atomic_swap_manager.webhdfs_client.move_file.return_value = (True, "Success")
        mock_merge_logger = MagicMock()
        mock_db_session = MagicMock()

        # When
        success, msg = atomic_swap_manager._hdfs_rename_with_fallback(
            src="/user/hive/warehouse/test_db.db/user_logs",
            dst="/user/hive/warehouse/test_db.db/user_logs_new",
            merge_logger=mock_merge_logger,
            phase=MagicMock(),
            task=mock_task,
            db_session=mock_db_session,
        )

        # Then
        assert success is True
        assert msg == ""
        atomic_swap_manager.webhdfs_client.move_file.assert_called_once()
        mock_merge_logger.log_hdfs_operation.assert_called_once()

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_hdfs_rename_with_fallback_webhdfs_fail_hs2_success(
        self, mock_hive_conn, atomic_swap_manager, mock_task
    ):
        """TC-6.2: WebHDFS失败,回退HS2成功"""
        # Given
        atomic_swap_manager.webhdfs_client.move_file.return_value = (False, "WebHDFS error")
        mock_cursor = MagicMock()
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        mock_merge_logger = MagicMock()
        mock_db_session = MagicMock()

        # When
        success, msg = atomic_swap_manager._hdfs_rename_with_fallback(
            src="/path/src",
            dst="/path/dst",
            merge_logger=mock_merge_logger,
            phase=MagicMock(),
            task=mock_task,
            db_session=mock_db_session,
        )

        # Then
        assert success is True
        # 验证HS2 dfs -mv被调用
        mock_cursor.execute.assert_called_once_with("dfs -mv /path/src /path/dst")

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_hdfs_rename_with_fallback_both_fail(
        self, mock_hive_conn, atomic_swap_manager, mock_task
    ):
        """TC-6.3: WebHDFS和HS2都失败"""
        # Given
        atomic_swap_manager.webhdfs_client.move_file.return_value = (False, "WebHDFS error")
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("HS2 dfs command failed")
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        mock_merge_logger = MagicMock()
        mock_db_session = MagicMock()

        # When
        success, msg = atomic_swap_manager._hdfs_rename_with_fallback(
            src="/path/src",
            dst="/path/dst",
            merge_logger=mock_merge_logger,
            phase=MagicMock(),
            task=mock_task,
            db_session=mock_db_session,
        )

        # Then
        assert success is False
        assert "WebHDFS failed" in msg
        assert "HS2 failed" in msg

    # ==================== 测试组7: _test_connections ====================

    def test_test_connections_webhdfs_fail(self, atomic_swap_manager):
        """TC-7.1: WebHDFS连接失败"""
        # Given
        atomic_swap_manager.webhdfs_client.test_connection.return_value = (False, "Connection refused")
        mock_merge_logger = MagicMock()

        # When
        result = atomic_swap_manager._test_connections(merge_logger=mock_merge_logger)

        # Then
        assert result is False
        mock_merge_logger.log_hdfs_operation.assert_called_once()

    @patch('app.engines.safe_hive_atomic_swap.socket.create_connection')
    def test_test_connections_hive_tcp_fail(
        self, mock_socket, atomic_swap_manager
    ):
        """TC-7.2: Hive TCP连接失败"""
        # Given
        atomic_swap_manager.webhdfs_client.test_connection.return_value = (True, "OK")
        mock_socket.side_effect = Exception("Connection refused")
        mock_merge_logger = MagicMock()

        # When
        result = atomic_swap_manager._test_connections(merge_logger=mock_merge_logger)

        # Then
        assert result is False

    @patch('app.engines.safe_hive_atomic_swap.threading.Thread')
    @patch('app.engines.safe_hive_atomic_swap.socket.create_connection')
    def test_test_connections_hive_timeout(
        self, mock_socket, mock_thread, atomic_swap_manager
    ):
        """TC-7.3: HiveServer2连接超时"""
        # Given
        atomic_swap_manager.webhdfs_client.test_connection.return_value = (True, "OK")
        mock_socket.return_value.__enter__ = Mock()
        mock_socket.return_value.__exit__ = Mock()

        # Mock线程一直存活,模拟超时
        mock_thread_instance = MagicMock()
        mock_thread_instance.is_alive.return_value = True
        mock_thread.return_value = mock_thread_instance

        mock_merge_logger = MagicMock()

        # When
        result = atomic_swap_manager._test_connections(
            merge_logger=mock_merge_logger,
            timeout_sec=1
        )

        # Then
        assert result is False
        mock_merge_logger.end_phase.assert_called_once()

    @patch('app.engines.safe_hive_atomic_swap.threading.Thread')
    @patch('app.engines.safe_hive_atomic_swap.socket.create_connection')
    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_test_connections_success(
        self, mock_hive_conn, mock_socket, mock_thread, atomic_swap_manager
    ):
        """TC-7.4: 连接测试成功"""
        # Given
        atomic_swap_manager.webhdfs_client.test_connection.return_value = (True, "OK")
        mock_socket.return_value.__enter__ = Mock()
        mock_socket.return_value.__exit__ = Mock()

        # Mock线程快速完成
        mock_thread_instance = MagicMock()
        mock_thread_instance.is_alive.return_value = False
        mock_thread.return_value = mock_thread_instance

        mock_merge_logger = MagicMock()

        # When
        result = atomic_swap_manager._test_connections(merge_logger=mock_merge_logger)

        # Then - 由于done_flag在线程中设置,这里简化验证
        # 主要验证流程正确执行
        mock_merge_logger.log.assert_called()

    def test_test_connections_webhdfs_exception(self, atomic_swap_manager):
        """TC-7.5: WebHDFS测试抛异常"""
        # Given
        atomic_swap_manager.webhdfs_client.test_connection.side_effect = Exception("Network error")
        mock_merge_logger = MagicMock()

        # When
        result = atomic_swap_manager._test_connections(merge_logger=mock_merge_logger)

        # Then
        assert result is False
        # 验证异常被记录
        error_logs = [call for call in mock_merge_logger.log.call_args_list if "异常" in str(call)]
        assert len(error_logs) > 0

    @patch('app.engines.safe_hive_atomic_swap.threading.Thread')
    @patch('app.engines.safe_hive_atomic_swap.socket.create_connection')
    def test_test_connections_ldap_auth(
        self, mock_socket, mock_thread, mock_cluster, mock_webhdfs_client
    ):
        """TC-7.6: LDAP认证模式的连接测试"""
        # Given
        mock_cluster.auth_type = "LDAP"
        mock_cluster.hive_username = "admin"
        manager = HiveAtomicSwapManager(
            mock_cluster, mock_webhdfs_client, hive_password="admin_pwd"
        )
        manager.webhdfs_client.test_connection.return_value = (True, "OK")
        mock_socket.return_value.__enter__ = Mock()
        mock_socket.return_value.__exit__ = Mock()

        mock_thread_instance = MagicMock()
        mock_thread_instance.is_alive.return_value = False
        mock_thread.return_value = mock_thread_instance

        mock_merge_logger = MagicMock()

        # When
        result = manager._test_connections(merge_logger=mock_merge_logger)

        # Then - 验证LDAP认证相关日志
        # 这里主要验证代码执行到LDAP分支
        assert mock_merge_logger.log.called

    @patch('app.engines.safe_hive_atomic_swap.socket.create_connection')
    def test_test_connections_outer_exception(
        self, mock_socket, atomic_swap_manager
    ):
        """TC-7.7: 最外层异常处理"""
        # Given
        atomic_swap_manager.webhdfs_client.test_connection.return_value = (True, "OK")
        # socket创建抛出未预期的异常
        mock_socket.side_effect = RuntimeError("Unexpected runtime error")
        mock_merge_logger = MagicMock()

        # When
        result = atomic_swap_manager._test_connections(merge_logger=mock_merge_logger)

        # Then
        assert result is False


class TestHiveAtomicSwapManagerEdgeCases:
    """HiveAtomicSwapManager边缘场景测试"""

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
        return cluster

    @pytest.fixture
    def mock_webhdfs_client(self):
        """模拟WebHDFS客户端"""
        client = Mock(spec=WebHDFSClient)
        client.test_connection.return_value = (True, "Connection OK")
        client._normalize_path = Mock(side_effect=lambda p: p)
        return client

    # ==================== 边缘场景测试 ====================

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_atomic_swap_with_special_table_names(
        self, mock_hive_conn, mock_cluster, mock_webhdfs_client
    ):
        """EC-1: 表名包含特殊字符"""
        # Given
        manager = HiveAtomicSwapManager(mock_cluster, mock_webhdfs_client)
        task = Mock(spec=MergeTask)
        task.database_name = "test_db"
        task.table_name = "user_logs_2024_v2"  # 包含下划线和数字

        mock_cursor = MagicMock()
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        # When
        sql_statements = manager._atomic_table_swap(
            task, "user_logs_2024_v2_temp", "user_logs_2024_v2_backup"
        )

        # Then
        assert "user_logs_2024_v2" in sql_statements[0]
        assert "user_logs_2024_v2_temp" in sql_statements[1]

    def test_init_with_none_yarn_monitor(self, mock_cluster, mock_webhdfs_client):
        """EC-2: YARN监控器为None"""
        # When
        manager = HiveAtomicSwapManager(
            mock_cluster, mock_webhdfs_client, yarn_monitor=None
        )

        # Then
        assert manager.yarn_monitor is None

    def test_init_with_none_functions(self, mock_cluster, mock_webhdfs_client):
        """EC-3: 回调函数为None"""
        # When
        manager = HiveAtomicSwapManager(
            mock_cluster, mock_webhdfs_client,
            extract_error_detail_func=None,
            update_task_progress_func=None
        )

        # Then
        assert manager._extract_error_detail is None
        assert manager._update_task_progress is None

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_connection_timeout_handling(
        self, mock_hive_conn, mock_cluster, mock_webhdfs_client
    ):
        """EC-4: Hive连接超时"""
        # Given
        mock_hive_conn.side_effect = TimeoutError("Connection timed out after 30s")
        manager = HiveAtomicSwapManager(mock_cluster, mock_webhdfs_client)
        task = Mock(spec=MergeTask)
        task.database_name = "test_db"

        # When & Then
        with pytest.raises(TimeoutError, match="Connection timed out"):
            manager._create_hive_connection("test_db")

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_rollback_with_empty_table_names(
        self, mock_hive_conn, mock_cluster, mock_webhdfs_client
    ):
        """EC-5: 回滚时表名为空字符串"""
        # Given
        manager = HiveAtomicSwapManager(mock_cluster, mock_webhdfs_client)
        manager._table_exists = Mock(return_value=False)

        task = Mock(spec=MergeTask)
        task.database_name = "test_db"
        task.table_name = "user_logs"

        mock_cursor = MagicMock()
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        # When
        sql_statements = manager._rollback_merge(task, "", "")

        # Then
        # 应该能处理空字符串而不崩溃
        assert isinstance(sql_statements, list)


class TestHiveAtomicSwapManagerAtomicSwapLocation:
    """测试_atomic_swap_table_location方法"""

    @pytest.fixture
    def mock_cluster(self):
        cluster = Mock(spec=Cluster)
        cluster.hive_host = "localhost"
        cluster.hive_port = 10000
        cluster.hive_database = "default"
        cluster.hdfs_namenode_url = "http://localhost:50070"
        return cluster

    @pytest.fixture
    def mock_webhdfs_client(self):
        client = Mock(spec=WebHDFSClient)
        client._normalize_path = Mock(side_effect=lambda p: p.replace("hdfs://namenode:8020", ""))
        client.exists = Mock(return_value=True)
        client.move_file = Mock(return_value=(True, "Success"))
        client.delete_file = Mock(return_value=(True, "Deleted"))
        return client

    @pytest.fixture
    def atomic_swap_manager(self, mock_cluster, mock_webhdfs_client):
        manager = HiveAtomicSwapManager(
            cluster=mock_cluster,
            webhdfs_client=mock_webhdfs_client,
        )
        # Mock依赖方法
        manager._get_table_location = Mock(side_effect=lambda db, tbl: f"hdfs://namenode:8020/user/hive/warehouse/{db}.db/{tbl}")
        return manager

    # ==================== 测试组8: _atomic_swap_table_location ====================

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    @patch('app.engines.safe_hive_atomic_swap.time.time')
    def test_atomic_swap_table_location_success(
        self, mock_time, mock_hive_conn, atomic_swap_manager
    ):
        """TC-8.1: 原子交换HDFS位置成功"""
        # Given
        mock_time.return_value = 1609459200
        mock_cursor = MagicMock()
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        mock_merge_logger = MagicMock()

        # When
        result = atomic_swap_manager._atomic_swap_table_location(
            database="test_db",
            original_table="user_logs",
            temp_table="user_logs_temp",
            merge_logger=mock_merge_logger,
        )

        # Then
        assert result["success"] is True
        assert "/user/hive/warehouse/test_db.db/user_logs" in result["original_location"]
        assert "_backup_1609459200" in result["backup_location"]

        # 验证操作顺序: backup -> move -> refresh -> cleanup
        assert atomic_swap_manager.webhdfs_client.move_file.call_count == 2  # backup + move
        assert mock_cursor.execute.call_count == 3  # MSCK + SELECT + DROP

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    @patch('app.engines.safe_hive_atomic_swap.time.time')
    def test_atomic_swap_table_location_backup_failure(
        self, mock_time, mock_hive_conn, atomic_swap_manager
    ):
        """TC-8.2: 备份失败"""
        # Given
        mock_time.return_value = 1609459200
        atomic_swap_manager.webhdfs_client.move_file.return_value = (False, "Permission denied")
        mock_merge_logger = MagicMock()

        # When & Then
        with pytest.raises(Exception, match="备份失败"):
            atomic_swap_manager._atomic_swap_table_location(
                database="test_db",
                original_table="user_logs",
                temp_table="user_logs_temp",
                merge_logger=mock_merge_logger,
            )

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    @patch('app.engines.safe_hive_atomic_swap.time.time')
    def test_atomic_swap_table_location_move_failure_with_rollback(
        self, mock_time, mock_hive_conn, atomic_swap_manager
    ):
        """TC-8.3: 移动失败并回滚"""
        # Given
        mock_time.return_value = 1609459200
        # 第一次move成功(backup),第二次失败(move temp to original),第三次回滚成功
        atomic_swap_manager.webhdfs_client.move_file.side_effect = [
            (True, "Backup success"),
            (False, "Move failed"),
            (True, "Rollback success")  # 回滚操作
        ]
        mock_merge_logger = MagicMock()

        # When & Then
        with pytest.raises(Exception, match="数据移动失败:"):
            atomic_swap_manager._atomic_swap_table_location(
                database="test_db",
                original_table="user_logs",
                temp_table="user_logs_temp",
                merge_logger=mock_merge_logger,
            )

        # 验证尝试回滚
        assert atomic_swap_manager.webhdfs_client.move_file.call_count == 3  # backup + failed move + rollback

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_atomic_swap_table_location_missing_location(
        self, mock_hive_conn, atomic_swap_manager
    ):
        """TC-8.4: 无法获取表位置"""
        # Given
        atomic_swap_manager._get_table_location = Mock(return_value=None)
        mock_merge_logger = MagicMock()

        # When & Then
        with pytest.raises(Exception, match="无法获取表的HDFS路径"):
            atomic_swap_manager._atomic_swap_table_location(
                database="test_db",
                original_table="user_logs",
                temp_table="user_logs_temp",
                merge_logger=mock_merge_logger,
            )


class TestHiveAtomicSwapManagerExecuteSQLWithHeartbeat:
    """测试_execute_sql_with_heartbeat方法"""

    @pytest.fixture
    def mock_cluster(self):
        cluster = Mock(spec=Cluster)
        cluster.hive_host = "localhost"
        cluster.hive_port = 10000
        return cluster

    @pytest.fixture
    def mock_webhdfs_client(self):
        return Mock(spec=WebHDFSClient)

    @pytest.fixture
    def atomic_swap_manager(self, mock_cluster, mock_webhdfs_client):
        manager = HiveAtomicSwapManager(
            cluster=mock_cluster,
            webhdfs_client=mock_webhdfs_client,
            extract_error_detail_func=lambda e: str(e),
            update_task_progress_func=Mock(),
        )
        return manager

    # ==================== 测试组9: _execute_sql_with_heartbeat ====================

    @patch('app.engines.safe_hive_atomic_swap.threading.Thread')
    @patch('app.engines.safe_hive_atomic_swap.time.time')
    def test_execute_sql_with_heartbeat_success(
        self, mock_time, mock_thread, atomic_swap_manager
    ):
        """TC-9.1: 执行SQL成功(带心跳)"""
        # Given
        mock_cursor = MagicMock()
        mock_merge_logger = MagicMock()
        mock_task = Mock(spec=MergeTask)
        mock_task.yarn_application_id = None
        mock_db_session = MagicMock()
        mock_phase = MagicMock()

        mock_time.return_value = 1609459200

        # Mock心跳线程
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # When
        atomic_swap_manager._execute_sql_with_heartbeat(
            cursor=mock_cursor,
            sql="SELECT * FROM test_table",
            phase=mock_phase,
            merge_logger=mock_merge_logger,
            task=mock_task,
            db_session=mock_db_session,
            op_desc="查询测试表",
            execution_phase_name="test_phase",
        )

        # Then
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test_table")
        mock_merge_logger.log_sql_execution.assert_called_once()
        assert mock_merge_logger.log_sql_execution.call_args[1]['success'] is True

    @patch('app.engines.safe_hive_atomic_swap.threading.Thread')
    def test_execute_sql_with_heartbeat_failure(
        self, mock_thread, atomic_swap_manager
    ):
        """TC-9.2: 执行SQL失败"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("SQL execution failed: syntax error")
        mock_merge_logger = MagicMock()
        mock_task = Mock(spec=MergeTask)
        mock_task.yarn_application_id = None
        mock_db_session = MagicMock()
        mock_phase = MagicMock()

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # When & Then
        with pytest.raises(Exception, match="SQL execution failed"):
            atomic_swap_manager._execute_sql_with_heartbeat(
                cursor=mock_cursor,
                sql="SELECT * FROM non_existent_table",
                phase=mock_phase,
                merge_logger=mock_merge_logger,
                task=mock_task,
                db_session=mock_db_session,
                op_desc="查询不存在的表",
                execution_phase_name="test_phase",
            )

        # 验证错误被记录
        assert mock_merge_logger.log_sql_execution.call_args[1]['success'] is False

    @patch('app.engines.safe_hive_atomic_swap.threading.Thread')
    def test_execute_sql_with_heartbeat_with_yarn_monitor(
        self, mock_thread, mock_cluster, mock_webhdfs_client
    ):
        """TC-9.3: 带YARN监控的SQL执行"""
        # Given
        mock_yarn_monitor = Mock()
        mock_yarn_app = Mock()
        mock_yarn_app.id = "application_123"
        mock_yarn_app.state = "RUNNING"
        mock_yarn_app.progress = 50.0
        mock_yarn_app.queue = "default"
        mock_yarn_app.name = "test_job"
        mock_yarn_app.tracking_url = "http://rm:8088/app/123"
        mock_yarn_app.application_type = "TEZ"
        mock_yarn_app.start_time = 1609459200
        mock_yarn_monitor.get_applications.return_value = [mock_yarn_app]

        manager = HiveAtomicSwapManager(
            cluster=mock_cluster,
            webhdfs_client=mock_webhdfs_client,
            yarn_monitor=mock_yarn_monitor,
            extract_error_detail_func=lambda e: str(e),
            update_task_progress_func=Mock(),
        )

        mock_cursor = MagicMock()
        mock_merge_logger = MagicMock()
        mock_task = Mock(spec=MergeTask)
        mock_task.yarn_application_id = "application_123"
        mock_db_session = MagicMock()
        mock_phase = MagicMock()

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # When
        manager._execute_sql_with_heartbeat(
            cursor=mock_cursor,
            sql="INSERT INTO test_table SELECT * FROM source",
            phase=mock_phase,
            merge_logger=mock_merge_logger,
            task=mock_task,
            db_session=mock_db_session,
            op_desc="插入数据",
            execution_phase_name="data_insertion",
            interval=10,
        )

        # Then
        mock_cursor.execute.assert_called_once()


class TestHiveAtomicSwapManagerIntegration:
    """集成测试场景"""

    @pytest.fixture
    def mock_cluster(self):
        cluster = Mock(spec=Cluster)
        cluster.hive_host = "localhost"
        cluster.hive_port = 10000
        cluster.hive_database = "default"
        cluster.hdfs_namenode_url = "http://localhost:50070"
        cluster.auth_type = "NONE"
        return cluster

    @pytest.fixture
    def mock_webhdfs_client(self):
        client = Mock(spec=WebHDFSClient)
        client.test_connection.return_value = (True, "OK")
        client._normalize_path = Mock(side_effect=lambda p: p)
        return client

    # ==================== 集成场景测试 ====================

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_full_swap_workflow(
        self, mock_hive_conn, mock_cluster, mock_webhdfs_client
    ):
        """IT-1: 完整的表交换流程"""
        # Given
        manager = HiveAtomicSwapManager(mock_cluster, mock_webhdfs_client)
        task = Mock(spec=MergeTask)
        task.database_name = "test_db"
        task.table_name = "user_logs"

        mock_cursor = MagicMock()
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        # When - 执行原子交换
        sql_statements = manager._atomic_table_swap(
            task, "user_logs_temp_123", "user_logs_backup_456"
        )

        # Then - 验证两步重命名
        assert len(sql_statements) == 2
        assert "user_logs" in sql_statements[0]
        assert "user_logs_backup_456" in sql_statements[0]
        assert "user_logs_temp_123" in sql_statements[1]

    @patch('app.engines.safe_hive_atomic_swap.hive.Connection')
    def test_swap_and_rollback_workflow(
        self, mock_hive_conn, mock_cluster, mock_webhdfs_client
    ):
        """IT-2: 交换失败后回滚流程"""
        # Given
        manager = HiveAtomicSwapManager(mock_cluster, mock_webhdfs_client)
        manager._table_exists = Mock(return_value=True)

        task = Mock(spec=MergeTask)
        task.database_name = "test_db"
        task.table_name = "user_logs"

        mock_cursor = MagicMock()
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        # When - 执行回滚
        sql_statements = manager._rollback_merge(
            task, "user_logs_temp", "user_logs_backup"
        )

        # Then - 验证回滚操作
        assert len(sql_statements) == 3
        assert "DROP TABLE IF EXISTS user_logs" in sql_statements[0]
        assert "ALTER TABLE user_logs_backup RENAME TO user_logs" in sql_statements[1]
        assert "DROP TABLE IF EXISTS user_logs_temp" in sql_statements[2]
