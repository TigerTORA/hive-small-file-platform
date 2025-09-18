"""
测试重构后的合并任务验证服务
"""

from unittest.mock import Mock, patch

import pytest

from app.engines.connection_manager import HiveConnectionManager
from app.engines.validation_service import MergeTaskValidationService
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask


class TestMergeTaskValidationService:
    """测试 MergeTaskValidationService 类"""

    @pytest.fixture
    def mock_connection_manager(self):
        """创建模拟连接管理器"""
        manager = Mock(spec=HiveConnectionManager)
        manager.test_metastore_connection.return_value = True
        manager.test_hdfs_connection.return_value = True
        return manager

    @pytest.fixture
    def validation_service(self, mock_connection_manager):
        """创建验证服务实例"""
        return MergeTaskValidationService(mock_connection_manager)

    @pytest.fixture
    def sample_merge_task(self):
        """创建示例合并任务"""
        task = Mock(spec=MergeTask)
        task.id = 1
        task.cluster_id = 1
        task.database_name = "test_db"
        task.table_name = "test_table"
        task.merge_strategy = "CONCATENATE"
        task.small_file_threshold = 128 * 1024 * 1024  # 128MB
        task.target_file_size = 256 * 1024 * 1024  # 256MB
        return task

    def test_validate_task_success(self, validation_service, sample_merge_task):
        """测试任务验证成功"""
        validation_service._validate_cluster_connection = Mock(
            return_value={"valid": True}
        )
        validation_service._validate_table_exists = Mock(return_value={"valid": True})
        validation_service._validate_merge_strategy = Mock(return_value={"valid": True})
        validation_service._validate_file_thresholds = Mock(
            return_value={"valid": True}
        )

        result = validation_service.validate_task(sample_merge_task)

        assert result["is_valid"] is True
        assert result["can_proceed"] is True
        assert "validation_details" in result

    def test_validate_task_connection_failure(
        self, validation_service, sample_merge_task
    ):
        """测试集群连接验证失败"""
        validation_service._validate_cluster_connection = Mock(
            return_value={"valid": False, "error": "Connection failed"}
        )

        result = validation_service.validate_task(sample_merge_task)

        assert result["is_valid"] is False
        assert result["can_proceed"] is False
        assert "Connection failed" in str(result["errors"])

    def test_validate_cluster_connection_success(self, validation_service):
        """测试集群连接验证成功"""
        result = validation_service._validate_cluster_connection()

        assert result["valid"] is True
        assert result["message"] == "Cluster connections are healthy"

    def test_validate_cluster_connection_metastore_failure(self, validation_service):
        """测试 MetaStore 连接失败"""
        validation_service.connection_manager.test_metastore_connection.return_value = (
            False
        )

        result = validation_service._validate_cluster_connection()

        assert result["valid"] is False
        assert "MetaStore connection failed" in result["error"]

    def test_validate_cluster_connection_hdfs_failure(self, validation_service):
        """测试 HDFS 连接失败"""
        validation_service.connection_manager.test_hdfs_connection.return_value = False

        result = validation_service._validate_cluster_connection()

        assert result["valid"] is False
        assert "HDFS connection failed" in result["error"]

    @patch("app.engines.validation_service.logger")
    def test_validate_table_exists_success(
        self, mock_logger, validation_service, sample_merge_task
    ):
        """测试表存在性验证成功"""
        mock_metastore_conn = Mock()
        mock_metastore_conn.execute.return_value.fetchone.return_value = (1,)
        validation_service.connection_manager.get_metastore_connection.return_value = (
            mock_metastore_conn
        )

        result = validation_service._validate_table_exists(sample_merge_task)

        assert result["valid"] is True
        assert (
            result["message"]
            == f"Table {sample_merge_task.database_name}.{sample_merge_task.table_name} exists"
        )

    def test_validate_table_exists_failure(self, validation_service, sample_merge_task):
        """测试表不存在"""
        mock_metastore_conn = Mock()
        mock_metastore_conn.execute.return_value.fetchone.return_value = None
        validation_service.connection_manager.get_metastore_connection.return_value = (
            mock_metastore_conn
        )

        result = validation_service._validate_table_exists(sample_merge_task)

        assert result["valid"] is False
        assert "does not exist" in result["error"]

    def test_validate_table_exists_exception(
        self, validation_service, sample_merge_task
    ):
        """测试表验证时发生异常"""
        validation_service.connection_manager.get_metastore_connection.side_effect = (
            Exception("DB Error")
        )

        result = validation_service._validate_table_exists(sample_merge_task)

        assert result["valid"] is False
        assert "DB Error" in result["error"]

    def test_validate_merge_strategy_concatenate(
        self, validation_service, sample_merge_task
    ):
        """测试 CONCATENATE 策略验证"""
        sample_merge_task.merge_strategy = "CONCATENATE"

        result = validation_service._validate_merge_strategy(sample_merge_task)

        assert result["valid"] is True
        assert "CONCATENATE" in result["message"]

    def test_validate_merge_strategy_insert_overwrite(
        self, validation_service, sample_merge_task
    ):
        """测试 INSERT_OVERWRITE 策略验证"""
        sample_merge_task.merge_strategy = "INSERT_OVERWRITE"

        result = validation_service._validate_merge_strategy(sample_merge_task)

        assert result["valid"] is True
        assert "INSERT_OVERWRITE" in result["message"]

    def test_validate_merge_strategy_safe_merge(
        self, validation_service, sample_merge_task
    ):
        """测试 SAFE_MERGE 策略验证"""
        sample_merge_task.merge_strategy = "SAFE_MERGE"

        result = validation_service._validate_merge_strategy(sample_merge_task)

        assert result["valid"] is True
        assert "SAFE_MERGE" in result["message"]

    def test_validate_merge_strategy_invalid(
        self, validation_service, sample_merge_task
    ):
        """测试无效的合并策略"""
        sample_merge_task.merge_strategy = "INVALID_STRATEGY"

        result = validation_service._validate_merge_strategy(sample_merge_task)

        assert result["valid"] is False
        assert "Unsupported merge strategy" in result["error"]

    def test_validate_file_thresholds_valid(
        self, validation_service, sample_merge_task
    ):
        """测试文件阈值验证通过"""
        result = validation_service._validate_file_thresholds(sample_merge_task)

        assert result["valid"] is True
        assert "File thresholds are valid" in result["message"]

    def test_validate_file_thresholds_small_threshold_too_small(
        self, validation_service, sample_merge_task
    ):
        """测试小文件阈值太小"""
        sample_merge_task.small_file_threshold = 1024  # 1KB

        result = validation_service._validate_file_thresholds(sample_merge_task)

        assert result["valid"] is False
        assert "Small file threshold too small" in result["error"]

    def test_validate_file_thresholds_target_size_too_small(
        self, validation_service, sample_merge_task
    ):
        """测试目标文件大小太小"""
        sample_merge_task.target_file_size = 1024 * 1024  # 1MB

        result = validation_service._validate_file_thresholds(sample_merge_task)

        assert result["valid"] is False
        assert "Target file size too small" in result["error"]

    def test_validate_file_thresholds_target_smaller_than_threshold(
        self, validation_service, sample_merge_task
    ):
        """测试目标文件大小小于小文件阈值"""
        sample_merge_task.small_file_threshold = 256 * 1024 * 1024  # 256MB
        sample_merge_task.target_file_size = 128 * 1024 * 1024  # 128MB

        result = validation_service._validate_file_thresholds(sample_merge_task)

        assert result["valid"] is False
        assert (
            "Target file size should be larger than small file threshold"
            in result["error"]
        )

    def test_get_validation_requirements(self, validation_service):
        """测试获取验证要求"""
        requirements = validation_service.get_validation_requirements()

        assert "cluster_connection" in requirements
        assert "table_existence" in requirements
        assert "merge_strategy" in requirements
        assert "file_thresholds" in requirements

        # 验证每个要求都有必要的字段
        for req_name, req_details in requirements.items():
            assert "description" in req_details
            assert "severity" in req_details
            assert req_details["severity"] in ["critical", "warning", "info"]

    @patch("app.engines.validation_service.logger")
    def test_validation_logging(
        self, mock_logger, validation_service, sample_merge_task
    ):
        """测试验证过程的日志记录"""
        validation_service._validate_cluster_connection = Mock(
            return_value={"valid": True}
        )
        validation_service._validate_table_exists = Mock(return_value={"valid": True})
        validation_service._validate_merge_strategy = Mock(return_value={"valid": True})
        validation_service._validate_file_thresholds = Mock(
            return_value={"valid": True}
        )

        validation_service.validate_task(sample_merge_task)

        # 验证记录了验证开始和结束的日志
        mock_logger.info.assert_called()

    def test_comprehensive_validation_report(
        self, validation_service, sample_merge_task
    ):
        """测试综合验证报告"""
        validation_service._validate_cluster_connection = Mock(
            return_value={"valid": True, "message": "Connections OK"}
        )
        validation_service._validate_table_exists = Mock(
            return_value={"valid": True, "message": "Table exists"}
        )
        validation_service._validate_merge_strategy = Mock(
            return_value={"valid": True, "message": "Strategy valid"}
        )
        validation_service._validate_file_thresholds = Mock(
            return_value={"valid": True, "message": "Thresholds valid"}
        )

        result = validation_service.validate_task(sample_merge_task)

        # 验证报告结构
        assert "validation_summary" in result
        assert "validation_details" in result
        assert "recommendations" in result
        assert result["validation_summary"]["total_checks"] == 4
        assert result["validation_summary"]["passed_checks"] == 4
        assert result["validation_summary"]["failed_checks"] == 0
