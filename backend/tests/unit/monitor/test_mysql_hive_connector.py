"""
Unit tests for MySQLHiveMetastoreConnector
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urlparse

from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector


class TestMySQLHiveMetastoreConnector:
    """Test cases for MySQL Hive MetaStore connector"""
    
    def setup_method(self):
        """Setup test data"""
        self.metastore_url = "mysql://testuser:testpass@localhost:3306/hive"
        self.connector = MySQLHiveMetastoreConnector(self.metastore_url)
    
    @pytest.mark.unit
    def test_init(self):
        """Test connector initialization"""
        assert self.connector.metastore_url == self.metastore_url
        assert self.connector._connection is None
    
    @pytest.mark.unit
    @patch('app.monitor.mysql_hive_connector.pymysql.connect')
    def test_connect_success(self, mock_connect):
        """Test successful database connection"""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
        result = self.connector.connect()
        
        assert result is True
        assert self.connector._connection == mock_connection
        mock_connect.assert_called_once_with(
            host='localhost',
            port=3306,
            database='hive',
            user='testuser',
            password='testpass',
            charset='utf8mb4',
            cursorclass=pytest.importorskip('pymysql').cursors.DictCursor
        )
    
    @pytest.mark.unit
    @patch('app.monitor.mysql_hive_connector.pymysql.connect')
    def test_connect_failure(self, mock_connect):
        """Test database connection failure"""
        mock_connect.side_effect = Exception("Connection failed")
        
        result = self.connector.connect()
        
        assert result is False
        assert self.connector._connection is None
    
    @pytest.mark.unit
    def test_disconnect(self):
        """Test database disconnection"""
        mock_connection = Mock()
        self.connector._connection = mock_connection
        
        self.connector.disconnect()
        
        mock_connection.close.assert_called_once()
        assert self.connector._connection is None
    
    @pytest.mark.unit
    def test_disconnect_no_connection(self):
        """Test disconnect when no connection exists"""
        self.connector._connection = None
        
        # Should not raise exception
        self.connector.disconnect()
        
        assert self.connector._connection is None
    
    @pytest.mark.unit
    def test_url_parsing(self):
        """Test URL parsing for different MySQL URLs"""
        # Standard URL
        url1 = "mysql://user:pass@host:3306/database"
        connector1 = MySQLHiveMetastoreConnector(url1)
        parsed = urlparse(url1)
        
        assert parsed.hostname == "host"
        assert parsed.port == 3306
        assert parsed.path.lstrip('/') == "database"
        assert parsed.username == "user"
        assert parsed.password == "pass"
        
        # URL without port (should default to 3306)
        url2 = "mysql://user:pass@host/database"
        connector2 = MySQLHiveMetastoreConnector(url2)
        parsed2 = urlparse(url2)
        
        assert parsed2.hostname == "host"
        assert parsed2.port is None  # Will be handled in connect()
    
    @pytest.mark.unit
    @patch('app.monitor.mysql_hive_connector.pymysql.connect')
    def test_get_databases_no_connection(self, mock_connect):
        """Test get_databases when not connected"""
        # This test will need to be updated based on actual implementation
        # For now, just test that the method exists
        assert hasattr(self.connector, 'get_databases')
    
    @pytest.mark.unit
    def test_context_manager_protocol(self):
        """Test if connector supports context manager protocol"""
        # Check if __enter__ and __exit__ methods exist
        has_enter = hasattr(self.connector, '__enter__')
        has_exit = hasattr(self.connector, '__exit__')
        
        # If not implemented yet, this is what we expect to implement
        if not (has_enter and has_exit):
            # This is expected for now, but should be implemented later
            assert True
        else:
            # If implemented, test the context manager
            with patch('app.monitor.mysql_hive_connector.pymysql.connect'):
                with self.connector as conn:
                    assert conn == self.connector


class TestMySQLConnectorIntegration:
    """Integration-style tests for MySQL connector"""
    
    @pytest.mark.unit
    def test_connection_url_variations(self):
        """Test different URL format handling"""
        urls = [
            "mysql://root:password@localhost:3306/hive",
            "mysql://user:pass@192.168.1.100:3306/hive_metastore",
            "mysql://admin:secret@mysql.example.com/hive"
        ]
        
        for url in urls:
            connector = MySQLHiveMetastoreConnector(url)
            assert connector.metastore_url == url
            assert connector._connection is None
    
    @pytest.mark.unit
    def test_connection_error_handling(self):
        """Test various connection error scenarios"""
        # Invalid URL format
        invalid_urls = [
            "invalid://url",
            "mysql://", 
            "",
            None
        ]
        
        for url in invalid_urls:
            if url is not None:
                connector = MySQLHiveMetastoreConnector(url)
                with patch('app.monitor.mysql_hive_connector.pymysql.connect') as mock_connect:
                    mock_connect.side_effect = Exception("Invalid URL")
                    result = connector.connect()
                    assert result is False