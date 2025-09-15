"""
表扫描服务核心业务逻辑单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.monitor.table_scanner import TableScanner
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric


class TestTableScanner:
    """表扫描器单元测试"""

    def setup_method(self):
        """测试前准备"""
        self.cluster = Cluster(
            id=1,
            name="test-cluster",
            hive_metastore_url="mysql://test:test@localhost:3306/hive",
            hdfs_namenode_url="hdfs://localhost:9000",
            connection_type="mysql"
        )
        self.mock_db = Mock()
        self.scanner = TableScanner(self.cluster, self.mock_db)

    @pytest.mark.unit
    def test_calculate_small_file_ratio(self):
        """测试小文件比例计算"""
        # 测试正常情况
        assert self.scanner._calculate_small_file_ratio(50, 100) == 0.5

        # 测试边界情况
        assert self.scanner._calculate_small_file_ratio(0, 100) == 0.0
        assert self.scanner._calculate_small_file_ratio(100, 100) == 1.0
        assert self.scanner._calculate_small_file_ratio(10, 0) == 0.0

    @pytest.mark.unit
    def test_determine_merge_strategy(self):
        """测试合并策略确定逻辑"""
        # 小表建议CONCATENATE
        strategy = self.scanner._determine_merge_strategy(
            file_count=20,
            small_file_count=15,
            table_size=1024*1024*10  # 10MB
        )
        assert strategy == "CONCATENATE"

        # 大表建议INSERT_OVERWRITE
        strategy = self.scanner._determine_merge_strategy(
            file_count=1000,
            small_file_count=800,
            table_size=1024*1024*1024*5  # 5GB
        )
        assert strategy == "INSERT_OVERWRITE"

    @pytest.mark.unit
    @patch('app.monitor.table_scanner.TableScanner._get_hive_connector')
    @patch('app.monitor.table_scanner.TableScanner._get_hdfs_scanner')
    def test_scan_single_table_success(self, mock_hdfs_scanner, mock_hive_connector):
        """测试单表扫描成功流程"""
        # Mock连接器
        mock_hive = Mock()
        mock_hdfs = Mock()
        mock_hive_connector.return_value = mock_hive
        mock_hdfs_scanner.return_value = mock_hdfs

        # Mock返回数据
        mock_hive.get_table_partitions.return_value = [
            {'partition': 'dt=2023-01-01', 'location': '/data/table/dt=2023-01-01'}
        ]
        mock_hdfs.scan_directory.return_value = {
            'total_files': 100,
            'small_files': 80,
            'total_size': 1024*1024*100,  # 100MB
            'avg_file_size': 1024*1024
        }

        # 执行扫描
        result = self.scanner.scan_single_table("test_db", "test_table")

        # 验证结果
        assert result is not None
        assert result.database_name == "test_db"
        assert result.table_name == "test_table"
        assert result.total_files == 100
        assert result.small_files == 80
        assert result.small_file_ratio == 0.8

    @pytest.mark.unit
    def test_scan_single_table_connection_failure(self):
        """测试连接失败情况"""
        with patch('app.monitor.table_scanner.TableScanner._get_hive_connector') as mock_hive:
            mock_hive.side_effect = Exception("Connection failed")

            result = self.scanner.scan_single_table("test_db", "test_table")
            assert result is None

    @pytest.mark.unit
    def test_calculate_priority_score(self):
        """测试优先级评分计算"""
        # 高优先级：小文件多且占用空间大
        score = self.scanner._calculate_priority_score(
            small_file_count=1000,
            total_size=1024*1024*1024,  # 1GB
            small_file_ratio=0.9,
            last_scan_days=30
        )
        assert score > 80

        # 低优先级：小文件少
        score = self.scanner._calculate_priority_score(
            small_file_count=10,
            total_size=1024*1024*100,  # 100MB
            small_file_ratio=0.1,
            last_scan_days=1
        )
        assert score < 30

    @pytest.mark.unit
    @patch('app.monitor.table_scanner.datetime')
    def test_save_scan_results(self, mock_datetime):
        """测试扫描结果保存"""
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

        # 创建测试指标
        metric = TableMetric(
            cluster_id=1,
            database_name="test_db",
            table_name="test_table",
            total_files=100,
            small_files=80,
            total_size=1024*1024*100,
            scan_time=datetime.now()
        )

        # 执行保存
        self.scanner._save_scan_results(metric)

        # 验证数据库操作
        self.mock_db.merge.assert_called_once_with(metric)
        self.mock_db.commit.assert_called_once()


class TestTableScannerIntegration:
    """表扫描器集成测试"""

    @pytest.mark.integration
    @patch('app.monitor.table_scanner.TableScanner._get_hive_connector')
    @patch('app.monitor.table_scanner.TableScanner._get_hdfs_scanner')
    def test_full_database_scan(self, mock_hdfs_scanner, mock_hive_connector):
        """测试完整数据库扫描流程"""
        cluster = Cluster(
            id=1,
            name="test-cluster",
            hive_metastore_url="mysql://test:test@localhost:3306/hive",
            hdfs_namenode_url="hdfs://localhost:9000"
        )

        mock_db = Mock()
        scanner = TableScanner(cluster, mock_db)

        # Mock连接器返回
        mock_hive = Mock()
        mock_hdfs = Mock()
        mock_hive_connector.return_value = mock_hive
        mock_hdfs_scanner.return_value = mock_hdfs

        # Mock数据库中的表
        mock_hive.get_tables.return_value = [
            "table1", "table2", "table3"
        ]

        # Mock每个表的分区和文件信息
        mock_hive.get_table_partitions.return_value = [
            {'partition': 'dt=2023-01-01', 'location': '/data/table/dt=2023-01-01'}
        ]
        mock_hdfs.scan_directory.return_value = {
            'total_files': 50,
            'small_files': 40,
            'total_size': 1024*1024*50,
            'avg_file_size': 1024*1024
        }

        # 执行扫描
        results = scanner.scan_database("test_db", max_tables=3)

        # 验证结果
        assert len(results) == 3
        assert all(result.database_name == "test_db" for result in results)
        assert {result.table_name for result in results} == {"table1", "table2", "table3"}

        # 验证数据库保存操作
        assert mock_db.merge.call_count == 3
        assert mock_db.commit.call_count == 3