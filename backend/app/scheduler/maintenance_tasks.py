import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from app.scheduler.celery_app import celery_app
from app.config.database import engine
from app.models.task_log import TaskLog
from app.models.table_metric import TableMetric
from app.models.partition_metric import PartitionMetric
from app.models.merge_task import MergeTask

logger = logging.getLogger(__name__)
SessionLocal = sessionmaker(bind=engine)

@celery_app.task(name='app.scheduler.maintenance_tasks.cleanup_old_logs')
def cleanup_old_logs(days_to_keep: int = 30):
    """
    清理过期的任务日志
    
    Args:
        days_to_keep: 保留天数，默认30天
    """
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # 删除过期的任务日志
        deleted_logs = db.query(TaskLog).filter(
            TaskLog.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_logs} old task logs (older than {days_to_keep} days)")
        
        return {
            'status': 'completed',
            'deleted_logs': deleted_logs,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old logs: {e}")
        db.rollback()
        return {
            'status': 'failed',
            'error': str(e)
        }
    
    finally:
        db.close()

@celery_app.task(name='app.scheduler.maintenance_tasks.cleanup_old_metrics')
def cleanup_old_metrics(days_to_keep: int = 90):
    """
    清理过期的监控指标数据
    
    Args:
        days_to_keep: 保留天数，默认90天
    """
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # 删除过期的分区指标
        deleted_partition_metrics = db.query(PartitionMetric).join(TableMetric).filter(
            TableMetric.scan_time < cutoff_date
        ).delete()
        
        # 删除过期的表指标
        deleted_table_metrics = db.query(TableMetric).filter(
            TableMetric.scan_time < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_table_metrics} table metrics and "
                   f"{deleted_partition_metrics} partition metrics (older than {days_to_keep} days)")
        
        return {
            'status': 'completed',
            'deleted_table_metrics': deleted_table_metrics,
            'deleted_partition_metrics': deleted_partition_metrics,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old metrics: {e}")
        db.rollback()
        return {
            'status': 'failed',
            'error': str(e)
        }
    
    finally:
        db.close()

@celery_app.task(name='app.scheduler.maintenance_tasks.cleanup_completed_tasks')
def cleanup_completed_tasks(days_to_keep: int = 60):
    """
    清理已完成的合并任务记录
    
    Args:
        days_to_keep: 保留天数，默认60天
    """
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # 获取要删除的任务ID，用于同时删除相关日志
        tasks_to_delete = db.query(MergeTask.id).filter(
            MergeTask.status.in_(['success', 'failed', 'cancelled']),
            MergeTask.completed_time < cutoff_date
        ).all()
        
        task_ids = [task[0] for task in tasks_to_delete]
        
        if task_ids:
            # 删除相关的任务日志
            deleted_logs = db.query(TaskLog).filter(
                TaskLog.task_id.in_(task_ids)
            ).delete(synchronize_session=False)
            
            # 删除任务记录
            deleted_tasks = db.query(MergeTask).filter(
                MergeTask.id.in_(task_ids)
            ).delete(synchronize_session=False)
            
            db.commit()
            
            logger.info(f"Cleaned up {deleted_tasks} completed tasks and "
                       f"{deleted_logs} related logs (older than {days_to_keep} days)")
        else:
            deleted_tasks = 0
            deleted_logs = 0
            logger.info("No completed tasks to cleanup")
        
        return {
            'status': 'completed',
            'deleted_tasks': deleted_tasks,
            'deleted_logs': deleted_logs,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup completed tasks: {e}")
        db.rollback()
        return {
            'status': 'failed',
            'error': str(e)
        }
    
    finally:
        db.close()

@celery_app.task(name='app.scheduler.maintenance_tasks.system_health_check')
def system_health_check():
    """
    系统健康检查
    检查数据库连接、Redis 连接、集群状态等
    """
    health_status = {
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'unknown',
        'redis': 'unknown',
        'clusters': [],
        'tasks': {
            'pending': 0,
            'running': 0,
            'failed_recent': 0
        }
    }
    
    db = SessionLocal()
    
    try:
        # 检查数据库连接
        db.execute('SELECT 1')
        health_status['database'] = 'healthy'
        
        # 检查集群状态
        from app.models.cluster import Cluster
        clusters = db.query(Cluster).all()
        for cluster in clusters:
            cluster_status = {
                'id': cluster.id,
                'name': cluster.name,
                'status': cluster.status,
                'scan_enabled': cluster.scan_enabled,
                'last_update': cluster.updated_time.isoformat() if cluster.updated_time else None
            }
            health_status['clusters'].append(cluster_status)
        
        # 检查任务状态
        health_status['tasks']['pending'] = db.query(MergeTask).filter(
            MergeTask.status == 'pending'
        ).count()
        
        health_status['tasks']['running'] = db.query(MergeTask).filter(
            MergeTask.status == 'running'
        ).count()
        
        # 最近24小时失败的任务数
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        health_status['tasks']['failed_recent'] = db.query(MergeTask).filter(
            MergeTask.status == 'failed',
            MergeTask.completed_time >= recent_cutoff
        ).count()
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status['database'] = 'unhealthy'
        health_status['database_error'] = str(e)
    
    finally:
        db.close()
    
    # 检查 Redis 连接
    try:
        from app.config.settings import settings
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status['redis'] = 'healthy'
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status['redis'] = 'unhealthy'
        health_status['redis_error'] = str(e)
    
    # 记录健康检查结果
    overall_status = 'healthy'
    if health_status['database'] != 'healthy' or health_status['redis'] != 'healthy':
        overall_status = 'unhealthy'
    elif health_status['tasks']['failed_recent'] > 10:  # 如果最近失败任务太多
        overall_status = 'degraded'
    
    health_status['overall_status'] = overall_status
    
    logger.info(f"System health check completed: {overall_status}")
    return health_status

@celery_app.task(name='app.scheduler.maintenance_tasks.generate_daily_report')
def generate_daily_report():
    """
    生成每日报告
    统计昨日的扫描情况、任务执行情况等
    """
    db = SessionLocal()
    
    try:
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        start_time = datetime.combine(yesterday, datetime.min.time())
        end_time = datetime.combine(yesterday, datetime.max.time())
        
        # 统计昨日扫描的表数量
        scanned_tables = db.query(TableMetric).filter(
            TableMetric.scan_time >= start_time,
            TableMetric.scan_time <= end_time
        ).count()
        
        # 统计昨日执行的任务
        tasks_completed = db.query(MergeTask).filter(
            MergeTask.completed_time >= start_time,
            MergeTask.completed_time <= end_time,
            MergeTask.status.in_(['success', 'failed'])
        ).all()
        
        successful_tasks = [t for t in tasks_completed if t.status == 'success']
        failed_tasks = [t for t in tasks_completed if t.status == 'failed']
        
        # 计算文件合并效果
        total_files_before = sum(t.files_before or 0 for t in successful_tasks)
        total_files_after = sum(t.files_after or 0 for t in successful_tasks)
        total_size_saved = sum(t.size_saved or 0 for t in successful_tasks)
        
        report = {
            'date': yesterday.isoformat(),
            'scanning': {
                'tables_scanned': scanned_tables
            },
            'merge_tasks': {
                'total_completed': len(tasks_completed),
                'successful': len(successful_tasks),
                'failed': len(failed_tasks),
                'success_rate': len(successful_tasks) / len(tasks_completed) * 100 if tasks_completed else 0
            },
            'merge_effectiveness': {
                'files_before': total_files_before,
                'files_after': total_files_after,
                'files_reduced': total_files_before - total_files_after,
                'size_saved_bytes': total_size_saved,
                'reduction_rate': (total_files_before - total_files_after) / total_files_before * 100 if total_files_before else 0
            }
        }
        
        logger.info(f"Daily report generated for {yesterday}: "
                   f"{scanned_tables} tables scanned, "
                   f"{len(successful_tasks)} successful merges, "
                   f"{total_files_before - total_files_after} files reduced")
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        return {
            'date': yesterday.isoformat(),
            'error': str(e)
        }
    
    finally:
        db.close()