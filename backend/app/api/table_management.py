"""
表管理API模块
负责基础的表查询、数据库列表、表指标等功能
"""

from typing import Dict, List, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.schemas.table_metric import TableMetricResponse

router = APIRouter()


@router.get("/metrics", response_model=list[TableMetricResponse])
async def get_table_metrics(
    cluster_id: int = Query(...),
    database_name: str = Query(None),
    db: Session = Depends(get_db),
):
    """获取表级指标数据（按表去重，返回最新记录）"""
    base = db.query(
        TableMetric.database_name,
        TableMetric.table_name,
        func.max(TableMetric.id).label("max_id"),
    ).filter(TableMetric.cluster_id == cluster_id)

    if database_name:
        base = base.filter(TableMetric.database_name == database_name)

    base = base.group_by(TableMetric.database_name, TableMetric.table_name)
    latest_ids = [row.max_id for row in base.all()]

    if not latest_ids:
        return []

    metrics = (
        db.query(TableMetric)
        .filter(TableMetric.id.in_(latest_ids))
        .order_by(TableMetric.database_name.asc(), TableMetric.table_name.asc())
        .all()
    )
    return metrics


@router.get("/small-files", response_model=dict)
async def get_small_file_summary(
    cluster_id: int = Query(...),
    database_name: str = Query(None),
    db: Session = Depends(get_db),
):
    """获取小文件统计摘要（保持与旧接口一致的返回结构）"""
    from sqlalchemy import func

    base = db.query(
        func.count(TableMetric.id).label("total_tables"),
        func.sum(TableMetric.total_files).label("total_files"),
        func.sum(TableMetric.small_files).label("total_small_files"),
        func.avg(TableMetric.avg_file_size).label("avg_file_size"),
    ).filter(TableMetric.cluster_id == cluster_id)

    if database_name:
        base = base.filter(TableMetric.database_name == database_name)

    result = base.first()

    total_files = result.total_files or 0
    total_small_files = result.total_small_files or 0
    ratio_percent = (total_small_files / total_files * 100) if total_files else 0

    return {
        "total_tables": int(result.total_tables or 0),
        "total_files": int(total_files),
        "total_small_files": int(total_small_files),
        "avg_file_size": float(result.avg_file_size or 0.0),
        "small_file_ratio": ratio_percent,
    }


@router.get("/databases/{cluster_id}")
async def get_databases(cluster_id: int, db: Session = Depends(get_db)):
    """获取集群的数据库列表"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # 从 table_metrics 表中获取已扫描的数据库列表
    databases = (
        db.query(TableMetric.database_name)
        .filter(TableMetric.cluster_id == cluster_id)
        .distinct()
        .all()
    )

    database_list = [db_row[0] for db_row in databases]
    return {"databases": database_list}


@router.get("/tables/{cluster_id}/{database_name}")
async def get_tables(
    cluster_id: int, database_name: str, db: Session = Depends(get_db)
):
    """获取指定数据库的表列表"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # 从 table_metrics 表中获取已扫描的表列表
    tables = (
        db.query(TableMetric.table_name)
        .filter(
            TableMetric.cluster_id == cluster_id,
            TableMetric.database_name == database_name,
        )
        .distinct()
        .all()
    )

    table_list = [table_row[0] for table_row in tables]
    return {"tables": table_list}


@router.get("/table-detail/{cluster_id}/{database_name}/{table_name}")
async def get_table_detail(
    cluster_id: int, database_name: str, table_name: str, db: Session = Depends(get_db)
):
    """获取单个表的详细信息"""
    # 获取最新的表指标记录
    latest_metric = (
        db.query(TableMetric)
        .filter(
            TableMetric.cluster_id == cluster_id,
            TableMetric.database_name == database_name,
            TableMetric.table_name == table_name,
        )
        .order_by(TableMetric.scan_time.desc())
        .first()
    )

    if not latest_metric:
        raise HTTPException(
            status_code=404,
            detail=f"Table {database_name}.{table_name} not found or not scanned",
        )

    return {
        "table_info": {
            "cluster_id": latest_metric.cluster_id,
            "database_name": latest_metric.database_name,
            "table_name": latest_metric.table_name,
            "table_type": latest_metric.table_type,
            "storage_format": latest_metric.storage_format,
            "table_path": latest_metric.table_path,
            "is_partitioned": bool(latest_metric.is_partitioned),
            "partition_count": latest_metric.partition_count,
            "table_owner": latest_metric.table_owner,
            "table_create_time": latest_metric.table_create_time,
        },
        "file_metrics": {
            "total_files": latest_metric.total_files,
            "small_files": latest_metric.small_files,
            "total_size": latest_metric.total_size,
            "avg_file_size": latest_metric.avg_file_size,
            "small_file_ratio": (
                (latest_metric.small_files / latest_metric.total_files * 100)
                if latest_metric.total_files > 0
                else 0
            ),
        },
        "scan_info": {
            "scan_time": latest_metric.scan_time,
            "scan_duration": latest_metric.scan_duration,
        },
        "cold_data_info": {
            "is_cold_data": bool(latest_metric.is_cold_data),
            "last_access_time": latest_metric.last_access_time,
            "days_since_last_access": latest_metric.days_since_last_access,
            "archive_status": latest_metric.archive_status,
            "archive_location": latest_metric.archive_location,
            "archived_at": latest_metric.archived_at,
        },
    }


@router.get("/table-history/{cluster_id}/{database_name}/{table_name}")
async def get_table_scan_history(
    cluster_id: int,
    database_name: str,
    table_name: str,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取表的扫描历史记录"""
    history = (
        db.query(TableMetric)
        .filter(
            TableMetric.cluster_id == cluster_id,
            TableMetric.database_name == database_name,
            TableMetric.table_name == table_name,
        )
        .order_by(TableMetric.scan_time.desc())
        .limit(limit)
        .all()
    )

    return {
        "table_name": f"{database_name}.{table_name}",
        "scan_count": len(history),
        "history": [
            {
                "scan_time": record.scan_time,
                "total_files": record.total_files,
                "small_files": record.small_files,
                "total_size": record.total_size,
                "scan_duration": record.scan_duration,
            }
            for record in history
        ],
    }


@router.get("/{cluster_id}/{database_name}/{table_name}/partitions")
async def get_table_partitions(
    cluster_id: int, database_name: str, table_name: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取表的分区列表"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        from app.engines.safe_hive_engine import SafeHiveMergeEngine
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"Getting partitions for {database_name}.{table_name} on cluster {cluster_id}")

        engine = SafeHiveMergeEngine(cluster)

        # 检查实际表结构，确定是否为真正的分区表
        logger.info(f"Checking real partition status for {database_name}.{table_name}")
        
        try:
            # 尝试检查表是否真的是分区表
            table_exists = engine._table_exists(database_name, table_name)
            if table_exists:
                is_partitioned = engine._is_partitioned_table(database_name, table_name)
                if is_partitioned:
                    # 如果是真的分区表，获取实际分区
                    real_partitions = engine._get_table_partitions(database_name, table_name)
                    return {
                        "table_name": table_name,
                        "is_partitioned": True,
                        "partitions": real_partitions or [],
                        "partition_count": len(real_partitions or []),
                        "message": f"共{len(real_partitions or [])}个分区",
                        "real_mode": True,
                    }
        except Exception as e:
            logger.warning(f"Failed to check real partition status: {str(e)}")
        
        # 如果表不存在或不是分区表，返回明确的非分区状态
        return {
            "table_name": table_name,
            "is_partitioned": False,
            "partitions": [],
            "partition_count": 0,
            "message": "该表不是分区表或不存在",
            "error_detail": "表结构检查：非分区表"
        }

        # 获取分区列表
        try:
            partitions = engine._get_table_partitions(database_name, table_name)
            if partitions is None:
                partitions = []
        except Exception as e:
            logger.error(f"Error getting table partitions: {str(e)}")
            return {
                "table_name": table_name,
                "is_partitioned": True,
                "partitions": [],
                "error": f"Failed to get partitions: {str(e)}",
                "message": "Error retrieving partition information",
            }

        # 解析分区信息，提取分区键和值
        partition_info = []
        for partition in partitions:
            try:
                # partition格式通常是: dt=2023-12-01/hour=00
                partition_parts = {}
                for part in partition.split("/"):
                    if "=" in part:
                        key, value = part.split("=", 1)
                        partition_parts[key] = value

                partition_info.append(
                    {"partition_spec": partition, "partition_keys": partition_parts}
                )
            except Exception as e:
                logger.warning(f"Error parsing partition {partition}: {str(e)}")
                # 保留原始分区字符串
                partition_info.append(
                    {"partition_spec": partition, "partition_keys": {}}
                )

        return {
            "table_name": table_name,
            "is_partitioned": True,
            "partition_count": len(partitions),
            "partitions": partition_info[:100],  # 最多返回100个分区
            "total_partitions": len(partitions),
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in get_table_partitions: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get partitions: {str(e)}"
        )
