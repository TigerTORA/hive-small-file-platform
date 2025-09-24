"""
合并任务日志系统单元测试
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.models.merge_task import MergeTask
from app.utils.merge_logger import (
    MergeLogEntry,
    MergeLogLevel,
    MergePhase,
    MergeTaskLogger,
)


class TestMergeLogLevel:
    """测试日志级别枚举"""

    @pytest.mark.unit
    def test_log_levels(self):
        """测试所有日志级别"""
        assert MergeLogLevel.DEBUG.value == "DEBUG"
        assert MergeLogLevel.INFO.value == "INFO"
        assert MergeLogLevel.WARNING.value == "WARNING"
        assert MergeLogLevel.ERROR.value == "ERROR"
        assert MergeLogLevel.CRITICAL.value == "CRITICAL"


class TestMergePhase:
    """测试合并阶段枚举"""

    @pytest.mark.unit
    def test_merge_phases(self):
        """测试所有合并阶段"""
        expected_phases = [
            "initialization",
            "connection_test",
            "pre_validation",
            "file_analysis",
            "temp_table_creation",
            "data_validation",
            "atomic_swap",
            "post_validation",
            "cleanup",
            "rollback",
            "completion",
        ]

        actual_phases = [phase.value for phase in MergePhase]
        assert set(actual_phases) == set(expected_phases)


class TestMergeLogEntry:
    """测试日志条目数据类"""

    @pytest.mark.unit
    def test_log_entry_creation(self):
        """测试日志条目创建"""
        entry = MergeLogEntry(
            timestamp="2023-01-01T12:00:00",
            task_id=1,
            phase="initialization",
            level="INFO",
            message="测试消息",
            details={"key": "value"},
            duration_ms=1000,
        )

        assert entry.timestamp == "2023-01-01T12:00:00"
        assert entry.task_id == 1
        assert entry.phase == "initialization"
        assert entry.level == "INFO"
        assert entry.message == "测试消息"
        assert entry.details == {"key": "value"}
        assert entry.duration_ms == 1000


class TestMergeTaskLogger:
    """测试合并任务日志记录器"""

    def setup_method(self):
        """测试前准备"""
        self.mock_task = Mock(spec=MergeTask)
        self.mock_task.id = 1
        self.mock_task.cluster_id = 1
        self.mock_task.database_name = "test_db"
        self.mock_task.table_name = "test_table"
        self.mock_task.partition_filter = "dt='2023-01-01'"
        self.mock_task.merge_strategy = "CONCATENATE"

        self.mock_db_session = Mock()

    @pytest.mark.unit
    @patch("app.utils.merge_logger.logging")
    @patch("app.utils.merge_logger.time")
    def test_logger_initialization(self, mock_time, mock_logging):
        """测试日志记录器初始化"""
        mock_time.time.return_value = 1640995200  # 2022-01-01 00:00:00

        logger = MergeTaskLogger(self.mock_task, self.mock_db_session)

        assert logger.task == self.mock_task
        assert logger.db_session == self.mock_db_session
        assert len(logger.log_entries) == 1  # 初始化日志
        assert logger.log_file_path.startswith("/tmp/merge_task_1_")

    @pytest.mark.unit
    @patch("app.utils.merge_logger.logging")
    @patch("app.utils.merge_logger.time")
    def test_start_and_end_phase(self, mock_time, mock_logging):
        """测试阶段开始和结束"""
        mock_time.time.side_effect = [1640995200, 1640995201, 1640995202]

        logger = MergeTaskLogger(self.mock_task, self.mock_db_session)

        # 开始阶段
        logger.start_phase(
            MergePhase.CONNECTION_TEST, "测试连接", {"host": "localhost"}
        )

        # 结束阶段
        logger.end_phase(
            MergePhase.CONNECTION_TEST,
            "连接成功",
            {"result": "connected"},
            success=True,
        )

        # 验证日志条目
        assert len(logger.log_entries) >= 3  # 初始化 + 开始 + 结束

        start_entry = logger.log_entries[-2]
        end_entry = logger.log_entries[-1]

        assert start_entry.phase == "connection_test"
        assert "开始阶段" in start_entry.message
        assert start_entry.details["host"] == "localhost"

        assert end_entry.phase == "connection_test"
        assert "阶段完成" in end_entry.message
        assert end_entry.duration_ms == 1000  # 1秒

    @pytest.mark.unit
    @patch("app.utils.merge_logger.logging")
    @patch("app.utils.merge_logger.time")
    def test_log_sql_execution(self, mock_time, mock_logging):
        """测试SQL执行日志"""
        mock_time.time.return_value = 1640995200

        logger = MergeTaskLogger(self.mock_task, self.mock_db_session)

        sql = "CREATE TABLE temp_table AS SELECT * FROM original_table"
        logger.log_sql_execution(
            sql_statement=sql,
            phase=MergePhase.TEMP_TABLE_CREATION,
            affected_rows=1000,
            success=True,
        )

        # 验证SQL日志
        sql_entry = logger.log_entries[-1]
        assert sql_entry.phase == "temp_table_creation"
        assert "SQL执行成功" in sql_entry.message
        assert sql_entry.sql_statement == sql
        assert sql_entry.affected_rows == 1000
        assert sql_entry.details["full_sql"] == sql
        assert sql_entry.details["execution_success"] is True

    @pytest.mark.unit
    @patch("app.utils.merge_logger.logging")
    @patch("app.utils.merge_logger.time")
    def test_log_hdfs_operation(self, mock_time, mock_logging):
        """测试HDFS操作日志"""
        mock_time.time.return_value = 1640995200

        logger = MergeTaskLogger(self.mock_task, self.mock_db_session)

        hdfs_stats = {"files_scanned": 100, "total_size": 1024 * 1024 * 100}

        logger.log_hdfs_operation(
            operation="list_files",
            path="/data/table/dt=2023-01-01",
            phase=MergePhase.FILE_ANALYSIS,
            stats=hdfs_stats,
            success=True,
        )

        # 验证HDFS日志
        hdfs_entry = logger.log_entries[-1]
        assert hdfs_entry.phase == "file_analysis"
        assert "HDFS操作成功" in hdfs_entry.message
        assert hdfs_entry.details["hdfs_operation"] == "list_files"
        assert hdfs_entry.details["hdfs_path"] == "/data/table/dt=2023-01-01"
        assert hdfs_entry.hdfs_stats == hdfs_stats

    @pytest.mark.unit
    @patch("app.utils.merge_logger.logging")
    @patch("app.utils.merge_logger.time")
    def test_log_file_statistics(self, mock_time, mock_logging):
        """测试文件统计日志"""
        mock_time.time.return_value = 1640995200

        logger = MergeTaskLogger(self.mock_task, self.mock_db_session)

        logger.log_file_statistics(
            phase=MergePhase.COMPLETION,
            table_name="test_table",
            files_before=500,
            files_after=10,
            hdfs_stats={"space_saved": 1024 * 1024 * 50},
        )

        # 验证文件统计日志
        stats_entry = logger.log_entries[-1]
        assert stats_entry.phase == "completion"
        assert "合并前: 500个文件" in stats_entry.message
        assert "合并后: 10个文件" in stats_entry.message
        assert stats_entry.files_before == 500
        assert stats_entry.files_after == 10

    @pytest.mark.unit
    @patch("app.utils.merge_logger.logging")
    @patch("app.utils.merge_logger.time")
    def test_get_log_summary(self, mock_time, mock_logging):
        """测试日志摘要生成"""
        mock_time.time.return_value = 1640995200

        logger = MergeTaskLogger(self.mock_task, self.mock_db_session)

        # 添加一些测试日志
        logger.log(MergePhase.CONNECTION_TEST, MergeLogLevel.INFO, "连接成功")
        logger.log(MergePhase.FILE_ANALYSIS, MergeLogLevel.WARNING, "发现小文件")
        logger.log(MergePhase.CLEANUP, MergeLogLevel.ERROR, "清理失败")

        summary = logger.get_log_summary()

        assert summary["task_id"] == 1
        assert summary["total_entries"] >= 4  # 初始化 + 3个测试日志
        assert summary["error_count"] == 1
        assert summary["warning_count"] == 1
        assert "connection_test" in summary["phase_statistics"]
        assert summary["log_file_path"].startswith("/tmp/merge_task_1_")

    @pytest.mark.unit
    @patch("app.utils.merge_logger.logging")
    @patch("app.utils.merge_logger.time")
    def test_export_logs_to_json(self, mock_time, mock_logging):
        """测试日志JSON导出"""
        mock_time.time.return_value = 1640995200

        logger = MergeTaskLogger(self.mock_task, self.mock_db_session)
        logger.log(MergePhase.CONNECTION_TEST, MergeLogLevel.INFO, "测试日志")

        json_logs = logger.export_logs_to_json()
        logs_data = json.loads(json_logs)

        assert "task_info" in logs_data
        assert "log_entries" in logs_data
        assert "summary" in logs_data

        assert logs_data["task_info"]["id"] == 1
        assert logs_data["task_info"]["database_name"] == "test_db"
        assert logs_data["task_info"]["table_name"] == "test_table"

    @pytest.mark.unit
    @patch("app.utils.merge_logger.logging")
    @patch("app.utils.merge_logger.time")
    @patch("app.utils.merge_logger.MergeTaskLogger._save_to_database")
    def test_database_save_called(self, mock_save_db, mock_time, mock_logging):
        """测试数据库保存被调用"""
        mock_time.time.return_value = 1640995200

        logger = MergeTaskLogger(self.mock_task, self.mock_db_session)
        logger.log(MergePhase.CONNECTION_TEST, MergeLogLevel.INFO, "测试日志")

        # 验证数据库保存被调用
        assert mock_save_db.call_count >= 2  # 初始化日志 + 测试日志

    @pytest.mark.unit
    @patch("app.utils.merge_logger.logging")
    @patch("app.utils.merge_logger.time")
    def test_database_save_error_handling(self, mock_time, mock_logging):
        """测试数据库保存错误处理"""
        mock_time.time.return_value = 1640995200

        # Mock数据库会话抛出异常
        self.mock_db_session.add.side_effect = Exception("DB Error")

        logger = MergeTaskLogger(self.mock_task, self.mock_db_session)

        # 日志记录应该继续工作，即使数据库保存失败
        logger.log(MergePhase.CONNECTION_TEST, MergeLogLevel.INFO, "测试日志")

        # 验证回滚被调用
        assert self.mock_db_session.rollback.called
