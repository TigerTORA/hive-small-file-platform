"""
MergeTaskValidationService单元测试

Story 6.10.1 - Task 4: 重写validation_service.py测试
测试策略: 单元测试为主,重点覆盖验证逻辑和格式检查
覆盖率目标: 13% → 80%

创建时间: 2025-10-13
预计时间: 4小时
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List

from app.engines.validation_service import MergeTaskValidationService
from app.engines.connection_manager import HiveConnectionManager
from app.models.merge_task import MergeTask


class TestMergeTaskValidationService:
    """MergeTaskValidationService单元测试类"""

    # ==================== Fixtures ====================

    @pytest.fixture
    def mock_connection_manager(self):
        """模拟连接管理器"""
        manager = MagicMock(spec=HiveConnectionManager)
        manager.test_connections = Mock(return_value=True)

        # Mock get_hive_connection context manager
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        manager.get_hive_connection = Mock(return_value=mock_conn)

        # Mock metastore_connector context manager
        mock_metastore = MagicMock()
        mock_metastore.__enter__ = Mock(return_value=mock_metastore)
        mock_metastore.__exit__ = Mock(return_value=False)
        manager.metastore_connector = mock_metastore

        return manager

    @pytest.fixture
    def validation_service(self, mock_connection_manager):
        """创建验证服务实例"""
        return MergeTaskValidationService(mock_connection_manager)

    @pytest.fixture
    def mock_task(self):
        """模拟MergeTask"""
        task = Mock(spec=MergeTask)
        task.id = 1
        task.database_name = "test_db"
        task.table_name = "user_logs"
        task.partition_filter = None
        return task

    # ==================== 测试组1: 初始化 ====================

    def test_init_success(self, mock_connection_manager):
        """TC-1.1: 正常初始化"""
        # When
        service = MergeTaskValidationService(mock_connection_manager)

        # Then
        assert service.connection_manager == mock_connection_manager

    # ==================== 测试组2: validate_task ====================

    def test_validate_task_success(self, validation_service, mock_task, mock_connection_manager):
        """TC-2.1: 任务验证成功"""
        # Given
        mock_connection_manager.test_connections.return_value = True
        validation_service._table_exists = Mock(return_value=True)
        validation_service._get_table_format_info = Mock(return_value={"input_format": "org.apache.hadoop.mapred.TextInputFormat"})
        validation_service._is_unsupported_table_type = Mock(return_value=False)
        validation_service._is_partitioned_table = Mock(return_value=False)

        # When
        result = validation_service.validate_task(mock_task)

        # Then
        assert result["valid"] is True
        assert result["message"] == "Task validation passed"
        assert isinstance(result["warnings"], list)

    def test_validate_task_connection_failure(self, validation_service, mock_task, mock_connection_manager):
        """TC-2.2: 连接失败"""
        # Given
        mock_connection_manager.test_connections.return_value = False

        # When
        result = validation_service.validate_task(mock_task)

        # Then
        assert result["valid"] is False
        assert "Failed to connect" in result["message"]

    def test_validate_task_table_not_exists(self, validation_service, mock_task, mock_connection_manager):
        """TC-2.3: 表不存在"""
        # Given
        mock_connection_manager.test_connections.return_value = True
        validation_service._table_exists = Mock(return_value=False)

        # When
        result = validation_service.validate_task(mock_task)

        # Then
        assert result["valid"] is False
        assert "does not exist" in result["message"]

    def test_validate_task_unsupported_table_type(self, validation_service, mock_task, mock_connection_manager):
        """TC-2.4: 不支持的表类型"""
        # Given
        mock_connection_manager.test_connections.return_value = True
        validation_service._table_exists = Mock(return_value=True)
        validation_service._get_table_format_info = Mock(return_value={"input_format": "org.apache.hudi.HudiInputFormat"})
        validation_service._is_unsupported_table_type = Mock(return_value=True)
        validation_service._unsupported_reason = Mock(return_value="Hudi tables are not supported")

        # When
        result = validation_service.validate_task(mock_task)

        # Then
        assert result["valid"] is False
        assert "Hudi" in result["message"]

    def test_validate_task_partitioned_table_warning(self, validation_service, mock_task, mock_connection_manager):
        """TC-2.5: 分区表但无分区过滤器(警告)"""
        # Given
        mock_connection_manager.test_connections.return_value = True
        validation_service._table_exists = Mock(return_value=True)
        validation_service._get_table_format_info = Mock(return_value={"input_format": "org.apache.hadoop.mapred.TextInputFormat"})
        validation_service._is_unsupported_table_type = Mock(return_value=False)
        validation_service._is_partitioned_table = Mock(return_value=True)
        mock_task.partition_filter = None

        # When
        result = validation_service.validate_task(mock_task)

        # Then
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert "no partition filter" in result["warnings"][0]

    def test_validate_task_with_partition_filter(self, validation_service, mock_task, mock_connection_manager):
        """TC-2.6: 带分区过滤器的验证"""
        # Given
        mock_connection_manager.test_connections.return_value = True
        validation_service._table_exists = Mock(return_value=True)
        validation_service._get_table_format_info = Mock(return_value={"input_format": "org.apache.hadoop.mapred.TextInputFormat"})
        validation_service._is_unsupported_table_type = Mock(return_value=False)
        validation_service._is_partitioned_table = Mock(return_value=True)
        validation_service._validate_partition_filter = Mock(return_value=False)
        mock_task.partition_filter = "dt='2024-01-01'"

        # When
        result = validation_service.validate_task(mock_task)

        # Then
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert "may not match any partitions" in result["warnings"][0]

    def test_validate_task_exception(self, validation_service, mock_task, mock_connection_manager):
        """TC-2.7: 验证过程中抛异常"""
        # Given
        mock_connection_manager.test_connections.side_effect = Exception("Connection timeout")

        # When
        result = validation_service.validate_task(mock_task)

        # Then
        assert result["valid"] is False
        assert "Validation error" in result["message"]

    # ==================== 测试组3: _table_exists ====================

    def test_table_exists_success(self, validation_service, mock_connection_manager):
        """TC-3.1: 表存在"""
        # Given
        mock_cursor = mock_connection_manager.get_hive_connection.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = ("user_logs",)

        # When
        result = validation_service._table_exists("test_db", "user_logs")

        # Then
        assert result is True
        mock_cursor.execute.assert_called_once_with("SHOW TABLES LIKE 'user_logs'")

    def test_table_exists_not_found(self, validation_service, mock_connection_manager):
        """TC-3.2: 表不存在"""
        # Given
        mock_cursor = mock_connection_manager.get_hive_connection.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = None

        # When
        result = validation_service._table_exists("test_db", "user_logs")

        # Then
        assert result is False

    def test_table_exists_exception(self, validation_service, mock_connection_manager):
        """TC-3.3: 检查表存在时抛异常"""
        # Given
        mock_connection_manager.get_hive_connection.side_effect = Exception("Connection error")

        # When
        result = validation_service._table_exists("test_db", "user_logs")

        # Then
        assert result is False

    # ==================== 测试组4: _is_partitioned_table ====================

    def test_is_partitioned_table_true(self, validation_service, mock_connection_manager):
        """TC-4.1: 是分区表"""
        # Given
        mock_metastore = mock_connection_manager.metastore_connector.__enter__.return_value
        mock_metastore.get_table_info.return_value = {"is_partitioned": True}

        # When
        result = validation_service._is_partitioned_table("test_db", "user_logs")

        # Then
        assert result is True

    def test_is_partitioned_table_false(self, validation_service, mock_connection_manager):
        """TC-4.2: 不是分区表"""
        # Given
        mock_metastore = mock_connection_manager.metastore_connector.__enter__.return_value
        mock_metastore.get_table_info.return_value = {"is_partitioned": False}

        # When
        result = validation_service._is_partitioned_table("test_db", "user_logs")

        # Then
        assert result is False

    def test_is_partitioned_table_exception(self, validation_service, mock_connection_manager):
        """TC-4.3: 检查分区表时抛异常"""
        # Given
        mock_metastore = mock_connection_manager.metastore_connector.__enter__.return_value
        mock_metastore.get_table_info.side_effect = Exception("Metastore error")

        # When
        result = validation_service._is_partitioned_table("test_db", "user_logs")

        # Then
        assert result is False

    # ==================== 测试组5: _get_table_partitions ====================

    def test_get_table_partitions_success(self, validation_service, mock_connection_manager):
        """TC-5.1: 成功获取分区列表"""
        # Given
        mock_cursor = mock_connection_manager.get_hive_connection.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [("dt=2024-01-01",), ("dt=2024-01-02",), ("dt=2024-01-03",)]

        # When
        result = validation_service._get_table_partitions("test_db", "user_logs")

        # Then
        assert len(result) == 3
        assert "dt=2024-01-01" in result

    def test_get_table_partitions_empty(self, validation_service, mock_connection_manager):
        """TC-5.2: 无分区"""
        # Given
        mock_cursor = mock_connection_manager.get_hive_connection.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []

        # When
        result = validation_service._get_table_partitions("test_db", "user_logs")

        # Then
        assert result == []

    def test_get_table_partitions_exception(self, validation_service, mock_connection_manager):
        """TC-5.3: 获取分区时抛异常"""
        # Given
        mock_connection_manager.get_hive_connection.side_effect = Exception("Hive error")

        # When
        result = validation_service._get_table_partitions("test_db", "user_logs")

        # Then
        assert result == []

    # ==================== 测试组6: _get_table_format_info ====================

    def test_get_table_format_info_success(self, validation_service, mock_connection_manager):
        """TC-6.1: 成功获取表格式信息"""
        # Given
        mock_metastore = mock_connection_manager.metastore_connector.__enter__.return_value
        mock_metastore.get_table_format_info.return_value = {
            "input_format": "org.apache.hadoop.mapred.TextInputFormat",
            "serde_lib": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
        }

        # When
        result = validation_service._get_table_format_info("test_db", "user_logs")

        # Then
        assert "input_format" in result
        assert "TextInputFormat" in result["input_format"]

    def test_get_table_format_info_exception(self, validation_service, mock_connection_manager):
        """TC-6.2: 获取格式信息时抛异常"""
        # Given
        mock_metastore = mock_connection_manager.metastore_connector.__enter__.return_value
        mock_metastore.get_table_format_info.side_effect = Exception("Metastore error")

        # When
        result = validation_service._get_table_format_info("test_db", "user_logs")

        # Then
        assert result == {}

    # ==================== 测试组7: _is_unsupported_table_type ====================

    def test_is_unsupported_table_type_hudi(self, validation_service):
        """TC-7.1: Hudi表"""
        # Given
        fmt = {"input_format": "org.apache.hudi.HudiInputFormat", "serde_lib": ""}

        # When
        result = validation_service._is_unsupported_table_type(fmt)

        # Then
        assert result is True

    def test_is_unsupported_table_type_iceberg(self, validation_service):
        """TC-7.2: Iceberg表"""
        # Given
        fmt = {"input_format": "org.apache.iceberg.mr.hive.HiveIcebergInputFormat", "serde_lib": ""}

        # When
        result = validation_service._is_unsupported_table_type(fmt)

        # Then
        assert result is True

    def test_is_unsupported_table_type_delta(self, validation_service):
        """TC-7.3: Delta Lake表"""
        # Given
        fmt = {"input_format": "io.delta.hive.DeltaInputFormat", "serde_lib": ""}

        # When
        result = validation_service._is_unsupported_table_type(fmt)

        # Then
        assert result is True

    def test_is_unsupported_table_type_acid(self, validation_service):
        """TC-7.4: ACID事务表"""
        # Given
        fmt = {"input_format": "", "serde_lib": "", "table_properties": {"transactional": "true"}}

        # When
        result = validation_service._is_unsupported_table_type(fmt)

        # Then
        assert result is True

    def test_is_unsupported_table_type_supported(self, validation_service):
        """TC-7.5: 支持的表类型"""
        # Given
        fmt = {"input_format": "org.apache.hadoop.mapred.TextInputFormat", "serde_lib": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"}

        # When
        result = validation_service._is_unsupported_table_type(fmt)

        # Then
        assert result is False

    # ==================== 测试组8: _unsupported_reason ====================

    def test_unsupported_reason_hudi(self, validation_service):
        """TC-8.1: Hudi表不支持原因"""
        # Given
        fmt = {"input_format": "org.apache.hudi.HudiInputFormat", "serde_lib": ""}

        # When
        result = validation_service._unsupported_reason(fmt)

        # Then
        assert "Hudi" in result
        assert "not supported" in result

    def test_unsupported_reason_iceberg(self, validation_service):
        """TC-8.2: Iceberg表不支持原因"""
        # Given
        fmt = {"input_format": "org.apache.iceberg.mr.hive.HiveIcebergInputFormat", "serde_lib": ""}

        # When
        result = validation_service._unsupported_reason(fmt)

        # Then
        assert "Iceberg" in result

    def test_unsupported_reason_delta(self, validation_service):
        """TC-8.3: Delta Lake表不支持原因"""
        # Given
        fmt = {"input_format": "io.delta.hive.DeltaInputFormat", "serde_lib": ""}

        # When
        result = validation_service._unsupported_reason(fmt)

        # Then
        assert "Delta" in result

    def test_unsupported_reason_acid(self, validation_service):
        """TC-8.4: ACID表不支持原因"""
        # Given
        fmt = {"input_format": "", "serde_lib": "", "table_properties": {"transactional": "true"}}

        # When
        result = validation_service._unsupported_reason(fmt)

        # Then
        assert "ACID" in result

    def test_unsupported_reason_unknown(self, validation_service):
        """TC-8.5: 未知不支持原因"""
        # Given
        fmt = {"input_format": "unknown.format", "serde_lib": ""}

        # When
        result = validation_service._unsupported_reason(fmt)

        # Then
        assert "Unsupported table format" in result

    # ==================== 测试组9: _validate_partition_filter ====================

    def test_validate_partition_filter_success(self, validation_service):
        """TC-9.1: 分区过滤器匹配成功"""
        # Given
        validation_service._get_table_partitions = Mock(return_value=["dt=2024-01-01", "dt=2024-01-02"])

        # When
        result = validation_service._validate_partition_filter("test_db", "user_logs", "dt=2024-01-01")

        # Then
        assert result is True

    def test_validate_partition_filter_no_match(self, validation_service):
        """TC-9.2: 分区过滤器无匹配"""
        # Given
        validation_service._get_table_partitions = Mock(return_value=["dt=2024-01-01", "dt=2024-01-02"])

        # When
        result = validation_service._validate_partition_filter("test_db", "user_logs", "dt=2024-12-31")

        # Then
        assert result is False

    def test_validate_partition_filter_no_partitions(self, validation_service):
        """TC-9.3: 表无分区"""
        # Given
        validation_service._get_table_partitions = Mock(return_value=[])

        # When
        result = validation_service._validate_partition_filter("test_db", "user_logs", "dt=2024-01-01")

        # Then
        assert result is False

    def test_validate_partition_filter_exception(self, validation_service):
        """TC-9.4: 验证分区过滤器时抛异常"""
        # Given
        validation_service._get_table_partitions = Mock(side_effect=Exception("Partition error"))

        # When
        result = validation_service._validate_partition_filter("test_db", "user_logs", "dt=2024-01-01")

        # Then
        assert result is False

    # ==================== 测试组10: get_table_columns ====================

    def test_get_table_columns_success(self, validation_service, mock_connection_manager):
        """TC-10.1: 成功获取表列信息"""
        # Given
        mock_cursor = mock_connection_manager.get_hive_connection.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [
            ("id", "int", ""),
            ("name", "string", ""),
            ("age", "int", ""),
            ("# Partition Information", "", ""),
            ("col_name", "", ""),
            ("dt", "string", ""),
        ]

        # When
        columns, partition_columns = validation_service.get_table_columns("test_db", "user_logs")

        # Then
        assert len(columns) == 3
        assert "id" in columns
        assert "name" in columns
        assert len(partition_columns) == 1
        assert "dt" in partition_columns

    def test_get_table_columns_no_partitions(self, validation_service, mock_connection_manager):
        """TC-10.2: 无分区列"""
        # Given
        mock_cursor = mock_connection_manager.get_hive_connection.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [
            ("id", "int", ""),
            ("name", "string", ""),
        ]

        # When
        columns, partition_columns = validation_service.get_table_columns("test_db", "user_logs")

        # Then
        assert len(columns) == 2
        assert len(partition_columns) == 0

    def test_get_table_columns_exception(self, validation_service, mock_connection_manager):
        """TC-10.3: 获取列信息时抛异常"""
        # Given
        mock_connection_manager.get_hive_connection.side_effect = Exception("Hive error")

        # When
        columns, partition_columns = validation_service.get_table_columns("test_db", "user_logs")

        # Then
        assert columns == []
        assert partition_columns == []


class TestMergeTaskValidationServiceEdgeCases:
    """MergeTaskValidationService边缘场景测试"""

    @pytest.fixture
    def mock_connection_manager(self):
        manager = MagicMock(spec=HiveConnectionManager)
        manager.test_connections = Mock(return_value=True)
        return manager

    @pytest.fixture
    def validation_service(self, mock_connection_manager):
        return MergeTaskValidationService(mock_connection_manager)

    # ==================== 边缘场景测试 ====================

    def test_is_unsupported_table_type_case_insensitive(self, validation_service):
        """EC-1: 大小写不敏感检测"""
        # Given
        fmt = {"input_format": "ORG.APACHE.HUDI.HudiInputFormat", "serde_lib": ""}

        # When
        result = validation_service._is_unsupported_table_type(fmt)

        # Then
        assert result is True

    def test_is_unsupported_table_type_empty_format(self, validation_service):
        """EC-2: 空格式信息"""
        # Given
        fmt = {}

        # When
        result = validation_service._is_unsupported_table_type(fmt)

        # Then
        assert result is False

    def test_validate_partition_filter_complex_pattern(self, validation_service):
        """EC-3: 复杂分区过滤器"""
        # Given
        validation_service._get_table_partitions = Mock(return_value=["year=2024/month=01/day=15"])

        # When
        result = validation_service._validate_partition_filter("test_db", "user_logs", "year=2024/month=01")

        # Then
        assert result is True
