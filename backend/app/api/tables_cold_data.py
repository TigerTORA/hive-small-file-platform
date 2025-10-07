"""
冷数据扫描与查询API模块

负责冷数据表的扫描、统计摘要和列表查询等功能。
冷数据是指长时间未被访问的表,可作为归档候选。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.database import SessionLocal, get_db
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.monitor.cold_data_scanner import SimpleColdDataScanner
from app.services.scan_service import scan_task_manager

router = APIRouter()


@router.post("/scan-cold-data/{cluster_id}")
async def scan_cold_data(
    cluster_id: int,
    # 兼容旧参数名 cold_days_threshold，同时支持 cold_threshold_days
    cold_days_threshold: Optional[int] = Query(
        None, description="冷数据阈值天数（兼容参数名）"
    ),
    cold_threshold_days: Optional[int] = Query(None, description="冷数据阈值天数"),
    database_name: Optional[str] = Query(None, description="指定数据库名称"),
    background: bool = Query(True, description="是否后台任务运行并输出任务日志"),
    db: Session = Depends(get_db),
):
    """
    扫描集群中的冷数据表

    根据最后访问时间阈值,识别长期未访问的表并标记为冷数据。
    支持同步和异步两种扫描模式。

    Args:
        cluster_id: 集群ID
        cold_days_threshold: 冷数据阈值天数(兼容参数)
        cold_threshold_days: 冷数据阈值天数
        database_name: 指定数据库名称,为空则扫描所有数据库
        background: 是否后台任务运行,默认True
        db: 数据库会话

    Returns:
        同步模式: 返回扫描结果统计
        异步模式: 返回task_id用于追踪进度
    """
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        threshold = (
            cold_days_threshold
            if cold_days_threshold is not None
            else (cold_threshold_days if cold_threshold_days is not None else 90)
        )

        if not background:
            cold_scanner = SimpleColdDataScanner(cluster)
            scan_result = cold_scanner.scan_cold_data(
                threshold_days=threshold, database_filter=database_name
            )
            cold_tables = scan_result.get("cold_tables", [])
            updated_count = 0
            for cold_table in cold_tables:
                db_name = cold_table.get("database_name")
                table_name = cold_table.get("table_name")
                last_access_time = cold_table.get("last_access_time")
                days_since_access = cold_table.get("days_since_last_access", 0)
                latest_metric = (
                    db.query(TableMetric)
                    .filter(
                        TableMetric.cluster_id == cluster_id,
                        TableMetric.database_name == db_name,
                        TableMetric.table_name == table_name,
                    )
                    .order_by(TableMetric.scan_time.desc())
                    .first()
                )
                if latest_metric:
                    latest_metric.is_cold_data = 1
                    latest_metric.last_access_time = last_access_time
                    latest_metric.days_since_last_access = days_since_access
                    updated_count += 1
            db.commit()
            return {
                "message": "Cold data scan completed",
                "cluster_id": cluster_id,
                "scan_config": {
                    "threshold_days": threshold,
                    "database_filter": database_name,
                },
                "scan_result": {
                    "cold_tables_found": len(cold_tables),
                    "database_records_updated": updated_count,
                    "scan_timestamp": datetime.utcnow().isoformat(),
                },
            }

        # 后台任务模式：集成任务视图 + 结构化日志
        task = scan_task_manager.create_scan_task(
            db, cluster_id, "cold-table-scan", f"扫描冷数据表(阈值{threshold}天)"
        )

        def run_cold_scan():
            db_thread = SessionLocal()
            try:
                cluster_t = (
                    db_thread.query(Cluster).filter(Cluster.id == cluster_id).first()
                )
                cold_scanner = SimpleColdDataScanner(cluster_t)
                scan_task_manager.info(
                    task.task_id,
                    "T301",
                    "开始冷数据表扫描",
                    db=db_thread,
                    phase="scan",
                    ctx={"threshold_days": threshold, "db": database_name},
                )
                scan_result = cold_scanner.scan_cold_data(
                    threshold_days=threshold, database_filter=database_name
                )
                cold_tables = (
                    scan_result.get("cold_tables", [])
                    if isinstance(scan_result, dict)
                    else []
                )
                updated_count = 0
                for cold_table in cold_tables:
                    db_name = cold_table.get("database_name")
                    table_name = cold_table.get("table_name")
                    last_access_time = cold_table.get("last_access_time")
                    days_since_access = cold_table.get("days_since_last_access", 0)
                    latest_metric = (
                        db_thread.query(TableMetric)
                        .filter(
                            TableMetric.cluster_id == cluster_id,
                            TableMetric.database_name == db_name,
                            TableMetric.table_name == table_name,
                        )
                        .order_by(TableMetric.scan_time.desc())
                        .first()
                    )
                    if latest_metric:
                        latest_metric.is_cold_data = 1
                        latest_metric.last_access_time = last_access_time
                        latest_metric.days_since_last_access = days_since_access
                        updated_count += 1
                db_thread.commit()
                scan_task_manager.info(
                    task.task_id,
                    "T390",
                    "冷数据表扫描完成",
                    db=db_thread,
                    phase="scan",
                    ctx={"found": len(cold_tables), "updated": updated_count},
                )
                scan_task_manager.complete_task(db_thread, task.task_id, success=True)
            except Exception as e:
                scan_task_manager.error(
                    task.task_id,
                    "ET390",
                    f"冷数据表扫描失败: {e}",
                    db=db_thread,
                    phase="scan",
                )
                scan_task_manager.complete_task(
                    db_thread, task.task_id, success=False, error_message=str(e)
                )
            finally:
                try:
                    db_thread.close()
                except Exception:
                    pass

        import threading

        threading.Thread(target=run_cold_scan, daemon=True).start()
        return {"message": "Cold data scan started", "task_id": task.task_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cold data scan failed: {str(e)}")


@router.get("/cold-data-summary/{cluster_id}")
async def get_cold_data_summary(cluster_id: int, db: Session = Depends(get_db)):
    """
    获取集群冷数据统计摘要

    返回冷数据表的总数、总大小、平均未访问天数,以及归档状态分布。

    Args:
        cluster_id: 集群ID
        db: 数据库会话

    Returns:
        包含冷数据摘要和归档状态分布的字典
    """
    # 获取冷数据表统计
    cold_data_stats = (
        db.query(
            func.count(TableMetric.id).label("cold_table_count"),
            func.sum(TableMetric.total_size).label("total_cold_size"),
            func.avg(TableMetric.days_since_last_access).label("avg_days_since_access"),
        )
        .filter(TableMetric.cluster_id == cluster_id, TableMetric.is_cold_data == 1)
        .first()
    )

    # 获取归档状态统计
    archive_stats = (
        db.query(TableMetric.archive_status, func.count(TableMetric.id).label("count"))
        .filter(TableMetric.cluster_id == cluster_id)
        .group_by(TableMetric.archive_status)
        .all()
    )

    return {
        "cluster_id": cluster_id,
        "cold_data_summary": {
            "cold_table_count": cold_data_stats.cold_table_count or 0,
            "total_cold_size_bytes": cold_data_stats.total_cold_size or 0,
            "avg_days_since_access": round(
                cold_data_stats.avg_days_since_access or 0, 1
            ),
        },
        "archive_status_breakdown": {status: count for status, count in archive_stats},
    }


@router.get("/cold-data-list/{cluster_id}")
async def get_cold_data_list(
    cluster_id: int,
    database_name: Optional[str] = Query(None),
    min_days_since_access: int = Query(0, description="最小未访问天数"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    order_by: str = Query("days_since_last_access", description="排序字段"),
    order_desc: bool = Query(True, description="是否降序"),
    db: Session = Depends(get_db),
):
    """
    获取冷数据表分页列表

    支持按数据库名称、未访问天数筛选,以及自定义排序和分页。

    Args:
        cluster_id: 集群ID
        database_name: 数据库名称筛选
        min_days_since_access: 最小未访问天数
        page: 页码,从1开始
        page_size: 每页记录数,1-200
        order_by: 排序字段名
        order_desc: 是否降序排列
        db: 数据库会话

    Returns:
        包含分页信息、筛选条件和冷数据表列表的字典
    """
    query = db.query(TableMetric).filter(
        TableMetric.cluster_id == cluster_id, TableMetric.is_cold_data == 1
    )

    if database_name:
        query = query.filter(TableMetric.database_name == database_name)

    if min_days_since_access > 0:
        query = query.filter(
            TableMetric.days_since_last_access >= min_days_since_access
        )

    # 排序
    if hasattr(TableMetric, order_by):
        order_column = getattr(TableMetric, order_by)
        if order_desc:
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

    # 分页
    total_count = query.count()
    offset = (page - 1) * page_size
    cold_tables = query.offset(offset).limit(page_size).all()

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
            "min_days_since_access": min_days_since_access,
        },
        "cold_tables": [
            {
                "database_name": table.database_name,
                "table_name": table.table_name,
                "table_size": table.total_size,
                "last_access_time": table.last_access_time,
                "days_since_last_access": table.days_since_last_access,
                "archive_status": table.archive_status,
                "archive_location": table.archive_location,
                "archived_at": table.archived_at,
            }
            for table in cold_tables
        ],
    }
