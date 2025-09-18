"""
表归档API模块
负责冷数据扫描、表归档、恢复等功能
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.monitor.cold_data_scanner import SimpleColdDataScanner
from app.monitor.simple_archive_engine import SimpleArchiveEngine

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
    db: Session = Depends(get_db),
):
    """扫描集群中的冷数据表"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        cold_scanner = SimpleColdDataScanner(cluster)

        threshold = (
            cold_days_threshold
            if cold_days_threshold is not None
            else (cold_threshold_days if cold_threshold_days is not None else 90)
        )

        scan_result = cold_scanner.scan_cold_data(
            threshold_days=threshold, database_filter=database_name
        )

        # 更新数据库中的冷数据标记
        cold_tables = scan_result.get("cold_tables", [])
        updated_count = 0

        for cold_table in cold_tables:
            db_name = cold_table.get("database_name")
            table_name = cold_table.get("table_name")
            last_access_time = cold_table.get("last_access_time")
            days_since_access = cold_table.get("days_since_last_access", 0)

            # 更新最新的表指标记录
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cold data scan failed: {str(e)}")


@router.get("/cold-data-summary/{cluster_id}")
async def get_cold_data_summary(cluster_id: int, db: Session = Depends(get_db)):
    """获取集群冷数据统计摘要"""
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
    """获取冷数据表列表"""
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


@router.post("/archive-table/{cluster_id}/{database_name}/{table_name}")
async def archive_table(
    cluster_id: int,
    database_name: str,
    table_name: str,
    force: bool = Query(False, description="强制归档，跳过检查"),
    db: Session = Depends(get_db),
):
    """归档指定表到冷存储"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # 检查表是否存在
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

    # 检查是否已经归档
    if table_metric.archive_status == "archived" and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Table {database_name}.{table_name} is already archived",
        )

    try:
        archive_engine = SimpleArchiveEngine(cluster)

        archive_result = archive_engine.archive_table(
            database_name=database_name, table_name=table_name, force=force
        )

        # 更新数据库记录
        table_metric.archive_status = "archived"
        table_metric.archive_location = archive_result.get("archive_location")
        table_metric.archived_at = datetime.utcnow()
        db.commit()

        return {
            "message": f"Table {database_name}.{table_name} archived successfully",
            "table_info": {
                "database_name": database_name,
                "table_name": table_name,
                "original_size": table_metric.total_size,
            },
            "archive_result": archive_result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Archive failed: {str(e)}")


@router.post("/restore-table/{cluster_id}/{database_name}/{table_name}")
async def restore_table(
    cluster_id: int, database_name: str, table_name: str, db: Session = Depends(get_db)
):
    """从归档存储恢复表"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # 检查表是否存在且已归档
    table_metric = (
        db.query(TableMetric)
        .filter(
            TableMetric.cluster_id == cluster_id,
            TableMetric.database_name == database_name,
            TableMetric.table_name == table_name,
            TableMetric.archive_status == "archived",
        )
        .order_by(TableMetric.scan_time.desc())
        .first()
    )

    if not table_metric:
        raise HTTPException(
            status_code=404,
            detail=f"Archived table {database_name}.{table_name} not found",
        )

    try:
        archive_engine = SimpleArchiveEngine(cluster)

        restore_result = archive_engine.restore_table(
            database_name=database_name,
            table_name=table_name,
            archive_location=table_metric.archive_location,
        )

        # 更新数据库记录
        table_metric.archive_status = "active"
        table_metric.archive_location = None
        table_metric.archived_at = None
        db.commit()

        return {
            "message": f"Table {database_name}.{table_name} restored successfully",
            "table_info": {"database_name": database_name, "table_name": table_name},
            "restore_result": restore_result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.get("/archive-status/{cluster_id}/{database_name}/{table_name}")
async def get_archive_status(
    cluster_id: int, database_name: str, table_name: str, db: Session = Depends(get_db)
):
    """获取表的归档状态"""
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
    """获取已归档表列表"""
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
    """获取归档统计信息"""
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
