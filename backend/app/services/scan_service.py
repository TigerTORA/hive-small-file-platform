from typing import Dict, List, Optional
import time
import json
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.scan_task import ScanTask
from app.models.cluster import Cluster
from app.monitor.hybrid_table_scanner import HybridTableScanner
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.schemas.scan_task import ScanTaskLog
from app.config.database import SessionLocal


class ScanTaskManager:
    """扫描任务管理器，支持进度追踪和日志记录"""
    
    def __init__(self):
        self.active_tasks: Dict[str, ScanTask] = {}
        self.task_logs: Dict[str, List[ScanTaskLog]] = {}
        self._lock = threading.Lock()
    
    def create_scan_task(
        self, 
        db: Session,
        cluster_id: int,
        task_type: str,
        task_name: str,
        target_database: Optional[str] = None,
        target_table: Optional[str] = None
    ) -> ScanTask:
        """创建扫描任务"""
        task = ScanTask(
            cluster_id=cluster_id,
            task_type=task_type,
            task_name=task_name,
            status='pending'
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        with self._lock:
            self.active_tasks[task.task_id] = task
            self.task_logs[task.task_id] = []
        
        return task
    
    def get_task(self, task_id: str) -> Optional[ScanTask]:
        """获取任务状态"""
        with self._lock:
            return self.active_tasks.get(task_id)
    
    def get_task_logs(self, task_id: str) -> List[ScanTaskLog]:
        """获取任务日志"""
        with self._lock:
            return self.task_logs.get(task_id, [])
    
    def add_log(
        self,
        task_id: str,
        level: str,
        message: str,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
        db: Optional[Session] = None,
    ):
        """添加任务日志（内存 + 可选持久化）"""
        log_entry = ScanTaskLog(
            timestamp=datetime.utcnow(),
            level=level,
            message=message,
            database_name=database_name,
            table_name=table_name
        )
        
        with self._lock:
            if task_id in self.task_logs:
                self.task_logs[task_id].append(log_entry)
                # 只保留最近100条日志
                if len(self.task_logs[task_id]) > 100:
                    self.task_logs[task_id] = self.task_logs[task_id][-100:]
        
        # 可选持久化到数据库
        if db is not None:
            try:
                from app.models.scan_task import ScanTask as ScanTaskModel
                from app.models.scan_task_log import ScanTaskLogDB
                db_task = db.query(ScanTaskModel).filter(ScanTaskModel.task_id == task_id).first()
                if db_task:
                    db_row = ScanTaskLogDB(
                        scan_task_id=db_task.id,
                        level=level,
                        message=message,
                        database_name=database_name,
                        table_name=table_name,
                    )
                    db.add(db_row)
                    db.commit()
            except Exception:
                # 持久化失败不影响主流程
                pass
    
    def update_task_progress(
        self, 
        db: Session,
        task_id: str, 
        completed_items: int = None,
        current_item: str = None,
        total_items: int = None,
        status: str = None,
        error_message: str = None,
        total_tables_scanned: int = None,
        total_files_found: int = None,
        total_small_files: int = None,
        estimated_remaining_seconds: int = None,
    ):
        """更新任务进度"""
        with self._lock:
            task = self.active_tasks.get(task_id)
            if not task:
                return
            
            if completed_items is not None:
                task.completed_items = completed_items
            if current_item is not None:
                task.current_item = current_item
            if total_items is not None:
                task.total_items = total_items
            if status is not None:
                task.status = status
            if error_message is not None:
                task.error_message = error_message
            if total_tables_scanned is not None:
                task.total_tables_scanned = total_tables_scanned
            if total_files_found is not None:
                task.total_files_found = total_files_found
            if total_small_files is not None:
                task.total_small_files = total_small_files
            
            # 更新数据库
            db_task = db.query(ScanTask).filter(ScanTask.task_id == task_id).first()
            if db_task:
                for key, value in task.__dict__.items():
                    if not key.startswith('_') and value is not None:
                        setattr(db_task, key, value)
                db.commit()

    def safe_update_progress(self, db: Session, task_id: str, **kwargs):
        """安全更新进度：
        - 仅透传已支持字段
        - 忽略未知字段并记录 WARN 日志
        - 任意异常将被捕获并记录，不中断主流程
        """
        allowed = {
            'completed_items', 'current_item', 'total_items', 'status', 'error_message',
            'total_tables_scanned', 'total_files_found', 'total_small_files',
            'estimated_remaining_seconds'
        }
        passed = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        ignored = [k for k in kwargs.keys() if k not in allowed]
        if ignored:
            try:
                self.add_log(task_id, 'WARN', f'safe_update_progress 忽略未知字段: {ignored}', db=db)
            except Exception:
                pass
        try:
            return self.update_task_progress(db, task_id, **passed)
        except Exception as e:
            try:
                self.add_log(task_id, 'WARN', f'safe_update_progress 更新失败: {e}', db=db)
            except Exception:
                pass
            return None
    
    def complete_task(self, db: Session, task_id: str, success: bool = True, error_message: str = None):
        """完成任务"""
        with self._lock:
            task = self.active_tasks.get(task_id)
            if not task:
                return
            
            task.status = 'completed' if success else 'failed'
            task.end_time = datetime.utcnow()
            task.duration = (task.end_time - task.start_time).total_seconds()
            
            if error_message:
                task.error_message = error_message
            
            # 更新数据库
            db_task = db.query(ScanTask).filter(ScanTask.task_id == task_id).first()
            if db_task:
                db_task.status = task.status
                db_task.end_time = task.end_time
                db_task.duration = task.duration
                if error_message:
                    db_task.error_message = error_message
                db.commit()
    
    from typing import Optional
    def scan_cluster_with_progress(self, db: Session, cluster_id: int, max_tables_per_db: Optional[int] = None, strict_real: bool = False) -> str:
        """执行集群扫描（带进度追踪）"""
        # 获取集群信息
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise ValueError("Cluster not found")
        
        # 创建任务
        task = self.create_scan_task(
            db, 
            cluster_id, 
            'cluster', 
            f'扫描集群: {cluster.name}'
        )
        
        # 在后台线程中执行扫描
        def run_scan():
            # 为后台线程创建独立的数据库会话，避免跨线程复用同一 Session 导致崩溃
            db_thread = SessionLocal()
            try:
                # 重新获取 cluster 与 task，确保在该会话上下文中托管
                cluster_t = db_thread.query(Cluster).filter(Cluster.id == cluster.id).first() if cluster else None
                task_t = db_thread.query(ScanTask).filter(ScanTask.id == task.id).first() if task else None
                if not cluster_t or not task_t:
                    raise RuntimeError('Failed to load task/cluster in thread-local session')

                self._execute_cluster_scan(db_thread, task_t, cluster_t, max_tables_per_db, strict_real)
            except Exception as e:
                try:
                    self.add_log(task.task_id, 'ERROR', f'扫描失败: {str(e)}', db=db_thread)
                finally:
                    self.complete_task(db_thread, task.task_id, success=False, error_message=str(e))
            finally:
                try:
                    db_thread.close()
                except Exception:
                    pass
        
        thread = threading.Thread(target=run_scan)
        thread.daemon = True
        thread.start()
        
        return task.task_id
    
    def _execute_cluster_scan(self, db: Session, task: ScanTask, cluster: Cluster, max_tables_per_db: Optional[int], strict_real: bool):
        """执行实际的集群扫描"""
        scan_start_time = time.time()
        self.add_log(task.task_id, 'INFO', f'🚀 开始扫描集群: {cluster.name}', db=db)
        self.safe_update_progress(db, task.task_id, status='running')
        
        try:
            # 步骤1: 测试连接
            self.add_log(task.task_id, 'INFO', f'🔗 正在连接MetaStore: {cluster.hive_metastore_url}', db=db)
            
            # 获取所有数据库
            databases = []
            metastore_connect_start = time.time()
            try:
                with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as connector:
                    databases = connector.get_databases()
                metastore_connect_time = time.time() - metastore_connect_start
                self.add_log(task.task_id, 'INFO', f'✅ MetaStore连接成功 (耗时: {metastore_connect_time:.2f}秒)', db=db)
                self.add_log(task.task_id, 'INFO', f'📊 发现 {len(databases)} 个数据库: {", ".join(databases[:5])}{"..." if len(databases) > 5 else ""}', db=db)
            except Exception as conn_error:
                self.add_log(task.task_id, 'ERROR', f'❌ MetaStore连接失败: {str(conn_error)}', db=db)
                self.add_log(task.task_id, 'INFO', f'💡 建议检查: 1) 网络连通性 2) 数据库服务状态 3) 用户权限', db=db)
                raise conn_error
            
            # 步骤2: 初始化扫描器和HDFS连接
            self.add_log(task.task_id, 'INFO', f'🔗 正在连接HDFS: {cluster.hdfs_namenode_url}', db=db)
            scanner = HybridTableScanner(cluster)
            hdfs_connect_start = time.time()
            
            # 测试HDFS连接
            scanner._initialize_hdfs_scanner()
            hdfs_ok = False
            try:
                hdfs_ok = scanner.hdfs_scanner.connect() if scanner.hdfs_scanner else False
                hdfs_connect_time = time.time() - hdfs_connect_start
                if hdfs_ok:
                    self.add_log(task.task_id, 'INFO', f'✅ HDFS连接成功 (耗时: {hdfs_connect_time:.2f}秒)', db=db)
                    scanner.hdfs_scanner.disconnect()
                else:
                    if strict_real:
                        raise Exception('HDFS连接失败（严格模式），中止扫描')
                    self.add_log(task.task_id, 'WARN', f'⚠️ HDFS连接失败，启用Mock模式继续扫描', db=db)
            except Exception as hdfs_error:
                if strict_real:
                    raise
                self.add_log(task.task_id, 'WARN', f'⚠️ HDFS连接失败: {str(hdfs_error)}', db=db)
                self.add_log(task.task_id, 'INFO', f'🔄 启用Mock HDFS模式进行演示扫描', db=db)
            
            # 步骤3: 开始批量扫描
            self.safe_update_progress(db, task.task_id, total_items=len(databases))
            estimated_total_time = len(databases) * 3  # 估算每个数据库3秒
            self.add_log(task.task_id, 'INFO', f'⏱️ 预计总扫描时间: {estimated_total_time}秒，每数据库限制扫描{max_tables_per_db}张表', db=db)
            
            total_tables_scanned = 0
            total_files_found = 0
            total_small_files = 0
            successful_databases = 0
            failed_databases = 0
            
            # 扫描每个数据库
            for i, database_name in enumerate(databases, 1):
                db_scan_start = time.time()
                self.safe_update_progress(
                    db, task.task_id, 
                    completed_items=i-1,
                    current_item=f'扫描数据库: {database_name}'
                )
                self.add_log(task.task_id, 'INFO', f'📁 [{i}/{len(databases)}] 开始扫描数据库: {database_name}', database_name=database_name, db=db)
                
                try:
                    # 扫描数据库中的表
                    result = scanner.scan_database_tables(db, database_name, max_tables=max_tables_per_db, strict_real=strict_real)
                    db_scan_time = time.time() - db_scan_start
                    
                    tables_scanned = result.get('tables_scanned', 0)
                    files_found = result.get('total_files', 0)
                    small_files = result.get('total_small_files', 0)
                    successful_tables = result.get('successful_tables', 0)
                    failed_tables = result.get('failed_tables', 0)
                    partitioned_tables = result.get('partitioned_tables', 0)
                    hdfs_mode = result.get('hdfs_mode', 'unknown')
                    scan_errors = result.get('errors', [])
                    metastore_time = result.get('metastore_query_time', 0)
                    hdfs_connect_time = result.get('hdfs_connect_time', 0)
                    original_table_count = result.get('original_table_count', 0)
                    filtered_table_count = result.get('filtered_table_count', 0)
                    limited_by_count = result.get('limited_by_count', 0)
                    avg_table_scan_time = result.get('avg_table_scan_time', 0)
                    
                    total_tables_scanned += tables_scanned
                    total_files_found += files_found
                    total_small_files += small_files
                    
                    # 记录详细的扫描过程信息
                    self.add_log(task.task_id, 'INFO', f'  └─ MetaStore查询: {metastore_time:.2f}秒, 发现{original_table_count}张表', database_name=database_name, db=db)
                    
                    if limited_by_count > 0:
                        self.add_log(task.task_id, 'INFO', f'  └─ 表数量限制: 跳过{limited_by_count}张表 (限制{max_tables_per_db}张/数据库)', database_name=database_name, db=db)
                    
                    if hdfs_mode != 'real':
                        self.add_log(task.task_id, 'INFO', f'  └─ HDFS连接: {hdfs_connect_time:.2f}秒 ({hdfs_mode}模式)', database_name=database_name, db=db)
                    
                    # 计算小文件比例
                    small_file_ratio = (small_files / files_found * 100) if files_found > 0 else 0
                    
                    # 生成详细的完成日志
                    status_parts = []
                    if successful_tables > 0:
                        status_parts.append(f'{successful_tables}表成功')
                    if failed_tables > 0:
                        status_parts.append(f'{failed_tables}表失败')
                    if partitioned_tables > 0:
                        status_parts.append(f'{partitioned_tables}个分区表')
                    
                    log_message = f'✅ 数据库 {database_name} 扫描完成: {", ".join(status_parts)}, {files_found}文件, {small_files}小文件'
                    if files_found > 0:
                        log_message += f' ({small_file_ratio:.1f}%)'
                    
                    if hdfs_mode == 'mock':
                        log_message += ' [Mock模式]'
                    
                    log_message += f' (耗时: {db_scan_time:.1f}秒, 平均{avg_table_scan_time:.2f}秒/表)'
                    
                    self.add_log(task.task_id, 'INFO', log_message, database_name=database_name, db=db)
                    
                    # 记录重要的警告和错误（过滤掉不重要的）
                    important_errors = [e for e in scan_errors if any(keyword in e for keyword in ['失败', '错误', '过高', 'Error', 'Failed'])]
                    for error in important_errors[:3]:  # 只显示前3个重要错误
                        if '小文件比例过高' in error:
                            self.add_log(task.task_id, 'WARN', f'  ⚠️ {error}', database_name=database_name, db=db)
                        else:
                            self.add_log(task.task_id, 'ERROR', f'  ❌ {error}', database_name=database_name, db=db)
                    
                    # 更新进度和剩余时间估算
                    remaining_dbs = len(databases) - i
                    avg_time_per_db = (time.time() - scan_start_time) / i
                    estimated_remaining = remaining_dbs * avg_time_per_db
                    
                    self.safe_update_progress(
                        db, task.task_id,
                        completed_items=i,
                        estimated_remaining_seconds=int(estimated_remaining)
                    )
                    # 确认该数据库扫描成功
                    successful_databases += 1
                    
                except Exception as db_error:
                    failed_databases += 1
                    db_scan_time = time.time() - db_scan_start
                    self.add_log(
                        task.task_id,
                        'ERROR',
                        f'❌ 数据库 {database_name} 扫描失败: {str(db_error)} (耗时: {db_scan_time:.1f}秒)',
                        database_name=database_name,
                        db=db,
                    )
                    # 提供具体的错误诊断建议
                    if "permission" in str(db_error).lower():
                        self.add_log(task.task_id, 'INFO', f'  💡 建议检查HDFS用户权限和访问策略', database_name=database_name, db=db)
                    elif "connection" in str(db_error).lower():
                        self.add_log(task.task_id, 'INFO', f'  💡 建议检查网络连通性和服务状态', database_name=database_name, db=db)
            
            # 最终统计和性能指标
            total_scan_time = time.time() - scan_start_time
            success_rate = (successful_databases / len(databases)) * 100 if databases else 0
            avg_time_per_db = total_scan_time / len(databases) if databases else 0
            avg_time_per_table = total_scan_time / total_tables_scanned if total_tables_scanned else 0
            
            self.safe_update_progress(
                db, task.task_id,
                completed_items=len(databases),
                total_tables_scanned=total_tables_scanned,
                total_files_found=total_files_found,
                total_small_files=total_small_files
            )
            
            # 生成详细的完成报告
            overall_small_file_ratio = (total_small_files / total_files_found * 100) if total_files_found > 0 else 0
            completion_message = f'🎉 集群扫描完成! 总计: {total_tables_scanned}表, {total_files_found}文件, {total_small_files}小文件 ({overall_small_file_ratio:.1f}%)'
            self.add_log(task.task_id, 'INFO', completion_message, db=db)
            
            # 性能统计
            self.add_log(task.task_id, 'INFO', f'📈 扫描统计: 耗时{total_scan_time:.1f}秒, 成功率{success_rate:.1f}%, 平均每表{avg_time_per_table:.2f}秒', db=db)
            self.add_log(task.task_id, 'INFO', f'📊 处理效率: {successful_databases}个数据库成功, {failed_databases}个失败', db=db)
            
            # 根据结果给出建议
            if overall_small_file_ratio > 70:
                self.add_log(task.task_id, 'WARN', f'⚠️ 小文件比例过高({overall_small_file_ratio:.1f}%)，建议立即执行合并优化', db=db)
            elif overall_small_file_ratio > 50:
                self.add_log(task.task_id, 'INFO', f'💡 建议对小文件比例较高的表进行合并处理', db=db)
            
            self.complete_task(db, task.task_id, success=True)
            
        except Exception as e:
            total_scan_time = time.time() - scan_start_time
            error_msg = str(e)
            self.add_log(task.task_id, 'ERROR', f'💥 集群扫描失败: {error_msg} (运行时间: {total_scan_time:.1f}秒)', db=db)
            
            # 根据错误类型提供具体建议
            if "Failed to connect to MetaStore" in error_msg:
                self.add_log(task.task_id, 'INFO', f'🔧 MetaStore连接问题排查:', db=db)
                self.add_log(task.task_id, 'INFO', f'  1. 检查网络连通性: ping {cluster.hive_metastore_url}', db=db)
                self.add_log(task.task_id, 'INFO', f'  2. 验证数据库服务状态和端口开放', db=db)
                self.add_log(task.task_id, 'INFO', f'  3. 确认用户名密码和数据库权限', db=db)
            elif "timeout" in error_msg.lower():
                self.add_log(task.task_id, 'INFO', f'⏱️ 连接超时问题可能原因:', db=db)
                self.add_log(task.task_id, 'INFO', f'  1. 网络延迟过高或防火墙阻挡', db=db)
                self.add_log(task.task_id, 'INFO', f'  2. 目标服务过载或响应缓慢', db=db)
            
            self.complete_task(db, task.task_id, success=False, error_message=error_msg)


# 全局任务管理器实例
scan_task_manager = ScanTaskManager()
