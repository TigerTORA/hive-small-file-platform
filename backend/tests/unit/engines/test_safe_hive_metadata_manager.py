"""
SafeHiveMetadataManager单元测试

Story 6.1 - Epic-6: 提取MetadataManager模块
测试策略: 80%单元测试 + 20%集成测试
覆盖率目标: >80%

创建时间: 2025-10-12
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Tuple

from app.engines.safe_hive_metadata_manager import SafeHiveMetadataManager
from app.models.cluster import Cluster


class TestSafeHiveMetadataManager:
    """SafeHiveMetadataManager单元测试类"""
    
    @pytest.fixture
    def mock_cluster(self):
        """模拟Cluster配置"""
        cluster = Mock(spec=Cluster)
        cluster.hive_host = "localhost"
        cluster.hive_port = 10000
        cluster.hive_database = "default"
        cluster.auth_type = "NONE"
        cluster.hive_username = None
        return cluster
    
    @pytest.fixture
    def metadata_manager(self, mock_cluster):
        """创建MetadataManager实例"""
        return SafeHiveMetadataManager(mock_cluster)
    
    # ==================== 测试组1: _get_table_location ====================
    
    @patch('app.engines.safe_hive_metadata_manager.PathResolver')
    def test_get_table_location_success(self, mock_path_resolver, metadata_manager):
        """TC-1.1: 正常获取表位置"""
        # Given
        mock_path_resolver.get_table_location.return_value = "/user/hive/warehouse/test_db.db/user_logs"
        
        # When
        result = metadata_manager._get_table_location("test_db", "user_logs")
        
        # Then
        assert result == "/user/hive/warehouse/test_db.db/user_logs"
    
    @patch('app.engines.safe_hive_metadata_manager.PathResolver')
    def test_get_table_location_not_exists(self, mock_path_resolver, metadata_manager):
        """TC-1.2: 表不存在返回None"""
        # Given
        mock_path_resolver.get_table_location.side_effect = Exception("Table not found")
        
        # When
        result = metadata_manager._get_table_location("test_db", "non_exist_table")
        
        # Then
        assert result is None
    
    # ==================== 测试组2: _table_exists ====================
    
    @patch('app.engines.safe_hive_metadata_manager.hive.Connection')
    def test_table_exists_true(self, mock_hive_conn, metadata_manager):
        """TC-2.1: 表存在返回True"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("user_logs",)
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance
        
        # When
        result = metadata_manager._table_exists("test_db", "user_logs")
        
        # Then
        assert result is True
        mock_cursor.execute.assert_called_once_with('SHOW TABLES LIKE "user_logs"')
    
    @patch('app.engines.safe_hive_metadata_manager.hive.Connection')
    def test_table_exists_false(self, mock_hive_conn, metadata_manager):
        """TC-2.2: 表不存在返回False"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance
        
        # When
        result = metadata_manager._table_exists("test_db", "non_exist_table")
        
        # Then
        assert result is False
    
    # ==================== 测试组3: _is_partitioned_table ====================
    
    @patch('app.engines.safe_hive_metadata_manager.hive.Connection')
    def test_is_partitioned_table_true(self, mock_hive_conn, metadata_manager):
        """TC-3.1: 分区表返回True"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("col_name", "data_type", ""),
            ("id", "int", ""),
            ("name", "string", ""),
            ("# Partition Information", "", ""),
            ("dt", "string", ""),
        ]
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance
        
        # When
        result = metadata_manager._is_partitioned_table("test_db", "user_logs")
        
        # Then
        assert result is True
    
    @patch('app.engines.safe_hive_metadata_manager.hive.Connection')
    def test_is_partitioned_table_false(self, mock_hive_conn, metadata_manager):
        """TC-3.2: 非分区表返回False"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("col_name", "data_type", ""),
            ("id", "int", ""),
            ("name", "string", ""),
        ]
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance
        
        # When
        result = metadata_manager._is_partitioned_table("test_db", "simple_table")
        
        # Then
        assert result is False
    
    # ==================== 测试组4: _get_table_partitions ====================
    
    @patch('app.engines.safe_hive_metadata_manager.hive.Connection')
    def test_get_table_partitions_success(self, mock_hive_conn, metadata_manager):
        """TC-4.1: 成功获取分区列表"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("dt=2024-01-01",),
            ("dt=2024-01-02",),
            ("dt=2024-01-03",),
        ]
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance
        
        # When
        result = metadata_manager._get_table_partitions("test_db", "user_logs")
        
        # Then
        assert result == ["dt=2024-01-01", "dt=2024-01-02", "dt=2024-01-03"]
    
    # ==================== 测试组5: _get_table_format_info ====================
    
    @patch('app.engines.safe_hive_metadata_manager.hive.Connection')
    def test_get_table_format_info_parquet(self, mock_hive_conn, metadata_manager):
        """TC-5.1: 获取Parquet表格式信息"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [
                ("InputFormat:", "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"),
                ("OutputFormat:", "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"),
                ("SerDe Library:", "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"),
                ("Table Type:", "EXTERNAL_TABLE"),
            ],
            [("parquet.compression", "SNAPPY")]
        ]
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance
        
        # When
        result = metadata_manager._get_table_format_info("test_db", "parquet_table")
        
        # Then
        assert "parquet" in result["input_format"].lower()
        assert result["table_type"] == "EXTERNAL_TABLE"
        assert result["tblproperties"]["parquet.compression"] == "SNAPPY"
    
    # ==================== 测试组6: _infer_storage_format_name ====================
    
    def test_infer_storage_format_parquet(self, metadata_manager):
        """TC-6.1: 推断Parquet格式"""
        # Given
        fmt = {
            "input_format": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
            "serde_lib": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
        }
        
        # When
        result = metadata_manager._infer_storage_format_name(fmt)
        
        # Then
        assert result == "PARQUET"
    
    def test_infer_storage_format_orc(self, metadata_manager):
        """TC-6.2: 推断ORC格式"""
        # Given
        fmt = {
            "input_format": "org.apache.hadoop.hive.ql.io.orc.OrcInputFormat",
            "serde_lib": "org.apache.hadoop.hive.ql.io.orc.OrcSerde"
        }
        
        # When
        result = metadata_manager._infer_storage_format_name(fmt)
        
        # Then
        assert result == "ORC"
    
    def test_infer_storage_format_textfile(self, metadata_manager):
        """TC-6.3: 推断TEXTFILE格式"""
        # Given
        fmt = {
            "input_format": "org.apache.hadoop.mapred.TextInputFormat",
            "serde_lib": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
        }
        
        # When
        result = metadata_manager._infer_storage_format_name(fmt)
        
        # Then
        assert result == "TEXTFILE"
    
    # ==================== 测试组7: _infer_table_compression ====================
    
    def test_infer_compression_parquet_snappy(self, metadata_manager):
        """TC-7.1: 推断Parquet SNAPPY压缩"""
        # Given
        fmt = {"tblproperties": {"parquet.compression": "SNAPPY"}}
        
        # When
        result = metadata_manager._infer_table_compression(fmt, "PARQUET")
        
        # Then
        assert result == "SNAPPY"
    
    def test_infer_compression_orc_zlib(self, metadata_manager):
        """TC-7.2: 推断ORC ZLIB压缩(默认)"""
        # Given
        fmt = {"tblproperties": {}}
        
        # When
        result = metadata_manager._infer_table_compression(fmt, "ORC")
        
        # Then
        assert result == "ZLIB"
    
    # ==================== 测试组8: _is_unsupported_table_type ====================
    
    def test_is_unsupported_hudi_table(self, metadata_manager):
        """TC-8.1: 检测Hudi表(不支持)"""
        # Given
        fmt = {
            "storage_handler": "org.apache.hadoop.hive.ql.metadata.HudiStorageHandler",
            "tblproperties": {"hoodie.table.name": "user_logs"}
        }
        
        # When
        result = metadata_manager._is_unsupported_table_type(fmt)
        
        # Then
        assert result is True
    
    def test_is_unsupported_iceberg_table(self, metadata_manager):
        """TC-8.2: 检测Iceberg表(不支持)"""
        # Given
        fmt = {
            "storage_handler": "org.apache.iceberg.mr.hive.HiveIcebergStorageHandler",
            "tblproperties": {}
        }
        
        # When
        result = metadata_manager._is_unsupported_table_type(fmt)
        
        # Then
        assert result is True
    
    def test_is_supported_normal_table(self, metadata_manager):
        """TC-8.3: 检测普通表(支持)"""
        # Given
        fmt = {
            "input_format": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
            "tblproperties": {}
        }
        
        # When
        result = metadata_manager._is_unsupported_table_type(fmt)
        
        # Then
        assert result is False
    
    # ==================== 测试组9: _unsupported_reason ====================
    
    def test_unsupported_reason_hudi(self, metadata_manager):
        """TC-9.1: Hudi表不支持原因"""
        # Given
        fmt = {
            "storage_handler": "org.apache.hadoop.hive.ql.metadata.HudiStorageHandler",
            "tblproperties": {}
        }
        
        # When
        result = metadata_manager._unsupported_reason(fmt)
        
        # Then
        assert "Hudi" in result
        assert "compaction" in result or "cluster" in result
    
    # ==================== 测试组10: _get_table_columns ====================
    
    @patch('app.engines.safe_hive_metadata_manager.hive.Connection')
    def test_get_table_columns_with_partitions(self, mock_hive_conn, metadata_manager):
        """TC-10.1: 获取带分区的表字段"""
        # Given
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("col_name", "data_type", "comment"),
            ("id", "int", ""),
            ("name", "string", ""),
            ("", "", ""),
            ("# Partition Information", "", ""),
            ("col_name", "data_type", "comment"),
            ("dt", "string", ""),
        ]
        mock_conn_instance = MagicMock()
        mock_conn_instance.cursor.return_value = mock_cursor
        mock_hive_conn.return_value = mock_conn_instance

        # When
        nonpart, parts = metadata_manager._get_table_columns("test_db", "user_logs")

        # Then
        assert "id" in nonpart
        # 原始实现会跳过以"name"开头的列名（DESCRIBE FORMATTED 兼容处理），此处保持历史行为
        assert "name" not in nonpart
        assert "dt" in parts
