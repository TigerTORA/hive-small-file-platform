import logging
from typing import List, Optional
from celery import current_task
from sqlalchemy.orm import sessionmaker
from app.scheduler.celery_app import celery_app
from app.config.database import engine
from app.models.cluster import Cluster
from app.monitor.hybrid_table_scanner import HybridTableScanner
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector

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
        
        # 统一到 HybridTableScanner
        scanner = HybridTableScanner(cluster)

        total_tables = 0
        total_files = 0
        total_small_files = 0
        errors: list[str] = []
        per_db: list[dict] = []

        # 列出数据库（可选过滤）
        databases: list[str] = []
        try:
            with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as meta:
                databases = meta.get_databases()
        except Exception as e:
            raise ValueError(f"Failed to enumerate databases from MetaStore: {e}")

        if database_filter:
            databases = [d for d in databases if database_filter in d]

        for db_name in databases:
            try:
                db_res = scanner.scan_database_tables(db, db_name, table_filter=None, max_tables=None, strict_real=True)
                total_tables += int(db_res.get('tables_scanned', 0))
                total_files += int(db_res.get('total_files', 0))
                total_small_files += int(db_res.get('total_small_files', 0))
                per_db.append({
                    'database': db_name,
                    'tables_scanned': int(db_res.get('tables_scanned', 0)),
                    'total_files': int(db_res.get('total_files', 0)),
                    'total_small_files': int(db_res.get('total_small_files', 0)),
                    'duration': db_res.get('scan_duration')
                })
            except Exception as e:
                errors.append(f"{db_name}: {e}")
                per_db.append({
                    'database': db_name,
                    'error': str(e)
                })

        logger.info(
            f"Hybrid scan completed for cluster {cluster.name}: {total_tables} tables, {total_files} files, {total_small_files} small files"
        )

        return {
            'status': 'completed',
            'cluster_id': cluster_id,
            'cluster_name': cluster.name,
            'scan_result': {
                'databases_scanned': len(databases),
                'tables_scanned': total_tables,
                'total_files': total_files,
                'total_small_files': total_small_files,
                'per_database': per_db,
                'errors': errors,
            }
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
        
        # 统一到 HybridTableScanner：通过数据库扫描接口限制为单表，便于持久化指标
        scanner = HybridTableScanner(cluster)
        db_result = scanner.scan_database_tables(
            db, database_name, table_filter=table_name, max_tables=1, strict_real=True
        )

        if int(db_result.get('tables_scanned', 0)) > 0:
            logger.info(
                f"Table scan completed: {db_result.get('total_files', 0)} files, {db_result.get('total_small_files', 0)} small files"
            )
            return {
                'status': 'completed',
                'cluster_id': cluster_id,
                'database_name': database_name,
                'table_name': table_name,
                'scan_result': db_result
            }
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
