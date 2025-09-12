"""
表级别资源锁管理器
防止同时对同一个表执行多个合并任务
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.merge_task import MergeTask

logger = logging.getLogger(__name__)

class TableLockManager:
    """表级别资源锁管理器"""
    
    @classmethod
    def acquire_table_lock(cls, db: Session, cluster_id: int, database_name: str, 
                          table_name: str, task_id: int, 
                          lock_timeout_minutes: int = 120) -> Dict[str, Any]:
        """
        获取表级别锁
        
        Args:
            db: 数据库会话
            cluster_id: 集群ID
            database_name: 数据库名
            table_name: 表名
            task_id: 任务ID
            lock_timeout_minutes: 锁超时时间（分钟）
            
        Returns:
            锁获取结果
        """
        try:
            # 检查是否有其他运行中的任务锁定了这个表
            existing_lock = db.query(MergeTask).filter(
                and_(
                    MergeTask.cluster_id == cluster_id,
                    MergeTask.database_name == database_name,
                    MergeTask.table_name == table_name,
                    MergeTask.table_lock_acquired == True,
                    MergeTask.status.in_(['pending', 'running']),
                    MergeTask.id != task_id  # 排除自己
                )
            ).first()
            
            if existing_lock:
                # 检查锁是否已过期
                if cls._is_lock_expired(existing_lock, lock_timeout_minutes):
                    logger.warning(f"Found expired lock on table {database_name}.{table_name}, releasing it")
                    cls._force_release_lock(db, existing_lock)
                else:
                    return {
                        'success': False,
                        'message': f'Table {database_name}.{table_name} is locked by task {existing_lock.id}',
                        'locked_by_task': existing_lock.id,
                        'lock_holder': existing_lock.lock_holder
                    }
            
            # 获取当前任务并设置锁
            current_task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
            if not current_task:
                return {
                    'success': False,
                    'message': f'Task {task_id} not found'
                }
            
            # 设置锁
            current_task.table_lock_acquired = True
            current_task.lock_holder = f"task_{task_id}"
            db.commit()
            
            logger.info(f"Acquired table lock for {database_name}.{table_name} by task {task_id}")
            
            return {
                'success': True,
                'message': f'Table lock acquired for {database_name}.{table_name}',
                'lock_holder': f"task_{task_id}"
            }
            
        except Exception as e:
            logger.error(f"Failed to acquire table lock: {e}")
            db.rollback()
            return {
                'success': False,
                'message': f'Failed to acquire lock: {str(e)}'
            }
    
    @classmethod
    def release_table_lock(cls, db: Session, task_id: int) -> Dict[str, Any]:
        """
        释放表级别锁
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            
        Returns:
            锁释放结果
        """
        try:
            task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
            if not task:
                return {
                    'success': False,
                    'message': f'Task {task_id} not found'
                }
            
            if task.table_lock_acquired:
                task.table_lock_acquired = False
                task.lock_holder = None
                db.commit()
                
                logger.info(f"Released table lock for {task.database_name}.{task.table_name} by task {task_id}")
                
                return {
                    'success': True,
                    'message': f'Table lock released for {task.database_name}.{task.table_name}'
                }
            else:
                return {
                    'success': True,
                    'message': 'No lock was held by this task'
                }
                
        except Exception as e:
            logger.error(f"Failed to release table lock: {e}")
            db.rollback()
            return {
                'success': False,
                'message': f'Failed to release lock: {str(e)}'
            }
    
    @classmethod
    def check_table_lock_status(cls, db: Session, cluster_id: int, 
                               database_name: str, table_name: str) -> Dict[str, Any]:
        """
        检查表锁状态
        
        Args:
            db: 数据库会话
            cluster_id: 集群ID
            database_name: 数据库名
            table_name: 表名
            
        Returns:
            锁状态信息
        """
        try:
            active_lock = db.query(MergeTask).filter(
                and_(
                    MergeTask.cluster_id == cluster_id,
                    MergeTask.database_name == database_name,
                    MergeTask.table_name == table_name,
                    MergeTask.table_lock_acquired == True,
                    MergeTask.status.in_(['pending', 'running'])
                )
            ).first()
            
            if active_lock:
                return {
                    'locked': True,
                    'locked_by_task': active_lock.id,
                    'lock_holder': active_lock.lock_holder,
                    'task_status': active_lock.status,
                    'locked_since': active_lock.started_time or active_lock.created_time
                }
            else:
                return {
                    'locked': False,
                    'message': f'Table {database_name}.{table_name} is not locked'
                }
                
        except Exception as e:
            logger.error(f"Failed to check table lock status: {e}")
            return {
                'locked': False,
                'error': str(e)
            }
    
    @classmethod
    def cleanup_expired_locks(cls, db: Session, lock_timeout_minutes: int = 120) -> Dict[str, Any]:
        """
        清理过期的锁
        
        Args:
            db: 数据库会话
            lock_timeout_minutes: 锁超时时间（分钟）
            
        Returns:
            清理结果
        """
        try:
            # 查找所有持有锁但已过期的任务
            expired_tasks = db.query(MergeTask).filter(
                and_(
                    MergeTask.table_lock_acquired == True,
                    MergeTask.status.in_(['pending', 'running'])
                )
            ).all()
            
            cleaned_count = 0
            for task in expired_tasks:
                if cls._is_lock_expired(task, lock_timeout_minutes):
                    cls._force_release_lock(db, task)
                    cleaned_count += 1
            
            db.commit()
            
            logger.info(f"Cleaned up {cleaned_count} expired table locks")
            
            return {
                'success': True,
                'cleaned_locks': cleaned_count,
                'message': f'Cleaned up {cleaned_count} expired locks'
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired locks: {e}")
            db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def _is_lock_expired(cls, task: MergeTask, timeout_minutes: int) -> bool:
        """
        检查锁是否已过期
        
        Args:
            task: 任务对象
            timeout_minutes: 超时时间（分钟）
            
        Returns:
            是否已过期
        """
        if not task.table_lock_acquired:
            return False
        
        # 使用任务开始时间或创建时间来判断
        lock_time = task.started_time or task.created_time
        if not lock_time:
            return False
        
        # 检查是否超过超时时间
        timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        return lock_time < timeout_threshold
    
    @classmethod
    def _force_release_lock(cls, db: Session, task: MergeTask):
        """
        强制释放锁（用于清理过期锁）
        
        Args:
            db: 数据库会话
            task: 任务对象
        """
        task.table_lock_acquired = False
        task.lock_holder = None
        
        # 如果任务仍在运行状态，将其标记为失败
        if task.status == 'running':
            task.status = 'failed'
            task.error_message = 'Task lock expired and was forcefully released'
            task.completed_time = datetime.utcnow()
        
        logger.warning(f"Force released expired lock for task {task.id} on table {task.database_name}.{task.table_name}")
    
    @classmethod
    def get_all_table_locks(cls, db: Session, cluster_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取所有表锁信息
        
        Args:
            db: 数据库会话
            cluster_id: 可选的集群ID过滤
            
        Returns:
            所有锁信息
        """
        try:
            query = db.query(MergeTask).filter(
                MergeTask.table_lock_acquired == True
            )
            
            if cluster_id:
                query = query.filter(MergeTask.cluster_id == cluster_id)
            
            locked_tasks = query.all()
            
            locks_info = []
            for task in locked_tasks:
                locks_info.append({
                    'task_id': task.id,
                    'cluster_id': task.cluster_id,
                    'database_name': task.database_name,
                    'table_name': task.table_name,
                    'lock_holder': task.lock_holder,
                    'task_status': task.status,
                    'locked_since': task.started_time or task.created_time,
                    'strategy': task.merge_strategy
                })
            
            return {
                'success': True,
                'total_locks': len(locks_info),
                'locks': locks_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get table locks: {e}")
            return {
                'success': False,
                'error': str(e)
            }