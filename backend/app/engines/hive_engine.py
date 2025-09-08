import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import time
from sqlalchemy.orm import Session
from pyhive import hive

from app.engines.base_engine import BaseMergeEngine
from app.models.merge_task import MergeTask
from app.models.cluster import Cluster
from app.monitor.hdfs_scanner import HDFSScanner
from app.monitor.hive_connector import HiveMetastoreConnector

logger = logging.getLogger(__name__)

class HiveMergeEngine(BaseMergeEngine):
    """
    基于 Hive SQL 的文件合并引擎
    支持 CONCATENATE 和 INSERT OVERWRITE 两种策略
    """
    
    def __init__(self, cluster: Cluster):
        super().__init__(cluster)
        self.hdfs_scanner = HDFSScanner(cluster.hdfs_namenode_url, cluster.hdfs_user)
        self.metastore_connector = HiveMetastoreConnector(cluster.hive_metastore_url)
    
    def validate_task(self, task: MergeTask) -> Dict[str, Any]:
        """验证合并任务是否可执行"""
        result = {
            'valid': True,
            'message': 'Task validation passed',
            'warnings': []
        }
        
        try:
            # 连接检查
            if not self._test_connections():
                result['valid'] = False
                result['message'] = 'Failed to connect to Hive or HDFS'
                return result
            
            # 检查表是否存在
            if not self._table_exists(task.database_name, task.table_name):
                result['valid'] = False
                result['message'] = f'Table {task.database_name}.{task.table_name} does not exist'
                return result
            
            # 检查分区过滤器（如果有的话）
            if task.partition_filter:
                if not self._validate_partition_filter(task.database_name, task.table_name, task.partition_filter):
                    result['warnings'].append('Partition filter may not match any partitions')
            
            # 检查表的文件格式是否支持合并
            table_format = self._get_table_format(task.database_name, task.table_name)
            if task.merge_strategy == 'concatenate' and table_format not in ['TEXTFILE', 'SEQUENCEFILE', 'RCFILE']:
                result['warnings'].append(f'CONCATENATE may not work well with {table_format} format')
            
            logger.info(f"Task validation completed for {task.database_name}.{task.table_name}")
            
        except Exception as e:
            logger.error(f"Task validation failed: {e}")
            result['valid'] = False
            result['message'] = str(e)
        
        return result
    
    def execute_merge(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        """执行文件合并"""
        start_time = time.time()
        result = {
            'success': False,
            'files_before': 0,
            'files_after': 0,
            'size_saved': 0,
            'duration': 0.0,
            'message': '',
            'sql_executed': []
        }
        
        try:
            # 更新任务状态为运行中
            self.update_task_status(task, 'running', db_session=db_session)
            self.log_task_event(task, 'INFO', f'Starting merge task with strategy: {task.merge_strategy}', db_session=db_session)
            
            # 建立连接
            if not self._test_connections():
                raise Exception('Failed to connect to Hive or HDFS')
            
            # 获取合并前的文件统计
            files_before = self._get_file_count(task.database_name, task.table_name, task.partition_filter)
            result['files_before'] = files_before
            self.log_task_event(task, 'INFO', f'Files before merge: {files_before}', db_session=db_session)
            
            # 执行合并
            if task.merge_strategy == 'concatenate':
                sql_statements = self._execute_concatenate_merge(task)
            elif task.merge_strategy == 'insert_overwrite':
                sql_statements = self._execute_insert_overwrite_merge(task)
            else:
                raise ValueError(f'Unsupported merge strategy: {task.merge_strategy}')
            
            result['sql_executed'] = sql_statements
            
            # 等待一段时间让 HDFS 同步
            time.sleep(5)
            
            # 获取合并后的文件统计
            files_after = self._get_file_count(task.database_name, task.table_name, task.partition_filter)
            result['files_after'] = files_after
            
            # 计算节省的空间（简化估算）
            if files_before > files_after:
                result['size_saved'] = (files_before - files_after) * 1024  # 简化估算
            
            result['success'] = True
            result['duration'] = time.time() - start_time
            result['message'] = f'Merge completed successfully. Files reduced from {files_before} to {files_after}'
            
            # 更新任务状态为成功
            self.update_task_status(
                task, 'success',
                files_before=files_before,
                files_after=files_after,
                size_saved=result['size_saved'],
                db_session=db_session
            )
            
            self.log_task_event(task, 'INFO', result['message'], db_session=db_session)
            
        except Exception as e:
            error_message = str(e)
            result['message'] = f'Merge failed: {error_message}'
            result['duration'] = time.time() - start_time
            
            # 更新任务状态为失败
            self.update_task_status(task, 'failed', error_message=error_message, db_session=db_session)
            self.log_task_event(task, 'ERROR', result['message'], db_session=db_session)
            
            logger.error(f"Merge execution failed for task {task.id}: {e}")
        
        finally:
            # 清理连接
            self._cleanup_connections()
        
        return result
    
    def get_merge_preview(self, task: MergeTask) -> Dict[str, Any]:
        """获取合并预览信息"""
        preview = {
            'estimated_files_before': 0,
            'estimated_files_after': 0,
            'estimated_size_reduction': 0,
            'estimated_duration': 0,
            'warnings': []
        }
        
        try:
            # 建立连接
            if not self._test_connections():
                raise Exception('Failed to connect to Hive or HDFS')
            
            # 获取当前文件数量
            current_files = self._get_file_count(task.database_name, task.table_name, task.partition_filter)
            preview['estimated_files_before'] = current_files
            
            # 估算合并后的文件数量
            if task.merge_strategy == 'concatenate':
                # CONCATENATE 通常能将小文件合并，但具体效果取决于文件大小分布
                preview['estimated_files_after'] = max(1, current_files // 10)  # 简化估算
            elif task.merge_strategy == 'insert_overwrite':
                # INSERT OVERWRITE 通常能更好地控制输出文件数量
                preview['estimated_files_after'] = max(1, current_files // 20)  # 简化估算
            
            # 估算空间节省
            files_reduced = preview['estimated_files_before'] - preview['estimated_files_after']
            preview['estimated_size_reduction'] = files_reduced * 1024  # 简化估算
            
            # 估算执行时间
            preview['estimated_duration'] = self.estimate_duration(task)
            
            # 添加警告信息
            if current_files < 10:
                preview['warnings'].append('表中文件数量较少，合并效果可能有限')
            
            if task.partition_filter and not self._validate_partition_filter(task.database_name, task.table_name, task.partition_filter):
                preview['warnings'].append('分区过滤器可能不匹配任何分区')
            
        except Exception as e:
            logger.error(f"Failed to generate merge preview: {e}")
            preview['warnings'].append(f'无法生成预览: {str(e)}')
        
        finally:
            self._cleanup_connections()
        
        return preview
    
    def estimate_duration(self, task: MergeTask) -> int:
        """估算任务执行时间"""
        try:
            file_count = self._get_file_count(task.database_name, task.table_name, task.partition_filter)
            
            # 基于文件数量的简单估算（秒）
            base_time = 30  # 基础时间
            file_factor = file_count * 0.1  # 每个文件增加 0.1 秒
            
            if task.merge_strategy == 'insert_overwrite':
                # INSERT OVERWRITE 通常比 CONCATENATE 慢
                file_factor *= 2
            
            return int(base_time + file_factor)
        
        except Exception as e:
            logger.error(f"Failed to estimate duration: {e}")
            return 300  # 默认 5 分钟
    
    def _test_connections(self) -> bool:
        """测试连接"""
        try:
            # 测试 HDFS 连接
            if not self.hdfs_scanner.connect():
                return False
            
            # 测试 Hive 连接
            conn = hive.Connection(
                host=self.cluster.hive_host,
                port=self.cluster.hive_port,
                database=self.cluster.hive_database
            )
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def _cleanup_connections(self):
        """清理连接"""
        try:
            self.hdfs_scanner.disconnect()
        except Exception as e:
            logger.warning(f"Failed to cleanup connections: {e}")
    
    def _table_exists(self, database_name: str, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            conn = hive.Connection(
                host=self.cluster.hive_host,
                port=self.cluster.hive_port,
                database=database_name
            )
            cursor = conn.cursor()
            cursor.execute(f'DESCRIBE {table_name}')
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result is not None
        except Exception:
            return False
    
    def _validate_partition_filter(self, database_name: str, table_name: str, partition_filter: str) -> bool:
        """验证分区过滤器"""
        try:
            conn = hive.Connection(
                host=self.cluster.hive_host,
                port=self.cluster.hive_port,
                database=database_name
            )
            cursor = conn.cursor()
            cursor.execute(f'SHOW PARTITIONS {table_name}')
            partitions = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            # 简单检查：看是否有分区匹配过滤条件
            # 这里简化处理，实际应该解析 partition_filter
            return len(partitions) > 0
        except Exception:
            return False
    
    def _get_table_format(self, database_name: str, table_name: str) -> str:
        """获取表的存储格式"""
        try:
            conn = hive.Connection(
                host=self.cluster.hive_host,
                port=self.cluster.hive_port,
                database=database_name
            )
            cursor = conn.cursor()
            cursor.execute(f'DESCRIBE FORMATTED {table_name}')
            
            rows = cursor.fetchall()
            for row in rows:
                if row[0] and 'InputFormat' in str(row[0]):
                    format_line = str(row[1]).upper()
                    if 'TEXT' in format_line:
                        return 'TEXTFILE'
                    elif 'PARQUET' in format_line:
                        return 'PARQUET'
                    elif 'ORC' in format_line:
                        return 'ORC'
                    elif 'SEQUENCE' in format_line:
                        return 'SEQUENCEFILE'
                    elif 'RCFILE' in format_line:
                        return 'RCFILE'
            
            cursor.close()
            conn.close()
            return 'TEXTFILE'  # 默认格式
        except Exception:
            return 'TEXTFILE'
    
    def _get_file_count(self, database_name: str, table_name: str, partition_filter: Optional[str] = None) -> int:
        """获取表的文件数量"""
        try:
            # 这里简化实现，实际应该通过 HDFS 扫描获取准确的文件数量
            # 或者查询 MetaStore 获取文件信息
            
            # 构建表路径
            table_path = self._build_table_path(database_name, table_name)
            
            if partition_filter:
                # 如果有分区过滤器，需要构建具体的分区路径
                # 这里简化处理，实际应该解析 partition_filter 构建正确的路径
                pass
            
            # 使用 HDFS 扫描器获取文件数量
            stats = self.hdfs_scanner.scan_directory(table_path, self.cluster.small_file_threshold)
            return stats['total_files']
            
        except Exception as e:
            logger.error(f"Failed to get file count: {e}")
            return 0
    
    def _execute_concatenate_merge(self, task: MergeTask) -> List[str]:
        """执行 CONCATENATE 合并"""
        sql_statements = []
        
        try:
            conn = hive.Connection(
                host=self.cluster.hive_host,
                port=self.cluster.hive_port,
                database=task.database_name
            )
            cursor = conn.cursor()
            
            # 设置 Hive 合并参数
            merge_settings = [
                "SET hive.merge.mapfiles=true",
                "SET hive.merge.mapredfiles=true",
                f"SET hive.merge.size.per.task={task.target_file_size or 256*1024*1024}"
            ]
            
            for setting in merge_settings:
                cursor.execute(setting)
                sql_statements.append(setting)
            
            # 执行 CONCATENATE 命令
            if task.partition_filter:
                sql = f"ALTER TABLE {task.table_name} PARTITION({task.partition_filter}) CONCATENATE"
            else:
                sql = f"ALTER TABLE {task.table_name} CONCATENATE"
            
            cursor.execute(sql)
            sql_statements.append(sql)
            
            cursor.close()
            conn.close()
            
            logger.info(f"CONCATENATE merge completed for {task.table_name}")
            
        except Exception as e:
            logger.error(f"CONCATENATE merge failed: {e}")
            raise
        
        return sql_statements
    
    def _execute_insert_overwrite_merge(self, task: MergeTask) -> List[str]:
        """执行 INSERT OVERWRITE 合并"""
        sql_statements = []
        
        try:
            conn = hive.Connection(
                host=self.cluster.hive_host,
                port=self.cluster.hive_port,
                database=task.database_name
            )
            cursor = conn.cursor()
            
            # 设置 Hive 合并参数
            merge_settings = [
                "SET hive.merge.mapfiles=true",
                "SET hive.merge.mapredfiles=true",
                f"SET hive.merge.size.per.task={task.target_file_size or 256*1024*1024}",
                "SET hive.exec.dynamic.partition=true",
                "SET hive.exec.dynamic.partition.mode=nonstrict"
            ]
            
            for setting in merge_settings:
                cursor.execute(setting)
                sql_statements.append(setting)
            
            # 构建 INSERT OVERWRITE 语句
            if task.partition_filter:
                sql = f"""
                INSERT OVERWRITE TABLE {task.table_name} PARTITION({task.partition_filter.split('=')[0]})
                SELECT * FROM {task.table_name} WHERE {task.partition_filter}
                """
            else:
                sql = f"""
                INSERT OVERWRITE TABLE {task.table_name}
                SELECT * FROM {task.table_name}
                """
            
            cursor.execute(sql)
            sql_statements.append(sql)
            
            cursor.close()
            conn.close()
            
            logger.info(f"INSERT OVERWRITE merge completed for {task.table_name}")
            
        except Exception as e:
            logger.error(f"INSERT OVERWRITE merge failed: {e}")
            raise
        
        return sql_statements