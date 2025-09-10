import logging
from typing import Dict, List, Optional
from datetime import datetime
import time
from sqlalchemy.orm import Session

from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.monitor.webhdfs_scanner import WebHDFSScanner
from app.monitor.enhanced_webhdfs_scanner import EnhancedWebHDFSScanner
from app.monitor.intelligent_hybrid_scanner import IntelligentHybridScanner
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
        
        # 直接尝试使用WebHDFS扫描器（不使用Kerberos）
        try:
            # 检测端口以确定服务类型
            if ':14000' in self.cluster.hdfs_namenode_url:
                port = 14000
                service_name = "HttpFS"
            else:
                port = 9870
                service_name = "WebHDFS"
            
            logger.info(f"尝试连接{service_name}服务: {self.cluster.hdfs_namenode_url}:{port}")
            
            # 使用WebHDFS扫描器（不使用Kerberos认证）
            webhdfs_scanner = WebHDFSScanner(
                namenode_url=self.cluster.hdfs_namenode_url,
                user=self.cluster.hdfs_user,
                webhdfs_port=port,
                password=self.cluster.hdfs_password
            )
            
            # 测试连接
            test_result = webhdfs_scanner.test_connection()
            
            if test_result['status'] == 'success':
                logger.info(f"✅ WebHDFS扫描器连接成功")
                logger.info(f"   服务类型: {test_result.get('service_type')}")
                logger.info(f"   认证方式: {test_result.get('auth_method')}")
                logger.info(f"   样例路径: {test_result.get('sample_paths')}")
                
                self.hdfs_scanner = webhdfs_scanner
                self.hdfs_mode = 'webhdfs_real'
                return
            else:
                logger.warning(f"WebHDFS连接失败: {test_result.get('message')}")
                
        except Exception as e:
            logger.warning(f"WebHDFS扫描器初始化失败: {e}")
        
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
            
            # 调试日志：检查table_stats的内容
            logger.info(f"扫描结果类型检查:")
            logger.info(f"  table_stats类型: {type(table_stats)}")
            logger.info(f"  table_stats键: {list(table_stats.keys()) if isinstance(table_stats, dict) else 'Not a dict'}")
            if isinstance(table_stats, dict):
                for key, value in table_stats.items():
                    logger.info(f"    {key}: {value} (类型: {type(value)})")
            
            # 标记数据来源
            table_stats['hdfs_mode'] = self.hdfs_mode
            
            # 检查必要字段是否存在，如果不存在则设置默认值
            required_fields = {
                'total_files': 0,
                'small_files': 0, 
                'total_size': 0,
                'avg_file_size': 0.0,
                'scan_duration': 0.0
            }
            
            for field, default_value in required_fields.items():
                if field not in table_stats:
                    logger.warning(f"字段 '{field}' 不存在，设置默认值 {default_value}")
                    table_stats[field] = default_value
            
            # 保存表级统计到数据库（包含增强的元数据）
            table_metric = TableMetric(
                cluster_id=self.cluster.id,
                database_name=database_name,
                table_name=table_name,
                table_path=table_path,
                # 增强的元数据字段
                table_type=table_info.get('table_type'),
                storage_format=table_info.get('storage_format'),
                input_format=table_info.get('input_format'),
                output_format=table_info.get('output_format'),
                serde_lib=table_info.get('serde_lib'),
                table_owner=table_info.get('table_owner'),
                table_create_time=table_info.get('table_create_time'),
                # 文件统计
                total_files=table_stats['total_files'],
                small_files=table_stats['small_files'],
                total_size=table_stats['total_size'],
                avg_file_size=table_stats['avg_file_size'],
                # 分区信息
                is_partitioned=1 if table_info['is_partitioned'] else 0,
                partition_count=table_info['partition_count'],
                partition_columns=None,  # TODO: 获取分区列信息
                # 扫描元数据
                scan_duration=table_stats['scan_duration']
            )
            
            db_session.add(table_metric)
            db_session.flush()  # 获取 table_metric.id
            
            # 保存分区级统计
            logger.info(f"分区统计数据检查: 共 {len(partition_stats)} 个分区")
            for i, partition_stat in enumerate(partition_stats):
                logger.info(f"  分区 {i+1}: {list(partition_stat.keys()) if isinstance(partition_stat, dict) else 'Not a dict'}")
                
                # 检查分区统计的必要字段
                partition_required_fields = {
                    'partition_name': 'main',
                    'partition_path': table_path,
                    'file_count': 0,
                    'small_file_count': 0,
                    'total_size': 0,
                    'avg_file_size': 0.0
                }
                
                for field, default_value in partition_required_fields.items():
                    if field not in partition_stat:
                        logger.warning(f"分区字段 '{field}' 不存在，设置默认值 {default_value}")
                        partition_stat[field] = default_value
                
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
        """详细的连接测试，包含诊断信息和建议"""
        results = {
            'overall_status': 'unknown',
            'test_time': datetime.now().isoformat(),
            'tests': {},
            'logs': [],
            'suggestions': []
        }
        
        def add_log(level: str, message: str):
            results['logs'].append({
                'level': level,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
        
        add_log('info', f'开始测试集群连接: {self.cluster.name}')
        
        # 1. 测试 MetaStore 连接 - 使用context manager确保连接生命周期管理
        add_log('info', '正在测试 Hive MetaStore 连接...')
        try:
            # 使用context manager来管理连接生命周期
            try:
                with self.hive_connector:
                    add_log('success', f"✅ MetaStore连接成功: {self.cluster.hive_metastore_url}")
                    
                    # 在连接上下文中获取数据库列表和MetaStore信息
                    try:
                        databases = self.hive_connector.get_databases()
                        add_log('success', f"✅ 成功获取到 {len(databases)} 个数据库: {databases[:3]}...")
                        
                        # 获取更详细的MetaStore统计信息
                        with self.hive_connector._connection.cursor() as cursor:
                            cursor.execute("SELECT COUNT(*) as table_count FROM TBLS")
                            table_count = cursor.fetchone()['table_count']
                            
                            cursor.execute("SELECT COUNT(*) as db_count FROM DBS")
                            db_count = cursor.fetchone()['db_count']
                        
                        results['tests']['metastore'] = {
                            'status': 'success',
                            'message': f'连接成功，找到 {len(databases)} 个数据库',
                            'databases_count': len(databases),
                            'total_databases': db_count,
                            'total_tables': table_count,
                            'sample_databases': databases[:5],
                            'mode': 'mysql'
                        }
                        
                    except Exception as db_e:
                        add_log('warning', f"⚠️ MetaStore基础连接成功但数据访问失败: {str(db_e)}")
                        results['tests']['metastore'] = {
                            'status': 'partial', 
                            'message': f'连接成功但数据访问失败: {str(db_e)}',
                            'mode': 'mysql'
                        }
                        results['suggestions'].append("检查数据库用户权限，确保有访问Hive MetaStore表的SELECT权限")
                        results['suggestions'].append("验证Hive MetaStore表结构完整性（DBS, TBLS表等）")
                        
            except ConnectionError as conn_e:
                add_log('error', f"❌ MetaStore连接失败: {str(conn_e)}")
                results['tests']['metastore'] = {'status': 'error', 'message': str(conn_e), 'mode': 'mysql'}
                self._add_metastore_suggestions(results, {'message': str(conn_e)})
                
        except Exception as e:
            error_msg = str(e)
            add_log('error', f"❌ MetaStore连接异常: {error_msg}")
            results['tests']['metastore'] = {'status': 'error', 'message': error_msg, 'mode': 'mysql'}
            self._add_metastore_suggestions(results, {'message': error_msg})
        
        # 2. 测试 HDFS 连接
        add_log('info', '正在测试 HDFS 连接...')
        try:
            # 尝试真实WebHDFS连接
            add_log('info', f'尝试连接 WebHDFS: {self.cluster.hdfs_namenode_url}')
            webhdfs_scanner = WebHDFSScanner(self.cluster.hdfs_namenode_url, self.cluster.hdfs_user)
            hdfs_result = webhdfs_scanner.test_connection()
            
            if hdfs_result.get('status') == 'success':
                add_log('success', f"✅ WebHDFS连接成功: {hdfs_result.get('webhdfs_url')}")
                hdfs_result['mode'] = 'real'
                results['tests']['hdfs'] = hdfs_result
                
                # 测试基本的HDFS操作
                try:
                    # 测试根目录访问
                    test_result = webhdfs_scanner.test_directory_access('/')
                    if test_result:
                        add_log('success', '✅ HDFS根目录访问权限正常')
                    else:
                        add_log('warning', '⚠️ HDFS根目录访问受限')
                        results['suggestions'].append('请检查HDFS用户权限配置')
                except:
                    add_log('warning', '⚠️ 无法测试HDFS目录访问权限')
                
            else:
                add_log('warning', f"⚠️ WebHDFS连接失败: {hdfs_result.get('message')}")
                
                # 回退到Mock模式
                add_log('info', '🔄 启用Mock HDFS模式进行测试')
                mock_scanner = MockHDFSScanner(self.cluster.hdfs_namenode_url, self.cluster.hdfs_user)
                mock_result = mock_scanner.test_connection()
                mock_result['mode'] = 'mock'
                mock_result['real_hdfs_error'] = hdfs_result.get('message')
                results['tests']['hdfs'] = mock_result
                
                add_log('info', '✅ Mock HDFS模式可用（将使用模拟数据进行演示）')
                self._add_hdfs_suggestions(results, hdfs_result)
                
        except Exception as e:
            error_msg = str(e)
            add_log('error', f"❌ HDFS连接异常: {error_msg}")
            results['tests']['hdfs'] = {'status': 'error', 'message': error_msg}
            self._add_hdfs_suggestions(results, {'message': error_msg})
        
        # 3. 综合评估
        metastore_ok = results['tests'].get('metastore', {}).get('status') == 'success'
        hdfs_ok = results['tests'].get('hdfs', {}).get('status') == 'success'
        
        if metastore_ok and hdfs_ok:
            results['overall_status'] = 'success'
            mode = results['tests']['hdfs'].get('mode', 'unknown')
            if mode == 'real':
                add_log('success', '🎉 所有连接测试通过！集群可以正常使用真实数据扫描')
            else:
                add_log('success', '🎉 MetaStore连接正常！将使用Mock模式进行HDFS数据演示')
                results['suggestions'].append('建议修复HDFS连接以获得真实的文件统计数据')
        elif metastore_ok:
            results['overall_status'] = 'partial'
            add_log('warning', '⚠️ MetaStore连接正常，但HDFS连接有问题。可以查看表结构但无法获取文件统计')
        else:
            results['overall_status'] = 'failed'
            add_log('error', '❌ 关键连接失败，集群无法正常工作')
            results['suggestions'].append('请先解决MetaStore连接问题，这是集群正常工作的前提')
        
        add_log('info', f'连接测试完成，总体状态: {results["overall_status"]}')
        return results
    
    def _add_metastore_suggestions(self, results: Dict, error_result: Dict):
        """添加MetaStore连接问题的诊断建议"""
        error_msg = error_result.get('message', '').lower()
        
        if 'connection refused' in error_msg or 'could not connect' in error_msg:
            results['suggestions'].extend([
                '网络连接被拒绝，请检查：',
                '1. MySQL/PostgreSQL服务是否正在运行',
                '2. 防火墙是否允许连接到数据库端口',
                '3. 数据库服务器地址和端口是否正确'
            ])
        elif 'access denied' in error_msg or 'authentication failed' in error_msg:
            results['suggestions'].extend([
                '数据库认证失败，请检查：',
                '1. 用户名和密码是否正确',
                '2. 数据库用户是否存在且有权限访问Hive MetaStore数据库',
                '3. 数据库连接URL格式是否正确'
            ])
        elif 'unknown database' in error_msg or 'database does not exist' in error_msg:
            results['suggestions'].extend([
                'MetaStore数据库不存在，请检查：',
                '1. Hive MetaStore是否正确初始化',
                '2. 数据库名称是否正确（通常为"hive"或"metastore"）',
                '3. 是否需要先运行schematool初始化MetaStore'
            ])
        elif 'timeout' in error_msg:
            results['suggestions'].extend([
                '连接超时，请检查：',
                '1. 网络连接是否稳定',
                '2. 数据库服务器是否响应缓慢',
                '3. 是否需要增加连接超时设置'
            ])
        else:
            results['suggestions'].extend([
                'MetaStore连接失败，建议检查：',
                '1. 连接URL格式：mysql://user:password@host:port/database',
                '2. 数据库服务状态和网络连通性',
                '3. 用户权限和认证信息'
            ])
    
    def _add_hdfs_suggestions(self, results: Dict, error_result: Dict):
        """添加HDFS连接问题的诊断建议"""
        error_msg = error_result.get('message', '').lower()
        
        if 'connection refused' in error_msg:
            results['suggestions'].extend([
                'HDFS连接被拒绝，请检查：',
                '1. NameNode服务是否正在运行',
                '2. WebHDFS是否已启用（dfs.webhdfs.enabled=true）',
                '3. 防火墙是否允许访问NameNode端口（通常是9870或50070）'
            ])
        elif 'unknown host' in error_msg or 'name resolution' in error_msg:
            results['suggestions'].extend([
                'HDFS主机名解析失败，请检查：',
                '1. NameNode主机名或IP地址是否正确',
                '2. DNS解析是否正常',
                '3. /etc/hosts文件是否包含正确的主机映射'
            ])
        elif 'unauthorized' in error_msg or 'permission denied' in error_msg:
            results['suggestions'].extend([
                'HDFS权限不足，请检查：',
                '1. HDFS用户是否存在且有权限',
                '2. Kerberos认证是否正确配置（如果启用）',
                '3. 是否需要代理用户配置'
            ])
        elif 'timeout' in error_msg:
            results['suggestions'].extend([
                'HDFS连接超时，请检查：',
                '1. 网络连接是否稳定',
                '2. NameNode是否处于安全模式',
                '3. 集群负载是否过高'
            ])
        else:
            results['suggestions'].extend([
                'HDFS连接失败，建议检查：',
                '1. NameNode地址格式：hdfs://namenode:port 或 http://namenode:port',
                '2. WebHDFS服务状态和配置',
                '3. 网络连通性和防火墙设置'
            ])
            
        # 总是提示Mock模式可用
        results['suggestions'].append('注意：即使HDFS连接失败，系统仍可使用Mock模式进行功能演示')