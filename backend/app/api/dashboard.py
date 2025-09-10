"""
Dashboard API endpoints for monitoring data aggregation
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.config.database import get_db
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.models.partition_metric import PartitionMetric
from app.models.merge_task import MergeTask
from pydantic import BaseModel

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
    small_files_merged: Optional[int]

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
    trend_30d: float
    last_scan: datetime

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    """
    Get overall dashboard summary statistics
    """
    # Cluster statistics
    total_clusters = db.query(Cluster).count()
    active_clusters = db.query(Cluster).filter(Cluster.status == "active").count()
    
    # Table statistics
    total_tables = db.query(TableMetric).count()
    monitored_tables = db.query(TableMetric).filter(
        TableMetric.scan_time.isnot(None)
    ).count()
    
    # File statistics aggregation
    file_stats = db.query(
        func.sum(TableMetric.total_files).label("total_files"),
        func.sum(TableMetric.small_files).label("small_files"),
        func.sum(TableMetric.total_size).label("total_size"),
        func.sum(TableMetric.total_size).label("small_file_size")
    ).first()
    
    total_files = file_stats.total_files or 0
    small_files = file_stats.small_files or 0
    total_size_bytes = file_stats.total_size or 0
    small_file_size_bytes = file_stats.small_file_size or 0
    
    # Calculate ratios and convert to GB
    small_file_ratio = (small_files / total_files * 100) if total_files > 0 else 0
    total_size_gb = total_size_bytes / (1024 ** 3)
    small_file_size_gb = small_file_size_bytes / (1024 ** 3)
    
    return DashboardSummary(
        total_clusters=total_clusters,
        active_clusters=active_clusters,
        total_tables=total_tables,
        monitored_tables=monitored_tables,
        total_files=total_files,
        total_small_files=small_files,
        small_file_ratio=round(small_file_ratio, 2),
        total_size_gb=round(total_size_gb, 2),
        small_file_size_gb=round(small_file_size_gb, 2)
    )

@router.get("/trends", response_model=List[TrendPoint])
async def get_small_file_trends(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
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
        func.sum(TableMetric.total_files).label("total_files")
    ).filter(
        TableMetric.scan_time >= start_date,
        TableMetric.scan_time.isnot(None)
    )
    
    # Add cluster filter if specified
    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        query = query.filter(TableMetric.cluster_id == cluster_id)
    
    # Group by date and get results
    trends = query.group_by(func.date(TableMetric.scan_time)).order_by(
        func.date(TableMetric.scan_time)
    ).all()
    
    result = []
    for trend in trends:
        total_files = trend.total_files or 0
        small_files = trend.total_small_files or 0
        ratio = (small_files / total_files * 100) if total_files > 0 else 0
        
        result.append(TrendPoint(
            date=str(trend.scan_date),
            small_files=small_files,
            total_files=total_files,
            ratio=round(ratio, 2)
        ))
    
    return result

@router.get("/file-distribution", response_model=List[FileDistributionItem])
async def get_file_distribution(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    db: Session = Depends(get_db)
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
        ("> 1GB", 1024 * 1024 * 1024, float('inf'))
    ]
    
    distribution = []
    total_files = 0
    total_size = 0
    
    # Calculate distribution
    for range_name, min_size, max_size in size_ranges:
        count = 0
        size_gb = 0
        
        for partition in partitions:
            avg_file_size = (partition.total_size / partition.file_count) if partition.file_count > 0 else 0
            
            if min_size <= avg_file_size < max_size:
                count += partition.file_count
                size_gb += partition.total_size / (1024 ** 3)
        
        total_files += count
        total_size += size_gb
        
        distribution.append({
            "range_name": range_name,
            "count": count,
            "size_gb": round(size_gb, 2)
        })
    
    # Calculate percentages
    result = []
    for item in distribution:
        percentage = (item["count"] / total_files * 100) if total_files > 0 else 0
        result.append(FileDistributionItem(
            size_range=item["range_name"],
            count=item["count"],
            size_gb=item["size_gb"],
            percentage=round(percentage, 1)
        ))
    
    return result

@router.get("/top-tables", response_model=List[TopTable])
async def get_top_tables(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of top tables to return"),
    db: Session = Depends(get_db)
) -> List[TopTable]:
    """
    Get top tables with most small files
    """
    query = db.query(TableMetric, Cluster.name.label("cluster_name")).join(
        Cluster, TableMetric.cluster_id == Cluster.id
    ).filter(
        TableMetric.small_files > 0,
        TableMetric.scan_time.isnot(None)
    )
    
    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        query = query.filter(TableMetric.cluster_id == cluster_id)
    
    top_tables = query.order_by(desc(TableMetric.small_files)).limit(limit).all()
    
    result = []
    for table_metric, cluster_name in top_tables:
        small_file_ratio = (table_metric.small_files / table_metric.total_files * 100) if table_metric.total_files > 0 else 0
        total_size_gb = table_metric.total_size / (1024 ** 3) if table_metric.total_size else 0
        
        result.append(TopTable(
            cluster_name=cluster_name,
            database_name=table_metric.database_name,
            table_name=table_metric.table_name,
            small_files=table_metric.small_files,
            total_files=table_metric.total_files,
            small_file_ratio=round(small_file_ratio, 2),
            total_size_gb=round(total_size_gb, 2),
            last_scan=table_metric.scan_time
        ))
    
    return result

@router.get("/recent-tasks", response_model=List[RecentTask])
async def get_recent_tasks(
    limit: int = Query(20, ge=1, le=100, description="Number of recent tasks to return"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    db: Session = Depends(get_db)
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
        result.append(RecentTask(
            id=task.id,
            task_name=task.task_name,
            cluster_name=cluster_name,
            table_name=f"{task.database_name}.{task.table_name}",
            status=task.status,
            created_time=task.created_time,
            updated_time=task.completed_time,
            small_files_merged=task.files_before
        ))
    
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
        stats = db.query(
            func.count(TableMetric.id).label("table_count"),
            func.sum(TableMetric.total_files).label("total_files"),
            func.sum(TableMetric.small_files).label("small_files"),
            func.sum(TableMetric.total_size).label("total_size")
        ).filter(TableMetric.cluster_id == cluster.id).first()
        
        # Get recent task count
        recent_tasks = db.query(func.count(MergeTask.id)).filter(
            MergeTask.cluster_id == cluster.id,
            MergeTask.created_time >= datetime.now() - timedelta(days=7)
        ).scalar()
        
        total_files = stats.total_files or 0
        small_files = stats.small_files or 0
        small_file_ratio = (small_files / total_files * 100) if total_files > 0 else 0
        
        result.append({
            "id": cluster.id,
            "name": cluster.name,
            "description": cluster.description,
            "table_count": stats.table_count or 0,
            "total_files": total_files,
            "small_files": small_files,
            "small_file_ratio": round(small_file_ratio, 2),
            "total_size_gb": round((stats.total_size or 0) / (1024 ** 3), 2),
            "recent_tasks": recent_tasks or 0,
            "status": cluster.status
        })
    
    return {
        "clusters": result,
        "summary": {
            "total_clusters": len(result),
            "active_clusters": len([c for c in result if c["status"] == "active"])
        }
    }

@router.get("/table-file-counts", response_model=List[TableFileCountItem])
async def get_table_file_counts(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of tables to return"),
    db: Session = Depends(get_db)
) -> List[TableFileCountItem]:
    """
    Get current file counts for all tables with trend information
    """
    # Base query for latest metrics per table
    query = db.query(
        TableMetric, 
        Cluster.name.label("cluster_name")
    ).join(
        Cluster, TableMetric.cluster_id == Cluster.id
    ).filter(
        TableMetric.scan_time.isnot(None)
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
        desc(TableMetric.scan_time)
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
        historical_7d = db.query(TableMetric).filter(
            TableMetric.cluster_id == metric.cluster_id,
            TableMetric.database_name == metric.database_name,
            TableMetric.table_name == metric.table_name,
            TableMetric.scan_time >= current_time - timedelta(days=7),
            TableMetric.scan_time < metric.scan_time
        ).order_by(desc(TableMetric.scan_time)).first()
        
        historical_30d = db.query(TableMetric).filter(
            TableMetric.cluster_id == metric.cluster_id,
            TableMetric.database_name == metric.database_name,
            TableMetric.table_name == metric.table_name,
            TableMetric.scan_time >= current_time - timedelta(days=30),
            TableMetric.scan_time < metric.scan_time
        ).order_by(desc(TableMetric.scan_time)).first()
        
        # Calculate percentage changes
        if historical_7d and historical_7d.total_files > 0:
            trend_7d = ((metric.total_files - historical_7d.total_files) / historical_7d.total_files) * 100
        
        if historical_30d and historical_30d.total_files > 0:
            trend_30d = ((metric.total_files - historical_30d.total_files) / historical_30d.total_files) * 100
        
        result.append(TableFileCountItem(
            table_id=table_key,
            cluster_name=cluster_name,
            database_name=metric.database_name,
            table_name=metric.table_name,
            current_files=metric.total_files,
            trend_7d=round(trend_7d, 1),
            trend_30d=round(trend_30d, 1),
            last_scan=metric.scan_time
        ))
    
    # Sort by current file count (descending)
    result.sort(key=lambda x: x.current_files, reverse=True)
    return result

@router.get("/table-file-trends/{table_id}", response_model=List[TableFileCountPoint])
async def get_table_file_trends(
    table_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
) -> List[TableFileCountPoint]:
    """
    Get file count trends for a specific table
    table_id format: cluster_id:database_name:table_name
    """
    try:
        cluster_id_str, database_name, table_name = table_id.split(":", 2)
        cluster_id = int(cluster_id_str)
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid table_id format. Expected: cluster_id:database:table")
    
    # Verify cluster exists
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get historical data for the specific table
    metrics = db.query(TableMetric).filter(
        TableMetric.cluster_id == cluster_id,
        TableMetric.database_name == database_name,
        TableMetric.table_name == table_name,
        TableMetric.scan_time >= start_date,
        TableMetric.scan_time.isnot(None)
    ).order_by(TableMetric.scan_time).all()
    
    result = []
    for metric in metrics:
        small_file_ratio = (metric.small_files / metric.total_files * 100) if metric.total_files > 0 else 0
        
        result.append(TableFileCountPoint(
            date=metric.scan_time.strftime("%Y-%m-%d %H:%M"),
            table_name=metric.table_name,
            database_name=metric.database_name,
            cluster_name=cluster.name,
            total_files=metric.total_files,
            small_files=metric.small_files,
            ratio=round(small_file_ratio, 2)
        ))
    
    return result