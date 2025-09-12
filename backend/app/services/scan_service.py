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
        table_name: Optional[str] = None
    ):
        """添加任务日志"""
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
        total_small_files: int = None
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
    
    def scan_cluster_with_progress(self, db: Session, cluster_id: int, max_tables_per_db: int = 20) -> str:
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
            try:
                self._execute_cluster_scan(db, task, cluster, max_tables_per_db)
            except Exception as e:
                self.add_log(task.task_id, 'ERROR', f'扫描失败: {str(e)}')
                self.complete_task(db, task.task_id, success=False, error_message=str(e))
        
        thread = threading.Thread(target=run_scan)
        thread.daemon = True
        thread.start()
        
        return task.task_id
    
    def _execute_cluster_scan(self, db: Session, task: ScanTask, cluster: Cluster, max_tables_per_db: int):
        """执行实际的集群扫描"""
        self.add_log(task.task_id, 'INFO', f'开始扫描集群: {cluster.name}')
        self.update_task_progress(db, task.task_id, status='running')
        
        try:
            # 获取所有数据库
            with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as connector:
                databases = connector.get_databases()
            
            self.update_task_progress(db, task.task_id, total_items=len(databases))
            self.add_log(task.task_id, 'INFO', f'找到 {len(databases)} 个数据库')
            
            scanner = HybridTableScanner(cluster)
            total_tables_scanned = 0
            total_files_found = 0
            total_small_files = 0
            
            # 扫描每个数据库
            for i, database_name in enumerate(databases, 1):
                self.update_task_progress(
                    db, task.task_id, 
                    completed_items=i-1,
                    current_item=f'扫描数据库: {database_name}'
                )
                self.add_log(task.task_id, 'INFO', f'开始扫描数据库: {database_name}', database_name=database_name)
                
                try:
                    # 扫描数据库中的表
                    result = scanner.scan_database_tables(db, database_name, max_tables=max_tables_per_db)
                    
                    tables_scanned = result.get('tables_scanned', 0)
                    files_found = result.get('total_files', 0)
                    small_files = result.get('total_small_files', 0)
                    
                    total_tables_scanned += tables_scanned
                    total_files_found += files_found
                    total_small_files += small_files
                    
                    self.add_log(
                        task.task_id, 'INFO', 
                        f'数据库 {database_name} 扫描完成: {tables_scanned}表, {files_found}文件, {small_files}小文件',
                        database_name=database_name
                    )
                    
                except Exception as db_error:
                    self.add_log(
                        task.task_id, 'ERROR', 
                        f'数据库 {database_name} 扫描失败: {str(db_error)}',
                        database_name=database_name
                    )
            
            # 更新最终统计
            self.update_task_progress(
                db, task.task_id,
                completed_items=len(databases),
                total_tables_scanned=total_tables_scanned,
                total_files_found=total_files_found,
                total_small_files=total_small_files
            )
            
            self.add_log(
                task.task_id, 'INFO', 
                f'集群扫描完成! 总计: {total_tables_scanned}表, {total_files_found}文件, {total_small_files}小文件'
            )
            
            self.complete_task(db, task.task_id, success=True)
            
        except Exception as e:
            self.add_log(task.task_id, 'ERROR', f'集群扫描失败: {str(e)}')
            self.complete_task(db, task.task_id, success=False, error_message=str(e))


# 全局任务管理器实例
scan_task_manager = ScanTaskManager()