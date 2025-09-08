from celery import Celery
from app.config.settings import settings

# 创建 Celery 应用
celery_app = Celery(
    "hive_small_file_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.scheduler.scan_tasks',
        'app.scheduler.merge_tasks',
    ]
)

# Celery 配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # 任务路由配置
    task_routes={
        'app.scheduler.scan_tasks.*': {'queue': 'scan'},
        'app.scheduler.merge_tasks.*': {'queue': 'merge'},
    },
    
    # Beat 调度配置
    beat_schedule={
        # 每6小时扫描一次所有启用的集群
        'scan-clusters': {
            'task': 'app.scheduler.scan_tasks.scan_all_clusters',
            'schedule': 6.0 * 60 * 60,  # 6 hours
        },
        
        # 每小时检查一次待执行的合并任务
        'check-pending-tasks': {
            'task': 'app.scheduler.merge_tasks.check_pending_tasks',
            'schedule': 60.0 * 60,  # 1 hour
        },
        
        # 每天清理一次过期的任务日志
        'cleanup-logs': {
            'task': 'app.scheduler.maintenance_tasks.cleanup_old_logs',
            'schedule': 24.0 * 60 * 60,  # 24 hours
        },
    },
    
    # 任务配置
    task_soft_time_limit=1800,  # 30 minutes soft limit
    task_time_limit=3600,       # 1 hour hard limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=100,
)