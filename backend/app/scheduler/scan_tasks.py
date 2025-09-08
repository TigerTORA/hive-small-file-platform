import logging
from typing import List, Optional
from celery import current_task
from sqlalchemy.orm import sessionmaker
from app.scheduler.celery_app import celery_app
from app.config.database import engine
from app.models.cluster import Cluster
from app.monitor.table_scanner import TableScanner

logger = logging.getLogger(__name__)
SessionLocal = sessionmaker(bind=engine)

@celery_app.task(bind=True, name='app.scheduler.scan_tasks.scan_all_clusters')
def scan_all_clusters(self):
    """
    扫描所有启用的集群
    定时任务，自动执行
    """
    db = SessionLocal()
    results = []
    
    try:
        # 获取所有启用扫描的集群
        clusters = db.query(Cluster).filter(
            Cluster.scan_enabled == True,
            Cluster.status == 'active'
        ).all()
        
        logger.info(f"Starting scan for {len(clusters)} clusters")
        
        for cluster in clusters:
            try:
                # 更新任务进度
                current_task.update_state(
                    state='PROGRESS',
                    meta={'current': len(results), 'total': len(clusters), 'cluster': cluster.name}
                )
                
                # 执行集群扫描
                result = scan_single_cluster.delay(cluster.id)
                results.append({
                    'cluster_id': cluster.id,
                    'cluster_name': cluster.name,
                    'task_id': result.id,
                    'status': 'started'
                })
                
                logger.info(f"Started scan task for cluster {cluster.name}: {result.id}")
                
            except Exception as e:
                logger.error(f"Failed to start scan for cluster {cluster.name}: {e}")
                results.append({
                    'cluster_id': cluster.id,
                    'cluster_name': cluster.name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        logger.info(f"Scan tasks started for {len(results)} clusters")
        return {
            'status': 'completed',
            'clusters_processed': len(results),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Failed to scan clusters: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }
    
    finally:
        db.close()

@celery_app.task(bind=True, name='app.scheduler.scan_tasks.scan_single_cluster')
def scan_single_cluster(self, cluster_id: int, database_filter: Optional[str] = None):
    """
    扫描单个集群
    
    Args:
        cluster_id: 集群ID
        database_filter: 数据库过滤器（可选）
    """
    db = SessionLocal()
    
    try:
        # 获取集群信息
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")
        
        logger.info(f"Starting scan for cluster {cluster.name} (ID: {cluster_id})")
        
        # 更新任务状态
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'initializing', 'cluster': cluster.name}
        )
        
        # 创建表扫描器
        scanner = TableScanner(cluster)
        
        # 执行扫描
        result = scanner.scan_cluster(db, database_filter)
        
        logger.info(f"Scan completed for cluster {cluster.name}: "
                   f"{result['tables_scanned']} tables, "
                   f"{result['total_files']} files, "
                   f"{result['total_small_files']} small files")
        
        return {
            'status': 'completed',
            'cluster_id': cluster_id,
            'cluster_name': cluster.name,
            'scan_result': result
        }
        
    except Exception as e:
        logger.error(f"Failed to scan cluster {cluster_id}: {e}")
        return {
            'status': 'failed',
            'cluster_id': cluster_id,
            'error': str(e)
        }
    
    finally:
        db.close()

@celery_app.task(bind=True, name='app.scheduler.scan_tasks.scan_single_table')
def scan_single_table(self, cluster_id: int, database_name: str, table_name: str):
    """
    扫描单个表
    
    Args:
        cluster_id: 集群ID
        database_name: 数据库名
        table_name: 表名
    """
    db = SessionLocal()
    
    try:
        # 获取集群信息
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")
        
        logger.info(f"Starting scan for table {database_name}.{table_name} in cluster {cluster.name}")
        
        # 创建表扫描器
        scanner = TableScanner(cluster)
        
        # 扫描单个表
        result = scanner.scan_single_table(db, database_name, table_name)
        
        if result:
            logger.info(f"Table scan completed: {result['total_files']} files, {result['small_files']} small files")
            return {
                'status': 'completed',
                'cluster_id': cluster_id,
                'database_name': database_name,
                'table_name': table_name,
                'scan_result': result
            }
        else:
            return {
                'status': 'failed',
                'cluster_id': cluster_id,
                'database_name': database_name,
                'table_name': table_name,
                'error': 'Scan returned no results'
            }
        
    except Exception as e:
        logger.error(f"Failed to scan table {database_name}.{table_name}: {e}")
        return {
            'status': 'failed',
            'cluster_id': cluster_id,
            'database_name': database_name,
            'table_name': table_name,
            'error': str(e)
        }
    
    finally:
        db.close()

@celery_app.task(name='app.scheduler.scan_tasks.trigger_cluster_scan')
def trigger_cluster_scan(cluster_id: int, database_filter: Optional[str] = None):
    """
    触发集群扫描（手动调用）
    
    Args:
        cluster_id: 集群ID
        database_filter: 数据库过滤器（可选）
    """
    logger.info(f"Manually triggered scan for cluster {cluster_id}")
    return scan_single_cluster.delay(cluster_id, database_filter)