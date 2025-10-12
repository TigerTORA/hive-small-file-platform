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


class TestShouldUseDynamicPartitionMerge:
    """测试_should_use_dynamic_partition_merge方法 (Story 6.5新增)"""

    def test_should_use_when_no_filter_and_partitioned(self, engine):
        """测试无partition_filter且是分区表时返回True"""
        # Mock task对象
        task = MagicMock()
        task.partition_filter = None

        # Mock metadata_manager返回True (是分区表)
        engine.metadata_manager._is_partitioned_table = MagicMock(return_value=True)

        result = engine._should_use_dynamic_partition_merge(task, "test_db", "test_table")
        assert result is True

    def test_should_not_use_when_has_filter(self, engine):
        """测试有partition_filter时返回False"""
        task = MagicMock()
        task.partition_filter = "dt='2023-01-01'"

        # 即使是分区表也应返回False
        engine.metadata_manager._is_partitioned_table = MagicMock(return_value=True)

        result = engine._should_use_dynamic_partition_merge(task, "test_db", "test_table")
        assert result is False

    def test_should_not_use_when_not_partitioned(self, engine):
        """测试非分区表时返回False"""
        task = MagicMock()
        task.partition_filter = None

        # Mock metadata_manager返回False (非分区表)
        engine.metadata_manager._is_partitioned_table = MagicMock(return_value=False)

        result = engine._should_use_dynamic_partition_merge(task, "test_db", "test_table")
        assert result is False

    def test_should_not_use_when_both_conditions_fail(self, engine):
        """测试有filter且非分区表时返回False"""
        task = MagicMock()
        task.partition_filter = "dt='2023-01-01'"

        engine.metadata_manager._is_partitioned_table = MagicMock(return_value=False)

        result = engine._should_use_dynamic_partition_merge(task, "test_db", "test_table")
        assert result is False


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


class TestBuildShadowRootPath:
    """测试_build_shadow_root_path方法 (Story 6.7新增)"""

    def test_build_with_valid_parent(self, engine):
        """测试用有效父目录构建影子根路径"""
        result = engine._build_shadow_root_path(
            "hdfs://namenode/user/hive/warehouse/db.db"
        )
        assert result == "hdfs://namenode/user/hive/warehouse/db.db/.merge_shadow"

    def test_build_with_empty_parent(self, engine):
        """测试空父目录返回空字符串"""
        result = engine._build_shadow_root_path("")
        assert result == ""

    def test_build_with_trailing_slash(self, engine):
        """测试带尾部斜杠的父目录"""
        result = engine._build_shadow_root_path(
            "hdfs://namenode/user/hive/warehouse/db.db/"
        )
        assert result == "hdfs://namenode/user/hive/warehouse/db.db//.merge_shadow"

    def test_build_preserves_protocol(self, engine):
        """测试保留协议前缀"""
        result = engine._build_shadow_root_path(
            "webhdfs://namenode:50070/user/hive/warehouse"
        )
        assert result == "webhdfs://namenode:50070/user/hive/warehouse/.merge_shadow"

    def test_build_with_deep_path(self, engine):
        """测试深层路径"""
        result = engine._build_shadow_root_path("hdfs://nn/a/b/c/d/e/f")
        assert result == "hdfs://nn/a/b/c/d/e/f/.merge_shadow"


class TestExtractParentDirectory:
    """测试_extract_parent_directory方法 (Story 6.6新增)"""

    def test_extract_from_normal_path(self, engine):
        """测试从正常路径提取父目录"""
        result = engine._extract_parent_directory(
            "hdfs://namenode/user/hive/warehouse/db.db/table"
        )
        assert result == "hdfs://namenode/user/hive/warehouse/db.db"

    def test_extract_from_path_with_trailing_slash(self, engine):
        """测试从带尾部斜杠的路径提取父目录"""
        result = engine._extract_parent_directory(
            "hdfs://namenode/user/hive/warehouse/db.db/table/"
        )
        assert result == "hdfs://namenode/user/hive/warehouse/db.db"

    def test_extract_from_none(self, engine):
        """测试None输入返回空字符串"""
        result = engine._extract_parent_directory(None)
        assert result == ""

    def test_extract_from_empty_string(self, engine):
        """测试空字符串返回空字符串"""
        result = engine._extract_parent_directory("")
        assert result == ""

    def test_extract_from_root_path(self, engine):
        """测试根路径的父目录"""
        result = engine._extract_parent_directory("hdfs://namenode/user")
        assert result == "hdfs://namenode"

    def test_extract_from_single_level_path(self, engine):
        """测试单级路径"""
        result = engine._extract_parent_directory("hdfs://namenode")
        assert result == "hdfs:/"

    def test_extract_preserves_protocol(self, engine):
        """测试保留协议前缀"""
        result = engine._extract_parent_directory(
            "webhdfs://namenode:50070/user/hive/warehouse/table"
        )
        assert result == "webhdfs://namenode:50070/user/hive/warehouse"

    def test_extract_from_deep_path(self, engine):
        """测试深层路径"""
        result = engine._extract_parent_directory(
            "hdfs://nn/a/b/c/d/e/f/table"
        )
        assert result == "hdfs://nn/a/b/c/d/e/f"

    def test_extract_multiple_trailing_slashes(self, engine):
        """测试多个尾部斜杠"""
        result = engine._extract_parent_directory(
            "hdfs://namenode/user/hive/warehouse/table///"
        )
        assert result == "hdfs://namenode/user/hive/warehouse"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
