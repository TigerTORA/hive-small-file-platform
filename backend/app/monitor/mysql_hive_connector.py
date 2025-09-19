import logging
from typing import List, Dict, Optional
import pymysql
from datetime import datetime
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

    def get_table_partitions_count(self, database_name: str, table_name: str) -> int:
        """获取表分区总数（用于分页）"""
        if not self._connection:
            raise ConnectionError("Not connected to MetaStore")
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(1) AS cnt
                    FROM PARTITIONS p
                    JOIN TBLS t ON p.TBL_ID = t.TBL_ID
                    JOIN DBS d ON t.DB_ID = d.DB_ID
                    WHERE d.NAME = %s AND t.TBL_NAME = %s
                    """,
                    (database_name, table_name),
                )
                row = cursor.fetchone()
                return int(row.get('cnt', 0)) if row else 0
        except Exception as e:
            logger.error(f"Failed to count partitions for {database_name}.{table_name}: {e}")
            return 0

    def get_table_partitions_paged(self, database_name: str, table_name: str, offset: int, limit: int) -> List[Dict]:
        """分页获取表分区信息（避免一次性全量查询）"""
        if not self._connection:
            raise ConnectionError("Not connected to MetaStore")
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        p.PART_NAME,
                        s.LOCATION as partition_path
                    FROM PARTITIONS p
                    JOIN SDS s ON p.SD_ID = s.SD_ID
                    JOIN TBLS t ON p.TBL_ID = t.TBL_ID
                    JOIN DBS d ON t.DB_ID = d.DB_ID
                    WHERE d.NAME = %s AND t.TBL_NAME = %s
                    ORDER BY p.PART_NAME
                    LIMIT %s OFFSET %s
                    """,
                    (database_name, table_name, int(limit), int(offset)),
                )
                results = cursor.fetchall()
                parts: List[Dict] = []
                for row in results:
                    parts.append({
                        'partition_name': row['PART_NAME'],
                        'partition_path': row['partition_path']
                    })
                return parts
        except Exception as e:
            logger.error(f"Failed to get paged partitions for {database_name}.{table_name}: {e}")
            return []

    def get_table_location(self, database_name: str, table_name: str) -> Optional[str]:
        """获取单表的 LOCATION（更高效，避免全量枚举）"""
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
        import time
        
        connect_start = time.time()
        connect_success = False
        error_details = None
        
        try:
            connect_success = self.connect()
            connect_time = time.time() - connect_start
            
            if not connect_success:
                return {
                    'status': 'error', 
                    'message': 'Failed to connect to MetaStore',
                    'connect_time': round(connect_time, 2),
                    'error_type': 'connection_failed'
                }
            
        except Exception as conn_error:
            connect_time = time.time() - connect_start
            error_msg = str(conn_error)
            
            # 分析连接错误类型
            if "Access denied" in error_msg:
                error_type = "authentication_failed"
                suggestion = "检查用户名和密码是否正确"
            elif "Unknown database" in error_msg:
                error_type = "database_not_found"
                suggestion = "检查数据库名称是否正确"
            elif "Can't connect" in error_msg or "Connection refused" in error_msg:
                error_type = "connection_refused"
                suggestion = "检查网络连通性和MySQL服务状态"
            elif "timeout" in error_msg.lower():
                error_type = "connection_timeout"
                suggestion = "检查网络延迟或增加连接超时时间"
            else:
                error_type = "unknown_error"
                suggestion = "请检查连接参数和网络配置"
            
            return {
                'status': 'error',
                'message': f'MetaStore连接失败: {error_msg}',
                'connect_time': round(connect_time, 2),
                'error_type': error_type,
                'suggestion': suggestion,
                'connection_url': f"mysql://{self.parsed_url.hostname}:{self.parsed_url.port or 3306}/{self.parsed_url.path.lstrip('/')}"
            }
        
        try:
            # 测试基本查询性能
            query_start = time.time()
            databases = self.get_databases()
            database_query_time = time.time() - query_start
            
            # 获取 MetaStore 统计信息
            stats_start = time.time()
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as table_count FROM TBLS")
                table_count = cursor.fetchone()['table_count']
                
                cursor.execute("SELECT COUNT(*) as db_count FROM DBS")
                db_count = cursor.fetchone()['db_count']
                
                cursor.execute("SELECT COUNT(*) as partition_count FROM PARTITIONS")
                partition_count = cursor.fetchone()['partition_count']
                
                # 获取MySQL版本信息
                cursor.execute("SELECT VERSION() as version")
                mysql_version = cursor.fetchone()['version']
                
            stats_query_time = time.time() - stats_start
            total_time = time.time() - connect_start
            
            return {
                'status': 'success',
                'message': f'MetaStore连接成功，MySQL {mysql_version}',
                'connect_time': round(connect_time, 2),
                'database_query_time': round(database_query_time, 2),
                'stats_query_time': round(stats_query_time, 2),
                'total_test_time': round(total_time, 2),
                'database_count': len(databases),
                'total_databases': db_count,
                'total_tables': table_count,
                'total_partitions': partition_count,
                'sample_databases': databases[:5],  # 只返回前5个数据库名
                'mysql_version': mysql_version,
                'connection_url': f"mysql://{self.parsed_url.hostname}:{self.parsed_url.port or 3306}/{self.parsed_url.path.lstrip('/')}"
            }
            
        except Exception as e:
            query_time = time.time() - connect_start
            error_msg = str(e)
            
            # 分析查询错误类型
            if "Table" in error_msg and "doesn't exist" in error_msg:
                error_type = "schema_mismatch"
                suggestion = "MetaStore数据库架构不匹配，请检查Hive版本兼容性"
            elif "permission" in error_msg.lower() or "access" in error_msg.lower():
                error_type = "permission_denied"
                suggestion = "数据库用户缺少必要的查询权限"
            else:
                error_type = "query_failed"
                suggestion = "MetaStore查询失败，请检查数据库状态"
                
            return {
                'status': 'partial',
                'message': f'连接成功但查询失败: {error_msg}',
                'connect_time': round(connect_time, 2),
                'total_test_time': round(query_time, 2),
                'error_type': error_type,
                'suggestion': suggestion
            }
        finally:
            if connect_success:
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

    def get_table_access_info(self, database_name: Optional[str] = None, table_name: Optional[str] = None) -> List[Dict]:
        """
        获取表的访问时间信息
        Args:
            database_name: 数据库名称，为空则获取所有数据库
            table_name: 表名称，为空则获取指定数据库的所有表
        Returns:
            包含访问时间信息的字典列表
        """
        if not self._connection:
            raise ConnectionError("Not connected to MetaStore")

        try:
            with self._connection.cursor() as cursor:
                base_query = """
                SELECT
                    d.NAME as database_name,
                    t.TBL_NAME as table_name,
                    t.LAST_ACCESS_TIME,
                    t.CREATE_TIME
                FROM TBLS t
                JOIN DBS d ON t.DB_ID = d.DB_ID
                """

                conditions = []
                params = []

                if database_name:
                    conditions.append("d.NAME = %s")
                    params.append(database_name)

                if table_name:
                    conditions.append("t.TBL_NAME = %s")
                    params.append(table_name)

                if conditions:
                    base_query += " WHERE " + " AND ".join(conditions)

                cursor.execute(base_query, params)
                results = cursor.fetchall()

                return [
                    {
                        'database_name': row['database_name'],
                        'table_name': row['table_name'],
                        'last_access_time': self._timestamp_to_datetime(row['LAST_ACCESS_TIME']),
                        'create_time': self._timestamp_to_datetime(row['CREATE_TIME'])
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"Failed to get table access info: {e}")
            return []

    def get_table_last_access_time(self, database_name: str, table_name: str) -> Optional[datetime]:
        """
        获取单个表的最后访问时间
        Args:
            database_name: 数据库名称
            table_name: 表名称
        Returns:
            最后访问时间，如果没有记录则返回None
        """
        if not self._connection:
            raise ConnectionError("Not connected to MetaStore")

        try:
            with self._connection.cursor() as cursor:
                query = """
                SELECT t.LAST_ACCESS_TIME
                FROM TBLS t
                JOIN DBS d ON t.DB_ID = d.DB_ID
                WHERE d.NAME = %s AND t.TBL_NAME = %s
                """
                cursor.execute(query, (database_name, table_name))
                result = cursor.fetchone()

                if result and result['LAST_ACCESS_TIME']:
                    return self._timestamp_to_datetime(result['LAST_ACCESS_TIME'])
                return None
        except Exception as e:
            logger.error(f"Failed to get last access time for {database_name}.{table_name}: {e}")
            return None

    def _timestamp_to_datetime(self, timestamp) -> Optional[datetime]:
        """
        将时间戳转换为datetime对象
        Args:
            timestamp: Unix时间戳
        Returns:
            datetime对象，如果时间戳无效则返回None
        """
        if timestamp and timestamp > 0:
            try:
                return datetime.fromtimestamp(timestamp)
            except (ValueError, OSError) as e:
                logger.warning(f"Invalid timestamp {timestamp}: {e}")
                return None
        return None

    def get_partition_access_info(self, database_name: Optional[str] = None,
                                table_name: Optional[str] = None) -> List[Dict]:
        """
        获取分区的访问时间信息
        Args:
            database_name: 数据库名称，为空则获取所有数据库
            table_name: 表名称，为空则获取指定数据库的所有表
        Returns:
            包含分区访问时间信息的字典列表
        """
        if not self._connection:
            raise ConnectionError("Not connected to MetaStore")

        try:
            with self._connection.cursor() as cursor:
                # 查询分区信息，包括分区访问时间和大小信息
                base_query = """
                SELECT DISTINCT
                    d.NAME as database_name,
                    t.TBL_NAME as table_name,
                    p.PART_NAME as partition_name,
                    sd.LOCATION as partition_path,
                    p.LAST_ACCESS_TIME,
                    p.CREATE_TIME,
                    COALESCE(ps.PARAM_VALUE, '0') as partition_size
                FROM PARTITIONS p
                JOIN TBLS t ON p.TBL_ID = t.TBL_ID
                JOIN DBS d ON t.DB_ID = d.DB_ID
                JOIN SDS sd ON p.SD_ID = sd.SD_ID
                LEFT JOIN PARTITION_PARAMS ps ON p.PART_ID = ps.PART_ID AND ps.PARAM_KEY = 'totalSize'
                """

                conditions = []
                params = []

                if database_name:
                    conditions.append("d.NAME = %s")
                    params.append(database_name)

                if table_name:
                    conditions.append("t.TBL_NAME = %s")
                    params.append(table_name)

                if conditions:
                    base_query += " WHERE " + " AND ".join(conditions)

                base_query += " ORDER BY d.NAME, t.TBL_NAME, p.PART_NAME"

                cursor.execute(base_query, params)
                results = cursor.fetchall()

                partition_list = []
                for row in results:
                    try:
                        partition_size = int(row.get('partition_size', 0))
                    except (ValueError, TypeError):
                        partition_size = 0

                    partition_info = {
                        'database_name': row['database_name'],
                        'table_name': row['table_name'],
                        'partition_name': row['partition_name'],
                        'partition_path': row['partition_path'],
                        'last_access_time': self._timestamp_to_datetime(row['LAST_ACCESS_TIME']),
                        'create_time': self._timestamp_to_datetime(row['CREATE_TIME']),
                        'partition_size': partition_size
                    }
                    partition_list.append(partition_info)

                logger.info(f"Retrieved access info for {len(partition_list)} partitions")
                return partition_list

        except Exception as e:
            logger.error(f"Failed to get partition access info: {e}")
            return []
