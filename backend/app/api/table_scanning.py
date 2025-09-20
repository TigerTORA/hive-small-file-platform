"""
表扫描API模块
负责表扫描、进度跟踪等功能
"""

import asyncio
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.cluster import Cluster
from app.models.partition_metric import PartitionMetric
from app.models.table_metric import TableMetric
from app.monitor.hybrid_table_scanner import HybridTableScanner
from app.schemas.scan_task import ScanTaskLog, ScanTaskProgress, ScanTaskResponse
from app.schemas.table_metric import ScanRequest
from app.services.scan_service import scan_task_manager
from app.utils.webhdfs_client import WebHDFSClient

router = APIRouter()


@router.post("/scan")
async def scan_tables(
    request: ScanRequest,
    strict_real: bool = Query(True, description="严格实连模式"),
    db: Session = Depends(get_db),
):
    """统一扫描接口：支持单表、单库或全库扫描"""
    cluster = db.query(Cluster).filter(Cluster.id == request.cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        scanner = HybridTableScanner(cluster)

        if request.table_name and request.database_name:
            # 单表扫描
            result = scanner.scan_single_table(
                db, request.database_name, request.table_name, strict_real=strict_real
            )
            return {
                "message": f"Table {request.database_name}.{request.table_name} scanned successfully",
                "scanned_tables": 1,
                "result": result,
            }
        elif request.database_name:
            # 单库扫描
            results = scanner.scan_database_tables(
                db, request.database_name, strict_real=strict_real
            )
            return {
                "message": f"Database {request.database_name} scanned successfully",
                "scanned_tables": len(results),
                "results": results,
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Either database_name or both database_name and table_name must be provided",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.post("/scan/{cluster_id}")
async def scan_all_cluster_databases_with_progress(
    cluster_id: int,
    strict_real: bool = Query(True, description="严格实连模式"),
    max_tables_per_db: Optional[int] = Query(None, description="每库最大扫描表数(为空表示不限制)"),
    db: Session = Depends(get_db),
):
    """集群级批量扫描（带进度追踪）

    简化为直接调用 ScanTaskManager.scan_cluster_with_progress，
    由其内部创建任务并在后台线程执行，避免双重后台调度。
    """
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        task_id = scan_task_manager.scan_cluster_with_progress(
            db,
            cluster_id,
            max_tables_per_db=max_tables_per_db,
            strict_real=strict_real,
        )

        return {
            "message": "Cluster scan started",
            "task_id": task_id,
            "cluster_id": cluster_id,
            "progress_url": f"/api/v1/tables/scan-progress/{task_id}",
            "status": "started",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start cluster scan: {str(e)}"
        )


@router.post("/scan/{cluster_id}/{database_name}")
async def scan_database_tables(
    cluster_id: int,
    database_name: str,
    strict_real: bool = Query(True, description="严格实连模式"),
    max_tables: int = Query(0, description="最大扫描表数，0表示不限制"),
    db: Session = Depends(get_db),
):
    """扫描指定数据库的所有表"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        scanner = HybridTableScanner(cluster)

        # 设置表数量限制
        max_tables_param = max_tables if max_tables > 0 else None

        results = scanner.scan_database_tables(
            db, database_name, max_tables=max_tables_param, strict_real=strict_real
        )

        return {
            "message": f"Database {database_name} scanned successfully",
            "database_name": database_name,
            "scanned_tables": len(results),
            "max_tables_limit": max_tables_param,
            "results": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database scan failed: {str(e)}")


@router.post("/scan-real/{cluster_id}/{database_name}")
async def scan_database_tables_real(
    cluster_id: int,
    database_name: str,
    max_tables: int = Query(0, description="最大扫描表数，0或负值表示不限制"),
    strict_real: bool = Query(True, description="严格实连模式"),
    db: Session = Depends(get_db),
):
    """对指定数据库执行严格实连扫描"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        scanner = HybridTableScanner(cluster)

        # 设置表数量限制
        max_tables_limit = max_tables if max_tables > 0 else None

        results = scanner.scan_database_tables(
            db, database_name, max_tables=max_tables_limit, strict_real=strict_real
        )

        return {
            "message": f"Real scan completed for database {database_name}",
            "database_name": database_name,
            "scanned_tables": len(results),
            "strict_real": strict_real,
            "max_tables_applied": max_tables_limit,
            "results": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Real scan failed: {str(e)}")


@router.get("/partition-metrics")
async def get_partition_metrics(
    cluster_id: int = Query(...),
    database_name: str = Query(...),
    table_name: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    concurrency: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """获取分区表的分区级小文件统计"""
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
        .first()
    )

    if not table_metric:
        raise HTTPException(
            status_code=404, detail=f"Table {database_name}.{table_name} not found"
        )

    if not table_metric.is_partitioned:
        raise HTTPException(
            status_code=400,
            detail=f"Table {database_name}.{table_name} is not a partitioned table",
        )

    try:
        # 使用WebHDFS扫描分区
        webhdfs_client = WebHDFSClient(
            namenode_url=cluster.hdfs_namenode_url, user=cluster.hdfs_user or "hdfs"
        )

        # 获取分区列表和统计信息
        # 这里简化实现，实际应该调用专门的分区扫描服务
        partition_metrics = []

        # 模拟分区数据（实际应该从HDFS获取）
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        # 这里应该实现真实的分区扫描逻辑
        total_partitions = table_metric.partition_count or 0

        return {
            "table_info": {
                "database_name": database_name,
                "table_name": table_name,
                "total_partitions": total_partitions,
            },
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": (
                    (total_partitions + page_size - 1) // page_size
                    if total_partitions > 0
                    else 0
                ),
            },
            "scan_config": {"concurrency": concurrency},
            "partition_metrics": partition_metrics,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Partition scan failed: {str(e)}")


@router.post("/scan-table/{cluster_id}/{database_name}/{table_name}")
async def scan_single_table(
    cluster_id: int,
    database_name: str,
    table_name: str,
    strict_real: bool = Query(True, description="严格实连模式"),
    db: Session = Depends(get_db),
):
    """扫描单个表"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        scanner = HybridTableScanner(cluster)
        result = scanner.scan_single_table(
            db, database_name, table_name, strict_real=strict_real
        )

        return {
            "message": f"Table {database_name}.{table_name} scanned successfully",
            "table_name": f"{database_name}.{table_name}",
            "strict_real": strict_real,
            "result": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Table scan failed: {str(e)}")


@router.get("/scan-progress/{task_id}", response_model=ScanTaskProgress)
async def get_scan_task_progress(task_id: str):
    """获取扫描任务进度（实时）"""
    try:
        progress = scan_task_manager.get_task_progress(task_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Task not found")
        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.get("/scan-progress/cluster/{cluster_id}")
async def get_scan_progress(cluster_id: int):
    """获取集群扫描进度概览"""
    try:
        progress_data = scan_task_manager.get_cluster_scan_overview(cluster_id)
        return progress_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get cluster progress: {str(e)}"
        )


@router.get("/scan-logs/{task_id}")
async def get_scan_task_logs(
    task_id: str,
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None, description="日志级别过滤"),
):
    """获取扫描任务的详细日志"""
    try:
        logs = scan_task_manager.get_task_logs(task_id, limit=limit, level=level)
        return {"task_id": task_id, "log_count": len(logs), "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")
