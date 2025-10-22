"""
核心表查询 API
提供基础的表指标查询、数据库列表、表列表等功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.schemas.table_metric import TableMetricResponse

router = APIRouter()


@router.get("/metrics", response_model=list[TableMetricResponse])
async def get_table_metrics(
    cluster_id: int = Query(..., description="Cluster ID to filter tables"),
    database_name: str = Query(None, description="Optional database name filter"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
):
    """Get latest table metrics per table (deduplicated by database_name + table_name).

    Args:
        cluster_id: Cluster ID to filter tables
        database_name: Optional database name filter
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return (default: 100, max: 1000)
    """
    base = db.query(
        TableMetric.database_name,
        TableMetric.table_name,
        func.max(TableMetric.id).label("max_id"),
    ).filter(TableMetric.cluster_id == cluster_id)

    if database_name:
        base = base.filter(TableMetric.database_name == database_name)

    base = base.group_by(TableMetric.database_name, TableMetric.table_name)

    # Apply pagination to the aggregation query first
    latest_ids_query = base.offset(skip).limit(limit)
    latest_ids = [row.max_id for row in latest_ids_query.all()]

    if not latest_ids:
        return []

    # Fetch full records for the paginated IDs
    metrics = (
        db.query(TableMetric)
        .filter(TableMetric.id.in_(latest_ids))
        .order_by(TableMetric.database_name.asc(), TableMetric.table_name.asc())
        .all()
    )
    return metrics


@router.get("/small-files", response_model=dict)
async def get_small_file_summary(
    cluster_id: int = Query(...), db: Session = Depends(get_db)
):
    """Get small file summary for a cluster"""
    result = (
        db.query(
            func.count(TableMetric.id).label("total_tables"),
            func.sum(TableMetric.total_files).label("total_files"),
            func.sum(TableMetric.small_files).label("total_small_files"),
            func.avg(TableMetric.avg_file_size).label("avg_file_size"),
        )
        .filter(TableMetric.cluster_id == cluster_id)
        .first()
    )

    return {
        "total_tables": result.total_tables or 0,
        "total_files": result.total_files or 0,
        "total_small_files": result.total_small_files or 0,
        "avg_file_size": float(result.avg_file_size or 0),
        "small_file_ratio": (
            (result.total_small_files / result.total_files * 100)
            if result.total_files
            else 0
        ),
    }


@router.get("/databases/{cluster_id}")
async def get_databases(cluster_id: int, db: Session = Depends(get_db)):
    """Get list of databases for a cluster"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as connector:
            databases = connector.get_databases()
            return {"databases": databases}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get databases: {str(e)}"
        )


@router.get("/tables/{cluster_id}/{database_name}")
async def get_tables(
    cluster_id: int, database_name: str, db: Session = Depends(get_db)
):
    """Get list of tables for a database in a cluster"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as connector:
            tables = connector.get_tables(database_name)
            return {"database": database_name, "tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tables: {str(e)}")


@router.get("/small-file-analysis/{cluster_id}")
async def analyze_small_file_ratios(cluster_id: int, db: Session = Depends(get_db)):
    """Analyze small file ratios for each table"""
    all_tables = (
        db.query(TableMetric).filter(TableMetric.cluster_id == cluster_id).all()
    )

    if not all_tables:
        return {"message": "No table data found", "tables": []}

    table_analysis = []
    for table in all_tables:
        if table.total_files and table.total_files > 0:
            small_file_ratio = (table.small_files / table.total_files) * 100
        else:
            small_file_ratio = 0

        # 确定优先级
        if small_file_ratio > 80:
            priority = "CRITICAL"
            priority_score = 5
        elif small_file_ratio > 60:
            priority = "HIGH"
            priority_score = 4
        elif small_file_ratio > 40:
            priority = "MEDIUM"
            priority_score = 3
        elif small_file_ratio > 20:
            priority = "LOW"
            priority_score = 2
        else:
            priority = "MINIMAL"
            priority_score = 1

        # 计算预估节省空间
        if table.small_files > 0 and table.avg_file_size > 0:
            small_files_total_size = table.small_files * table.avg_file_size
            estimated_savings_gb = small_files_total_size / (1024 * 1024 * 1024) * 0.3
        else:
            estimated_savings_gb = 0

        table_info = {
            "database_name": table.database_name,
            "table_name": table.table_name,
            "table_path": table.table_path,
            "total_files": table.total_files,
            "small_files": table.small_files,
            "small_file_ratio": round(small_file_ratio, 2),
            "priority": priority,
            "priority_score": priority_score,
            "avg_file_size_mb": (
                round(table.avg_file_size / (1024 * 1024), 2)
                if table.avg_file_size
                else 0
            ),
            "total_size_gb": (
                round(table.total_size / (1024 * 1024 * 1024), 2)
                if table.total_size
                else 0
            ),
            "estimated_savings_gb": round(estimated_savings_gb, 2),
            "is_partitioned": table.is_partitioned,
            "partition_count": table.partition_count,
            "last_scan": table.scan_time.isoformat() if table.scan_time else None,
        }

        table_analysis.append(table_info)

    # 排序
    table_analysis.sort(
        key=lambda x: (-x["priority_score"], -x["small_file_ratio"], -x["small_files"])
    )

    # 统计
    total_tables = len(table_analysis)
    critical_tables = len([t for t in table_analysis if t["priority"] == "CRITICAL"])
    high_priority_tables = len([t for t in table_analysis if t["priority"] == "HIGH"])
    total_small_files = sum([t["small_files"] for t in table_analysis])
    total_files = sum([t["total_files"] for t in table_analysis])
    overall_small_file_ratio = (
        (total_small_files / total_files * 100) if total_files > 0 else 0
    )
    total_estimated_savings = sum([t["estimated_savings_gb"] for t in table_analysis])

    recommendations = []
    if critical_tables > 0:
        recommendations.append(
            f"Immediately merge {critical_tables} critical tables with >80% small files"
        )
    if high_priority_tables > 0:
        recommendations.append(
            f"Schedule merging for {high_priority_tables} high priority tables"
        )
    if overall_small_file_ratio > 50:
        recommendations.append("Consider cluster-wide small file optimization strategy")

    return {
        "cluster_id": cluster_id,
        "summary": {
            "total_tables": total_tables,
            "critical_tables": critical_tables,
            "high_priority_tables": high_priority_tables,
            "overall_small_file_ratio": round(overall_small_file_ratio, 2),
            "total_estimated_savings_gb": round(total_estimated_savings, 2),
        },
        "recommendations": recommendations,
        "tables": table_analysis[:50],
    }
