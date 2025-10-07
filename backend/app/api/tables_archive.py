"""
表归档与恢复API模块

负责表的归档、恢复、状态查询和统计分析等功能。
使用存储策略(Storage Policy)机制实现冷热数据分层存储。
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.database import SessionLocal, get_db
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.monitor.simple_archive_engine import SimpleArchiveEngine
from app.services.scan_service import scan_task_manager

router = APIRouter()


@router.post("/archive-with-progress/{cluster_id}/{database_name}/{table_name}")
async def archive_table_with_progress(
    cluster_id: int,
    database_name: str,
    table_name: str,
    force: bool = Query(False, description="强制归档，跳过检查"),
    mode: str = Query("storage-policy", description="归档模式：仅支持 storage-policy"),
    policy: Optional[str] = Query(
        "COLD", description="当 mode=storage-policy 时的策略名称"
    ),
    recursive: bool = Query(
        True, description="当 mode=storage-policy 时是否递归应用到子目录"
    ),
    db: Session = Depends(get_db),
):
    """
    以后台任务形式执行表归档

    通过设置HDFS存储策略将表数据迁移到冷存储层。
    支持进度追踪和结构化日志输出。

    Args:
        cluster_id: 集群ID
        database_name: 数据库名称
        table_name: 表名称
        force: 是否强制归档,跳过检查
        mode: 归档模式,目前仅支持 'storage-policy'
        policy: 存储策略名称,默认 'COLD'
        recursive: 是否递归应用到子目录,默认True
        db: 数据库会话

    Returns:
        包含task_id和进度URL的字典,用于追踪归档进度

    Raises:
        HTTPException: 当集群不存在或归档模式不支持时
    """
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # 创建任务
    task_type = "archive-table-policy" if mode == "storage-policy" else "archive-table"
    task = scan_task_manager.create_scan_task(
        db,
        cluster_id=cluster_id,
        task_type=task_type,
        task_name=f"归档表: {database_name}.{table_name}",
        target_database=database_name,
        target_table=table_name,
    )

    task_id = task.task_id

    # 后台线程执行归档（结构化日志）
    def run_archive():
        db_thread = SessionLocal()
        try:
            # 线程内重新获取 Cluster，避免跨会话对象导致的 attribute refresh 异常
            cluster_t = (
                db_thread.query(Cluster).filter(Cluster.id == cluster_id).first()
            )
            if not cluster_t:
                raise RuntimeError("Cluster not found in thread session")
            archive_engine = SimpleArchiveEngine(cluster_t)
            if mode == "storage-policy":
                # 策略归档：设置存储策略
                scan_task_manager.safe_update_progress(
                    db_thread,
                    task_id,
                    status="running",
                    total_items=3,
                    completed_items=0,
                    current_item="init",
                )
                scan_task_manager.info(
                    task_id,
                    "PL101",
                    "开始策略归档",
                    db=db_thread,
                    phase="archive",
                    ctx={
                        "db": database_name,
                        "table": table_name,
                        "policy": policy,
                        "recursive": recursive,
                    },
                    database_name=database_name,
                    table_name=table_name,
                )
                scan_task_manager.safe_update_progress(
                    db_thread, task_id, completed_items=1, current_item="apply"
                )
                res = archive_engine.apply_storage_policy_table(
                    db_thread,
                    database_name,
                    table_name,
                    policy=policy or "COLD",
                    recursive=recursive,
                )
                scan_task_manager.info(
                    task_id,
                    "PL120",
                    "设置存储策略完成",
                    db=db_thread,
                    phase="archive",
                    ctx={
                        "paths_success": res.get("paths_success"),
                        "paths_failed": res.get("paths_failed"),
                        "effective": res.get("policy_effective"),
                    },
                    database_name=database_name,
                    table_name=table_name,
                )
                scan_task_manager.safe_update_progress(
                    db_thread, task_id, completed_items=2, current_item="finalize"
                )
                scan_task_manager.info(
                    task_id,
                    "PL190",
                    "策略归档完成",
                    db=db_thread,
                    phase="archive",
                    ctx={"mover_hint": True},
                    database_name=database_name,
                    table_name=table_name,
                )
                scan_task_manager.safe_update_progress(
                    db_thread, task_id, completed_items=3, current_item="done"
                )
                scan_task_manager.complete_task(db_thread, task_id, success=True)
            else:
                raise RuntimeError(
                    "Directory-move archive is disabled; use storage-policy"
                )
        except Exception as e:
            # 区分错误码
            if mode == "storage-policy":
                scan_task_manager.error(
                    task_id,
                    "EL190",
                    f"策略归档失败: {e}",
                    db=db_thread,
                    phase="archive",
                    database_name=database_name,
                    table_name=table_name,
                )
            else:
                scan_task_manager.error(
                    task_id,
                    "EA190",
                    f"表归档失败: {e}",
                    db=db_thread,
                    phase="archive",
                    database_name=database_name,
                    table_name=table_name,
                )
            scan_task_manager.complete_task(
                db_thread, task_id, success=False, error_message=str(e)
            )
        finally:
            try:
                db_thread.close()
            except Exception:
                pass

    import threading

    threading.Thread(target=run_archive, daemon=True).start()

    return {
        "message": "Archive started",
        "task_id": task_id,
        "cluster_id": cluster_id,
        "progress_url": f"/api/v1/tables/scan-progress/{task_id}",
        "status": "started",
    }


@router.post("/restore-with-progress/{cluster_id}/{database_name}/{table_name}")
async def restore_table_with_progress(
    cluster_id: int,
    database_name: str,
    table_name: str,
    db: Session = Depends(get_db),
):
    """
    以后台任务形式执行表恢复

    通过将存储策略设置为HOT,将表数据从冷存储层恢复到热存储层。
    支持进度追踪和结构化日志输出。

    Args:
        cluster_id: 集群ID
        database_name: 数据库名称
        table_name: 表名称
        db: 数据库会话

    Returns:
        包含task_id的字典,用于追踪恢复进度

    Raises:
        HTTPException: 当集群不存在时
    """
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    task = scan_task_manager.create_scan_task(
        db,
        cluster_id=cluster_id,
        task_type="restore-table-policy",
        task_name=f"恢复表策略: {database_name}.{table_name}",
        target_database=database_name,
        target_table=table_name,
    )
    task_id = task.task_id

    def run_restore():
        db_thread = SessionLocal()
        try:
            # 线程内重新获取 Cluster
            cluster_t = (
                db_thread.query(Cluster).filter(Cluster.id == cluster_id).first()
            )
            if not cluster_t:
                raise RuntimeError("Cluster not found in thread session")
            scan_task_manager.safe_update_progress(
                db_thread,
                task_id,
                status="running",
                total_items=3,
                completed_items=0,
                current_item="init",
            )
            scan_task_manager.info(
                task_id,
                "PL101",
                "开始策略归档",
                db=db_thread,
                phase="restore",
                ctx={
                    "db": database_name,
                    "table": table_name,
                    "policy": "HOT",
                    "recursive": True,
                },
                database_name=database_name,
                table_name=table_name,
            )
            scan_task_manager.safe_update_progress(
                db_thread, task_id, completed_items=1, current_item="apply"
            )
            engine = SimpleArchiveEngine(cluster_t)
            res = engine.apply_storage_policy_table(
                db_thread, database_name, table_name, policy="HOT", recursive=True
            )
            scan_task_manager.info(
                task_id,
                "PL120",
                "设置存储策略完成",
                db=db_thread,
                phase="restore",
                ctx={
                    "paths_success": res.get("paths_success"),
                    "paths_failed": res.get("paths_failed"),
                    "effective": res.get("policy_effective"),
                },
                database_name=database_name,
                table_name=table_name,
            )
            scan_task_manager.safe_update_progress(
                db_thread, task_id, completed_items=2, current_item="finalize"
            )
            scan_task_manager.info(
                task_id,
                "PL190",
                "策略归档完成",
                db=db_thread,
                phase="restore",
                ctx={"mover_hint": False},
                database_name=database_name,
                table_name=table_name,
            )
            scan_task_manager.safe_update_progress(
                db_thread, task_id, completed_items=3, current_item="done"
            )
            scan_task_manager.complete_task(db_thread, task_id, success=True)
        except Exception as e:
            scan_task_manager.error(
                task_id,
                "EL190",
                f"策略归档失败: {e}",
                db=db_thread,
                phase="restore",
                database_name=database_name,
                table_name=table_name,
            )
            scan_task_manager.complete_task(
                db_thread, task_id, success=False, error_message=str(e)
            )
        finally:
            try:
                db_thread.close()
            except Exception:
                pass

    import threading

    threading.Thread(target=run_restore, daemon=True).start()
    return {
        "message": "Restore started",
        "task_id": task_id,
        "cluster_id": cluster_id,
        "status": "started",
    }


@router.get("/archive-status/{cluster_id}/{database_name}/{table_name}")
async def get_archive_status(
    cluster_id: int, database_name: str, table_name: str, db: Session = Depends(get_db)
):
    """
    获取表的归档状态

    查询指定表的当前归档状态、归档位置、归档时间等信息。

    Args:
        cluster_id: 集群ID
        database_name: 数据库名称
        table_name: 表名称
        db: 数据库会话

    Returns:
        包含表信息和归档详情的字典

    Raises:
        HTTPException: 当表不存在时返回404
    """
    table_metric = (
        db.query(TableMetric)
        .filter(
            TableMetric.cluster_id == cluster_id,
            TableMetric.database_name == database_name,
            TableMetric.table_name == table_name,
        )
        .order_by(TableMetric.scan_time.desc())
        .first()
    )

    if not table_metric:
        raise HTTPException(
            status_code=404, detail=f"Table {database_name}.{table_name} not found"
        )

    return {
        "table_info": {
            "database_name": database_name,
            "table_name": table_name,
            "cluster_id": cluster_id,
        },
        "archive_info": {
            "archive_status": table_metric.archive_status,
            "archive_location": table_metric.archive_location,
            "archived_at": table_metric.archived_at,
            "is_cold_data": bool(table_metric.is_cold_data),
            "days_since_last_access": table_metric.days_since_last_access,
        },
    }


@router.get("/archived-tables/{cluster_id}")
async def list_archived_tables(
    cluster_id: int,
    database_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    获取已归档表的分页列表

    返回指定集群中所有已归档的表,支持数据库筛选和分页。

    Args:
        cluster_id: 集群ID
        database_name: 数据库名称筛选,为空则返回所有数据库
        page: 页码,从1开始
        page_size: 每页记录数,1-200
        db: 数据库会话

    Returns:
        包含分页信息和已归档表列表的字典
    """
    query = db.query(TableMetric).filter(
        TableMetric.cluster_id == cluster_id, TableMetric.archive_status == "archived"
    )

    if database_name:
        query = query.filter(TableMetric.database_name == database_name)

    total_count = query.count()
    offset = (page - 1) * page_size
    archived_tables = (
        query.order_by(TableMetric.archived_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return {
        "cluster_id": cluster_id,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,
        },
        "archived_tables": [
            {
                "database_name": table.database_name,
                "table_name": table.table_name,
                "original_size": table.total_size,
                "archive_location": table.archive_location,
                "archived_at": table.archived_at,
                "days_since_last_access": table.days_since_last_access,
            }
            for table in archived_tables
        ],
    }


@router.get("/archive-statistics/{cluster_id}")
async def get_archive_statistics(
    cluster_id: int,
    days_range: int = Query(30, description="统计天数范围"),
    db: Session = Depends(get_db),
):
    """
    获取归档统计信息

    返回指定时间范围内的归档统计,包括归档表数量、总大小、平均大小,
    以及按数据库分组的归档分布。

    Args:
        cluster_id: 集群ID
        days_range: 统计天数范围,默认30天
        db: 数据库会话

    Returns:
        包含时间范围、总体统计和数据库分布的字典
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_range)

    # 获取时间范围内的归档统计
    archive_stats = (
        db.query(
            func.count(TableMetric.id).label("archived_count"),
            func.sum(TableMetric.total_size).label("total_archived_size"),
            func.avg(TableMetric.total_size).label("avg_table_size"),
        )
        .filter(
            TableMetric.cluster_id == cluster_id,
            TableMetric.archive_status == "archived",
            TableMetric.archived_at >= start_date,
        )
        .first()
    )

    # 获取按数据库分组的归档统计
    db_stats = (
        db.query(
            TableMetric.database_name,
            func.count(TableMetric.id).label("count"),
            func.sum(TableMetric.total_size).label("total_size"),
        )
        .filter(
            TableMetric.cluster_id == cluster_id,
            TableMetric.archive_status == "archived",
        )
        .group_by(TableMetric.database_name)
        .all()
    )

    return {
        "cluster_id": cluster_id,
        "time_range": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days_range,
        },
        "overall_statistics": {
            "archived_tables_count": archive_stats.archived_count or 0,
            "total_archived_size_bytes": archive_stats.total_archived_size or 0,
            "average_table_size_bytes": archive_stats.avg_table_size or 0,
        },
        "database_breakdown": [
            {
                "database_name": db_name,
                "archived_count": count,
                "total_size_bytes": total_size,
            }
            for db_name, count, total_size in db_stats
        ],
    }
