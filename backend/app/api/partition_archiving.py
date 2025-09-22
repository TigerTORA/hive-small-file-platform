"""
分区归档API模块
负责分区级别的冷数据扫描、分区归档、恢复等功能
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.models.partition_metric import PartitionMetric
from app.monitor.partition_cold_data_scanner import PartitionColdDataScanner
from app.monitor.partition_archive_engine import PartitionArchiveEngine
from app.services.scan_service import scan_task_manager
from app.config.database import SessionLocal

router = APIRouter()


@router.post("/scan-cold-partitions/{cluster_id}")
async def scan_cold_partitions(
    cluster_id: int,
    cold_threshold_days: Optional[int] = Query(90, description="冷数据阈值天数"),
    database_name: Optional[str] = Query(None, description="指定数据库名称"),
    table_name: Optional[str] = Query(None, description="指定表名称"),
    min_partition_size: int = Query(0, description="最小分区大小阈值（字节）"),
    background: bool = Query(True, description="是否作为后台任务运行并输出任务日志"),
    db: Session = Depends(get_db),
):
    """扫描集群中的冷数据分区"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        if not background:
            cold_scanner = PartitionColdDataScanner(cluster, cold_threshold_days)
            scan_result = cold_scanner.scan_cold_partitions(
                db_session=db,
                database_name=database_name,
                table_name=table_name,
                min_partition_size=min_partition_size
            )
            return {
                "message": "Cold partition scan completed",
                "cluster_id": cluster_id,
                "scan_config": {
                    "threshold_days": cold_threshold_days,
                    "database_filter": database_name,
                    "table_filter": table_name,
                    "min_partition_size": min_partition_size,
                },
                "scan_result": scan_result,
            }

        # 后台任务模式：创建任务并在后台线程执行
        task = scan_task_manager.create_scan_task(
            db,
            cluster_id,
            'partition-cold-scan',
            f'扫描冷分区 (阈值{cold_threshold_days}天)'
        )

        def run_scan():
            db_thread = SessionLocal()
            try:
                cluster_t = db_thread.query(Cluster).filter(Cluster.id == cluster_id).first()
                if not cluster_t:
                    scan_task_manager.error(task.task_id, 'E401', '集群不存在', db=db_thread, phase='scan')
                    scan_task_manager.complete_task(db_thread, task.task_id, success=False, error_message='Cluster not found')
                    return
                cold_scanner = PartitionColdDataScanner(cluster_t, cold_threshold_days or 90)
                scan_task_manager.info(task.task_id, 'C401', '开始冷分区扫描', db=db_thread, phase='scan', ctx={'threshold_days': cold_threshold_days or 90, 'db': database_name, 'table': table_name, 'min_size': min_partition_size})
                result = cold_scanner.scan_cold_partitions(
                    db_session=db_thread,
                    database_name=database_name,
                    table_name=table_name,
                    min_partition_size=min_partition_size
                )
                count = 0
                try:
                    count = len(result.get('cold_partitions', []))
                except Exception:
                    pass
                scan_task_manager.info(task.task_id, 'C490', '冷分区扫描完成', db=db_thread, phase='scan', ctx={'found': count})
                scan_task_manager.complete_task(db_thread, task.task_id, success=True)
            except Exception as e:
                scan_task_manager.error(task.task_id, 'E490', f'冷分区扫描失败: {e}', db=db_thread, phase='scan')
                scan_task_manager.complete_task(db_thread, task.task_id, success=False, error_message=str(e))
            finally:
                try:
                    db_thread.close()
                except Exception:
                    pass

        import threading
        t = threading.Thread(target=run_scan, daemon=True)
        t.start()
        return {"message": "Cold partition scan started", "task_id": task.task_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cold partition scan failed: {str(e)}")


@router.get("/cold-partitions-summary/{cluster_id}")
async def get_cold_partitions_summary(
    cluster_id: int,
    database_name: Optional[str] = Query(None, description="数据库名过滤"),
    table_name: Optional[str] = Query(None, description="表名过滤"),
    db: Session = Depends(get_db)
):
    """获取集群冷分区统计摘要"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        cold_scanner = PartitionColdDataScanner(cluster)
        summary = cold_scanner.get_cold_partitions_summary(
            db_session=db,
            database_name=database_name,
            table_name=table_name
        )
        return summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cold partitions summary: {str(e)}")


@router.get("/cold-partitions-list/{cluster_id}")
async def get_cold_partitions_list(
    cluster_id: int,
    database_name: Optional[str] = Query(None, description="数据库名过滤"),
    table_name: Optional[str] = Query(None, description="表名过滤"),
    coldness_level: str = Query('cold', description="冷热程度 (very_cold, cold, warm)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取冷分区列表"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        cold_scanner = PartitionColdDataScanner(cluster)

        # 计算偏移量
        offset = (page - 1) * page_size

        partitions = cold_scanner.get_partitions_by_coldness(
            db_session=db,
            coldness_level=coldness_level,
            database_name=database_name,
            table_name=table_name,
            limit=page_size
        )

        # 获取总数 (简化实现，实际应该在scanner中实现分页)
        base_query = db.query(PartitionMetric).join(TableMetric).filter(
            TableMetric.cluster_id == cluster_id
        )

        if database_name:
            base_query = base_query.filter(TableMetric.database_name == database_name)
        if table_name:
            base_query = base_query.filter(TableMetric.table_name == table_name)

        if coldness_level == 'very_cold':
            base_query = base_query.filter(PartitionMetric.days_since_last_access > 180)
        elif coldness_level == 'cold':
            base_query = base_query.filter(PartitionMetric.days_since_last_access.between(90, 180))
        elif coldness_level == 'warm':
            base_query = base_query.filter(PartitionMetric.days_since_last_access < 90)

        total_count = base_query.count()

        return {
            "cluster_id": cluster_id,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size,
            },
            "filters": {
                "database_name": database_name,
                "table_name": table_name,
                "coldness_level": coldness_level,
            },
            "cold_partitions": partitions[:page_size],  # 简化分页
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cold partitions list: {str(e)}")


@router.post("/archive-partition/{cluster_id}/{database_name}/{table_name}/{partition_name}")
async def archive_partition(
    cluster_id: int,
    database_name: str,
    table_name: str,
    partition_name: str,
    force: bool = Query(False, description="强制归档，跳过检查"),
    background: bool = Query(True, description="是否后台任务运行并输出任务日志"),
    db: Session = Depends(get_db),
):
    """归档指定分区到冷存储"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        if not background:
            archive_engine = PartitionArchiveEngine(cluster)
            archive_result = archive_engine.archive_partition(
                db_session=db,
                database_name=database_name,
                table_name=table_name,
                partition_name=partition_name,
                force=force
            )
            return {
                "message": f"Partition {database_name}.{table_name}.{partition_name} archived successfully",
                "archive_result": archive_result,
            }

        # 后台任务
        task = scan_task_manager.create_scan_task(
            db, cluster_id, 'partition-archive', f'归档分区: {database_name}.{table_name}.{partition_name}'
        )

        def run_archive():
            db_thread = SessionLocal()
            try:
                cluster_t = db_thread.query(Cluster).filter(Cluster.id == cluster_id).first()
                engine = PartitionArchiveEngine(cluster_t)
                scan_task_manager.info(task.task_id, 'P101', '开始分区归档', db=db_thread, phase='archive', ctx={'db': database_name, 'table': table_name, 'partition': partition_name, 'force': force})
                res = engine.archive_partition(db_thread, database_name, table_name, partition_name, force)
                scan_task_manager.info(task.task_id, 'P190', '分区归档完成', db=db_thread, phase='archive', ctx={'files_moved': res.get('files_moved'), 'archive_location': res.get('archive_location')})
                scan_task_manager.complete_task(db_thread, task.task_id, success=True)
            except Exception as e:
                scan_task_manager.error(task.task_id, 'E190', f'分区归档失败: {e}', db=db_thread, phase='archive')
                scan_task_manager.complete_task(db_thread, task.task_id, success=False, error_message=str(e))
            finally:
                try:
                    db_thread.close()
                except Exception:
                    pass
        import threading
        threading.Thread(target=run_archive, daemon=True).start()
        return {"message": "Partition archive started", "task_id": task.task_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Archive failed: {str(e)}")


@router.post("/restore-partition/{cluster_id}/{database_name}/{table_name}/{partition_name}")
async def restore_partition(
    cluster_id: int,
    database_name: str,
    table_name: str,
    partition_name: str,
    background: bool = Query(True, description="是否后台任务运行并输出任务日志"),
    db: Session = Depends(get_db)
):
    """从归档存储恢复分区"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        if not background:
            archive_engine = PartitionArchiveEngine(cluster)
            restore_result = archive_engine.restore_partition(
                db_session=db,
                database_name=database_name,
                table_name=table_name,
                partition_name=partition_name
            )
            return {
                "message": f"Partition {database_name}.{table_name}.{partition_name} restored successfully",
                "restore_result": restore_result,
            }
        task = scan_task_manager.create_scan_task(
            db, cluster_id, 'partition-restore', f'恢复分区: {database_name}.{table_name}.{partition_name}'
        )
        def run_restore():
            db_thread = SessionLocal()
            try:
                cluster_t = db_thread.query(Cluster).filter(Cluster.id == cluster_id).first()
                engine = PartitionArchiveEngine(cluster_t)
                scan_task_manager.info(task.task_id, 'R101', '开始分区恢复', db=db_thread, phase='restore', ctx={'db': database_name, 'table': table_name, 'partition': partition_name})
                res = engine.restore_partition(db_thread, database_name, table_name, partition_name)
                scan_task_manager.info(task.task_id, 'R190', '分区恢复完成', db=db_thread, phase='restore', ctx={'files_restored': res.get('files_restored'), 'restored_location': res.get('restored_location')})
                scan_task_manager.complete_task(db_thread, task.task_id, success=True)
            except Exception as e:
                scan_task_manager.error(task.task_id, 'ER190', f'分区恢复失败: {e}', db=db_thread, phase='restore')
                scan_task_manager.complete_task(db_thread, task.task_id, success=False, error_message=str(e))
            finally:
                try:
                    db_thread.close()
                except Exception:
                    pass
        import threading
        threading.Thread(target=run_restore, daemon=True).start()
        return {"message": "Partition restore started", "task_id": task.task_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.post("/batch-archive-partitions/{cluster_id}")
async def batch_archive_partitions(
    cluster_id: int,
    partition_list: List[Dict[str, str]] = Body(..., description="分区列表"),
    force: bool = Query(False, description="强制归档，跳过检查"),
    background: bool = Query(True, description="是否后台任务运行并输出任务日志"),
    db: Session = Depends(get_db),
):
    """批量归档分区"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        if not background:
            archive_engine = PartitionArchiveEngine(cluster)
            batch_result = archive_engine.batch_archive_partitions(
                db_session=db,
                partition_list=partition_list,
                force=force
            )
            return {
                "message": f"Batch archive completed for {len(partition_list)} partitions",
                "batch_result": batch_result,
            }
        task = scan_task_manager.create_scan_task(
            db, cluster_id, 'batch-partition-archive', f'批量分区归档: {len(partition_list)} 个'
        )
        def run_batch():
            db_thread = SessionLocal()
            try:
                scan_task_manager.info(task.task_id, 'PB101', '开始批量分区归档', db=db_thread, phase='archive', ctx={'total': len(partition_list), 'force': force})
                cluster_t = db_thread.query(Cluster).filter(Cluster.id == cluster_id).first()
                engine = PartitionArchiveEngine(cluster_t)
                res = engine.batch_archive_partitions(db_thread, partition_list, force)
                scan_task_manager.info(task.task_id, 'PB190', '批量分区归档完成', db=db_thread, phase='archive', ctx={'success': res.get('success_count'), 'failed': res.get('failed_count')})
                scan_task_manager.complete_task(db_thread, task.task_id, success=True)
            except Exception as e:
                scan_task_manager.error(task.task_id, 'EB190', f'批量分区归档失败: {e}', db=db_thread, phase='archive')
                scan_task_manager.complete_task(db_thread, task.task_id, success=False, error_message=str(e))
            finally:
                try:
                    db_thread.close()
                except Exception:
                    pass
        import threading
        threading.Thread(target=run_batch, daemon=True).start()
        return {"message": "Batch partition archive started", "task_id": task.task_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch archive failed: {str(e)}")


@router.get("/partition-archive-status/{cluster_id}/{database_name}/{table_name}/{partition_name}")
async def get_partition_archive_status(
    cluster_id: int,
    database_name: str,
    table_name: str,
    partition_name: str,
    db: Session = Depends(get_db)
):
    """获取分区的归档状态"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        archive_engine = PartitionArchiveEngine(cluster)

        status_info = archive_engine.get_partition_archive_status(
            db_session=db,
            database_name=database_name,
            table_name=table_name,
            partition_name=partition_name
        )

        if not status_info['exists']:
            raise HTTPException(
                status_code=404,
                detail=f"Partition {database_name}.{table_name}.{partition_name} not found"
            )

        return status_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get partition status: {str(e)}")


@router.get("/archived-partitions/{cluster_id}")
async def list_archived_partitions(
    cluster_id: int,
    database_name: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取已归档分区列表"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        archive_engine = PartitionArchiveEngine(cluster)

        # 简化实现，实际应该在engine中支持分页
        archived_list = archive_engine.list_archived_partitions(
            db_session=db,
            database_name=database_name,
            table_name=table_name,
            limit=page_size
        )

        return archived_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list archived partitions: {str(e)}")


@router.get("/partition-archive-statistics/{cluster_id}")
async def get_partition_archive_statistics(
    cluster_id: int,
    days_range: int = Query(30, description="统计天数范围"),
    db: Session = Depends(get_db),
):
    """获取分区归档统计信息"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        archive_engine = PartitionArchiveEngine(cluster)

        statistics = archive_engine.get_partition_archive_statistics(db_session=db)

        return {
            "cluster_id": cluster_id,
            "statistics": statistics,
            "query_range_days": days_range,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get partition archive statistics: {str(e)}")


@router.get("/partition-coldness-distribution/{cluster_id}")
async def get_partition_coldness_distribution(
    cluster_id: int,
    database_name: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取分区冷热程度分布"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        base_query = db.query(PartitionMetric).join(TableMetric).filter(
            TableMetric.cluster_id == cluster_id
        )

        if database_name:
            base_query = base_query.filter(TableMetric.database_name == database_name)
        if table_name:
            base_query = base_query.filter(TableMetric.table_name == table_name)

        # 统计不同冷热程度的分区数量
        very_cold_count = base_query.filter(PartitionMetric.days_since_last_access > 180).count()
        cold_count = base_query.filter(PartitionMetric.days_since_last_access.between(90, 180)).count()
        warm_count = base_query.filter(PartitionMetric.days_since_last_access < 90).count()

        # 统计归档状态分布
        archived_count = base_query.filter(PartitionMetric.archive_status == 'archived').count()
        active_count = base_query.filter(PartitionMetric.archive_status == 'active').count()

        total_count = base_query.count()

        return {
            "cluster_id": cluster_id,
            "filters": {
                "database_name": database_name,
                "table_name": table_name,
            },
            "coldness_distribution": {
                "very_cold_180d_plus": very_cold_count,
                "cold_90_180d": cold_count,
                "warm_under_90d": warm_count,
                "total_partitions": total_count,
            },
            "archive_status_distribution": {
                "archived": archived_count,
                "active": active_count,
                "total_partitions": total_count,
            },
            "statistics_timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get partition coldness distribution: {str(e)}")


@router.post("/auto-archive-by-policy/{cluster_id}")
async def auto_archive_by_policy(
    cluster_id: int,
    policy_config: Dict[str, Any] = Body(..., description="归档策略配置"),
    dry_run: bool = Query(False, description="干运行模式，只返回匹配的分区不执行归档"),
    background: bool = Query(True, description="是否后台任务运行并输出任务日志"),
    db: Session = Depends(get_db),
):
    """根据策略自动归档分区"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        # 解析策略配置
        min_days_since_access = policy_config.get('min_days_since_access', 90)
        min_partition_size = policy_config.get('min_partition_size', 0)
        max_partition_size = policy_config.get('max_partition_size', None)
        database_filter = policy_config.get('database_name')
        table_filter = policy_config.get('table_name')

        # 构建查询
        query = db.query(PartitionMetric).join(TableMetric).filter(
            TableMetric.cluster_id == cluster_id,
            PartitionMetric.is_cold_data == 1,
            PartitionMetric.archive_status == 'active',
            PartitionMetric.days_since_last_access >= min_days_since_access
        )

        if min_partition_size > 0:
            query = query.filter(PartitionMetric.total_size >= min_partition_size)

        if max_partition_size:
            query = query.filter(PartitionMetric.total_size <= max_partition_size)

        if database_filter:
            query = query.filter(TableMetric.database_name == database_filter)

        if table_filter:
            query = query.filter(TableMetric.table_name == table_filter)

        candidate_partitions = query.all()

        # 构建分区列表
        partition_list = []
        for p in candidate_partitions:
            table_metric = p.table_metric
            partition_list.append({
                'database_name': table_metric.database_name,
                'table_name': table_metric.table_name,
                'partition_name': p.partition_name,
                'days_since_access': p.days_since_last_access,
                'total_size': p.total_size
            })

        if dry_run and not background:
            return {
                "message": "Dry run completed",
                "policy_config": policy_config,
                "candidate_partitions": len(partition_list),
                "partitions": partition_list[:100],  # 限制返回数量
            }

        # 执行批量归档
        if not background:
            if partition_list:
                archive_engine = PartitionArchiveEngine(cluster)
                batch_result = archive_engine.batch_archive_partitions(
                    db_session=db,
                    partition_list=partition_list,
                    force=False
                )
                return {
                    "message": "Auto archive by policy completed",
                    "policy_config": policy_config,
                    "batch_result": batch_result,
                }
            else:
                return {
                    "message": "No partitions found matching the policy criteria",
                    "policy_config": policy_config,
                    "candidate_partitions": 0,
                }

        # 后台策略执行
        task = scan_task_manager.create_scan_task(
            db, cluster_id, 'policy-partition-archive', '策略驱动分区归档'
        )
        def run_policy():
            db_thread = SessionLocal()
            try:
                scan_task_manager.info(task.task_id, 'PL101', '开始策略归档', db=db_thread, phase='archive', ctx=policy_config)
                cluster_t = db_thread.query(Cluster).filter(Cluster.id == cluster_id).first()
                engine = PartitionArchiveEngine(cluster_t)
                if dry_run or not partition_list:
                    scan_task_manager.info(task.task_id, 'PL120', '策略匹配结果', db=db_thread, phase='archive', ctx={'candidates': len(partition_list)})
                    scan_task_manager.complete_task(db_thread, task.task_id, success=True)
                    return
                res = engine.batch_archive_partitions(db_thread, partition_list, False)
                scan_task_manager.info(task.task_id, 'PL190', '策略归档完成', db=db_thread, phase='archive', ctx={'success': res.get('success_count'), 'failed': res.get('failed_count')})
                scan_task_manager.complete_task(db_thread, task.task_id, success=True)
            except Exception as e:
                scan_task_manager.error(task.task_id, 'EL190', f'策略归档失败: {e}', db=db_thread, phase='archive')
                scan_task_manager.complete_task(db_thread, task.task_id, success=False, error_message=str(e))
            finally:
                try:
                    db_thread.close()
                except Exception:
                    pass
        import threading
        threading.Thread(target=run_policy, daemon=True).start()
        return {"message": "Policy partition archive started", "task_id": task.task_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto archive by policy failed: {str(e)}")
