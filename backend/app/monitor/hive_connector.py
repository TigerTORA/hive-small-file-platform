import logging
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from .base_connector import BaseMetastoreConnector

logger = logging.getLogger(__name__)

class HiveMetastoreConnector(BaseMetastoreConnector):
    """
    直接连接 Hive MetaStore 数据库获取表信息
    避免通过 Hive SQL 查询的开销
    """
    
    def __init__(self, metastore_url: str):
        """
        初始化 MetaStore 连接
        Args:
            metastore_url: PostgreSQL connection URL, e.g., postgresql://user:pass@host:5432/hive_metastore
        """
        super().__init__(metastore_url)
    
    def _create_connection(self):
        """创建PostgreSQL连接"""
        return psycopg2.connect(
            host=self.parsed_url.hostname,
            port=self.parsed_url.port or 5432,
            database=self.parsed_url.path.lstrip('/'),
            user=self.parsed_url.username,
            password=self.parsed_url.password,
            cursor_factory=RealDictCursor
        )
    
    def _execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """执行查询"""
        with self._connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()
    
    def get_databases(self) -> List[str]:
        """获取所有数据库名称"""
        if not self._connection:
            raise ConnectionError("Not connected to MetaStore")
        
        try:
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT NAME FROM DBS ORDER BY NAME")
                return [row['name'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get databases: {e}")
            return []
    
    def get_tables(self, database_name: str) -> List[Dict]:
        """
        获取指定数据库中的所有表信息
        Args:
            database_name: 数据库名称
        Returns:
            包含表信息的字典列表
        """
        if not self._connection:
            raise ConnectionError("Not connected to MetaStore")
        
        try:
            with self._connection.cursor() as cursor:
                # 获取表基本信息和存储路径
                query = """
                SELECT 
                    t.TBL_NAME,
                    s.LOCATION as table_path,
                    t.TBL_TYPE,
                    COUNT(p.PART_ID) as partition_count
                FROM TBLS t 
                JOIN SDS s ON t.SD_ID = s.SD_ID 
                JOIN DBS d ON t.DB_ID = d.DB_ID
                LEFT JOIN PARTITIONS p ON p.TBL_ID = t.TBL_ID
                WHERE d.NAME = %s
                GROUP BY t.TBL_NAME, s.LOCATION, t.TBL_TYPE
                ORDER BY t.TBL_NAME
                """
                cursor.execute(query, (database_name,))
                
                tables = []
                for row in cursor.fetchall():
                    tables.append({
                        'table_name': row['tbl_name'],
                        'table_path': row['table_path'],
                        'table_type': row['tbl_type'],
                        'is_partitioned': row['partition_count'] > 0,
                        'partition_count': row['partition_count'] or 0
                    })
                
                return tables
        except Exception as e:
            logger.error(f"Failed to get tables for database {database_name}: {e}")
            return []
    
    def get_table_partitions(self, database_name: str, table_name: str) -> List[Dict]:
        """
        获取表的所有分区信息
        Args:
            database_name: 数据库名称
            table_name: 表名称
        Returns:
            包含分区信息的字典列表
        """
        if not self._connection:
            raise ConnectionError("Not connected to MetaStore")
        
        try:
            with self._connection.cursor() as cursor:
                query = """
                SELECT 
                    p.PART_NAME,
                    s.LOCATION as partition_path
                FROM PARTITIONS p
                JOIN SDS s ON p.SD_ID = s.SD_ID
                JOIN TBLS t ON p.TBL_ID = t.TBL_ID
                JOIN DBS d ON t.DB_ID = d.DB_ID
                WHERE d.NAME = %s AND t.TBL_NAME = %s
                ORDER BY p.PART_NAME
                """
                cursor.execute(query, (database_name, table_name))
                
                partitions = []
                for row in cursor.fetchall():
                    partitions.append({
                        'partition_name': row['part_name'],
                        'partition_path': row['partition_path']
                    })
                
                return partitions
        except Exception as e:
            logger.error(f"Failed to get partitions for table {database_name}.{table_name}: {e}")
            return []

    def get_table_location(self, database_name: str, table_name: str) -> Optional[str]:
        """获取单表的 LOCATION（PostgreSQL MetaStore）"""
        if not self._connection:
            raise ConnectionError("Not connected to MetaStore")
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT s.LOCATION as table_path
                    FROM TBLS t
                    JOIN DBS d ON t.DB_ID = d.DB_ID
                    JOIN SDS s ON t.SD_ID = s.SD_ID
                    WHERE d.NAME = %s AND t.TBL_NAME = %s
                    LIMIT 1
                    """,
                    (database_name, table_name),
                )
                row = cursor.fetchone()
                return row['table_path'] if row and row.get('table_path') else None
        except Exception as e:
            logger.error(f"Failed to get table location for {database_name}.{table_name}: {e}")
            return None
    
    def test_connection(self) -> Dict[str, any]:
        """测试连接并返回基本信息"""
        if not self.connect():
            return {'status': 'error', 'message': 'Failed to connect'}
        
        try:
            databases = self.get_databases()
            return {
                'status': 'success',
                'database_count': len(databases),
                'databases': databases[:10]  # 只返回前10个数据库名
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
