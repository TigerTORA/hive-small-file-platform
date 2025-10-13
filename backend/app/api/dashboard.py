"""
Dashboard API endpoints for monitoring data aggregation
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

# Remove import as we'll implement validation inline
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.models.partition_metric import PartitionMetric
from app.models.table_metric import TableMetric

router = APIRouter()


# Response Models
class DashboardSummary(BaseModel):
    total_clusters: int
    active_clusters: int
    total_tables: int
    monitored_tables: int
    total_files: int
    total_small_files: int
    small_file_ratio: float
    total_size_gb: float
    small_file_size_gb: float
    files_reduced: int
    size_saved_gb: float


class TrendPoint(BaseModel):
    date: str
    small_files: int
    total_files: int
    ratio: float


class FileDistributionItem(BaseModel):
    size_range: str
    count: int
    size_gb: float
    percentage: float


class TopTable(BaseModel):
    cluster_name: str
    database_name: str
    table_name: str
    small_files: int
    total_files: int
    small_file_ratio: float
    total_size_gb: float
    last_scan: datetime


class RecentTask(BaseModel):
    id: int
    task_name: str
    cluster_name: str
    table_name: str
    status: str
    created_time: datetime
    updated_time: Optional[datetime]
    files_before: Optional[int]
    files_after: Optional[int]
    files_reduced: Optional[int]
    size_saved: Optional[int]


class TableFileCountPoint(BaseModel):
    date: str
    table_name: str
    database_name: str
    cluster_name: str
    total_files: int
    small_files: int
    ratio: float


class TableFileCountItem(BaseModel):
    table_id: str  # cluster_id:database:table format
    cluster_name: str
    database_name: str
    table_name: str
    current_files: int
    trend_7d: float  # percentage change


class ColdDataItem(BaseModel):
    cluster_name: str
    database_name: str
    table_name: str
    partition_name: Optional[str]
    last_access_time: Optional[datetime]
    days_since_last_access: Optional[int]
    total_size_gb: float
    file_count: int


class FileClassificationItem(BaseModel):
    category: str
    count: int
    size_gb: float
    percentage: float
    description: str


class DetailedColdnessStats(BaseModel):
    partitions: Dict[str, int]
    tables: Dict[str, int]
    total_size_gb: float


class EnhancedColdnessDistribution(BaseModel):
    cluster_id: int
    cluster_name: str
    distribution: Dict[str, DetailedColdnessStats]
    summary: Dict[str, Any]
    distribution_timestamp: str


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    """
    Get overall dashboard summary statistics
    """
    # Cluster statistics
    total_clusters = db.query(Cluster).count()
    active_clusters = db.query(Cluster).filter(Cluster.status == "active").count()

    # Table statistics（按最新扫描记录去重）
    table_query = db.query(TableMetric)

    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        table_query = table_query.filter(TableMetric.cluster_id == cluster_id)

    table_query = table_query.order_by(
        TableMetric.cluster_id,
        TableMetric.database_name,
        TableMetric.table_name,
        desc(TableMetric.scan_time),
    )

    unique_tables: Dict[tuple[int, str, str], TableMetric] = {}
    for table_metric in table_query:
        table_key = (
            table_metric.cluster_id,
            table_metric.database_name,
            table_metric.table_name,
        )
        if table_key not in unique_tables:
            unique_tables[table_key] = table_metric

    latest_metrics = list(unique_tables.values())

    total_tables = len(latest_metrics)
    monitored_tables = sum(
        1 for metric in latest_metrics if metric.scan_time is not None
    )

    # File statistics aggregation（基于去重后的最新指标）
    total_files = sum(metric.total_files or 0 for metric in latest_metrics)
    small_files = sum(metric.small_files or 0 for metric in latest_metrics)
    total_size_bytes = sum(metric.total_size or 0 for metric in latest_metrics)
    small_file_size_bytes = total_size_bytes

    # Calculate ratios and convert to GB
    small_file_ratio = (small_files / total_files * 100) if total_files > 0 else 0
    total_size_gb = total_size_bytes / (1024**3)
    small_file_size_gb = small_file_size_bytes / (1024**3)

    # 修复：查询completed状态的任务（而不是success）
    merge_query = db.query(MergeTask).filter(MergeTask.status == "completed")
    if cluster_id:
        merge_query = merge_query.filter(MergeTask.cluster_id == cluster_id)
    merge_tasks = merge_query.all()

    files_reduced = 0
    size_saved_bytes = 0
    for task in merge_tasks:
        if task.files_before is not None and task.files_after is not None:
            files_reduced += max(task.files_before - task.files_after, 0)
        if task.size_saved:
            size_saved_bytes += max(task.size_saved, 0)

    size_saved_gb = size_saved_bytes / (1024**3)

    return DashboardSummary(
        total_clusters=total_clusters,
        active_clusters=active_clusters,
        total_tables=total_tables,
        monitored_tables=monitored_tables,
        total_files=total_files,
        total_small_files=small_files,
        small_file_ratio=round(small_file_ratio, 2),
        total_size_gb=round(total_size_gb, 2),
        small_file_size_gb=round(small_file_size_gb, 2),
        files_reduced=files_reduced,
        size_saved_gb=round(size_saved_gb, 2),
    )


@router.get("/trends", response_model=List[TrendPoint])
async def get_small_file_trends(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db),
) -> List[TrendPoint]:
    """
    Get small file trends over time
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Base query
    query = db.query(
        func.date(TableMetric.scan_time).label("scan_date"),
        func.sum(TableMetric.small_files).label("total_small_files"),
        func.sum(TableMetric.total_files).label("total_files"),
    ).filter(TableMetric.scan_time >= start_date, TableMetric.scan_time.isnot(None))

    # Add cluster filter if specified
    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        query = query.filter(TableMetric.cluster_id == cluster_id)

    # Group by date and get results
    trends = (
        query.group_by(func.date(TableMetric.scan_time))
        .order_by(func.date(TableMetric.scan_time))
        .all()
    )

    result = []
    for trend in trends:
        total_files = trend.total_files or 0
        small_files = trend.total_small_files or 0
        ratio = (small_files / total_files * 100) if total_files > 0 else 0

        result.append(
            TrendPoint(
                date=str(trend.scan_date),
                small_files=small_files,
                total_files=total_files,
                ratio=round(ratio, 2),
            )
        )

    return result


@router.get("/file-distribution", response_model=List[FileDistributionItem])
async def get_file_distribution(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    db: Session = Depends(get_db),
) -> List[FileDistributionItem]:
    """
    Get file size distribution statistics
    """
    # Base query for partition metrics
    query = db.query(PartitionMetric)

    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")

        # Join with TableMetric to filter by cluster
        query = query.join(TableMetric).filter(TableMetric.cluster_id == cluster_id)

    partitions = query.all()

    # Define size ranges (in bytes)
    size_ranges = [
        ("< 1MB", 0, 1024 * 1024),
        ("1MB - 128MB", 1024 * 1024, 128 * 1024 * 1024),
        ("128MB - 1GB", 128 * 1024 * 1024, 1024 * 1024 * 1024),
        ("> 1GB", 1024 * 1024 * 1024, float("inf")),
    ]

    distribution = []
    total_files = 0
    total_size = 0

    # Calculate distribution
    for range_name, min_size, max_size in size_ranges:
        count = 0
        size_gb = 0

        for partition in partitions:
            avg_file_size = (
                (partition.total_size / partition.file_count)
                if partition.file_count > 0
                else 0
            )

            if min_size <= avg_file_size < max_size:
                count += partition.file_count
                size_gb += partition.total_size / (1024**3)

        total_files += count
        total_size += size_gb

        distribution.append(
            {"range_name": range_name, "count": count, "size_gb": round(size_gb, 2)}
        )

    # Calculate percentages
    result = []
    for item in distribution:
        percentage = (item["count"] / total_files * 100) if total_files > 0 else 0
        result.append(
            FileDistributionItem(
                size_range=item["range_name"],
                count=item["count"],
                size_gb=item["size_gb"],
                percentage=round(percentage, 1),
            )
        )

    return result


@router.get("/top-tables", response_model=List[TopTable])
async def get_top_tables(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of top tables to return"),
    db: Session = Depends(get_db),
) -> List[TopTable]:
    """
    Get top tables with most small files
    """
    query = (
        db.query(TableMetric, Cluster.name.label("cluster_name"))
        .join(Cluster, TableMetric.cluster_id == Cluster.id)
        .filter(TableMetric.small_files > 0, TableMetric.scan_time.isnot(None))
    )

    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        query = query.filter(TableMetric.cluster_id == cluster_id)

    top_tables = query.order_by(desc(TableMetric.small_files)).limit(limit).all()

    result = []
    for table_metric, cluster_name in top_tables:
        small_file_ratio = (
            (table_metric.small_files / table_metric.total_files * 100)
            if table_metric.total_files > 0
            else 0
        )
        total_size_gb = (
            table_metric.total_size / (1024**3) if table_metric.total_size else 0
        )

        result.append(
            TopTable(
                cluster_name=cluster_name,
                database_name=table_metric.database_name,
                table_name=table_metric.table_name,
                small_files=table_metric.small_files,
                total_files=table_metric.total_files,
                small_file_ratio=round(small_file_ratio, 2),
                total_size_gb=round(total_size_gb, 2),
                last_scan=table_metric.scan_time,
            )
        )

    return result


@router.get("/recent-tasks", response_model=List[RecentTask])
async def get_recent_tasks(
    limit: int = Query(
        20, ge=1, le=100, description="Number of recent tasks to return"
    ),
    status: Optional[str] = Query(None, description="Filter by task status"),
    db: Session = Depends(get_db),
) -> List[RecentTask]:
    """
    Get recent merge tasks
    """
    query = db.query(MergeTask, Cluster.name.label("cluster_name")).join(
        Cluster, MergeTask.cluster_id == Cluster.id
    )

    if status:
        query = query.filter(MergeTask.status == status)

    recent_tasks = query.order_by(desc(MergeTask.created_time)).limit(limit).all()

    result = []
    for task, cluster_name in recent_tasks:
        files_before = task.files_before
        files_after = task.files_after
        files_reduced = None
        if files_before is not None and files_after is not None:
            delta = files_before - files_after
            files_reduced = delta if delta > 0 else 0

        result.append(
            RecentTask(
                id=task.id,
                task_name=task.task_name,
                cluster_name=cluster_name,
                table_name=f"{task.database_name}.{task.table_name}",
                status=task.status,
                created_time=task.created_time,
                updated_time=task.completed_time,
                files_before=files_before,
                files_after=files_after,
                files_reduced=files_reduced,
                size_saved=(
                    task.size_saved if task.size_saved and task.size_saved > 0 else None
                ),
            )
        )

    return result


@router.get("/cluster-stats")
async def get_cluster_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get detailed statistics for each cluster
    """
    clusters = db.query(Cluster).filter(Cluster.status == "active").all()

    result = []
    for cluster in clusters:
        # Get cluster statistics
        stats = (
            db.query(
                func.count(TableMetric.id).label("table_count"),
                func.sum(TableMetric.total_files).label("total_files"),
                func.sum(TableMetric.small_files).label("small_files"),
                func.sum(TableMetric.total_size).label("total_size"),
            )
            .filter(TableMetric.cluster_id == cluster.id)
            .first()
        )

        # Get recent task count
        recent_tasks = (
            db.query(func.count(MergeTask.id))
            .filter(
                MergeTask.cluster_id == cluster.id,
                MergeTask.created_time >= datetime.now() - timedelta(days=7),
            )
            .scalar()
        )

        total_files = stats.total_files or 0
        small_files = stats.small_files or 0
        small_file_ratio = (small_files / total_files * 100) if total_files > 0 else 0

        result.append(
            {
                "id": cluster.id,
                "name": cluster.name,
                "description": cluster.description,
                "table_count": stats.table_count or 0,
                "total_files": total_files,
                "small_files": small_files,
                "small_file_ratio": round(small_file_ratio, 2),
                "total_size_gb": round((stats.total_size or 0) / (1024**3), 2),
                "recent_tasks": recent_tasks or 0,
                "status": cluster.status,
            }
        )

    return {
        "clusters": result,
        "summary": {
            "total_clusters": len(result),
            "active_clusters": len([c for c in result if c["status"] == "active"]),
        },
    }


@router.get("/table-file-counts", response_model=List[TableFileCountItem])
async def get_table_file_counts(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of tables to return"),
    db: Session = Depends(get_db),
) -> List[TableFileCountItem]:
    """
    Get current file counts for all tables with trend information
    """
    # Base query for latest metrics per table
    query = (
        db.query(TableMetric, Cluster.name.label("cluster_name"))
        .join(Cluster, TableMetric.cluster_id == Cluster.id)
        .filter(TableMetric.scan_time.isnot(None))
    )

    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        query = query.filter(TableMetric.cluster_id == cluster_id)

    # Get latest scan for each table
    latest_metrics = query.order_by(
        TableMetric.cluster_id,
        TableMetric.database_name,
        TableMetric.table_name,
        desc(TableMetric.scan_time),
    ).all()

    # Group by table to get latest metrics
    table_metrics = {}
    for metric, cluster_name in latest_metrics:
        table_key = f"{metric.cluster_id}:{metric.database_name}:{metric.table_name}"
        if table_key not in table_metrics:
            table_metrics[table_key] = (metric, cluster_name)

    result = []
    current_time = datetime.now()

    for table_key, (metric, cluster_name) in list(table_metrics.items())[:limit]:
        # Calculate trends by comparing with historical data
        trend_7d = 0.0
        trend_30d = 0.0

        # Get historical data for trends
        historical_7d = (
            db.query(TableMetric)
            .filter(
                TableMetric.cluster_id == metric.cluster_id,
                TableMetric.database_name == metric.database_name,
                TableMetric.table_name == metric.table_name,
                TableMetric.scan_time >= current_time - timedelta(days=7),
                TableMetric.scan_time < metric.scan_time,
            )
            .order_by(desc(TableMetric.scan_time))
            .first()
        )

        historical_30d = (
            db.query(TableMetric)
            .filter(
                TableMetric.cluster_id == metric.cluster_id,
                TableMetric.database_name == metric.database_name,
                TableMetric.table_name == metric.table_name,
                TableMetric.scan_time >= current_time - timedelta(days=30),
                TableMetric.scan_time < metric.scan_time,
            )
            .order_by(desc(TableMetric.scan_time))
            .first()
        )

        # Calculate percentage changes
        if historical_7d and historical_7d.total_files > 0:
            trend_7d = (
                (metric.total_files - historical_7d.total_files)
                / historical_7d.total_files
            ) * 100

        if historical_30d and historical_30d.total_files > 0:
            trend_30d = (
                (metric.total_files - historical_30d.total_files)
                / historical_30d.total_files
            ) * 100

        result.append(
            TableFileCountItem(
                table_id=table_key,
                cluster_name=cluster_name,
                database_name=metric.database_name,
                table_name=metric.table_name,
                current_files=metric.total_files,
                trend_7d=round(trend_7d, 1),
                trend_30d=round(trend_30d, 1),
                last_scan=metric.scan_time,
            )
        )

    # Sort by current file count (descending)
    result.sort(key=lambda x: x.current_files, reverse=True)
    return result


@router.get("/table-file-trends/{table_id}", response_model=List[TableFileCountPoint])
async def get_table_file_trends(
    table_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db),
) -> List[TableFileCountPoint]:
    """
    Get file count trends for a specific table
    table_id format: cluster_id:database_name:table_name
    """
    try:
        cluster_id_str, database_name, table_name = table_id.split(":", 2)
        cluster_id = int(cluster_id_str)
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=400,
            detail="Invalid table_id format. Expected: cluster_id:database:table",
        )

    # Verify cluster exists
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Get historical data for the specific table
    metrics = (
        db.query(TableMetric)
        .filter(
            TableMetric.cluster_id == cluster_id,
            TableMetric.database_name == database_name,
            TableMetric.table_name == table_name,
            TableMetric.scan_time >= start_date,
            TableMetric.scan_time.isnot(None),
        )
        .order_by(TableMetric.scan_time)
        .all()
    )

    result = []
    for metric in metrics:
        small_file_ratio = (
            (metric.small_files / metric.total_files * 100)
            if metric.total_files > 0
            else 0
        )

        result.append(
            TableFileCountPoint(
                date=metric.scan_time.strftime("%Y-%m-%d %H:%M"),
                table_name=metric.table_name,
                database_name=metric.database_name,
                cluster_name=cluster.name,
                total_files=metric.total_files,
                small_files=metric.small_files,
                ratio=round(small_file_ratio, 2),
            )
        )

    return result


@router.get("/file-classification", response_model=List[FileClassificationItem])
async def get_file_classification(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    db: Session = Depends(get_db),
) -> List[FileClassificationItem]:
    """
    Get file classification statistics based on compressibility
    """
    # Base query for tables
    query = db.query(TableMetric)
    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        query = query.filter(TableMetric.cluster_id == cluster_id)

    tables = query.filter(TableMetric.scan_time.isnot(None)).all()

    # Initialize statistics
    compressible_small_files = 0
    uncompressible_acid = 0
    uncompressible_datalake = 0
    uncompressible_single_partition = 0
    normal_large_files = 0

    compressible_size = 0.0
    acid_size = 0.0
    datalake_size = 0.0
    single_partition_size = 0.0
    large_files_size = 0.0

    for table in tables:
        # Simple classification based on storage format and properties
        input_format = (table.input_format or "").lower()
        serde_lib = (table.serde_lib or "").lower()

        # Check for unsupported table types based on available fields
        is_acid = "acid" in input_format
        is_datalake = any(
            x in input_format or x in serde_lib for x in ["hudi", "iceberg", "delta"]
        )

        if is_acid:
            uncompressible_acid += table.small_files or 0
            acid_size += (table.total_size or 0) / (1024**3)
        elif is_datalake:
            uncompressible_datalake += table.small_files or 0
            datalake_size += (table.total_size or 0) / (1024**3)
        else:
            # Check if files are small or large
            if table.small_files and table.small_files > 0:
                compressible_small_files += table.small_files
                # Calculate small file size portion
                small_file_ratio = (
                    table.small_files / table.total_files
                    if table.total_files > 0
                    else 0
                )
                compressible_size += (
                    (table.total_size or 0) * small_file_ratio / (1024**3)
                )

            # Large files
            large_files = (table.total_files or 0) - (table.small_files or 0)
            if large_files > 0:
                normal_large_files += large_files
                large_file_ratio = (
                    large_files / table.total_files if table.total_files > 0 else 0
                )
                large_files_size += (
                    (table.total_size or 0) * large_file_ratio / (1024**3)
                )

    # Calculate totals for percentages
    total_files = (
        compressible_small_files
        + uncompressible_acid
        + uncompressible_datalake
        + uncompressible_single_partition
        + normal_large_files
    )

    categories = [
        {
            "category": "可压缩小文件",
            "count": compressible_small_files,
            "size_gb": round(compressible_size, 2),
            "description": "可以进行合并优化的小文件",
        },
        {
            "category": "不可压缩-ACID表",
            "count": uncompressible_acid,
            "size_gb": round(acid_size, 2),
            "description": "事务表，不支持合并",
        },
        {
            "category": "不可压缩-数据湖表",
            "count": uncompressible_datalake,
            "size_gb": round(datalake_size, 2),
            "description": "Hudi/Iceberg/Delta表",
        },
        {
            "category": "不可压缩-其他",
            "count": uncompressible_single_partition,
            "size_gb": round(single_partition_size, 2),
            "description": "其他不支持压缩的情况",
        },
        {
            "category": "正常大文件",
            "count": normal_large_files,
            "size_gb": round(large_files_size, 2),
            "description": ">=128MB的文件",
        },
    ]

    result = []
    for cat in categories:
        percentage = (cat["count"] / total_files * 100) if total_files > 0 else 0
        result.append(
            FileClassificationItem(
                category=cat["category"],
                count=cat["count"],
                size_gb=cat["size_gb"],
                percentage=round(percentage, 1),
                description=cat["description"],
            )
        )

    return result


@router.get(
    "/enhanced-coldness-distribution", response_model=EnhancedColdnessDistribution
)
async def get_enhanced_coldness_distribution(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    db: Session = Depends(get_db),
) -> EnhancedColdnessDistribution:
    """
    Get enhanced coldness distribution with 7 time ranges and partition/table breakdown
    """
    # Verify cluster if specified
    cluster_name = "All Clusters"
    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        cluster_name = cluster.name
        cluster_id_filter = cluster_id
    else:
        cluster_id_filter = None

    # Define time ranges in days
    time_ranges = {
        "within_1_day": (0, 1),
        "day_1_to_7": (1, 7),
        "week_1_to_month": (7, 30),
        "month_1_to_3": (30, 90),
        "month_3_to_6": (90, 180),
        "month_6_to_12": (180, 365),
        "year_1_to_3": (365, 1095),
        "over_3_years": (1095, 999999),
    }

    distribution = {}
    total_partitions = 0
    total_tables = 0
    total_partitions_size = 0.0
    total_tables_size = 0.0

    # Process partition data - include ALL partitions
    partition_query = db.query(PartitionMetric)
    if cluster_id_filter:
        partition_query = partition_query.join(TableMetric).filter(
            TableMetric.cluster_id == cluster_id_filter
        )

    partitions = (
        partition_query.all()
    )  # Include all partitions, not just those with access time

    # Process table data - include ALL tables
    table_query = db.query(TableMetric)
    if cluster_id_filter:
        table_query = table_query.filter(TableMetric.cluster_id == cluster_id_filter)

    # Get all tables, prioritizing latest metrics for each table
    all_tables = table_query.order_by(
        TableMetric.cluster_id,
        TableMetric.database_name,
        TableMetric.table_name,
        desc(TableMetric.scan_time),
    ).all()

    # Get latest metric for each unique table
    table_metrics = {}
    for table in all_tables:
        table_key = f"{table.cluster_id}:{table.database_name}:{table.table_name}"
        if table_key not in table_metrics:
            table_metrics[table_key] = table

    tables = list(table_metrics.values())

    # Initialize distribution
    for range_name in time_ranges:
        distribution[range_name] = DetailedColdnessStats(
            partitions={"count": 0, "size_gb": 0},
            tables={"count": 0, "size_gb": 0},
            total_size_gb=0.0,
        )

    # Categorize partitions with intelligent time inference
    current_time = datetime.now()
    for partition in partitions:
        # Intelligent time calculation
        if partition.days_since_last_access is not None:
            # Use actual access time if available
            days = partition.days_since_last_access
        elif hasattr(partition, "scan_time") and partition.scan_time:
            # Fall back to scan time
            days = (current_time - partition.scan_time).days
        else:
            # Default to "unknown" - classify as recent for conservative estimation
            days = 7  # Assume accessed within a week if no data

        size_gb = (partition.total_size or 0) / (1024**3)

        for range_name, (min_days, max_days) in time_ranges.items():
            if min_days <= days < max_days:
                distribution[range_name].partitions["count"] += 1
                distribution[range_name].partitions["size_gb"] += size_gb
                break

        total_partitions += 1
        total_partitions_size += size_gb

    # Categorize tables with intelligent time inference
    for table in tables:
        # Intelligent time calculation for tables
        if table.days_since_last_access is not None:
            # Use actual access time if available
            days = table.days_since_last_access
        elif table.scan_time:
            # Fall back to scan time - how long since last scan
            days = (current_time - table.scan_time).days
        else:
            # Default to "unknown" - classify as recent for conservative estimation
            days = 30  # Assume accessed within a month if no data

        size_gb = (table.total_size or 0) / (1024**3)

        for range_name, (min_days, max_days) in time_ranges.items():
            if min_days <= days < max_days:
                distribution[range_name].tables["count"] += 1
                distribution[range_name].tables["size_gb"] += size_gb
                distribution[range_name].total_size_gb += size_gb
                break

        total_tables += 1
        total_tables_size += size_gb

    # Round all size values
    for range_stats in distribution.values():
        range_stats.partitions["size_gb"] = round(range_stats.partitions["size_gb"], 2)
        range_stats.tables["size_gb"] = round(range_stats.tables["size_gb"], 2)
        range_stats.total_size_gb = round(range_stats.total_size_gb, 2)

    return EnhancedColdnessDistribution(
        cluster_id=cluster_id_filter or 0,
        cluster_name=cluster_name,
        distribution=distribution,
        summary={
            "total_partitions": total_partitions,
            "total_tables": total_tables,
            "total_size_gb": round(total_tables_size, 2),
            "partition_total_size_gb": round(total_partitions_size, 2),
        },
        distribution_timestamp=datetime.now().isoformat(),
    )


@router.get("/coldest-data", response_model=List[ColdDataItem])
async def get_coldest_data(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    limit: int = Query(
        10, ge=1, le=50, description="Number of coldest data entries to return"
    ),
    db: Session = Depends(get_db),
) -> List[ColdDataItem]:
    """
    Get coldest data ranking (longest time since last access)
    """
    result = []

    # Get coldest partitions first
    partition_query = (
        db.query(
            PartitionMetric,
            TableMetric.cluster_id,
            TableMetric.database_name,
            TableMetric.table_name,
            Cluster.name.label("cluster_name"),
        )
        .join(TableMetric, PartitionMetric.table_metric_id == TableMetric.id)
        .join(Cluster, TableMetric.cluster_id == Cluster.id)
        .filter(
            PartitionMetric.days_since_last_access.isnot(None),
            PartitionMetric.days_since_last_access > 0,
        )
    )

    # Apply cluster filter if specified
    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        partition_query = partition_query.filter(TableMetric.cluster_id == cluster_id)

    # Get coldest partitions
    cold_partitions = (
        partition_query.order_by(desc(PartitionMetric.days_since_last_access))
        .limit(limit)
        .all()
    )

    for (
        partition,
        cluster_id_val,
        database_name,
        table_name,
        cluster_name,
    ) in cold_partitions:
        total_size_gb = (partition.total_size or 0) / (1024**3)

        result.append(
            ColdDataItem(
                cluster_name=cluster_name,
                database_name=database_name,
                table_name=table_name,
                partition_name=partition.partition_name,
                last_access_time=partition.last_access_time,
                days_since_last_access=partition.days_since_last_access,
                total_size_gb=round(total_size_gb, 2),
                file_count=partition.file_count or 0,
            )
        )

    # If we don't have enough partition data, supplement with table data
    if len(result) < limit:
        remaining_limit = limit - len(result)

        table_query = (
            db.query(TableMetric, Cluster.name.label("cluster_name"))
            .join(Cluster, TableMetric.cluster_id == Cluster.id)
            .filter(
                TableMetric.days_since_last_access.isnot(None),
                TableMetric.days_since_last_access > 0,
            )
        )

        if cluster_id:
            table_query = table_query.filter(TableMetric.cluster_id == cluster_id)

        cold_tables = (
            table_query.order_by(desc(TableMetric.days_since_last_access))
            .limit(remaining_limit)
            .all()
        )

        for table, cluster_name in cold_tables:
            total_size_gb = (table.total_size or 0) / (1024**3)

            result.append(
                ColdDataItem(
                    cluster_name=cluster_name,
                    database_name=table.database_name,
                    table_name=table.table_name,
                    partition_name=None,  # Table level, no partition
                    last_access_time=table.last_access_time,
                    days_since_last_access=table.days_since_last_access,
                    total_size_gb=round(total_size_gb, 2),
                    file_count=table.total_files or 0,
                )
            )

    return result


# Storage Format Distribution Models
class StorageFormatItem(BaseModel):
    format_name: str
    table_count: int
    total_size_gb: float
    small_files: int
    total_files: int
    percentage: float


class CompressionFormatItem(BaseModel):
    compression_name: str
    table_count: int
    total_size_gb: float
    small_files: int
    total_files: int
    percentage: float


class FormatCompressionItem(BaseModel):
    format_combination: str
    storage_format: str
    compression_format: str
    table_count: int
    total_size_gb: float
    small_files: int
    total_files: int
    percentage: float


@router.get("/storage-format-distribution", response_model=List[StorageFormatItem])
async def get_storage_format_distribution(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    db: Session = Depends(get_db),
) -> List[StorageFormatItem]:
    """
    Get storage format distribution statistics
    """
    query = db.query(TableMetric)

    # Apply cluster filter if specified
    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        query = query.filter(TableMetric.cluster_id == cluster_id)

    # Get all table metrics
    tables = query.all()

    if not tables:
        return []

    # Group by storage format
    format_stats = {}
    total_tables = len(tables)

    for table in tables:
        # Normalize storage format
        storage_format = (table.storage_format or "UNKNOWN").upper()

        # Get format name with compression info if available
        # For now, we'll use storage format only since compression field doesn't exist
        format_name = storage_format

        # If storage format is empty or None, try to infer from input/output formats
        if storage_format in ["", "UNKNOWN", None]:
            input_fmt = (table.input_format or "").lower()
            output_fmt = (table.output_format or "").lower()

            if "parquet" in input_fmt or "parquet" in output_fmt:
                format_name = "PARQUET"
            elif "orc" in input_fmt or "orc" in output_fmt:
                format_name = "ORC"
            elif "text" in input_fmt or "text" in output_fmt:
                format_name = "TEXT"
            elif "avro" in input_fmt or "avro" in output_fmt:
                format_name = "AVRO"
            else:
                format_name = "OTHER"

        if format_name not in format_stats:
            format_stats[format_name] = {
                "table_count": 0,
                "total_size": 0,
                "small_files": 0,
                "total_files": 0,
            }

        # Accumulate stats
        format_stats[format_name]["table_count"] += 1
        format_stats[format_name]["total_size"] += table.total_size or 0
        format_stats[format_name]["small_files"] += table.small_files or 0
        format_stats[format_name]["total_files"] += table.total_files or 0

    # Convert to response format
    result = []
    for format_name, stats in format_stats.items():
        total_size_gb = stats["total_size"] / (1024**3)
        percentage = (
            (stats["table_count"] / total_tables * 100) if total_tables > 0 else 0
        )

        result.append(
            StorageFormatItem(
                format_name=format_name,
                table_count=stats["table_count"],
                total_size_gb=round(total_size_gb, 2),
                small_files=stats["small_files"],
                total_files=stats["total_files"],
                percentage=round(percentage, 1),
            )
        )

    # Sort by table count descending
    result.sort(key=lambda x: x.table_count, reverse=True)

    return result


@router.get(
    "/format-compression-distribution", response_model=List[FormatCompressionItem]
)
async def get_format_compression_distribution(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    db: Session = Depends(get_db),
) -> List[FormatCompressionItem]:
    """
    Get storage format and compression format combination distribution statistics
    包含表级和分区级数据的完整统计
    """

    def get_format_info(table):
        """Extract storage and compression format information from table"""
        # Normalize storage format
        storage_format = (table.storage_format or "UNKNOWN").upper()

        # Infer storage format from input/output formats if not set
        input_fmt = (table.input_format or "").lower()
        output_fmt = (table.output_format or "").lower()
        serde_lib = (table.serde_lib or "").lower()

        if storage_format == "UNKNOWN" or not storage_format:
            if (
                "parquet" in input_fmt
                or "parquet" in output_fmt
                or "parquet" in serde_lib
            ):
                storage_format = "PARQUET"
            elif "orc" in input_fmt or "orc" in output_fmt or "orc" in serde_lib:
                storage_format = "ORC"
            elif "text" in input_fmt or "text" in output_fmt or "text" in serde_lib:
                storage_format = "TEXT"
            else:
                storage_format = "OTHER"

        # Infer compression format based on storage format
        compression_format = "NONE"  # 默认无压缩

        if storage_format == "PARQUET":
            compression_format = "SNAPPY"  # Parquet默认使用Snappy压缩
        elif storage_format == "ORC":
            compression_format = "ZLIB"  # ORC默认使用ZLIB压缩
        elif storage_format == "TEXT":
            compression_format = "NONE"  # Text格式通常无压缩
        elif "gzip" in input_fmt or "gzip" in output_fmt or "gz" in input_fmt:
            compression_format = "GZIP"
        elif "lz4" in input_fmt or "lz4" in output_fmt:
            compression_format = "LZ4"
        elif "bzip2" in input_fmt or "bzip2" in output_fmt:
            compression_format = "BZIP2"

        return storage_format, compression_format

    # 1. 查询表级数据
    table_query = db.query(TableMetric)
    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        table_query = table_query.filter(TableMetric.cluster_id == cluster_id)

    # 获取所有表并去重（取每个表最新的metric）
    all_tables = table_query.order_by(
        TableMetric.cluster_id,
        TableMetric.database_name,
        TableMetric.table_name,
        desc(TableMetric.scan_time),
    ).all()

    # 表去重
    table_metrics = {}
    for table in all_tables:
        table_key = f"{table.cluster_id}:{table.database_name}:{table.table_name}"
        if table_key not in table_metrics:
            table_metrics[table_key] = table

    # 2. 查询分区级数据
    partition_query = db.query(
        PartitionMetric,
        TableMetric.storage_format,
        TableMetric.input_format,
        TableMetric.output_format,
        TableMetric.serde_lib,
        TableMetric.cluster_id,
        TableMetric.database_name,
        TableMetric.table_name,
    ).join(TableMetric, PartitionMetric.table_metric_id == TableMetric.id)

    if cluster_id:
        partition_query = partition_query.filter(TableMetric.cluster_id == cluster_id)

    partitions = partition_query.all()

    # 3. 统计格式组合
    combination_stats = {}
    total_table_count = len(table_metrics)

    # 处理表级数据
    for table in table_metrics.values():
        storage_format, compression_format = get_format_info(table)

        # Create combination key
        if compression_format == "NONE":
            format_combination = f"{storage_format}(无压缩)"
        else:
            format_combination = f"{storage_format}({compression_format}压缩)"

        if format_combination not in combination_stats:
            combination_stats[format_combination] = {
                "storage_format": storage_format,
                "compression_format": compression_format,
                "table_count": 0,
                "table_total_size": 0,
                "table_small_files": 0,
                "table_total_files": 0,
                "partition_total_size": 0,
                "partition_small_files": 0,
                "partition_total_files": 0,
            }

        stats = combination_stats[format_combination]
        stats["table_count"] += 1
        stats["table_total_size"] += table.total_size or 0
        stats["table_small_files"] += table.small_files or 0
        stats["table_total_files"] += table.total_files or 0

    # 处理分区级数据（分区继承表的格式信息）
    for (
        partition,
        storage_format_raw,
        input_format,
        output_format,
        serde_lib,
        cluster_id_val,
        database_name,
        table_name,
    ) in partitions:

        # 创建临时表对象用于格式推断
        temp_table = type(
            "obj",
            (object,),
            {
                "storage_format": storage_format_raw,
                "input_format": input_format,
                "output_format": output_format,
                "serde_lib": serde_lib,
            },
        )()

        storage_format, compression_format = get_format_info(temp_table)

        # Create combination key
        if compression_format == "NONE":
            format_combination = f"{storage_format}(无压缩)"
        else:
            format_combination = f"{storage_format}({compression_format}压缩)"

        if format_combination not in combination_stats:
            combination_stats[format_combination] = {
                "storage_format": storage_format,
                "compression_format": compression_format,
                "table_count": 0,
                "table_total_size": 0,
                "table_small_files": 0,
                "table_total_files": 0,
                "partition_total_size": 0,
                "partition_small_files": 0,
                "partition_total_files": 0,
            }

        stats = combination_stats[format_combination]
        # 分区数据累加到对应格式组合中
        stats["partition_total_size"] += partition.total_size or 0
        stats["partition_small_files"] += partition.small_file_count or 0
        stats["partition_total_files"] += partition.file_count or 0

    # 4. Convert to response format
    result = []
    for format_combination, stats in combination_stats.items():
        table_total_size = stats["table_total_size"]
        partition_total_size = stats["partition_total_size"]
        total_size_bytes = (
            table_total_size if table_total_size > 0 else partition_total_size
        )

        table_small_files = stats["table_small_files"]
        partition_small_files = stats["partition_small_files"]
        small_files = (
            table_small_files if table_small_files > 0 else partition_small_files
        )

        table_total_files = stats["table_total_files"]
        partition_total_files = stats["partition_total_files"]
        total_files = (
            table_total_files if table_total_files > 0 else partition_total_files
        )

        total_size_gb = total_size_bytes / (1024**3)
        percentage = (
            (stats["table_count"] / total_table_count * 100)
            if total_table_count > 0
            else 0
        )

        result.append(
            FormatCompressionItem(
                format_combination=format_combination,
                storage_format=stats["storage_format"],
                compression_format=stats["compression_format"],
                table_count=stats["table_count"],
                total_size_gb=round(total_size_gb, 2),
                small_files=small_files,
                total_files=total_files,
                percentage=round(percentage, 1),
            )
        )

    # Sort by total size (descending)
    result.sort(key=lambda x: x.total_size_gb, reverse=True)

    return result


@router.get(
    "/compression-format-distribution", response_model=List[CompressionFormatItem]
)
async def get_compression_format_distribution(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    db: Session = Depends(get_db),
) -> List[CompressionFormatItem]:
    """
    Get compression format distribution statistics
    """
    query = db.query(TableMetric)

    # Apply cluster filter if specified
    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        query = query.filter(TableMetric.cluster_id == cluster_id)

    # Get all table metrics
    tables = query.all()

    if not tables:
        return []

    # Group by compression format
    compression_stats = {}
    total_tables = len(tables)

    for table in tables:
        # 基于存储格式推断压缩格式
        compression_name = "NONE"  # 默认无压缩

        input_fmt = (table.input_format or "").lower()
        output_fmt = (table.output_format or "").lower()
        serde_lib = (table.serde_lib or "").lower()

        # 基于文件格式推断压缩格式
        if "parquet" in input_fmt or "parquet" in output_fmt or "parquet" in serde_lib:
            compression_name = "SNAPPY"  # Parquet默认使用Snappy压缩
        elif "orc" in input_fmt or "orc" in output_fmt or "orc" in serde_lib:
            compression_name = "ZLIB"  # ORC默认使用ZLIB压缩
        elif "gzip" in input_fmt or "gzip" in output_fmt or "gz" in input_fmt:
            compression_name = "GZIP"
        elif "lz4" in input_fmt or "lz4" in output_fmt:
            compression_name = "LZ4"
        elif "bzip2" in input_fmt or "bzip2" in output_fmt:
            compression_name = "BZIP2"
        elif "text" in input_fmt or "text" in output_fmt:
            compression_name = "NONE"  # Text格式通常无压缩

        # 注意：current_compression字段目前在模型中不存在，先跳过

        if compression_name not in compression_stats:
            compression_stats[compression_name] = {
                "table_count": 0,
                "total_size": 0,
                "small_files": 0,
                "total_files": 0,
            }

        # Accumulate stats
        compression_stats[compression_name]["table_count"] += 1
        compression_stats[compression_name]["total_size"] += table.total_size or 0
        compression_stats[compression_name]["small_files"] += table.small_files or 0
        compression_stats[compression_name]["total_files"] += table.total_files or 0

    # Convert to response format
    result = []
    for compression_name, stats in compression_stats.items():
        total_size_gb = stats["total_size"] / (1024**3)
        percentage = (
            (stats["table_count"] / total_tables * 100) if total_tables > 0 else 0
        )

        result.append(
            CompressionFormatItem(
                compression_name=compression_name,
                table_count=stats["table_count"],
                total_size_gb=round(total_size_gb, 2),
                small_files=stats["small_files"],
                total_files=stats["total_files"],
                percentage=round(percentage, 1),
            )
        )

    # Sort by table count descending
    result.sort(key=lambda x: x.table_count, reverse=True)

    return result
