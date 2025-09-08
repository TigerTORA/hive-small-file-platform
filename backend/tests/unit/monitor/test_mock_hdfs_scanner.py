"""
Unit tests for MockHDFSScanner
"""
import pytest
from unittest.mock import Mock, patch

from app.monitor.mock_hdfs_scanner import MockHDFSScanner


class TestMockHDFSScanner:
    """Test cases for Mock HDFS Scanner"""
    
    def setup_method(self):
        """Setup test data"""
        self.hdfs_url = "hdfs://localhost:9000"
        self.scanner = MockHDFSScanner(self.hdfs_url)
    
    @pytest.mark.unit
    def test_init(self):
        """Test scanner initialization"""
        assert self.scanner.namenode_url == self.hdfs_url
        assert self.scanner.user == "hdfs"
        assert self.scanner._connected is False
    
    @pytest.mark.unit
    def test_init_with_custom_user(self):
        """Test scanner initialization with custom user"""
        scanner = MockHDFSScanner(self.hdfs_url, user="testuser")
        assert scanner.namenode_url == self.hdfs_url
        assert scanner.user == "testuser"
        assert scanner._connected is False
    
    @pytest.mark.unit
    def test_connect_success(self):
        """Test successful connection"""
        result = self.scanner.connect()
        
        assert result is True
        assert self.scanner._connected is True
    
    @pytest.mark.unit
    def test_disconnect(self):
        """Test disconnection"""
        # First connect
        self.scanner.connect()
        assert self.scanner._connected is True
        
        # Then disconnect
        self.scanner.disconnect()
        assert self.scanner._connected is False
    
    @pytest.mark.unit
    def test_test_connection_success(self):
        """Test connection test when successful"""
        result = self.scanner.test_connection()
        
        assert result['status'] == 'success'
        assert result['namenode'] == self.hdfs_url
        assert result['user'] == 'hdfs'
        assert result['connected'] is True
    
    @pytest.mark.unit
    @patch.object(MockHDFSScanner, 'connect')
    def test_test_connection_failure(self, mock_connect):
        """Test connection test when connection fails"""
        mock_connect.return_value = False
        
        result = self.scanner.test_connection()
        
        assert result['status'] == 'error'
        assert 'Failed to connect' in result['message']
        assert result['connected'] is False
    
    @pytest.mark.unit
    def test_scan_table_partitions_not_connected(self):
        """Test scanning when not connected raises error"""
        partitions = []
        small_file_threshold = 134217728
        
        with pytest.raises(ConnectionError, match="Not connected to HDFS"):
            self.scanner.scan_table_partitions("/test/path", partitions, small_file_threshold)
    
    @pytest.mark.unit
    def test_scan_table_partitions_connected(self):
        """Test scanning table partitions when connected"""
        # Connect first
        self.scanner.connect()
        
        partitions = []
        small_file_threshold = 134217728
        table_path = "/warehouse/test.db/test_table"
        
        table_stats, partition_stats = self.scanner.scan_table_partitions(
            table_path, partitions, small_file_threshold
        )
        
        # Verify table stats structure
        assert isinstance(table_stats, dict)
        assert 'total_files' in table_stats
        assert 'small_files' in table_stats
        assert 'total_size' in table_stats
        assert 'avg_file_size' in table_stats
        assert 'scan_duration' in table_stats
        
        # Verify data consistency
        assert table_stats['total_files'] > 0
        assert table_stats['small_files'] <= table_stats['total_files']
        assert table_stats['total_size'] > 0
        
        # Verify partition stats structure
        assert isinstance(partition_stats, list)
        assert len(partition_stats) == 1  # Non-partitioned table should have 1 default partition
        
        partition = partition_stats[0]
        assert partition['partition_name'] == 'default'
        assert partition['partition_path'] == table_path
        assert partition['file_count'] == table_stats['total_files']
        assert partition['small_file_count'] == table_stats['small_files']
    
    @pytest.mark.unit
    def test_scan_table_partitions_with_partitions(self):
        """Test scanning partitioned table"""
        # Connect first
        self.scanner.connect()
        
        partitions = [
            {
                'partition_name': 'year=2024/month=01',
                'partition_path': '/warehouse/test.db/table/year=2024/month=01'
            },
            {
                'partition_name': 'year=2024/month=02', 
                'partition_path': '/warehouse/test.db/table/year=2024/month=02'
            }
        ]
        small_file_threshold = 134217728
        table_path = "/warehouse/test.db/partitioned_table"
        
        table_stats, partition_stats = self.scanner.scan_table_partitions(
            table_path, partitions, small_file_threshold
        )
        
        # Should have stats for each partition
        assert len(partition_stats) == len(partitions)
        
        # Verify each partition has required fields
        for i, partition_stat in enumerate(partition_stats):
            assert partition_stat['partition_name'] == partitions[i]['partition_name']
            assert partition_stat['partition_path'] == partitions[i]['partition_path']
            assert 'file_count' in partition_stat
            assert 'small_file_count' in partition_stat
            assert 'total_size' in partition_stat
            assert 'avg_file_size' in partition_stat
            
            # Data consistency checks
            assert partition_stat['small_file_count'] <= partition_stat['file_count']
            assert partition_stat['total_size'] >= 0
    
    @pytest.mark.unit
    def test_get_directory_stats_not_connected(self):
        """Test get_directory_stats when not connected"""
        with pytest.raises(ConnectionError, match="Not connected to HDFS"):
            self.scanner.get_directory_stats("/test/path")
    
    @pytest.mark.unit
    def test_get_directory_stats_connected(self):
        """Test get_directory_stats when connected"""
        # Connect first
        self.scanner.connect()
        
        test_path = "/warehouse/test_directory"
        result = self.scanner.get_directory_stats(test_path)
        
        # Verify structure
        assert isinstance(result, dict)
        assert result['path'] == test_path
        assert 'file_count' in result
        assert 'total_size' in result
        assert 'avg_file_size' in result
        assert 'directories' in result
        assert 'last_modified' in result
        
        # Verify data types and consistency
        assert isinstance(result['file_count'], int)
        assert isinstance(result['total_size'], int)
        assert isinstance(result['avg_file_size'], (int, float))
        assert isinstance(result['directories'], int)
        assert isinstance(result['last_modified'], (int, float))
        
        assert result['file_count'] >= 0
        assert result['total_size'] >= 0
        assert result['directories'] >= 0
    
    @pytest.mark.unit
    def test_mock_randomization(self):
        """Test that mock data is randomized between calls"""
        # Connect first
        self.scanner.connect()
        
        partitions = []
        small_file_threshold = 134217728
        table_path = "/warehouse/test.db/test_table"
        
        # Get multiple samples
        results = []
        for _ in range(5):
            table_stats, _ = self.scanner.scan_table_partitions(
                table_path, partitions, small_file_threshold
            )
            results.append(table_stats['total_files'])
        
        # Should have some variation in results (mock uses random)
        # At least one result should be different from the first
        unique_values = set(results)
        assert len(unique_values) > 1 or len(results) == 1  # Allow for small chance all are same
    
    @pytest.mark.unit
    def test_avg_file_size_calculation(self):
        """Test average file size calculation consistency"""
        # Connect first
        self.scanner.connect()
        
        partitions = []
        small_file_threshold = 134217728
        table_path = "/warehouse/test.db/test_table"
        
        table_stats, _ = self.scanner.scan_table_partitions(
            table_path, partitions, small_file_threshold
        )
        
        # Average file size should be total_size / total_files
        if table_stats['total_files'] > 0:
            expected_avg = table_stats['total_size'] / table_stats['total_files']
            assert abs(table_stats['avg_file_size'] - expected_avg) < 1.0  # Allow for small rounding differences
        else:
            assert table_stats['avg_file_size'] == 0
    
    @pytest.mark.unit
    def test_connection_state_management(self):
        """Test connection state is properly managed"""
        # Initial state
        assert self.scanner._connected is False
        
        # After connect
        self.scanner.connect()
        assert self.scanner._connected is True
        
        # After disconnect
        self.scanner.disconnect()
        assert self.scanner._connected is False
        
        # Multiple connects should work
        self.scanner.connect()
        self.scanner.connect()
        assert self.scanner._connected is True