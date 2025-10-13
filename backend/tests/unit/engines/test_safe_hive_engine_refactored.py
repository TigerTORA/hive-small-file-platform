"""
safe_hive_engine_refactored.py 单元测试
测试SafeHiveMergeEngine主控制器的委托调用逻辑

作者: Dev Agent (James)
日期: 2025-10-12
Story: 6.10.1 Task 5
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from app.engines.safe_hive_engine_refactored import (
    SafeHiveMergeEngine,
    SafeHiveMergeEngineRefactored,
)
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_cluster():
    """创建测试用的Cluster对象"""
    return Cluster(
        id=1,
        name="test_cluster",
        description="Test cluster",
        hive_host="localhost",
        hive_port=10000,
        hive_metastore_url="mysql://user:pass@localhost:3306/hive",
        hdfs_namenode_url="hdfs://localhost:9000",
    )


@pytest.fixture
def mock_task():
    """创建测试用的MergeTask对象"""
    task = MagicMock(spec=MergeTask)
    task.id = 1
    task.cluster_id = 1
    task.task_name = "test_task"
    task.database_name = "test_db"
    task.table_name = "test_table"
    task.partition_filter = None
    task.target_file_size = 134217728  # 128MB
    task.target_storage_format = "PARQUET"
    task.target_compression = "SNAPPY"
    task.use_ec = False
    task.status = "pending"
    return task


@pytest.fixture
def mock_db_session():
    """创建Mock的数据库session"""
    return MagicMock()


@pytest.fixture
def safe_engine(mock_cluster):
    """
    创建SafeHiveMergeEngine实例，Mock所有依赖模块
    """
    with patch(
        "app.engines.safe_hive_engine_refactored.HiveConnectionManager"
    ) as MockConnMgr, patch(
        "app.engines.safe_hive_engine_refactored.MergeTaskValidationService"
    ) as MockValService, patch(
        "app.engines.safe_hive_engine_refactored.MergeTaskExecutor"
    ) as MockExecutor, patch(
        "app.engines.safe_hive_engine_refactored.MergeProgressTracker"
    ) as MockTracker:

        # 设置Mock返回值
        mock_conn_mgr = MagicMock()
        mock_val_service = MagicMock()
        mock_executor = MagicMock()
        mock_tracker = MagicMock()

        MockConnMgr.return_value = mock_conn_mgr
        MockValService.return_value = mock_val_service
        MockExecutor.return_value = mock_executor
        MockTracker.return_value = mock_tracker

        engine = SafeHiveMergeEngine(mock_cluster)

        # 保留Mock引用以便测试验证
        engine._mock_conn_mgr = mock_conn_mgr
        engine._mock_val_service = mock_val_service
        engine._mock_executor = mock_executor
        engine._mock_tracker = mock_tracker

        yield engine


# ============================================================
# 测试类1: TestSafeHiveMergeEngineInit
# 测试SafeHiveMergeEngine初始化逻辑
# ============================================================


class TestSafeHiveMergeEngineInit:
    """测试组1: 初始化"""

    def test_init_success(self, mock_cluster):
        """
        TC-1.1: 成功初始化SafeHiveMergeEngine
        Given: 有效的Cluster对象
        When: 初始化SafeHiveMergeEngine
        Then: 所有依赖模块正确创建
        """
        # Given & When
        with patch(
            "app.engines.safe_hive_engine_refactored.HiveConnectionManager"
        ) as MockConnMgr, patch(
            "app.engines.safe_hive_engine_refactored.MergeTaskValidationService"
        ) as MockValService, patch(
            "app.engines.safe_hive_engine_refactored.MergeTaskExecutor"
        ) as MockExecutor, patch(
            "app.engines.safe_hive_engine_refactored.MergeProgressTracker"
        ) as MockTracker:

            engine = SafeHiveMergeEngine(mock_cluster)

            # Then
            assert engine is not None
            MockConnMgr.assert_called_once_with(mock_cluster)
            MockValService.assert_called_once()
            MockExecutor.assert_called_once()
            MockTracker.assert_called_once()

    def test_backward_compatibility_alias(self, mock_cluster):
        """
        TC-1.2: 验证向后兼容别名SafeHiveMergeEngineRefactored
        Given: 有效的Cluster对象
        When: 使用别名SafeHiveMergeEngineRefactored初始化
        Then: 返回相同的SafeHiveMergeEngine类
        """
        # Given & When
        with patch(
            "app.engines.safe_hive_engine_refactored.HiveConnectionManager"
        ), patch(
            "app.engines.safe_hive_engine_refactored.MergeTaskValidationService"
        ), patch(
            "app.engines.safe_hive_engine_refactored.MergeTaskExecutor"
        ), patch(
            "app.engines.safe_hive_engine_refactored.MergeProgressTracker"
        ):

            # Then
            assert SafeHiveMergeEngineRefactored is SafeHiveMergeEngine


# ============================================================
# 测试类2: TestSafeHiveMergeEngineDelegation
# 测试SafeHiveMergeEngine的委托调用逻辑
# ============================================================


class TestSafeHiveMergeEngineDelegation:
    """测试组2: 委托调用"""

    def test_set_progress_callback(self, safe_engine):
        """
        TC-2.1: 设置进度回调函数
        Given: SafeHiveMergeEngine实例和回调函数
        When: 调用set_progress_callback
        Then: 回调函数正确设置到executor
        """
        # Given
        callback = Mock()

        # When
        safe_engine.set_progress_callback(callback)

        # Then
        safe_engine._mock_executor.set_progress_callback.assert_called_once_with(
            callback
        )

    def test_validate_task(self, safe_engine, mock_task):
        """
        TC-2.2: 验证合并任务
        Given: SafeHiveMergeEngine实例和MergeTask
        When: 调用validate_task
        Then: 委托给validation_service.validate_task
        """
        # Given
        expected_result = {"valid": True, "reason": ""}
        safe_engine._mock_val_service.validate_task.return_value = expected_result

        # When
        result = safe_engine.validate_task(mock_task)

        # Then
        assert result == expected_result
        safe_engine._mock_val_service.validate_task.assert_called_once_with(mock_task)

    def test_execute_merge(self, safe_engine, mock_task, mock_db_session):
        """
        TC-2.3: 执行合并任务
        Given: SafeHiveMergeEngine实例、MergeTask和数据库session
        When: 调用execute_merge
        Then: 委托给executor.execute_merge
        """
        # Given
        expected_result = {"success": True, "message": "Merge completed"}
        safe_engine._mock_executor.execute_merge.return_value = expected_result

        # When
        result = safe_engine.execute_merge(mock_task, mock_db_session)

        # Then
        assert result == expected_result
        safe_engine._mock_executor.execute_merge.assert_called_once_with(
            mock_task, mock_db_session
        )

    def test_get_merge_preview(self, safe_engine, mock_task):
        """
        TC-2.4: 获取合并预览信息
        Given: SafeHiveMergeEngine实例和MergeTask
        When: 调用get_merge_preview
        Then: 委托给progress_tracker.get_merge_preview
        """
        # Given
        expected_result = {
            "files_before": 1000,
            "files_after": 10,
            "size_saved": 1024000,
        }
        safe_engine._mock_tracker.get_merge_preview.return_value = expected_result

        # When
        result = safe_engine.get_merge_preview(mock_task)

        # Then
        assert result == expected_result
        safe_engine._mock_tracker.get_merge_preview.assert_called_once_with(mock_task)

    def test_estimate_duration(self, safe_engine, mock_task):
        """
        TC-2.5: 估算合并任务执行时间
        Given: SafeHiveMergeEngine实例和MergeTask
        When: 调用estimate_duration
        Then: 委托给progress_tracker.estimate_duration
        """
        # Given
        expected_duration = 300  # 5分钟
        safe_engine._mock_tracker.estimate_duration.return_value = expected_duration

        # When
        result = safe_engine.estimate_duration(mock_task)

        # Then
        assert result == expected_duration
        safe_engine._mock_tracker.estimate_duration.assert_called_once_with(mock_task)


# ============================================================
# 测试类3: TestSafeHiveMergeEngineLegacyMethods
# 测试向后兼容的旧方法
# ============================================================


class TestSafeHiveMergeEngineLegacyMethods:
    """测试组3: 向后兼容方法"""

    def test_execute_concatenate(self, safe_engine, mock_task, mock_db_session):
        """
        TC-3.1: 向后兼容的CONCATENATE执行方法
        Given: SafeHiveMergeEngine实例、MergeTask和数据库session
        When: 调用_execute_concatenate
        Then: 设置merge_strategy为CONCATENATE并委托执行
        """
        # Given
        expected_result = {"success": True, "method": "CONCATENATE"}
        safe_engine._mock_executor.execute_merge.return_value = expected_result

        # When
        result = safe_engine._execute_concatenate(mock_task, mock_db_session)

        # Then
        assert result == expected_result
        assert mock_task.merge_strategy == "CONCATENATE"
        safe_engine._mock_executor.execute_merge.assert_called_once_with(
            mock_task, mock_db_session
        )

    def test_execute_insert_overwrite(self, safe_engine, mock_task, mock_db_session):
        """
        TC-3.2: 向后兼容的INSERT OVERWRITE执行方法
        Given: SafeHiveMergeEngine实例、MergeTask和数据库session
        When: 调用_execute_insert_overwrite
        Then: 设置merge_strategy为INSERT_OVERWRITE并委托执行
        """
        # Given
        expected_result = {"success": True, "method": "INSERT_OVERWRITE"}
        safe_engine._mock_executor.execute_merge.return_value = expected_result

        # When
        result = safe_engine._execute_insert_overwrite(mock_task, mock_db_session)

        # Then
        assert result == expected_result
        assert mock_task.merge_strategy == "INSERT_OVERWRITE"
        safe_engine._mock_executor.execute_merge.assert_called_once_with(
            mock_task, mock_db_session
        )

    def test_execute_safe_merge(self, safe_engine, mock_task, mock_db_session):
        """
        TC-3.3: 向后兼容的SAFE_MERGE执行方法
        Given: SafeHiveMergeEngine实例、MergeTask和数据库session
        When: 调用_execute_safe_merge
        Then: 设置merge_strategy为SAFE_MERGE并委托执行
        """
        # Given
        expected_result = {"success": True, "method": "SAFE_MERGE"}
        safe_engine._mock_executor.execute_merge.return_value = expected_result

        # When
        result = safe_engine._execute_safe_merge(mock_task, mock_db_session)

        # Then
        assert result == expected_result
        assert mock_task.merge_strategy == "SAFE_MERGE"
        safe_engine._mock_executor.execute_merge.assert_called_once_with(
            mock_task, mock_db_session
        )


# ============================================================
# 测试类4: TestSafeHiveMergeEngineContextManager
# 测试上下文管理器功能
# ============================================================


class TestSafeHiveMergeEngineContextManager:
    """测试组4: 上下文管理器"""

    def test_context_manager_normal_exit(self, safe_engine):
        """
        TC-4.1: 正常退出上下文管理器
        Given: SafeHiveMergeEngine实例
        When: 使用with语句正常退出
        Then: 调用connection_manager.cleanup_connections
        """
        # Given & When
        with safe_engine:
            pass

        # Then
        safe_engine._mock_conn_mgr.cleanup_connections.assert_called_once()

    def test_context_manager_exception_exit(self, safe_engine):
        """
        TC-4.2: 异常退出上下文管理器
        Given: SafeHiveMergeEngine实例
        When: 使用with语句时抛出异常
        Then: 仍然调用connection_manager.cleanup_connections
        """
        # Given & When & Then
        try:
            with safe_engine:
                raise ValueError("Test exception")
        except ValueError:
            pass

        safe_engine._mock_conn_mgr.cleanup_connections.assert_called_once()

    def test_context_manager_no_connection_manager(self, mock_cluster):
        """
        TC-4.3: 上下文管理器退出时connection_manager为None
        Given: SafeHiveMergeEngine实例，connection_manager被设置为None
        When: 使用with语句退出
        Then: 不抛出异常
        """
        # Given
        with patch(
            "app.engines.safe_hive_engine_refactored.HiveConnectionManager"
        ), patch(
            "app.engines.safe_hive_engine_refactored.MergeTaskValidationService"
        ), patch(
            "app.engines.safe_hive_engine_refactored.MergeTaskExecutor"
        ), patch(
            "app.engines.safe_hive_engine_refactored.MergeProgressTracker"
        ):

            engine = SafeHiveMergeEngine(mock_cluster)
            engine.connection_manager = None

            # When & Then - 不应抛出异常
            with engine:
                pass


# ============================================================
# 测试类5: TestSafeHiveMergeEngineIntegration
# 测试完整工作流程
# ============================================================


class TestSafeHiveMergeEngineIntegration:
    """测试组5: 集成测试"""

    def test_full_merge_workflow(self, safe_engine, mock_task, mock_db_session):
        """
        TC-5.1: 完整的合并工作流程
        Given: SafeHiveMergeEngine实例和MergeTask
        When: 执行完整的验证→预览→估算→执行流程
        Then: 所有委托调用正确执行
        """
        # Given
        safe_engine._mock_val_service.validate_task.return_value = {
            "valid": True,
            "reason": "",
        }
        safe_engine._mock_tracker.get_merge_preview.return_value = {
            "files_before": 1000,
            "files_after": 10,
        }
        safe_engine._mock_tracker.estimate_duration.return_value = 300
        safe_engine._mock_executor.execute_merge.return_value = {
            "success": True,
            "message": "Merge completed",
        }

        # When
        validation_result = safe_engine.validate_task(mock_task)
        preview = safe_engine.get_merge_preview(mock_task)
        duration = safe_engine.estimate_duration(mock_task)
        merge_result = safe_engine.execute_merge(mock_task, mock_db_session)

        # Then
        assert validation_result["valid"] is True
        assert preview["files_before"] == 1000
        assert preview["files_after"] == 10
        assert duration == 300
        assert merge_result["success"] is True

        safe_engine._mock_val_service.validate_task.assert_called_once_with(mock_task)
        safe_engine._mock_tracker.get_merge_preview.assert_called_once_with(mock_task)
        safe_engine._mock_tracker.estimate_duration.assert_called_once_with(mock_task)
        safe_engine._mock_executor.execute_merge.assert_called_once_with(
            mock_task, mock_db_session
        )

    def test_full_workflow_with_callback(
        self, safe_engine, mock_task, mock_db_session
    ):
        """
        TC-5.2: 带进度回调的完整工作流程
        Given: SafeHiveMergeEngine实例、MergeTask和回调函数
        When: 设置回调后执行合并
        Then: 回调函数正确设置并执行合并
        """
        # Given
        callback = Mock()
        safe_engine._mock_executor.execute_merge.return_value = {
            "success": True,
            "message": "Merge completed",
        }

        # When
        safe_engine.set_progress_callback(callback)
        result = safe_engine.execute_merge(mock_task, mock_db_session)

        # Then
        assert result["success"] is True
        safe_engine._mock_executor.set_progress_callback.assert_called_once_with(
            callback
        )
        safe_engine._mock_executor.execute_merge.assert_called_once_with(
            mock_task, mock_db_session
        )


# ============================================================
# 测试类6: TestSafeHiveMergeEngineEdgeCases
# 测试边缘场景
# ============================================================


class TestSafeHiveMergeEngineEdgeCases:
    """测试组6: 边缘场景"""

    def test_validate_task_returns_invalid(self, safe_engine, mock_task):
        """
        TC-6.1: 验证任务返回无效结果
        Given: SafeHiveMergeEngine实例和无效的MergeTask
        When: 调用validate_task
        Then: 返回无效结果
        """
        # Given
        expected_result = {
            "valid": False,
            "reason": "Table is unsupported type: Hudi",
        }
        safe_engine._mock_val_service.validate_task.return_value = expected_result

        # When
        result = safe_engine.validate_task(mock_task)

        # Then
        assert result["valid"] is False
        assert "Hudi" in result["reason"]

    def test_execute_merge_returns_failure(
        self, safe_engine, mock_task, mock_db_session
    ):
        """
        TC-6.2: 执行合并返回失败结果
        Given: SafeHiveMergeEngine实例和MergeTask
        When: 调用execute_merge返回失败
        Then: 返回失败结果
        """
        # Given
        expected_result = {
            "success": False,
            "error": "Hive connection timeout",
        }
        safe_engine._mock_executor.execute_merge.return_value = expected_result

        # When
        result = safe_engine.execute_merge(mock_task, mock_db_session)

        # Then
        assert result["success"] is False
        assert "timeout" in result["error"]

    def test_estimate_duration_returns_zero(self, safe_engine, mock_task):
        """
        TC-6.3: 估算时间返回0（空表或小表）
        Given: SafeHiveMergeEngine实例和空表任务
        When: 调用estimate_duration
        Then: 返回0秒
        """
        # Given
        safe_engine._mock_tracker.estimate_duration.return_value = 0

        # When
        result = safe_engine.estimate_duration(mock_task)

        # Then
        assert result == 0

    def test_get_merge_preview_zero_files(self, safe_engine, mock_task):
        """
        TC-6.4: 获取预览信息时源表无文件
        Given: SafeHiveMergeEngine实例和无文件的表
        When: 调用get_merge_preview
        Then: 返回files_before=0
        """
        # Given
        expected_result = {
            "files_before": 0,
            "files_after": 0,
            "size_saved": 0,
        }
        safe_engine._mock_tracker.get_merge_preview.return_value = expected_result

        # When
        result = safe_engine.get_merge_preview(mock_task)

        # Then
        assert result["files_before"] == 0
        assert result["files_after"] == 0

    def test_callback_is_none(self, safe_engine):
        """
        TC-6.5: 设置进度回调为None
        Given: SafeHiveMergeEngine实例
        When: 调用set_progress_callback(None)
        Then: 正常执行不抛异常
        """
        # Given & When
        safe_engine.set_progress_callback(None)

        # Then
        safe_engine._mock_executor.set_progress_callback.assert_called_once_with(None)
