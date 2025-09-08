import logging
from typing import Dict, List, Optional
from datetime import datetime
import time
from sqlalchemy.orm import Session

from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.monitor.mock_hdfs_scanner import MockHDFSScanner
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.models.partition_metric import PartitionMetric

logger = logging.getLogger(__name__)

class MockTableScanner:
    """
    模拟版本的表扫描服务，用于演示完整流程
    """
    
    def __init__(self, cluster: Cluster):
        self.cluster = cluster
        self.hive_connector = MySQLHiveMetastoreConnector(cluster.hive_metastore_url)
        self.hdfs_scanner = MockHDFSScanner(cluster.hdfs_namenode_url, cluster.hdfs_user)
    
    def scan_table(self, db_session: Session, database_name: str, table_info: Dict) -> Dict:
        """
        扫描单个表的文件分布
        """
        table_name = table_info['table_name']
        table_path = table_info['table_path']
        
        logger.info(f"Scanning table {database_name}.{table_name} at {table_path}")
        
        try:
            # 获取分区信息（如果是分区表）
            partitions = []
            if table_info['is_partitioned']:
                partitions = self.hive_connector.get_table_partitions(database_name, table_name)
            
            # 扫描 HDFS 文件（使用模拟扫描器）
            table_stats, partition_stats = self.hdfs_scanner.scan_table_partitions(
                table_path, partitions, self.cluster.small_file_threshold
            )
            
            # 保存表级统计到数据库
            table_metric = TableMetric(
                cluster_id=self.cluster.id,
                database_name=database_name,
                table_name=table_name,
                table_path=table_path,
                total_files=table_stats['total_files'],
                small_files=table_stats['small_files'],
                total_size=table_stats['total_size'],
                avg_file_size=table_stats['avg_file_size'],
                is_partitioned=1 if table_info['is_partitioned'] else 0,
                partition_count=table_info['partition_count'],
                scan_duration=table_stats['scan_duration']
            )
            
            db_session.add(table_metric)
            db_session.flush()  # 获取 table_metric.id
            
            # 保存分区级统计
            for partition_stat in partition_stats:
                partition_metric = PartitionMetric(
                    table_metric_id=table_metric.id,
                    partition_name=partition_stat['partition_name'],
                    partition_path=partition_stat['partition_path'],
                    file_count=partition_stat['file_count'],
                    small_file_count=partition_stat['small_file_count'],
                    total_size=partition_stat['total_size'],
                    avg_file_size=partition_stat['avg_file_size']
                )
                db_session.add(partition_metric)
            
            db_session.commit()
            
            logger.info(f"Saved metrics for table {database_name}.{table_name}: "
                       f"{table_stats['total_files']} files, {table_stats['small_files']} small files")
            
            return table_stats
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to scan table {database_name}.{table_name}: {e}")
            raise
    
    def scan_database_tables(self, db_session: Session, database_name: str,
                           table_filter: Optional[str] = None) -> Dict:
        """
        扫描指定数据库的所有表
        """
        start_time = time.time()
        result = {
            'database_name': database_name,
            'tables_scanned': 0,
            'total_files': 0,
            'total_small_files': 0,
            'scan_duration': 0.0,
            'errors': []
        }
        
        try:
            # 连接服务
            if not self.hive_connector.connect():
                raise Exception("Failed to connect to Hive MetaStore")
            
            if not self.hdfs_scanner.connect():
                raise Exception("Failed to connect to HDFS")
            
            # 获取表列表
            tables = self.hive_connector.get_tables(database_name)
            if table_filter:
                tables = [t for t in tables if table_filter in t['table_name']]
            
            logger.info(f"Found {len(tables)} tables in database {database_name}")
            
            # 扫描每个表
            for table_info in tables:
                try:
                    table_result = self.scan_table(db_session, database_name, table_info)
                    result['tables_scanned'] += 1
                    result['total_files'] += table_result.get('total_files', 0)
                    result['total_small_files'] += table_result.get('small_files', 0)
                    
                except Exception as e:
                    error_msg = f"Failed to scan table {table_info['table_name']}: {e}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
            
            result['scan_duration'] = time.time() - start_time
            
        except Exception as e:
            error_msg = f"Database {database_name} scan failed: {e}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
        
        finally:
            self.hive_connector.disconnect()
            self.hdfs_scanner.disconnect()
        
        return result
    
    def test_connections(self) -> Dict:
        """测试连接状态"""
        results = {}
        
        # 测试 MetaStore 连接
        try:
            metastore_result = self.hive_connector.test_connection()
            results['metastore'] = metastore_result
        except Exception as e:
            results['metastore'] = {'status': 'error', 'message': str(e)}
        
        # 测试 HDFS 连接
        try:
            hdfs_result = self.hdfs_scanner.test_connection()
            results['hdfs'] = hdfs_result
        except Exception as e:
            results['hdfs'] = {'status': 'error', 'message': str(e)}
        
        return results