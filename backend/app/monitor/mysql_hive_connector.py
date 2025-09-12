import logging
from typing import List, Dict, Optional
import pymysql
from .base_connector import BaseMetastoreConnector

logger = logging.getLogger(__name__)

class MySQLHiveMetastoreConnector(BaseMetastoreConnector):
    """
    连接 MySQL 版本的 Hive MetaStore 数据库获取表信息
    专门适配 CDP 集群的 MySQL MetaStore
    """
    
    def __init__(self, metastore_url: str):
        """
        初始化 MetaStore 连接
        Args:
            metastore_url: MySQL connection URL, e.g., mysql://user:pass@host:3306/hive
        """
        super().__init__(metastore_url)
    
    def _create_connection(self):
        """创建MySQL连接"""
        return pymysql.connect(
            host=self.parsed_url.hostname,
            port=self.parsed_url.port or 3306,
            database=self.parsed_url.path.lstrip('/'),
            user=self.parsed_url.username,
            password=self.parsed_url.password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def _execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """执行查询"""
        with self._connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()
    
    
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
                # 获取表详细信息和存储元数据
                query = """
                SELECT 
                    t.TBL_NAME,
                    s.LOCATION as table_path,
                    t.TBL_TYPE,
                    t.OWNER as table_owner,
                    FROM_UNIXTIME(t.CREATE_TIME) as table_create_time,
                    s.INPUT_FORMAT,
                    s.OUTPUT_FORMAT,
                    ser.SLIB as serde_lib,
                    COUNT(p.PART_ID) as partition_count
                FROM TBLS t 
                JOIN SDS s ON t.SD_ID = s.SD_ID 
                JOIN DBS d ON t.DB_ID = d.DB_ID
                LEFT JOIN PARTITIONS p ON p.TBL_ID = t.TBL_ID
                LEFT JOIN SERDES ser ON s.SERDE_ID = ser.SERDE_ID
                WHERE d.NAME = %s
                GROUP BY t.TBL_NAME, s.LOCATION, t.TBL_TYPE, t.OWNER, t.CREATE_TIME, 
                         s.INPUT_FORMAT, s.OUTPUT_FORMAT, ser.SLIB
                ORDER BY t.TBL_NAME
                """
                cursor.execute(query, (database_name,))
                results = cursor.fetchall()
                
                tables = []
                for row in results:
                    # 解析存储格式
                    input_format = row.get('INPUT_FORMAT', '')
                    storage_format = self._extract_storage_format(input_format)
                    
                    tables.append({
                        'table_name': row['TBL_NAME'],
                        'table_path': row['table_path'],
                        'table_type': row['TBL_TYPE'],
                        'table_owner': row.get('table_owner'),
                        'table_create_time': row.get('table_create_time'),
                        'input_format': row.get('INPUT_FORMAT'),
                        'output_format': row.get('OUTPUT_FORMAT'),
                        'serde_lib': row.get('serde_lib'),
                        'storage_format': storage_format,
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
                results = cursor.fetchall()
                
                partitions = []
                for row in results:
                    partitions.append({
                        'partition_name': row['PART_NAME'],
                        'partition_path': row['partition_path']
                    })
                
                return partitions
        except Exception as e:
            logger.error(f"Failed to get partitions for table {database_name}.{table_name}: {e}")
            return []
    
    def test_connection(self) -> Dict[str, any]:
        """测试连接并返回基本信息"""
        if not self.connect():
            return {'status': 'error', 'message': 'Failed to connect'}
        
        try:
            databases = self.get_databases()
            
            # 获取一些基本的 MetaStore 信息
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as table_count FROM TBLS")
                table_count = cursor.fetchone()['table_count']
                
                cursor.execute("SELECT COUNT(*) as db_count FROM DBS")
                db_count = cursor.fetchone()['db_count']
            
            return {
                'status': 'success',
                'database_count': len(databases),
                'total_databases': db_count,
                'total_tables': table_count,
                'sample_databases': databases[:5]  # 只返回前5个数据库名
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