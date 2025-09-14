import logging
import re
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import time
from sqlalchemy.orm import Session
from pyhive import hive

from app.engines.base_engine import BaseMergeEngine
from app.models.merge_task import MergeTask
from app.models.cluster import Cluster
from app.monitor.hive_connector import HiveMetastoreConnector
from app.utils.webhdfs_client import WebHDFSClient
from app.config.database import SessionLocal
from app.models.table_metric import TableMetric
from app.services.path_resolver import PathResolver
from app.utils.yarn_monitor import YarnResourceManagerMonitor
from app.utils.encryption import decrypt_cluster_password
from app.utils.merge_logger import MergeTaskLogger, MergePhase, MergeLogLevel

logger = logging.getLogger(__name__)

class SafeHiveMergeEngine(BaseMergeEngine):
    """
    安全的Hive合并引擎
    使用临时表+原子重命名的策略，确保合并过程中原表可读
    支持分区级别的合并操作
    """
    
    def __init__(self, cluster: Cluster):
        super().__init__(cluster)
        # 使用 WebHDFSClient 进行文件统计，移除对 HDFSScanner 的依赖
        self.hdfs_scanner = None
        self.metastore_connector = HiveMetastoreConnector(cluster.hive_metastore_url)
        self.progress_callback: Optional[Callable[[str, str], None]] = None
        
        # 初始化WebHDFS客户端用于精确的文件统计
        self.webhdfs_client = WebHDFSClient(
            namenode_url=cluster.hdfs_namenode_url,
            user=cluster.hdfs_user or "hdfs"
        )
        
        # 初始化YARN监控器（如果配置了YARN RM URL）
        self.yarn_monitor = None
        if cluster.yarn_resource_manager_url:
            yarn_urls = [url.strip() for url in cluster.yarn_resource_manager_url.split(',')]
            self.yarn_monitor = YarnResourceManagerMonitor(yarn_urls)
        
        # 解密LDAP密码
        self.hive_password = None
        if cluster.hive_password:
            # 解密失败时回退到明文，以兼容直接存放明文密码的环境
            try:
                self.hive_password = decrypt_cluster_password(cluster)
            except Exception:
                self.hive_password = None
            if not self.hive_password:
                self.hive_password = cluster.hive_password
    
    def set_progress_callback(self, callback: Callable[[str, str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def _report_progress(self, phase: str, message: str):
        """报告执行进度"""
        if self.progress_callback:
            self.progress_callback(phase, message)
        logger.info(f"[{phase}] {message}")
    
    def _update_task_progress(self, task: MergeTask, db_session: Session, 
                             execution_phase: str = None, 
                             progress_percentage: float = None,
                             estimated_remaining_time: int = None,
                             processed_files_count: int = None,
                             total_files_count: int = None,
                             yarn_application_id: str = None,
                             current_operation: str = None):
        """更新任务的详细进度信息到数据库"""
        try:
            if execution_phase is not None:
                task.execution_phase = execution_phase
            if progress_percentage is not None:
                task.progress_percentage = progress_percentage
            if estimated_remaining_time is not None:
                task.estimated_remaining_time = estimated_remaining_time
            if processed_files_count is not None:
                task.processed_files_count = processed_files_count
            if total_files_count is not None:
                task.total_files_count = total_files_count
            if yarn_application_id is not None:
                task.yarn_application_id = yarn_application_id
            if current_operation is not None:
                task.current_operation = current_operation
            
            db_session.commit()
            logger.debug(f"Updated task {task.id} progress: {execution_phase} - {progress_percentage}%")
        except Exception as e:
            logger.error(f"Failed to update task progress: {e}")
            db_session.rollback()
    
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
            
            # 存储/格式检查：禁止对不受支持的表进行合并（如 Hudi/Iceberg/Delta/ACID）
            fmt = self._get_table_format_info(task.database_name, task.table_name)
            if self._is_unsupported_table_type(fmt):
                result['valid'] = False
                result['message'] = self._unsupported_reason(fmt)
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
        """执行安全文件合并（带详尽日志记录）"""
        start_time = time.time()
        
        # 初始化详尽日志记录器
        merge_logger = MergeTaskLogger(task, db_session)
        
        result = {
            'success': False,
            'files_before': 0,
            'files_after': 0,
            'size_saved': 0,
            'duration': 0.0,
            'message': '',
            'sql_executed': [],
            'temp_table_created': '',
            'backup_table_created': '',
            'log_summary': {},
            'detailed_logs': []
        }
        
        temp_table_name = self._generate_temp_table_name(task.table_name)
        backup_table_name = self._generate_backup_table_name(task.table_name)

        # 运行期再次进行严格的表类型校验，避免误操作
        fmt = self._get_table_format_info(task.database_name, task.table_name)
        if self._is_unsupported_table_type(fmt):
            msg = self._unsupported_reason(fmt)
            self._report_progress('failed', msg)
            self.update_task_status(task, 'failed', error_message=msg, db_session=db_session)
            return {
                'success': False,
                'files_before': 0,
                'files_after': 0,
                'size_saved': 0,
                'duration': time.time() - start_time,
                'message': msg,
                'sql_executed': [],
                'temp_table_created': '',
                'backup_table_created': '',
                'log_summary': {},
                'detailed_logs': []
            }

        # 如果指定了分区过滤器，优先按分区级别执行合并（不进行整表原子切换）
        if task.partition_filter:
            try:
                # 连接测试
                if not self._test_connections():
                    raise Exception('Failed to connect to Hive or HDFS')

                # 预统计：分区文件数
                part_path = self._resolve_partition_path(task.database_name, task.table_name, task.partition_filter)
                files_before = None
                files_after = None
                if part_path:
                    try:
                        stats_before = self.webhdfs_client.scan_directory_stats(part_path, self.cluster.small_file_threshold or 134217728)
                        files_before = int(getattr(stats_before, 'total_files', 0) or 0)
                    except Exception:
                        files_before = None

                spec = self._partition_filter_to_spec(task.partition_filter)
                if not spec:
                    raise Exception(f'Unsupported partition_filter: {task.partition_filter}')

                # 路径一：CONCATENATE（原地合并）
                if (task.merge_strategy or 'concatenate') == 'concatenate':
                    merge_logger.start_phase(MergePhase.TEMP_TABLE_CREATION, "分区级合并（CONCATENATE）")
                    conn = self._create_hive_connection(task.database_name)
                    cursor = conn.cursor()
                    sql = f"ALTER TABLE {task.table_name} PARTITION ({spec}) CONCATENATE"
                    merge_logger.log_sql_execution(sql, MergePhase.TEMP_TABLE_CREATION)
                    cursor.execute(sql)
                    cursor.close(); conn.close()
                    merge_logger.end_phase(MergePhase.TEMP_TABLE_CREATION, "分区 CONCATENATE 完成")
                else:
                    # 路径二：INSERT OVERWRITE 单分区（重写分区数据，控制 reducer 数减少文件数）
                    merge_logger.start_phase(MergePhase.TEMP_TABLE_CREATION, "分区级合并（INSERT OVERWRITE）")
                    nonpart_cols, part_cols = self._get_table_columns(task.database_name, task.table_name)
                    if not nonpart_cols:
                        raise Exception('Failed to get table columns')
                    conn = self._create_hive_connection(task.database_name)
                    cursor = conn.cursor()
                    settings = [
                        "SET hive.merge.mapfiles=true",
                        "SET hive.merge.mapredfiles=true",
                        "SET hive.exec.dynamic.partition.mode=nonstrict",
                        "SET hive.tez.auto.reducer.parallelism=false",
                        "SET mapred.reduce.tasks=1"
                    ]
                    for st in settings:
                        merge_logger.log_sql_execution(st, MergePhase.TEMP_TABLE_CREATION, success=True)
                        cursor.execute(st)
                    # 静态分区覆盖：分区列不出现在 SELECT 列表
                    cols_expr = ', '.join([f"`{c}`" for c in nonpart_cols])
                    insert_sql = (
                        f"INSERT OVERWRITE TABLE {task.table_name} PARTITION ({spec}) "
                        f"SELECT {cols_expr} FROM {task.table_name} WHERE {task.partition_filter} DISTRIBUTE BY 1"
                    )
                    merge_logger.log_sql_execution(insert_sql, MergePhase.TEMP_TABLE_CREATION)
                    cursor.execute(insert_sql)
                    cursor.close(); conn.close()
                    merge_logger.end_phase(MergePhase.TEMP_TABLE_CREATION, "分区 INSERT OVERWRITE 完成")

                # 统计合并后文件数
                if part_path:
                    try:
                        stats_after = self.webhdfs_client.scan_directory_stats(part_path, self.cluster.small_file_threshold or 134217728)
                        files_after = int(getattr(stats_after, 'total_files', 0) or 0)
                    except Exception:
                        files_after = None

                # 汇总结果
                result['success'] = True
                result['duration'] = time.time() - start_time
                result['message'] = (
                    f"Partition-level merge completed via "
                    f"{(task.merge_strategy or 'concatenate').upper()} for ({spec})"
                )
                result['files_before'] = files_before
                result['files_after'] = files_after
                result['size_saved'] = 0

                # 更新任务状态
                self._update_task_progress(
                    task, db_session,
                    execution_phase="completion",
                    progress_percentage=100.0,
                    processed_files_count=files_after if files_after is not None else 0,
                    current_operation=f"分区合并完成: PARTITION ({spec})"
                )
                self.update_task_status(
                    task, 'success',
                    files_before=files_before if isinstance(files_before, int) else None,
                    files_after=files_after if isinstance(files_after, int) else None,
                    size_saved=0,
                    db_session=db_session
                )
                self.log_task_event(task, 'INFO', result['message'], db_session=db_session)
                return result
            except Exception as e:
                # 若分区级失败，直接失败（不做整表替代）
                result['message'] = f'Partition-level merge failed: {e}'
                result['duration'] = time.time() - start_time
                self._report_progress('failed', result['message'])
                self.update_task_status(task, 'failed', error_message=str(e), db_session=db_session)
                self.log_task_event(task, 'ERROR', result['message'], db_session=db_session)
                return result
        
        try:
            # 更新任务状态为运行中
            self.update_task_status(task, 'running', db_session=db_session)
            merge_logger.start_phase(MergePhase.INITIALIZATION, "初始化安全合并任务", {
                "temp_table_name": temp_table_name,
                "backup_table_name": backup_table_name,
                "merge_strategy": "safe_hive_engine"
            })
            
            # 更新进度：初始化阶段
            self._update_task_progress(
                task, db_session, 
                execution_phase="initialization",
                progress_percentage=5.0,
                current_operation="初始化安全合并任务"
            )
            self._report_progress('initializing', 'Starting safe merge with temporary table strategy')
            
            # 建立连接
            merge_logger.start_phase(MergePhase.CONNECTION_TEST, "建立Hive、HDFS、YARN连接")
            self._report_progress('connecting', 'Establishing connections to Hive and HDFS')
            
            if not self._test_connections():
                merge_logger.end_phase(MergePhase.CONNECTION_TEST, "连接测试失败", success=False, details={
                    "hive_host": self.cluster.hive_host,
                    "hdfs_namenode": self.cluster.hdfs_namenode_url,
                    "yarn_rm": self.cluster.yarn_resource_manager_url
                })
                raise Exception('Failed to connect to Hive or HDFS')
            
            merge_logger.end_phase(MergePhase.CONNECTION_TEST, "所有连接测试成功", success=True)
            
            # 更新进度：连接测试完成
            self._update_task_progress(
                task, db_session,
                execution_phase="connection_test",
                progress_percentage=10.0,
                current_operation="连接测试完成"
            )
            
            # 获取合并前的文件统计
            merge_logger.start_phase(MergePhase.FILE_ANALYSIS, "分析当前文件结构")
            self._report_progress('analyzing', 'Analyzing current file structure')
            
            # 更新进度：文件分析阶段
            self._update_task_progress(
                task, db_session,
                execution_phase="file_analysis", 
                progress_percentage=15.0,
                current_operation="分析当前文件结构"
            )
            
            files_before = self._get_file_count_with_logging(task.database_name, task.table_name, 
                                                           task.partition_filter, merge_logger)
            result['files_before'] = files_before
            
            merge_logger.log_file_statistics(
                MergePhase.FILE_ANALYSIS, 
                f"{task.database_name}.{task.table_name}",
                files_before=files_before
            )
            merge_logger.end_phase(MergePhase.FILE_ANALYSIS, f"文件分析完成，当前{files_before if files_before is not None else '未知'}个文件")
            
            # 更新进度：文件分析完成，包含文件数信息
            self._update_task_progress(
                task, db_session,
                execution_phase="file_analysis",
                progress_percentage=25.0,
                total_files_count=files_before,
                current_operation=f"文件分析完成，发现{files_before if files_before is not None else '未知'}个文件"
            )
            
            # 第一步：创建临时表
            merge_logger.start_phase(MergePhase.TEMP_TABLE_CREATION, f"创建临时表: {temp_table_name}")
            self._report_progress('creating_temp_table', f'Creating temporary table: {temp_table_name}')
            
            # 更新进度：创建临时表阶段
            self._update_task_progress(
                task, db_session,
                execution_phase="temp_table_creation",
                progress_percentage=35.0,
                current_operation=f"创建临时表: {temp_table_name}"
            )
            
            create_temp_sql = self._create_temp_table_with_logging(task, temp_table_name, merge_logger)
            result['sql_executed'].extend(create_temp_sql)
            result['temp_table_created'] = temp_table_name
            
            merge_logger.end_phase(MergePhase.TEMP_TABLE_CREATION, f"临时表创建完成: {temp_table_name}")
            
            # 更新进度：临时表创建完成
            self._update_task_progress(
                task, db_session,
                execution_phase="temp_table_creation", 
                progress_percentage=45.0,
                current_operation=f"临时表创建完成: {temp_table_name}"
            )
            
            # 第二步：验证临时表数据
            merge_logger.start_phase(MergePhase.DATA_VALIDATION, "验证临时表数据完整性")
            self._report_progress('validating', 'Validating temporary table data integrity')
            
            # 更新进度：数据验证阶段
            self._update_task_progress(
                task, db_session,
                execution_phase="data_validation",
                progress_percentage=55.0,
                current_operation="验证临时表数据完整性"
            )
            
            validation_result = self._validate_temp_table_data(task, temp_table_name)
            
            merge_logger.log_data_validation(
                MergePhase.DATA_VALIDATION, "行数一致性检查",
                validation_result['original_count'], validation_result['temp_count'],
                validation_result['valid'], details=validation_result
            )
            
            if not validation_result['valid']:
                merge_logger.end_phase(MergePhase.DATA_VALIDATION, "数据验证失败", success=False)
                raise Exception(f'Temporary table validation failed: {validation_result["message"]}')
            
            merge_logger.end_phase(MergePhase.DATA_VALIDATION, "数据验证通过")
            
            # 获取合并后的文件统计（从临时表）
            files_after = self._get_temp_table_file_count(task.database_name, temp_table_name, task.partition_filter)
            result['files_after'] = files_after
            
            merge_logger.log_file_statistics(
                MergePhase.DATA_VALIDATION, temp_table_name,
                files_after=files_after
            )
            
            # 第三步：原子切换表（关键步骤）
            merge_logger.start_phase(MergePhase.ATOMIC_SWAP, "执行原子表切换")
            self._report_progress('atomic_swap', 'Performing atomic table swap')
            
            # 更新进度：原子切换阶段
            self._update_task_progress(
                task, db_session,
                execution_phase="atomic_swap",
                progress_percentage=75.0,
                processed_files_count=files_after,
                current_operation="执行原子表切换"
            )
            
            swap_sql = self._atomic_table_swap_with_logging(task, temp_table_name, backup_table_name, merge_logger)
            result['sql_executed'].extend(swap_sql)
            result['backup_table_created'] = backup_table_name
            
            merge_logger.end_phase(MergePhase.ATOMIC_SWAP, "原子表切换完成")
            
            # 更新进度：原子切换完成
            self._update_task_progress(
                task, db_session,
                execution_phase="atomic_swap",
                progress_percentage=85.0,
                current_operation="原子表切换完成"
            )
            
            # 切换完成后，重新统计一次目标表文件数，确保展示准确
            try:
                files_after_actual = self._get_file_count_with_logging(
                    task.database_name, task.table_name, task.partition_filter, merge_logger
                )
                if isinstance(files_after_actual, int):
                    files_after = files_after_actual
                    result['files_after'] = files_after
            except Exception as _:
                pass

            # 计算节省的空间（简化估算）
            if isinstance(files_before, int) and isinstance(files_after, int) and files_before > files_after:
                result['size_saved'] = (files_before - files_after) * 64 * 1024 * 1024  # 假设每个文件平均64MB
            
            result['success'] = True
            result['duration'] = time.time() - start_time
            result['message'] = (
                f"Safe merge completed successfully. Files reduced from "
                f"{files_before if files_before is not None else 'NaN'} to {files_after if files_after is not None else 'NaN'}"
            )
            result['log_summary'] = merge_logger.get_log_summary()
            
            merge_logger.log_task_completion(True, int(result['duration'] * 1000), {
                "files_before": files_before,
                "files_after": files_after,
                "files_reduced": files_before - files_after,
                "size_saved": result['size_saved']
            })
            
            self._report_progress('completed', f"Safe merge completed successfully. Files: {files_before if files_before is not None else 'NaN'} → {files_after if files_after is not None else 'NaN'}")
            
            # 更新进度：任务完成
            self._update_task_progress(
                task, db_session,
                execution_phase="completion",
                progress_percentage=100.0,
                processed_files_count=files_after,
                current_operation=f"合并完成：{files_before if files_before is not None else 'NaN'} → {files_after if files_after is not None else 'NaN'} 文件"
            )
            
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
        """测试连接：Hive 成功即可放行，HDFS 失败仅告警"""
        # 1) HDFS/HttpFS（不作为阻塞条件）
        try:
            ok, msg = self.webhdfs_client.test_connection()
            if not ok:
                logger.warning(f"WebHDFS test failed: {msg} (non-blocking)")
        except Exception as e:
            logger.warning(f"WebHDFS test exception: {e} (non-blocking)")

        # 2) Hive（必须成功）
        try:
            hive_conn_params = {
                'host': self.cluster.hive_host,
                'port': self.cluster.hive_port,
                'database': self.cluster.hive_database or 'default'
            }
            if (self.cluster.auth_type or '').upper() == "LDAP" and self.cluster.hive_username:
                hive_conn_params['username'] = self.cluster.hive_username
                if self.hive_password:
                    hive_conn_params['password'] = self.hive_password
                hive_conn_params['auth'] = 'LDAP'
                logger.info(f"Using LDAP authentication for user: {self.cluster.hive_username}")

            conn = hive.Connection(**hive_conn_params)
            cursor = conn.cursor(); cursor.execute('SELECT 1'); cursor.fetchall()
            cursor.close(); conn.close()
            logger.info("Hive connection test passed")
            return True
        except Exception as e:
            logger.error(f"Hive connection test failed: {e}")
            return False
    
    def _get_table_location(self, database_name: str, table_name: str) -> Optional[str]:
        """获取表的HDFS位置（优先MetaStore，其次HS2，最后默认路径）"""
        try:
            return PathResolver.get_table_location(self.cluster, database_name, table_name)
        except Exception as e:
            logger.error(f"Failed to resolve table location: {e}")
            return None

    def _create_hive_connection(self, database_name: str = None):
        """创建Hive连接（支持LDAP认证）"""
        hive_conn_params = {
            'host': self.cluster.hive_host,
            'port': self.cluster.hive_port,
            'database': database_name or self.cluster.hive_database or 'default'
        }
        
        # 如果配置了LDAP认证
        if self.cluster.auth_type == "LDAP" and self.cluster.hive_username:
            hive_conn_params['username'] = self.cluster.hive_username
            if self.hive_password:
                hive_conn_params['password'] = self.hive_password
            hive_conn_params['auth'] = 'LDAP'
            logger.debug(f"Creating LDAP connection for user: {self.cluster.hive_username}")
        
        return hive.Connection(**hive_conn_params)

    def _cleanup_connections(self):
        """清理连接"""
        try:
            if self.hdfs_scanner:
                self.hdfs_scanner.disconnect()
            self.webhdfs_client.close()
            if self.yarn_monitor:
                self.yarn_monitor.close()
        except Exception as e:
            logger.warning(f"Failed to cleanup connections: {e}")
    
    def _table_exists(self, database_name: str, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            conn = self._create_hive_connection(database_name)
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
            conn = self._create_hive_connection(database_name)
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
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f'SHOW PARTITIONS {table_name}')
            partitions = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return partitions
        except Exception as e:
            logger.error(f"Failed to get table partitions: {e}")
            return []

    def _get_table_format_info(self, database_name: str, table_name: str) -> Dict[str, Any]:
        """获取表的格式/属性信息，用于安全校验。
        返回：{'input_format': str, 'serde_lib': str, 'storage_handler': str, 'tblproperties': {k:v}}
        """
        info: Dict[str, Any] = {
            'input_format': '',
            'serde_lib': '',
            'storage_handler': '',
            'tblproperties': {}
        }
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            # 读取格式信息
            cursor.execute(f"DESCRIBE FORMATTED {table_name}")
            rows = cursor.fetchall()
            for row in rows:
                if not row or len(row) < 2:
                    continue
                k = str(row[0]).strip()
                v = str(row[1]).strip() if row[1] is not None else ''
                if 'InputFormat' in k:
                    info['input_format'] = v
                elif 'SerDe Library' in k:
                    info['serde_lib'] = v
                elif 'Storage Handler' in k:
                    info['storage_handler'] = v
            # 读取表属性
            try:
                cursor.execute(f"SHOW TBLPROPERTIES {table_name}")
                props = cursor.fetchall()
                for pr in props:
                    # 常见返回为 (key, value)
                    if len(pr) >= 2:
                        info['tblproperties'][str(pr[0]).strip()] = str(pr[1]).strip()
            except Exception:
                pass
            cursor.close(); conn.close()
        except Exception:
            pass
        return info

    def _is_unsupported_table_type(self, fmt: Dict[str, Any]) -> bool:
        """识别不受支持的表类型（Hudi/Iceberg/Delta/ACID等）"""
        input_fmt = str(fmt.get('input_format', '')).lower()
        serde_lib = str(fmt.get('serde_lib', '')).lower()
        storage_handler = str(fmt.get('storage_handler', '')).lower()
        props = {str(k).lower(): str(v).lower() for k, v in fmt.get('tblproperties', {}).items()}

        # Hudi 检测：handler/serde/input 或 hoodie.* 属性
        if ('hudi' in input_fmt or 'hudi' in serde_lib or 'hudi' in storage_handler or
            any(k.startswith('hoodie.') for k in props.keys())):
            return True
        # Iceberg 检测
        if 'iceberg' in input_fmt or 'iceberg' in storage_handler or 'iceberg' in serde_lib:
            return True
        # Delta 检测
        if 'delta' in input_fmt or 'delta' in storage_handler or 'delta' in serde_lib:
            return True
        # ACID 事务表：必须 transactional=true 或 storage handler 含 acid
        if props.get('transactional') == 'true' or 'acid' in storage_handler:
            return True
        return False

    def _unsupported_reason(self, fmt: Dict[str, Any]) -> str:
        input_fmt = str(fmt.get('input_format', '')).lower()
        serde_lib = str(fmt.get('serde_lib', '')).lower()
        storage_handler = str(fmt.get('storage_handler', '')).lower()
        props = {str(k).lower(): str(v).lower() for k, v in fmt.get('tblproperties', {}).items()}

        if ('hudi' in input_fmt or 'hudi' in serde_lib or 'hudi' in storage_handler or
            any(k.startswith('hoodie.') for k in props.keys())):
            return '目标表为 Hudi 表，当前合并引擎不支持对 Hudi 表执行合并，请使用 Hudi 自带的压缩/合并机制（如 compaction/cluster）'
        if 'iceberg' in input_fmt or 'iceberg' in storage_handler or 'iceberg' in serde_lib:
            return '目标表为 Iceberg 表，当前合并引擎不支持该表的合并操作'
        if 'delta' in input_fmt or 'delta' in storage_handler or 'delta' in serde_lib:
            return '目标表为 Delta 表，当前合并引擎不支持该表的合并操作'
        if props.get('transactional') == 'true' or 'acid' in storage_handler:
            return '目标表为 ACID/事务表，当前合并引擎不支持该表的合并操作'
        return '目标表类型不受支持，已阻止合并操作'

    def _get_table_columns(self, database_name: str, table_name: str) -> (List[str], List[str]):
        """获取表的字段列表（非分区列、分区列）"""
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f'DESCRIBE FORMATTED {table_name}')
            rows = cursor.fetchall()
            cursor.close(); conn.close()
            nonpart: List[str] = []
            parts: List[str] = []
            in_part = False
            for row in rows:
                if not row or len(row) < 1:
                    continue
                first = str(row[0]).strip()
                if not first:
                    continue
                if first.startswith('#'):
                    if 'Partition Information' in first:
                        in_part = True
                    continue
                if first.lower() == 'col_name' or first.lower().startswith('name'):
                    continue
                # 过滤非字段行（如详细信息）
                if ':' in first:
                    # 进入详细信息部分
                    break
                if in_part:
                    parts.append(first)
                else:
                    nonpart.append(first)
            # 去掉可能的空白/无效项
            nonpart = [c for c in nonpart if c and c != 'col_name']
            parts = [c for c in parts if c and c != 'col_name']
            return nonpart, parts
        except Exception:
            return [], []

    def _partition_filter_to_spec(self, partition_filter: str) -> Optional[str]:
        """将 WHERE 风格的分区过滤转换为 PARTITION 规范，例如:
        "dt='2024-01-01' AND region='cn'" -> "dt='2024-01-01', region='cn'"
        仅支持等值 AND 组合。
        """
        if not partition_filter:
            return None
        # 标准化 AND 分隔为逗号（不区分大小写）
        normalized = re.sub(r"\s+and\s+", ",", partition_filter.strip(), flags=re.IGNORECASE)
        parts = [p.strip() for p in normalized.split(',') if p.strip()]
        specs = []
        for p in parts:
            if '=' not in p:
                return None
            k, v = p.split('=', 1)
            k = k.strip()
            v = v.strip()
            # 如果值没有引号且不是纯数字，补充单引号
            if not (v.startswith("'") or v.startswith('"')):
                if re.fullmatch(r"[0-9]+", v):
                    pass
                else:
                    v = f"'{v}'"
            specs.append(f"{k}={v}")
        return ', '.join(specs) if specs else None

    def _resolve_partition_path(self, database_name: str, table_name: str, partition_filter: str) -> Optional[str]:
        """根据分区过滤器解析分区在 HDFS 的路径（在表根路径下拼接spec）。"""
        try:
            root = self._get_table_location(database_name, table_name)
            if not root:
                return None
            # 规范化为路径: key=value/key2=value2
            normalized = re.sub(r"\s+and\s+", '/', partition_filter.strip(), flags=re.IGNORECASE)
            normalized = normalized.replace(',', '/').replace(' ', '')
            normalized = normalized.replace("'", '').replace('"', '')
            if not normalized:
                return None
            return root.rstrip('/') + '/' + normalized
        except Exception:
            return None
    
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
            conn = self._create_hive_connection(task.database_name)
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
            conn = self._create_hive_connection(task.database_name)
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
            conn = self._create_hive_connection(task.database_name)
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
            conn = self._create_hive_connection(task.database_name)
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
    
    def _get_file_count(self, database_name: str, table_name: str, partition_filter: Optional[str] = None) -> Optional[int]:
        """获取表的文件数量（使用WebHDFS精确统计）"""
        try:
            # 获取表的HDFS路径
            table_location = self._get_table_location(database_name, table_name)
            if not table_location:
                logger.error(f"Could not get table location for {database_name}.{table_name}")
                return None
            
            logger.info(f"Getting file count for table {database_name}.{table_name} at location: {table_location}")
            
            # 使用WebHDFS客户端获取准确的文件统计
            stats = self.webhdfs_client.get_table_hdfs_stats(
                table_location, 
                self.cluster.small_file_threshold or 134217728
            )
            
            if stats.get('success', False):
                total_files = stats.get('total_files', 0)
                logger.info(f"WebHDFS stats for {database_name}.{table_name}: {total_files} files, "
                           f"{stats.get('small_files_count', 0)} small files")
                return total_files
            else:
                logger.error(f"WebHDFS stats failed: {stats.get('error', 'Unknown error')}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to get file count using WebHDFS: {e}")
            # 如果WebHDFS失败，使用备用方法
            return self._get_file_count_fallback(database_name, table_name, partition_filter)
    
    def _get_temp_table_file_count(self, database_name: str, temp_table_name: str, partition_filter: Optional[str] = None) -> Optional[int]:
        """获取临时表的文件数量（使用WebHDFS精确统计）"""
        try:
            # 获取临时表的HDFS路径
            table_location = self._get_table_location(database_name, temp_table_name)
            if not table_location:
                logger.error(f"Could not get temp table location for {database_name}.{temp_table_name}")
                return None
            
            logger.info(f"Getting file count for temp table {database_name}.{temp_table_name} at location: {table_location}")
            
            # 使用WebHDFS客户端获取准确的文件统计
            stats = self.webhdfs_client.get_table_hdfs_stats(
                table_location, 
                self.cluster.small_file_threshold or 134217728
            )
            
            if stats.get('success', False):
                total_files = stats.get('total_files', 0)
                logger.info(f"WebHDFS stats for temp table {database_name}.{temp_table_name}: {total_files} files")
                return total_files
            else:
                logger.error(f"WebHDFS stats failed for temp table: {stats.get('error', 'Unknown error')}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to get temp table file count: {e}")
            return None
    
    def _get_file_count_fallback(self, database_name: str, table_name: str, partition_filter: Optional[str] = None) -> Optional[int]:
        """获取文件数量的备用方法"""
        try:
            # 简单估算：基于表大小和平均文件大小
            # 在实际环境中可以通过其他方式获取更准确的文件数量
            return None  # 统计失败不再估算，交由前端显示 NaN
        except Exception as e:
            logger.error(f"Fallback file count method failed: {e}")
            return 0
    
    def _get_file_count_with_logging(self, database_name: str, table_name: str, 
                                   partition_filter: Optional[str], merge_logger) -> int:
        """带日志记录的文件数量获取"""
        try:
            table_location = self._get_table_location(database_name, table_name)
            if not table_location:
                merge_logger.log(
                    MergePhase.FILE_ANALYSIS, MergeLogLevel.ERROR,
                    f"无法获取表{database_name}.{table_name}的HDFS位置",
                    details={"database": database_name, "table": table_name}
                )
                return 0
            
            merge_logger.log_hdfs_operation(
                "get_table_stats", table_location, MergePhase.FILE_ANALYSIS
            )
            
            stats = self.webhdfs_client.get_table_hdfs_stats(
                table_location, self.cluster.small_file_threshold or 134217728
            )
            
            if stats.get('success', False):
                file_count = stats.get('total_files', 0)
                merge_logger.log_hdfs_operation(
                    "get_table_stats", table_location, MergePhase.FILE_ANALYSIS,
                    stats=stats, success=True
                )
                return file_count
            else:
                merge_logger.log_hdfs_operation(
                    "get_table_stats", table_location, MergePhase.FILE_ANALYSIS,
                    success=False, error_message=stats.get('error', 'Unknown error')
                )
                # 兜底：使用最近一次扫描指标
                try:
                    db = SessionLocal()
                    metric = (
                        db.query(TableMetric)
                        .filter(
                            TableMetric.cluster_id == self.cluster.id,
                            TableMetric.database_name == database_name,
                            TableMetric.table_name == table_name,
                        )
                        .order_by(TableMetric.scan_time.desc())
                        .first()
                    )
                    if metric and metric.total_files is not None:
                        merge_logger.log(
                            MergePhase.FILE_ANALYSIS, MergeLogLevel.INFO,
                            "使用最近一次扫描指标兜底文件数",
                            details={"total_files": metric.total_files}
                        )
                        return int(metric.total_files)
                except Exception:
                    pass
                return 0
                
        except Exception as e:
            merge_logger.log(
                MergePhase.FILE_ANALYSIS, MergeLogLevel.ERROR,
                f"获取文件数量失败: {str(e)}",
                details={"error": str(e), "table": f"{database_name}.{table_name}"}
            )
            return self._get_file_count_fallback(database_name, table_name, partition_filter)
    
    def _create_temp_table_with_logging(self, task: MergeTask, temp_table_name: str, merge_logger) -> List[str]:
        """带详细日志记录的临时表创建"""
        sql_statements = []
        
        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()
            
            # 设置 Hive 合并参数
            merge_settings = [
                "SET hive.merge.mapfiles=true",
                "SET hive.merge.mapredfiles=true", 
                "SET hive.merge.size.per.task=268435456",  # 256MB
                "SET hive.exec.dynamic.partition=true",
                "SET hive.exec.dynamic.partition.mode=nonstrict",
                # 关键：禁止 Tez 自动并行，配合单 reducer 强制减少输出文件数
                "SET hive.tez.auto.reducer.parallelism=false",
                "SET mapred.reduce.tasks=1"  # 减少输出文件数
            ]
            
            for setting in merge_settings:
                merge_logger.log_sql_execution(setting, MergePhase.TEMP_TABLE_CREATION, success=True)
                cursor.execute(setting)
                sql_statements.append(setting)
            
            # 删除可能存在的临时表
            drop_temp_sql = f"DROP TABLE IF EXISTS {temp_table_name}"
            merge_logger.log_sql_execution(drop_temp_sql, MergePhase.TEMP_TABLE_CREATION)
            cursor.execute(drop_temp_sql)
            sql_statements.append(drop_temp_sql)
            
            # 创建临时表并执行合并
            if task.partition_filter:
                create_sql = f"""
                CREATE TABLE {temp_table_name} 
                AS SELECT * FROM {task.table_name} 
                WHERE {task.partition_filter}
                DISTRIBUTE BY 1
                """
            else:
                create_sql = f"""
                CREATE TABLE {temp_table_name} 
                AS SELECT * FROM {task.table_name}
                DISTRIBUTE BY 1
                """
            
            merge_logger.log_sql_execution(create_sql, MergePhase.TEMP_TABLE_CREATION)
            cursor.execute(create_sql)
            sql_statements.append(create_sql)
            
            cursor.close()
            conn.close()
            
            merge_logger.log(
                MergePhase.TEMP_TABLE_CREATION, MergeLogLevel.INFO,
                f"临时表{temp_table_name}创建成功",
                details={"temp_table": temp_table_name, "sql_count": len(sql_statements)}
            )
            
        except Exception as e:
            merge_logger.log_sql_execution(
                create_sql if 'create_sql' in locals() else "CREATE TABLE ...", 
                MergePhase.TEMP_TABLE_CREATION,
                success=False, error_message=str(e)
            )
            raise
        
        return sql_statements
    
    def _atomic_table_swap_with_logging(self, task: MergeTask, temp_table_name: str, 
                                      backup_table_name: str, merge_logger) -> List[str]:
        """带详细日志记录的原子表切换"""
        sql_statements = []
        
        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()
            
            # 第一步：将原表重命名为备份表
            rename_to_backup_sql = f"ALTER TABLE {task.table_name} RENAME TO {backup_table_name}"
            merge_logger.log_sql_execution(rename_to_backup_sql, MergePhase.ATOMIC_SWAP)
            cursor.execute(rename_to_backup_sql)
            sql_statements.append(rename_to_backup_sql)
            
            merge_logger.log(
                MergePhase.ATOMIC_SWAP, MergeLogLevel.INFO,
                f"原表重命名为备份表: {task.table_name} -> {backup_table_name}",
                details={"original_table": task.table_name, "backup_table": backup_table_name}
            )
            
            # 第二步：将临时表重命名为原表名
            rename_temp_to_original_sql = f"ALTER TABLE {temp_table_name} RENAME TO {task.table_name}"
            merge_logger.log_sql_execution(rename_temp_to_original_sql, MergePhase.ATOMIC_SWAP)
            cursor.execute(rename_temp_to_original_sql)
            sql_statements.append(rename_temp_to_original_sql)
            
            merge_logger.log(
                MergePhase.ATOMIC_SWAP, MergeLogLevel.INFO,
                f"临时表重命名为原表: {temp_table_name} -> {task.table_name}",
                details={"temp_table": temp_table_name, "original_table": task.table_name}
            )
            
            cursor.close()
            conn.close()
            
            merge_logger.log(
                MergePhase.ATOMIC_SWAP, MergeLogLevel.INFO,
                "原子表切换成功完成",
                details={
                    "swap_operations": 2,
                    "backup_created": backup_table_name,
                    "active_table": task.table_name
                }
            )
            
        except Exception as e:
            merge_logger.log(
                MergePhase.ATOMIC_SWAP, MergeLogLevel.ERROR,
                f"原子表切换失败: {str(e)}",
                details={"error": str(e), "failed_operation": "table_rename"}
            )
            raise
        
        return sql_statements
