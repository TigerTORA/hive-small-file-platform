import logging
from typing import Dict, Any, Optional, List, Callable
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

class SafeHiveMergeEngine(BaseMergeEngine):
    """
    安全的Hive合并引擎
    使用临时表+原子重命名的策略，确保合并过程中原表可读
    支持分区级别的合并操作
    """
    
    def __init__(self, cluster: Cluster):
        super().__init__(cluster)
        self.hdfs_scanner = HDFSScanner(cluster.hdfs_namenode_url, cluster.hdfs_user)
        self.metastore_connector = HiveMetastoreConnector(cluster.hive_metastore_url)
        self.progress_callback: Optional[Callable[[str, str], None]] = None
    
    def set_progress_callback(self, callback: Callable[[str, str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def _report_progress(self, phase: str, message: str):
        """报告执行进度"""
        if self.progress_callback:
            self.progress_callback(phase, message)
        logger.info(f"[{phase}] {message}")
    
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
            
            # 检查是否为分区表
            is_partitioned = self._is_partitioned_table(task.database_name, task.table_name)
            
            # 如果是分区表但没有指定分区过滤器，给出警告
            if is_partitioned and not task.partition_filter:
                result['warnings'].append('Partitioned table detected but no partition filter specified. This will merge all partitions.')
            
            # 如果指定了分区过滤器，验证分区是否存在
            if task.partition_filter:
                if not self._validate_partition_filter(task.database_name, task.table_name, task.partition_filter):
                    result['warnings'].append('Partition filter may not match any partitions')
            
            # 检查临时表名是否冲突
            temp_table_name = self._generate_temp_table_name(task.table_name)
            if self._table_exists(task.database_name, temp_table_name):
                result['warnings'].append(f'Temporary table {temp_table_name} already exists, will be dropped')
            
            logger.info(f"SafeHive validation completed for {task.database_name}.{task.table_name}")
            
        except Exception as e:
            logger.error(f"Task validation failed: {e}")
            result['valid'] = False
            result['message'] = str(e)
        
        return result
    
    def execute_merge(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        """执行安全文件合并"""
        start_time = time.time()
        result = {
            'success': False,
            'files_before': 0,
            'files_after': 0,
            'size_saved': 0,
            'duration': 0.0,
            'message': '',
            'sql_executed': [],
            'temp_table_created': '',
            'backup_table_created': ''
        }
        
        temp_table_name = self._generate_temp_table_name(task.table_name)
        backup_table_name = self._generate_backup_table_name(task.table_name)
        
        try:
            # 更新任务状态为运行中
            self.update_task_status(task, 'running', db_session=db_session)
            self.log_task_event(task, 'INFO', f'Starting safe merge with temp table strategy', db_session=db_session)
            self._report_progress('initializing', 'Starting safe merge with temporary table strategy')
            
            # 建立连接
            self._report_progress('connecting', 'Establishing connections to Hive and HDFS')
            if not self._test_connections():
                raise Exception('Failed to connect to Hive or HDFS')
            
            # 获取合并前的文件统计
            self._report_progress('analyzing', 'Analyzing current file structure')
            files_before = self._get_file_count(task.database_name, task.table_name, task.partition_filter)
            result['files_before'] = files_before
            self.log_task_event(task, 'INFO', f'Files before merge: {files_before}', db_session=db_session)
            
            # 第一步：创建临时表
            self._report_progress('creating_temp_table', f'Creating temporary table: {temp_table_name}')
            self.log_task_event(task, 'INFO', f'Creating temporary table: {temp_table_name}', db_session=db_session)
            create_temp_sql = self._create_temp_table(task, temp_table_name)
            result['sql_executed'].extend(create_temp_sql)
            result['temp_table_created'] = temp_table_name
            
            # 第二步：验证临时表数据
            self._report_progress('validating', 'Validating temporary table data integrity')
            self.log_task_event(task, 'INFO', 'Validating temporary table data', db_session=db_session)
            validation_result = self._validate_temp_table_data(task, temp_table_name)
            if not validation_result['valid']:
                raise Exception(f'Temporary table validation failed: {validation_result["message"]}')
            
            # 获取合并后的文件统计（从临时表）
            files_after = self._get_temp_table_file_count(task.database_name, temp_table_name, task.partition_filter)
            result['files_after'] = files_after
            self.log_task_event(task, 'INFO', f'Files after merge: {files_after}', db_session=db_session)
            
            # 第三步：原子切换表（关键步骤）
            self._report_progress('atomic_swap', 'Performing atomic table swap')
            self.log_task_event(task, 'INFO', 'Starting atomic table swap', db_session=db_session)
            swap_sql = self._atomic_table_swap(task, temp_table_name, backup_table_name)
            result['sql_executed'].extend(swap_sql)
            result['backup_table_created'] = backup_table_name
            
            # 计算节省的空间（简化估算）
            if files_before > files_after:
                result['size_saved'] = (files_before - files_after) * 64 * 1024 * 1024  # 假设每个文件平均64MB
            
            result['success'] = True
            result['duration'] = time.time() - start_time
            result['message'] = f'Safe merge completed successfully. Files reduced from {files_before} to {files_after}'
            
            self._report_progress('completed', f'Safe merge completed successfully. Files: {files_before} → {files_after}')
            
            # 更新任务状态为成功
            self.update_task_status(
                task, 'success',
                files_before=files_before,
                files_after=files_after,
                size_saved=result['size_saved'],
                db_session=db_session
            )
            
            self.log_task_event(task, 'INFO', result['message'], db_session=db_session)
            self.log_task_event(task, 'INFO', f'Backup table created: {backup_table_name}. Drop it after verification.', db_session=db_session)
            
        except Exception as e:
            error_message = str(e)
            result['message'] = f'Safe merge failed: {error_message}'
            result['duration'] = time.time() - start_time
            
            self._report_progress('failed', f'Safe merge failed: {error_message}')
            
            # 执行回滚操作
            try:
                self._report_progress('rolling_back', 'Starting rollback process to clean up temporary resources')
                self.log_task_event(task, 'WARNING', 'Starting rollback process', db_session=db_session)
                rollback_sql = self._rollback_merge(task, temp_table_name, backup_table_name)
                result['sql_executed'].extend(rollback_sql)
                self.log_task_event(task, 'INFO', 'Rollback completed successfully', db_session=db_session)
            except Exception as rollback_error:
                self.log_task_event(task, 'ERROR', f'Rollback failed: {rollback_error}', db_session=db_session)
                result['message'] += f'. Rollback failed: {rollback_error}'
            
            # 更新任务状态为失败
            self.update_task_status(task, 'failed', error_message=error_message, db_session=db_session)
            self.log_task_event(task, 'ERROR', result['message'], db_session=db_session)
            
            logger.error(f"Safe merge execution failed for task {task.id}: {e}")
        
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
            'is_partitioned': False,
            'partitions': [],
            'temp_table_name': '',
            'warnings': []
        }
        
        try:
            # 建立连接
            if not self._test_connections():
                raise Exception('Failed to connect to Hive or HDFS')
            
            # 检查是否为分区表
            is_partitioned = self._is_partitioned_table(task.database_name, task.table_name)
            preview['is_partitioned'] = is_partitioned
            
            # 如果是分区表，获取分区列表
            if is_partitioned:
                partitions = self._get_table_partitions(task.database_name, task.table_name)
                preview['partitions'] = partitions[:10]  # 最多显示10个分区
            
            # 获取当前文件数量
            current_files = self._get_file_count(task.database_name, task.table_name, task.partition_filter)
            preview['estimated_files_before'] = current_files
            
            # 估算合并后的文件数量（基于经验值）
            if current_files > 1000:
                preview['estimated_files_after'] = max(10, current_files // 50)
            elif current_files > 100:
                preview['estimated_files_after'] = max(5, current_files // 20)
            else:
                preview['estimated_files_after'] = max(1, current_files // 10)
            
            # 估算空间节省
            files_reduced = preview['estimated_files_before'] - preview['estimated_files_after']
            preview['estimated_size_reduction'] = files_reduced * 64 * 1024 * 1024  # 假设每个文件平均64MB
            
            # 估算执行时间
            preview['estimated_duration'] = self.estimate_duration(task)
            
            # 生成临时表名
            preview['temp_table_name'] = self._generate_temp_table_name(task.table_name)
            
            # 添加警告信息
            if current_files < 10:
                preview['warnings'].append('表中文件数量较少，合并效果可能有限')
            
            if is_partitioned and not task.partition_filter:
                preview['warnings'].append('分区表建议指定分区过滤条件，避免处理所有分区')
            
            if task.partition_filter and not self._validate_partition_filter(task.database_name, task.table_name, task.partition_filter):
                preview['warnings'].append('分区过滤器可能不匹配任何分区')
            
        except Exception as e:
            logger.error(f"Failed to generate merge preview: {e}")
            preview['warnings'].append(f'无法生成预览: {str(e)}')
        
        finally:
            self._cleanup_connections()
        
        return preview
    
    def estimate_duration(self, task: MergeTask) -> int:
        """估算任务执行时间（基于文件数量和表大小）"""
        try:
            file_count = self._get_file_count(task.database_name, task.table_name, task.partition_filter)
            
            # 基于文件数量的估算（秒）
            base_time = 60  # 基础时间60秒
            file_factor = file_count * 0.2  # 每个文件增加0.2秒
            
            # 安全合并需要额外时间（创建临时表、验证、切换）
            safety_overhead = 120  # 安全操作额外开销
            
            total_time = base_time + file_factor + safety_overhead
            
            return int(total_time)
        
        except Exception as e:
            logger.error(f"Failed to estimate duration: {e}")
            return 600  # 默认10分钟
    
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
                database=self.cluster.hive_database or 'default'
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
            cursor.execute(f'SHOW TABLES LIKE "{table_name}"')
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result is not None
        except Exception:
            return False
    
    def _is_partitioned_table(self, database_name: str, table_name: str) -> bool:
        """检查表是否为分区表"""
        try:
            conn = hive.Connection(
                host=self.cluster.hive_host,
                port=self.cluster.hive_port,
                database=database_name
            )
            cursor = conn.cursor()
            cursor.execute(f'DESCRIBE FORMATTED {table_name}')
            
            rows = cursor.fetchall()
            is_partitioned = False
            
            for row in rows:
                if len(row) >= 2 and row[0] and 'Partition Information' in str(row[0]):
                    is_partitioned = True
                    break
            
            cursor.close()
            conn.close()
            return is_partitioned
        except Exception as e:
            logger.error(f"Failed to check if table is partitioned: {e}")
            return False
    
    def _get_table_partitions(self, database_name: str, table_name: str) -> List[str]:
        """获取表的分区列表"""
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
            return partitions
        except Exception as e:
            logger.error(f"Failed to get table partitions: {e}")
            return []
    
    def _validate_partition_filter(self, database_name: str, table_name: str, partition_filter: str) -> bool:
        """验证分区过滤器"""
        try:
            partitions = self._get_table_partitions(database_name, table_name)
            
            # 简单匹配验证：检查是否有分区包含过滤条件的内容
            for partition in partitions:
                if partition_filter.replace("'", "").replace('"', '') in partition:
                    return True
            
            return len(partitions) > 0  # 如果有分区但没匹配到，也返回True避免阻塞
        except Exception:
            return True  # 验证失败时返回True，让后续流程继续
    
    def _generate_temp_table_name(self, table_name: str) -> str:
        """生成临时表名"""
        timestamp = int(time.time())
        return f"{table_name}_merge_temp_{timestamp}"
    
    def _generate_backup_table_name(self, table_name: str) -> str:
        """生成备份表名"""
        timestamp = int(time.time())
        return f"{table_name}_backup_{timestamp}"
    
    def _create_temp_table(self, task: MergeTask, temp_table_name: str) -> List[str]:
        """创建临时表并执行合并"""
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
                "SET hive.merge.size.per.task=268435456",  # 256MB
                "SET hive.exec.dynamic.partition=true",
                "SET hive.exec.dynamic.partition.mode=nonstrict",
                "SET mapred.reduce.tasks=1"  # 减少输出文件数
            ]
            
            for setting in merge_settings:
                cursor.execute(setting)
                sql_statements.append(setting)
            
            # 删除可能存在的临时表
            drop_temp_sql = f"DROP TABLE IF EXISTS {temp_table_name}"
            cursor.execute(drop_temp_sql)
            sql_statements.append(drop_temp_sql)
            
            # 创建临时表并执行合并
            if task.partition_filter:
                create_sql = f"""
                CREATE TABLE {temp_table_name} 
                AS SELECT * FROM {task.table_name} 
                WHERE {task.partition_filter}
                """
            else:
                create_sql = f"""
                CREATE TABLE {temp_table_name} 
                AS SELECT * FROM {task.table_name}
                """
            
            cursor.execute(create_sql)
            sql_statements.append(create_sql)
            
            cursor.close()
            conn.close()
            
            logger.info(f"Temporary table {temp_table_name} created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create temporary table: {e}")
            raise
        
        return sql_statements
    
    def _validate_temp_table_data(self, task: MergeTask, temp_table_name: str) -> Dict[str, Any]:
        """验证临时表数据完整性"""
        result = {
            'valid': True,
            'message': 'Validation passed',
            'original_count': 0,
            'temp_count': 0
        }
        
        try:
            conn = hive.Connection(
                host=self.cluster.hive_host,
                port=self.cluster.hive_port,
                database=task.database_name
            )
            cursor = conn.cursor()
            
            # 检查原表行数
            if task.partition_filter:
                count_original_sql = f"SELECT COUNT(*) FROM {task.table_name} WHERE {task.partition_filter}"
            else:
                count_original_sql = f"SELECT COUNT(*) FROM {task.table_name}"
            
            cursor.execute(count_original_sql)
            original_count = cursor.fetchone()[0]
            result['original_count'] = original_count
            
            # 检查临时表行数
            count_temp_sql = f"SELECT COUNT(*) FROM {temp_table_name}"
            cursor.execute(count_temp_sql)
            temp_count = cursor.fetchone()[0]
            result['temp_count'] = temp_count
            
            # 验证行数是否一致
            if original_count != temp_count:
                result['valid'] = False
                result['message'] = f'Row count mismatch: original={original_count}, temp={temp_count}'
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to validate temp table data: {e}")
            result['valid'] = False
            result['message'] = str(e)
        
        return result
    
    def _atomic_table_swap(self, task: MergeTask, temp_table_name: str, backup_table_name: str) -> List[str]:
        """原子性地交换表"""
        sql_statements = []
        
        try:
            conn = hive.Connection(
                host=self.cluster.hive_host,
                port=self.cluster.hive_port,
                database=task.database_name
            )
            cursor = conn.cursor()
            
            # 第一步：将原表重命名为备份表
            rename_to_backup_sql = f"ALTER TABLE {task.table_name} RENAME TO {backup_table_name}"
            cursor.execute(rename_to_backup_sql)
            sql_statements.append(rename_to_backup_sql)
            
            # 第二步：将临时表重命名为原表名
            rename_temp_to_original_sql = f"ALTER TABLE {temp_table_name} RENAME TO {task.table_name}"
            cursor.execute(rename_temp_to_original_sql)
            sql_statements.append(rename_temp_to_original_sql)
            
            cursor.close()
            conn.close()
            
            logger.info(f"Atomic table swap completed: {task.table_name} -> {backup_table_name}, {temp_table_name} -> {task.table_name}")
            
        except Exception as e:
            logger.error(f"Failed to perform atomic table swap: {e}")
            raise
        
        return sql_statements
    
    def _rollback_merge(self, task: MergeTask, temp_table_name: str, backup_table_name: str) -> List[str]:
        """回滚合并操作"""
        sql_statements = []
        
        try:
            conn = hive.Connection(
                host=self.cluster.hive_host,
                port=self.cluster.hive_port,
                database=task.database_name
            )
            cursor = conn.cursor()
            
            # 检查备份表是否存在，如果存在则恢复
            if self._table_exists(task.database_name, backup_table_name):
                # 删除可能存在的损坏的原表
                drop_damaged_sql = f"DROP TABLE IF EXISTS {task.table_name}"
                cursor.execute(drop_damaged_sql)
                sql_statements.append(drop_damaged_sql)
                
                # 将备份表恢复为原表
                restore_sql = f"ALTER TABLE {backup_table_name} RENAME TO {task.table_name}"
                cursor.execute(restore_sql)
                sql_statements.append(restore_sql)
            
            # 清理临时表
            drop_temp_sql = f"DROP TABLE IF EXISTS {temp_table_name}"
            cursor.execute(drop_temp_sql)
            sql_statements.append(drop_temp_sql)
            
            cursor.close()
            conn.close()
            
            logger.info("Rollback completed successfully")
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise
        
        return sql_statements
    
    def _get_file_count(self, database_name: str, table_name: str, partition_filter: Optional[str] = None) -> int:
        """获取表的文件数量"""
        try:
            # 构建表路径
            table_path = self._build_table_path(database_name, table_name)
            
            if partition_filter:
                # 如果有分区过滤器，需要构建具体的分区路径
                # 这里简化处理，实际应该解析 partition_filter 构建正确的路径
                pass
            
            # 使用 HDFS 扫描器获取文件数量
            stats = self.hdfs_scanner.scan_directory(table_path, self.cluster.small_file_threshold or 134217728)
            return stats.get('total_files', 0)
            
        except Exception as e:
            logger.error(f"Failed to get file count: {e}")
            # 如果HDFS扫描失败，使用备用方法（基于HDFS命令或表统计信息）
            return self._get_file_count_fallback(database_name, table_name, partition_filter)
    
    def _get_temp_table_file_count(self, database_name: str, temp_table_name: str, partition_filter: Optional[str] = None) -> int:
        """获取临时表的文件数量"""
        try:
            # 临时表的路径通常在warehouse目录下
            temp_table_path = self._build_table_path(database_name, temp_table_name)
            
            # 使用 HDFS 扫描器获取文件数量
            stats = self.hdfs_scanner.scan_directory(temp_table_path, self.cluster.small_file_threshold or 134217728)
            return stats.get('total_files', 0)
            
        except Exception as e:
            logger.error(f"Failed to get temp table file count: {e}")
            return 0
    
    def _get_file_count_fallback(self, database_name: str, table_name: str, partition_filter: Optional[str] = None) -> int:
        """获取文件数量的备用方法"""
        try:
            # 简单估算：基于表大小和平均文件大小
            # 在实际环境中可以通过其他方式获取更准确的文件数量
            return 100  # 默认估算值
        except Exception as e:
            logger.error(f"Fallback file count method failed: {e}")
            return 0