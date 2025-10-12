"""
Story 6.3单元测试 - 测试新提取的辅助方法
"""
import pytest
from unittest.mock import MagicMock

from app.engines.safe_hive_engine import SafeHiveMergeEngine
from app.models.cluster import Cluster


@pytest.fixture
def mock_cluster():
    """创建mock cluster对象"""
    return Cluster(
        id=1,
        name="test-cluster",
        hive_metastore_url="mysql://test:test@localhost:3306/hive",
        hdfs_namenode_url="hdfs://localhost:9000",
        hive_host="localhost",
        hive_port=10000,
    )


@pytest.fixture
def engine(mock_cluster):
    """创建SafeHiveMergeEngine实例"""
    engine = SafeHiveMergeEngine(mock_cluster)
    # Mock metadata_manager to avoid real connections
    engine.metadata_manager = MagicMock()
    return engine


class TestInitMergeResultDict:
    """测试_init_merge_result_dict方法"""

    def test_init_result_dict_structure(self, engine):
        """测试结果字典包含所有必需字段"""
        result = engine._init_merge_result_dict()

        # 验证所有必需字段存在
        assert "success" in result
        assert "files_before" in result
        assert "files_after" in result
        assert "size_saved" in result
        assert "duration" in result
        assert "message" in result
        assert "sql_executed" in result
        assert "temp_table_created" in result
        assert "backup_table_created" in result
        assert "log_summary" in result
        assert "detailed_logs" in result

    def test_init_result_dict_default_values(self, engine):
        """测试结果字典的默认值正确"""
        result = engine._init_merge_result_dict()

        assert result["success"] is False
        assert result["files_before"] == 0
        assert result["files_after"] == 0
        assert result["size_saved"] == 0
        assert result["duration"] == 0.0
        assert result["message"] == ""
        assert result["sql_executed"] == []
        assert result["temp_table_created"] == ""
        assert result["backup_table_created"] == ""
        assert result["log_summary"] == {}
        assert result["detailed_logs"] == []

    def test_init_result_dict_is_mutable(self, engine):
        """测试返回的字典是可修改的"""
        result = engine._init_merge_result_dict()
        result["success"] = True
        result["files_before"] = 100

        assert result["success"] is True
        assert result["files_before"] == 100


class TestDetermineTargetFormat:
    """测试_determine_target_format方法"""

    def test_use_task_target_format(self, engine):
        """测试使用任务指定的目标格式"""
        result = engine._determine_target_format("TEXTFILE", "PARQUET")
        assert result == "PARQUET"

    def test_use_original_format_when_no_target(self, engine):
        """测试无目标格式时使用原始格式"""
        result = engine._determine_target_format("ORC", None)
        assert result == "ORC"

    def test_default_to_textfile(self, engine):
        """测试两者都为None时默认使用TEXTFILE"""
        result = engine._determine_target_format(None, None)
        assert result == "TEXTFILE"

    def test_uppercase_conversion(self, engine):
        """测试格式会被转换为大写"""
        result = engine._determine_target_format("orc", "parquet")
        assert result == "PARQUET"

    def test_invalid_format_fallback_to_original(self, engine):
        """测试无效格式回退到原始格式"""
        result = engine._determine_target_format("ORC", "INVALID_FORMAT")
        assert result == "ORC"

    def test_invalid_format_fallback_to_textfile(self, engine):
        """测试无效格式且无原始格式时回退到TEXTFILE"""
        result = engine._determine_target_format(None, "INVALID_FORMAT")
        assert result == "TEXTFILE"

    def test_all_valid_formats(self, engine):
        """测试所有有效格式都被接受"""
        valid_formats = ["PARQUET", "ORC", "TEXTFILE", "RCFILE", "AVRO"]
        for fmt in valid_formats:
            result = engine._determine_target_format(None, fmt)
            assert result == fmt


class TestCalculateJobCompression:
    """测试_calculate_job_compression方法"""

    def test_keep_original_compression(self, engine):
        """测试KEEP偏好保留原始压缩"""
        result = engine._calculate_job_compression("GZIP", "KEEP")
        assert result == "GZIP"

    def test_keep_with_no_original(self, engine):
        """测试KEEP但无原始压缩时返回None"""
        result = engine._calculate_job_compression(None, "KEEP")
        assert result is None

    def test_use_specified_compression(self, engine):
        """测试使用指定的压缩设置"""
        result = engine._calculate_job_compression("GZIP", "SNAPPY")
        assert result == "SNAPPY"

    def test_default_to_snappy(self, engine):
        """测试无偏好且无原始压缩时默认SNAPPY"""
        result = engine._calculate_job_compression(None, None)
        assert result == "SNAPPY"

    def test_use_original_when_no_preference(self, engine):
        """测试无偏好时使用原始压缩"""
        result = engine._calculate_job_compression("GZIP", None)
        assert result == "GZIP"

    def test_empty_string_treated_as_none(self, engine):
        """测试空字符串被视为None"""
        result = engine._calculate_job_compression("", None)
        assert result == "SNAPPY"

    def test_default_keyword_treated_as_none(self, engine):
        """测试DEFAULT关键字被视为None"""
        result = engine._calculate_job_compression("DEFAULT", None)
        assert result == "SNAPPY"

    def test_uppercase_conversion(self, engine):
        """测试压缩设置被转换为大写"""
        result = engine._calculate_job_compression("gzip", None)
        assert result == "GZIP"

    def test_keep_overrides_specified_compression(self, engine):
        """测试KEEP偏好优先于指定压缩"""
        result = engine._calculate_job_compression("GZIP", "KEEP")
        assert result == "GZIP"
        # KEEP应该返回原始压缩,而不是任何其他值
        result2 = engine._calculate_job_compression("LZO", "KEEP")
        assert result2 == "LZO"


class TestNormalizeCompressionPreference:
    """测试_normalize_compression_preference方法 (Story 6.4新增)"""

    def test_normalize_none_input(self, engine):
        """测试None输入返回None"""
        result = engine._normalize_compression_preference(None)
        assert result is None

    def test_normalize_empty_string(self, engine):
        """测试空字符串返回None"""
        result = engine._normalize_compression_preference("")
        assert result is None

    def test_normalize_default_keyword(self, engine):
        """测试DEFAULT关键字返回None"""
        result = engine._normalize_compression_preference("DEFAULT")
        assert result is None

    def test_normalize_default_lowercase(self, engine):
        """测试default小写也返回None"""
        result = engine._normalize_compression_preference("default")
        assert result is None

    def test_normalize_snappy(self, engine):
        """测试SNAPPY被转换为大写"""
        result = engine._normalize_compression_preference("snappy")
        assert result == "SNAPPY"

    def test_normalize_gzip(self, engine):
        """测试GZIP被转换为大写"""
        result = engine._normalize_compression_preference("gzip")
        assert result == "GZIP"

    def test_normalize_keep(self, engine):
        """测试KEEP被保留"""
        result = engine._normalize_compression_preference("KEEP")
        assert result == "KEEP"

    def test_normalize_already_uppercase(self, engine):
        """测试已经大写的值保持不变"""
        result = engine._normalize_compression_preference("LZO")
        assert result == "LZO"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
