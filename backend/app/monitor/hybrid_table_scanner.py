import logging
from typing import Dict, List, Optional
from datetime import datetime
import time
from sqlalchemy.orm import Session

from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.monitor.webhdfs_scanner import WebHDFSScanner
from app.monitor.mock_hdfs_scanner import MockHDFSScanner
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.models.partition_metric import PartitionMetric

logger = logging.getLogger(__name__)

class HybridTableScanner:
    """
    混合版本的表扫描服务
    - 使用真实的Hive MetaStore获取表信息
    - 智能选择HDFS扫描器：优先使用真实HDFS，失败时回退到Mock模式
    """
    
    def __init__(self, cluster: Cluster):
        self.cluster = cluster
        self.hive_connector = MySQLHiveMetastoreConnector(cluster.hive_metastore_url)
        
        # 初始化HDFS扫描器，但在运行时智能选择
        self.hdfs_scanner = None
        self.hdfs_mode = None  # 'real' or 'mock'
        
    def _initialize_hdfs_scanner(self):
        """智能初始化HDFS扫描器"""
        if self.hdfs_scanner is not None:
            return  # 已经初始化过
        
        # 尝试真实的WebHDFS连接
        try:
            webhdfs_scanner = WebHDFSScanner(self.cluster.hdfs_namenode_url, self.cluster.hdfs_user)
            result = webhdfs_scanner.test_connection()
            
            if result['status'] == 'success':
                logger.info(f"✅ 使用真实WebHDFS扫描器: {result['webhdfs_url']}")
                self.hdfs_scanner = webhdfs_scanner
                self.hdfs_mode = 'real'
                return
            else:
                logger.warning(f"WebHDFS连接失败: {result.get('message')}")
        except Exception as e:
            logger.warning(f"WebHDFS测试失败: {e}")
        
        # 回退到Mock模式
        logger.info("🔄 回退到Mock HDFS扫描器模式")
        self.hdfs_scanner = MockHDFSScanner(self.cluster.hdfs_namenode_url, self.cluster.hdfs_user)
        self.hdfs_mode = 'mock'
    
    def scan_table(self, db_session: Session, database_name: str, table_info: Dict) -> Dict:
        """
        扫描单个表的文件分布
        """
        table_name = table_info['table_name']
        table_path = table_info['table_path']
        
        logger.info(f"Scanning table {database_name}.{table_name} at {table_path}")
        
        # 确保HDFS扫描器已初始化
        self._initialize_hdfs_scanner()
        
        try:
            # 获取分区信息（如果是分区表）
            partitions = []
            if table_info['is_partitioned']:
                partitions = self.hive_connector.get_table_partitions(database_name, table_name)
                logger.info(f"Found {len(partitions)} partitions for table {table_name}")
            
            # 扫描 HDFS 文件
            table_stats, partition_stats = self.hdfs_scanner.scan_table_partitions(
                table_path, partitions, self.cluster.small_file_threshold
            )
            
            # 标记数据来源
            table_stats['hdfs_mode'] = self.hdfs_mode
            
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
            
            logger.info(f"Saved metrics for table {database_name}.{table_name} "
                       f"({self.hdfs_mode} mode): {table_stats['total_files']} files, "
                       f"{table_stats['small_files']} small files")
            
            return table_stats
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to scan table {database_name}.{table_name}: {e}")
            raise
    
    def scan_database_tables(self, db_session: Session, database_name: str,
                           table_filter: Optional[str] = None, max_tables: int = 10) -> Dict:
        """
        扫描指定数据库的表（限制数量避免过长时间）
        """
        start_time = time.time()
        result = {
            'database_name': database_name,
            'tables_scanned': 0,
            'total_files': 0,
            'total_small_files': 0,
            'scan_duration': 0.0,
            'hdfs_mode': None,
            'errors': []
        }
        
        try:
            # 连接服务
            if not self.hive_connector.connect():
                raise Exception("Failed to connect to Hive MetaStore")
            
            # 初始化HDFS扫描器
            self._initialize_hdfs_scanner()
            
            if not self.hdfs_scanner.connect():
                raise Exception("Failed to connect to HDFS")
            
            result['hdfs_mode'] = self.hdfs_mode
            
            # 获取表列表
            tables = self.hive_connector.get_tables(database_name)
            if table_filter:
                tables = [t for t in tables if table_filter in t['table_name']]
            
            # 限制扫描表的数量
            tables = tables[:max_tables]
            
            logger.info(f"Found {len(tables)} tables in database {database_name} "
                       f"(limited to {max_tables} for demo)")
            
            # 扫描每个表
            for i, table_info in enumerate(tables, 1):
                try:
                    logger.info(f"[{i}/{len(tables)}] Scanning {table_info['table_name']}...")
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
            if self.hdfs_scanner:
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
        
        # 智能测试 HDFS 连接
        try:
            # 尝试真实HDFS
            webhdfs_scanner = WebHDFSScanner(self.cluster.hdfs_namenode_url, self.cluster.hdfs_user)
            hdfs_result = webhdfs_scanner.test_connection()
            
            if hdfs_result['status'] == 'success':
                hdfs_result['mode'] = 'real'
                results['hdfs'] = hdfs_result
            else:
                # 回退到Mock
                mock_scanner = MockHDFSScanner(self.cluster.hdfs_namenode_url, self.cluster.hdfs_user)
                mock_result = mock_scanner.test_connection()
                mock_result['mode'] = 'mock'
                mock_result['real_hdfs_error'] = hdfs_result.get('message')
                results['hdfs'] = mock_result
        except Exception as e:
            results['hdfs'] = {'status': 'error', 'message': str(e)}
        
        return results