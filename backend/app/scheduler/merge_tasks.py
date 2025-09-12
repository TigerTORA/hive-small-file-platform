import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from celery import current_task
from sqlalchemy.orm import sessionmaker
from app.scheduler.celery_app import celery_app
from app.config.database import engine
from app.models.merge_task import MergeTask
from app.models.cluster import Cluster
from app.engines.engine_factory import MergeEngineFactory
from app.utils.table_lock_manager import TableLockManager

logger = logging.getLogger(__name__)
SessionLocal = sessionmaker(bind=engine)

@celery_app.task(bind=True, name='app.scheduler.merge_tasks.execute_merge_task')
def execute_merge_task(self, task_id: int):
    """
    执行合并任务
    
    Args:
        task_id: 任务ID
    """
    db = SessionLocal()
    
    try:
        # 获取任务信息
        task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # 获取集群信息
        cluster = db.query(Cluster).filter(Cluster.id == task.cluster_id).first()
        if not cluster:
            raise ValueError(f"Cluster {task.cluster_id} not found")
        
        logger.info(f"Starting merge task {task_id}: {task.task_name}")
        
        # 尝试获取表级别锁
        lock_result = TableLockManager.acquire_table_lock(
            db, cluster.id, task.database_name, task.table_name, task.id
        )
        
        if not lock_result['success']:
            logger.error(f"Failed to acquire table lock for task {task_id}: {lock_result['message']}")
            task.status = 'failed'
            task.error_message = f"Cannot acquire table lock: {lock_result['message']}"
            task.completed_time = datetime.utcnow()
            db.commit()
            raise ValueError(f"Table lock acquisition failed: {lock_result['message']}")
        
        # 更新任务状态和 Celery 任务ID
        task.status = 'running'
        task.celery_task_id = self.request.id
        task.started_time = datetime.utcnow()
        task.current_phase = 'initializing'
        task.progress = 5.0  # 获得锁并开始初始化
        db.commit()
        
        # 更新任务进度
        current_task.update_state(
            state='PROGRESS',
            meta={
                'status': 'initializing',
                'task_name': task.task_name,
                'table': f"{task.database_name}.{task.table_name}"
            }
        )
        
        # 统一使用SafeHiveMergeEngine，支持所有合并策略
        engine = MergeEngineFactory.get_engine(cluster)
        
        # 验证任务
        validation = engine.validate_task(task)
        if not validation['valid']:
            raise ValueError(f"Task validation failed: {validation['message']}")
        
        if validation.get('warnings'):
            logger.warning(f"Task validation warnings: {validation['warnings']}")
        
        # 更新进度
        current_task.update_state(
            state='PROGRESS',
            meta={
                'status': 'executing',
                'task_name': task.task_name,
                'table': f"{task.database_name}.{task.table_name}",
                'phase': 'starting_merge'
            }
        )
        
        # 执行合并，监控不同阶段的进度
        try:
            # 为 safe_merge 引擎添加进度回调
            if task.merge_strategy == 'safe_merge':
                # SafeHiveMergeEngine 的进度监控
                def progress_callback(phase, message):
                    current_task.update_state(
                        state='PROGRESS',
                        meta={
                            'status': 'executing',
                            'task_name': task.task_name,
                            'table': f"{task.database_name}.{task.table_name}",
                            'phase': phase,
                            'message': message
                        }
                    )
                
                # 如果引擎支持进度回调，则设置
                if hasattr(engine, 'set_progress_callback'):
                    engine.set_progress_callback(progress_callback)
            
            result = engine.execute_merge(task, db)
            
        except Exception as merge_error:
            # 合并执行失败，更新详细错误信息
            current_task.update_state(
                state='FAILURE',
                meta={
                    'status': 'failed',
                    'task_name': task.task_name,
                    'table': f"{task.database_name}.{task.table_name}",
                    'error': str(merge_error),
                    'phase': 'execution_failed'
                }
            )
            raise merge_error
        
        if result['success']:
            # 更新任务状态
            task.status = 'success'
            task.completed_time = datetime.utcnow()
            task.progress = 100.0
            task.current_phase = 'completed'
            
            # 更新执行结果信息
            if 'files_before' in result:
                task.files_before = result['files_before']
            if 'files_after' in result:
                task.files_after = result['files_after']
            if 'size_saved' in result:
                task.size_saved = result['size_saved']
            
            db.commit()
            
            # 释放表锁
            TableLockManager.release_table_lock(db, task_id)
            
            logger.info(f"Merge task {task_id} completed successfully: {result['message']}")
            return {
                'status': 'completed',
                'task_id': task_id,
                'task_name': task.task_name,
                'result': result
            }
        else:
            raise Exception(f"Merge execution failed: {result['message']}")
        
    except Exception as e:
        logger.error(f"Failed to execute merge task {task_id}: {e}")
        
        # 更新任务状态为失败
        try:
            task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
            if task:
                task.status = 'failed'
                task.error_message = str(e)
                task.completed_time = datetime.utcnow()
                task.current_phase = 'failed'
                db.commit()
                
                # 释放表锁
                TableLockManager.release_table_lock(db, task_id)
        except Exception as db_error:
            logger.error(f"Failed to update task status: {db_error}")
        
        return {
            'status': 'failed',
            'task_id': task_id,
            'error': str(e)
        }
    
    finally:
        db.close()

@celery_app.task(name='app.scheduler.merge_tasks.check_pending_tasks')
def check_pending_tasks():
    """
    检查待执行的合并任务，并自动执行符合条件的任务
    定时任务，每小时执行一次
    """
    db = SessionLocal()
    results = []
    
    try:
        # 获取所有待执行的任务
        pending_tasks = db.query(MergeTask).filter(
            MergeTask.status == 'pending'
        ).order_by(MergeTask.created_time).all()
        
        logger.info(f"Found {len(pending_tasks)} pending merge tasks")
        
        for task in pending_tasks:
            try:
                # 检查任务是否满足自动执行条件
                if should_auto_execute_task(task):
                    # 启动任务执行
                    result = execute_merge_task.delay(task.id)
                    
                    results.append({
                        'task_id': task.id,
                        'task_name': task.task_name,
                        'celery_task_id': result.id,
                        'status': 'started'
                    })
                    
                    logger.info(f"Auto-started merge task {task.id}: {task.task_name}")
                
            except Exception as e:
                logger.error(f"Failed to check/start task {task.id}: {e}")
                results.append({
                    'task_id': task.id,
                    'task_name': task.task_name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return {
            'status': 'completed',
            'pending_tasks_checked': len(pending_tasks),
            'tasks_started': len([r for r in results if r['status'] == 'started']),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Failed to check pending tasks: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }
    
    finally:
        db.close()

@celery_app.task(name='app.scheduler.merge_tasks.batch_create_merge_tasks')
def batch_create_merge_tasks(cluster_id: int, small_file_threshold: int = 1000):
    """
    批量创建合并任务
    根据扫描结果自动为小文件较多的表创建合并任务
    
    Args:
        cluster_id: 集群ID
        small_file_threshold: 小文件数量阈值，超过此值的表会创建合并任务
    """
    db = SessionLocal()
    created_tasks = []
    
    try:
        # 获取集群信息
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")
        
        # 获取该集群最新的表扫描结果
        from app.models.table_metric import TableMetric
        from sqlalchemy import func
        
        # 找出小文件数量超过阈值的表
        problematic_tables = db.query(TableMetric).filter(
            TableMetric.cluster_id == cluster_id,
            TableMetric.small_files >= small_file_threshold
        ).order_by(TableMetric.small_files.desc()).all()
        
        logger.info(f"Found {len(problematic_tables)} tables with >= {small_file_threshold} small files")
        
        for table_metric in problematic_tables:
            try:
                # 检查是否已经存在该表的待执行或运行中的任务
                existing_task = db.query(MergeTask).filter(
                    MergeTask.cluster_id == cluster_id,
                    MergeTask.database_name == table_metric.database_name,
                    MergeTask.table_name == table_metric.table_name,
                    MergeTask.status.in_(['pending', 'running'])
                ).first()
                
                if existing_task:
                    logger.info(f"Task already exists for table {table_metric.table_name}, skipping")
                    continue
                
                # 使用智能策略选择创建合并任务
                smart_task_config = MergeEngineFactory.create_smart_merge_task(
                    cluster=cluster,
                    database_name=table_metric.database_name,
                    table_name=table_metric.table_name,
                    table_format=getattr(table_metric, 'storage_format', None),
                    file_count=table_metric.total_files,
                    table_size=table_metric.total_size,
                    partition_count=table_metric.partition_count if table_metric.is_partitioned else 0
                )
                
                new_task = MergeTask(
                    cluster_id=cluster_id,
                    task_name=smart_task_config['task_name'],
                    table_name=table_metric.table_name,
                    database_name=table_metric.database_name,
                    merge_strategy=smart_task_config['recommended_strategy'],
                    strategy_reason=smart_task_config['strategy_reason'],
                    auto_selected=True,
                    status='pending'
                )
                
                db.add(new_task)
                db.flush()  # 获取任务ID
                
                created_tasks.append({
                    'task_id': new_task.id,
                    'table': f"{table_metric.database_name}.{table_metric.table_name}",
                    'small_files': table_metric.small_files,
                    'total_files': table_metric.total_files,
                    'strategy': smart_task_config['recommended_strategy'],
                    'strategy_reason': smart_task_config['strategy_reason'],
                    'validation': smart_task_config['validation']
                })
                
                logger.info(f"Created merge task for {table_metric.database_name}.{table_metric.table_name} "
                           f"({table_metric.small_files} small files)")
                
            except Exception as e:
                logger.error(f"Failed to create task for table {table_metric.table_name}: {e}")
        
        db.commit()
        
        return {
            'status': 'completed',
            'cluster_id': cluster_id,
            'tasks_created': len(created_tasks),
            'created_tasks': created_tasks
        }
        
    except Exception as e:
        logger.error(f"Failed to batch create merge tasks: {e}")
        db.rollback()
        return {
            'status': 'failed',
            'cluster_id': cluster_id,
            'error': str(e)
        }
    
    finally:
        db.close()

def should_auto_execute_task(task: MergeTask) -> bool:
    """
    判断任务是否应该自动执行
    
    Args:
        task: 合并任务对象
        
    Returns:
        是否应该自动执行
    """
    # 简单的自动执行逻辑：
    # 1. 任务创建时间超过1小时（避免频繁执行）
    # 2. 可以添加更复杂的业务逻辑，如：
    #    - 检查集群负载
    #    - 检查业务时间窗口
    #    - 检查任务优先级
    
    if not task.created_time:
        return False
    
    # 任务创建超过1小时后才自动执行
    auto_execute_delay = timedelta(hours=1)
    return datetime.utcnow() - task.created_time > auto_execute_delay

@celery_app.task(name='app.scheduler.merge_tasks.cancel_task')
def cancel_task(task_id: int):
    """
    取消正在运行的任务
    
    Args:
        task_id: 任务ID
    """
    db = SessionLocal()
    
    try:
        task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if task.status != 'running':
            raise ValueError(f"Task {task_id} is not running (status: {task.status})")
        
        # 尝试撤销 Celery 任务
        if task.celery_task_id:
            celery_app.control.revoke(task.celery_task_id, terminate=True)
        
        # 更新任务状态
        task.status = 'cancelled'
        task.error_message = 'Task cancelled by user'
        task.completed_time = datetime.utcnow()
        db.commit()
        
        logger.info(f"Task {task_id} cancelled successfully")
        return {'status': 'success', 'message': f'Task {task_id} cancelled'}
        
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        return {'status': 'failed', 'error': str(e)}
    
    finally:
        db.close()