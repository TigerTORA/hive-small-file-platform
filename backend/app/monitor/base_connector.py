import logging
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class BaseMetastoreConnector(ABC):
    """
    Hive MetaStore连接器基类
    抽取公共逻辑，避免代码重复
    """
    
    def __init__(self, metastore_url: str):
        self.metastore_url = metastore_url
        self._connection = None
        self.parsed_url = urlparse(metastore_url)
    
    @abstractmethod
    def _create_connection(self) -> Any:
        """子类实现具体的连接创建逻辑"""
        pass
    
    @abstractmethod
    def _execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """子类实现具体的查询执行逻辑"""
        pass
    
    def connect(self) -> bool:
        """建立数据库连接"""
        try:
            self._connection = self._create_connection()
            logger.info(f"Connected to {self.__class__.__name__}: {self.parsed_url.hostname}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MetaStore: {e}")
            return False
    
    def disconnect(self):
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def get_databases(self) -> List[str]:
        """获取所有数据库名称"""
        if not self._connection:
            raise ConnectionError("Not connected to MetaStore")
        
        try:
            results = self._execute_query("SELECT NAME FROM DBS ORDER BY NAME")
            return [row['NAME'] if isinstance(row, dict) else row[0] for row in results]
        except Exception as e:
            logger.error(f"Failed to get databases: {e}")
            return []
    
    def test_connection(self) -> Dict[str, any]:
        """测试连接并返回基本信息"""
        if not self.connect():
            return {'status': 'error', 'message': 'Failed to connect'}
        
        try:
            databases = self.get_databases()
            
            # 获取基本的MetaStore信息
            table_count_results = self._execute_query("SELECT COUNT(*) as table_count FROM TBLS")
            table_count = table_count_results[0]['table_count'] if isinstance(table_count_results[0], dict) else table_count_results[0][0]
            
            db_count_results = self._execute_query("SELECT COUNT(*) as db_count FROM DBS")
            db_count = db_count_results[0]['db_count'] if isinstance(db_count_results[0], dict) else db_count_results[0][0]
            
            return {
                'status': 'success',
                'database_count': len(databases),
                'total_databases': db_count,
                'total_tables': table_count,
                'sample_databases': databases[:5]
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            self.disconnect()
    
    def __enter__(self):
        """Context manager entry"""
        if not self.connect():
            raise ConnectionError("Failed to connect to MetaStore")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
    
    def _extract_storage_format(self, input_format: str) -> str:
        """
        从INPUT_FORMAT中提取存储格式
        Args:
            input_format: Hive输入格式类名
        Returns:
            简化的存储格式名称
        """
        if not input_format:
            return 'UNKNOWN'
        
        format_mapping = {
            'parquet': 'PARQUET',
            'orc': 'ORC', 
            'avro': 'AVRO',
            'text': 'TEXT',
            'sequence': 'SEQUENCE',
            'rcfile': 'RCFILE'
        }
        
        input_format_lower = input_format.lower()
        for key, value in format_mapping.items():
            if key in input_format_lower:
                return value
        
        return 'OTHER'