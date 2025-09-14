from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List, Optional
import asyncio
import time
from app.config.database import get_db
from app.models.table_metric import TableMetric
from app.models.cluster import Cluster
from app.schemas.table_metric import TableMetricResponse, ScanRequest
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.monitor.hybrid_table_scanner import HybridTableScanner
from app.services.scan_service import scan_task_manager
from app.schemas.scan_task import ScanTaskResponse, ScanTaskProgress
from app.utils.webhdfs_client import WebHDFSClient

router = APIRouter()

@router.get("/metrics", response_model=list[TableMetricResponse])
async def get_table_metrics(
    cluster_id: int = Query(...),
    database_name: str = Query(None),
    db: Session = Depends(get_db)
):
    """Get latest table metrics per table (deduplicated by database_name + table_name)."""
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
    db: Session = Depends(get_db)
):
    """Get small file summary for a cluster"""
    from sqlalchemy import func
    
    result = db.query(
        func.count(TableMetric.id).label("total_tables"),
        func.sum(TableMetric.total_files).label("total_files"),
        func.sum(TableMetric.small_files).label("total_small_files"),
        func.avg(TableMetric.avg_file_size).label("avg_file_size")
    ).filter(TableMetric.cluster_id == cluster_id).first()
    
    return {
        "total_tables": result.total_tables or 0,
        "total_files": result.total_files or 0,
        "total_small_files": result.total_small_files or 0,
        "avg_file_size": float(result.avg_file_size or 0),
        "small_file_ratio": (result.total_small_files / result.total_files * 100) if result.total_files else 0
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
        raise HTTPException(status_code=500, detail=f"Failed to get databases: {str(e)}")

@router.get("/tables/{cluster_id}/{database_name}")
async def get_tables(cluster_id: int, database_name: str, db: Session = Depends(get_db)):
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

@router.post("/scan")
async def scan_tables(
    scan_request: ScanRequest,
    strict_real: bool = Query(True, description="严格实连模式（失败不降级Mock）"),
    db: Session = Depends(get_db)
):
    """Unified scan endpoint for tables - can scan single table or database"""
    cluster = db.query(Cluster).filter(Cluster.id == scan_request.cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        scanner = HybridTableScanner(cluster)
        
        if scan_request.table_name and scan_request.database_name:
            # Scan single table
            with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as connector:
                tables = connector.get_tables(scan_request.database_name)
                table_info = next((t for t in tables if t['table_name'] == scan_request.table_name), None)
                if not table_info:
                    raise HTTPException(status_code=404, detail="Table not found")
            
            table_result = scanner.scan_table(db, scan_request.database_name, table_info, strict_real=strict_real)
            return {
                "cluster_id": scan_request.cluster_id,
                "database_name": scan_request.database_name,
                "table_name": scan_request.table_name,
                "scan_result": table_result,
                "status": "completed"
            }
        
        elif scan_request.database_name:
            # Scan database
            # 不限制每库表数，严格模式可选
            result = scanner.scan_database_tables(db, scan_request.database_name, max_tables=None, strict_real=strict_real)
            return {
                "cluster_id": scan_request.cluster_id,
                "database_name": scan_request.database_name,
                "scan_result": result,
                "status": "completed"
            }
        else:
            raise HTTPException(status_code=400, detail="Either database_name or both database_name and table_name must be provided")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@router.post("/scan/{cluster_id}")
async def scan_all_cluster_databases_with_progress(
    cluster_id: int,
    max_tables_per_db: Optional[int] = Query(None, description="每库最大扫描表数（空表示不限制）"),
    strict_real: bool = Query(True, description="严格实连模式（失败不降级Mock）"),
    db: Session = Depends(get_db)
):
    """启动带进度追踪的集群扫描任务"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        # 启动进度追踪的扫描任务
        task_id = scan_task_manager.scan_cluster_with_progress(db, cluster_id, max_tables_per_db, strict_real)
        
        return {
            "cluster_id": cluster_id,
            "task_id": task_id,
            "status": "started",
            "message": "扫描任务已启动，请使用task_id查询进度"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {str(e)}")

@router.post("/scan/{cluster_id}/{database_name}")
async def scan_database_tables(
    cluster_id: int, 
    database_name: str,
    table_filter: str = Query(None),
    db: Session = Depends(get_db)
):
    """Scan all tables in a database for small files (Mock mode)"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        scanner = HybridTableScanner(cluster)
        # 显式 Mock 路径，仍旧保持原有限制以利快速返回
        result = scanner.scan_database_tables(db, database_name, table_filter, max_tables=10, strict_real=False)
        return {
            "cluster_id": cluster_id,
            "database_name": database_name,
            "scan_result": result,
            "status": "completed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@router.post("/scan-real/{cluster_id}/{database_name}")
async def scan_database_tables_real(
    cluster_id: int, 
    database_name: str,
    table_filter: str = Query(None),
    max_tables: int = Query(0, description="0或负值表示不限制"),
    strict_real: bool = Query(True, description="严格实连模式（默认开启）"),
    db: Session = Depends(get_db)
):
    """Scan tables using real MetaStore and intelligent HDFS connection"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        scanner = HybridTableScanner(cluster)
        limit = None if max_tables <= 0 else max_tables
        result = scanner.scan_database_tables(db, database_name, table_filter, limit, strict_real=strict_real)
        return {
            "cluster_id": cluster_id,
            "database_name": database_name,
            "scan_result": result,
            "status": "completed"
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
    concurrency: int = Query(5, ge=1, le=20, description="并发扫描分区数"),
    db: Session = Depends(get_db),
):
    """Return per-partition small file stats for a partitioned table.

    Uses MetaStore to fetch partition locations and WebHDFS client to compute stats.
    """
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        # Fetch partition list from MetaStore (paged)
        with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as connector:
            total = connector.get_table_partitions_count(database_name, table_name)
            if total == 0:
                return {"items": [], "total": 0, "page": page, "page_size": page_size}
            offset = (page - 1) * page_size
            partitions = connector.get_table_partitions_paged(database_name, table_name, offset, page_size)

        # 并发扫描每个分区路径（为避免 requests.Session 线程安全问题，线程内各自创建 client）
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def scan_one(idx: int, part_name: str, part_path: str):
            try:
                local_client = WebHDFSClient(cluster.hdfs_namenode_url, user=cluster.hdfs_user or 'hdfs')
                try:
                    stats = local_client.scan_directory_stats(
                        part_path,
                        small_file_threshold=cluster.small_file_threshold or 134217728,
                    )
                    item = {
                        "partition_spec": part_name,
                        "partition_path": part_path,
                        "file_count": int(getattr(stats, 'total_files', 0) or 0),
                        "small_file_count": int(getattr(stats, 'small_files_count', 0) or 0),
                        "total_size": int(getattr(stats, 'total_size', 0) or 0),
                        "avg_file_size": float(getattr(stats, 'average_file_size', 0) or 0.0),
                    }
                finally:
                    try:
                        local_client.close()
                    except Exception:
                        pass
                return idx, item
            except Exception as e:
                # 出错时返回占位数据，避免整页失败
                return idx, {
                    "partition_spec": part_name,
                    "partition_path": part_path,
                    "file_count": 0,
                    "small_file_count": 0,
                    "total_size": 0,
                    "avg_file_size": 0.0,
                    "error": str(e),
                }

        futures = []
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            for idx, p in enumerate(partitions):
                part_name = p.get('partition_name') or p.get('PART_NAME')
                part_path = p.get('partition_path') or p.get('partition_path')
                if not part_path:
                    continue
                futures.append(executor.submit(scan_one, idx, part_name, part_path))

            results: list[tuple[int, dict]] = []
            for fut in as_completed(futures):
                results.append(fut.result())

        # 按原顺序还原
        results.sort(key=lambda x: x[0])
        items = [item for _, item in results]

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get partition metrics: {str(e)}")

@router.post("/scan-table/{cluster_id}/{database_name}/{table_name}")
async def scan_single_table(
    cluster_id: int, 
    database_name: str, 
    table_name: str,
    db: Session = Depends(get_db)
):
    """Scan a single table for small files"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        # 获取表信息
        with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as connector:
            tables = connector.get_tables(database_name)
            table_info = next((t for t in tables if t['table_name'] == table_name), None)
            if not table_info:
                raise HTTPException(status_code=404, detail="Table not found")
        
        # 扫描表
        scanner = HybridTableScanner(cluster)
        if not scanner.hive_connector.connect():
            raise Exception("Failed to connect to MetaStore")
        
        # 初始化HDFS扫描器（智能混合模式）
        scanner._initialize_hdfs_scanner()
        if not scanner.hdfs_scanner.connect():
            raise Exception("Failed to connect to HDFS")
        
        try:
            table_result = scanner.scan_table(db, database_name, table_info)
            return {
                "cluster_id": cluster_id,
                "database_name": database_name,
                "table_name": table_name,
                "scan_result": table_result,
                "status": "completed"
            }
        finally:
            scanner.hive_connector.disconnect()
            scanner.hdfs_scanner.disconnect()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Table scan failed: {str(e)}")

@router.post("/scan-mock/{cluster_id}/{database_name}/{table_name}")
async def scan_single_table_mock(
    cluster_id: int, 
    database_name: str, 
    table_name: str,
    db: Session = Depends(get_db)
):
    """Scan a single table for small files using mock data (for testing)"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        import random
        from datetime import datetime
        
        # 生成模拟的扫描结果
        total_files = random.randint(10, 500)
        small_files = random.randint(5, total_files // 2)
        
        mock_result = {
            "cluster_id": cluster_id,
            "database_name": database_name,
            "table_name": table_name,
            "scan_result": {
                "table_name": table_name,
                "total_files": total_files,
                "small_files": small_files,
                "small_file_ratio": round(small_files / total_files * 100, 2) if total_files > 0 else 0,
                "avg_file_size": random.randint(10000000, 200000000),  # 10MB to 200MB
                "total_size": random.randint(100000000, 10000000000),  # 100MB to 10GB
                "is_partitioned": random.choice([True, False]),
                "partition_count": random.randint(0, 50) if random.choice([True, False]) else 0,
                "scan_mode": "mock",
                "scan_time": datetime.now().isoformat(),
                "scan_duration": round(random.uniform(0.5, 3.0), 2)
            },
            "status": "completed"
        }
        
        return mock_result
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mock table scan failed: {str(e)}")

@router.get("/test-connection/{cluster_id}")
async def test_cluster_connections(cluster_id: int, db: Session = Depends(get_db)):
    """Test cluster connections (Mock mode)"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        scanner = HybridTableScanner(cluster)
        results = scanner.test_connections()
        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "connections": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

@router.get("/test-connection-real/{cluster_id}")
async def test_cluster_connections_real(cluster_id: int, db: Session = Depends(get_db)):
    """Test real cluster connections with intelligent fallback"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        scanner = HybridTableScanner(cluster)
        results = scanner.test_connections()
        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "connections": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Real connection test failed: {str(e)}")

@router.get("/small-file-analysis/{cluster_id}")
async def analyze_small_file_ratios(cluster_id: int, db: Session = Depends(get_db)):
    """Analyze small file ratios for each table - DRAFT VERSION"""
    # Get all tables for the cluster
    all_tables = db.query(TableMetric).filter(TableMetric.cluster_id == cluster_id).all()
    
    if not all_tables:
        return {"message": "No table data found", "tables": []}
    
    # Calculate ratios for each table - lots of repetitive code here
    table_analysis = []
    for table in all_tables:
        # Basic calculations
        if table.total_files and table.total_files > 0:
            small_file_ratio = (table.small_files / table.total_files) * 100
        else:
            small_file_ratio = 0
        
        # Determine priority level - hardcoded thresholds
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
            
        # Calculate estimated space savings - rough calculation
        if table.small_files > 0 and table.avg_file_size > 0:
            small_files_total_size = table.small_files * table.avg_file_size
            estimated_savings_gb = small_files_total_size / (1024 * 1024 * 1024) * 0.3  # assume 30% savings
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
            "avg_file_size_mb": round(table.avg_file_size / (1024 * 1024), 2) if table.avg_file_size else 0,
            "total_size_gb": round(table.total_size / (1024 * 1024 * 1024), 2) if table.total_size else 0,
            "estimated_savings_gb": round(estimated_savings_gb, 2),
            "is_partitioned": table.is_partitioned,
            "partition_count": table.partition_count,
            "last_scan": table.scan_time.isoformat() if table.scan_time else None
        }
        
        table_analysis.append(table_info)
    
    # Sort by priority and small file ratio - multiple sorting criteria
    table_analysis.sort(key=lambda x: (-x["priority_score"], -x["small_file_ratio"], -x["small_files"]))
    
    # Calculate overall statistics - repetitive calculations
    total_tables = len(table_analysis)
    critical_tables = len([t for t in table_analysis if t["priority"] == "CRITICAL"])
    high_priority_tables = len([t for t in table_analysis if t["priority"] == "HIGH"])
    total_small_files = sum([t["small_files"] for t in table_analysis])
    total_files = sum([t["total_files"] for t in table_analysis])
    overall_small_file_ratio = (total_small_files / total_files * 100) if total_files > 0 else 0
    total_estimated_savings = sum([t["estimated_savings_gb"] for t in table_analysis])
    
    # Recommendations - hardcoded logic
    recommendations = []
    if critical_tables > 0:
        recommendations.append(f"Immediately merge {critical_tables} critical tables with >80% small files")
    if high_priority_tables > 0:
        recommendations.append(f"Schedule merging for {high_priority_tables} high priority tables")
    if overall_small_file_ratio > 50:
        recommendations.append("Consider cluster-wide small file optimization strategy")
    
    return {
        "cluster_id": cluster_id,
        "summary": {
            "total_tables": total_tables,
            "critical_tables": critical_tables,
            "high_priority_tables": high_priority_tables,
            "overall_small_file_ratio": round(overall_small_file_ratio, 2),
            "total_estimated_savings_gb": round(total_estimated_savings, 2)
        },
        "recommendations": recommendations,
        "tables": table_analysis[:50]  # Limit to top 50 for performance
    }

@router.get("/{cluster_id}/{database_name}/{table_name}/partitions")
async def get_table_partitions(
    cluster_id: int, 
    database_name: str, 
    table_name: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取表的分区列表"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        from app.engines.safe_hive_engine import SafeHiveMergeEngine
        engine = SafeHiveMergeEngine(cluster)
        
        # 检查表是否存在
        if not engine._table_exists(database_name, table_name):
            raise HTTPException(status_code=404, detail="Table not found")
        
        # 检查是否为分区表
        is_partitioned = engine._is_partitioned_table(database_name, table_name)
        
        if not is_partitioned:
            return {
                "table_name": table_name,
                "is_partitioned": False,
                "partitions": [],
                "message": "This table is not partitioned"
            }
        
        # 获取分区列表
        partitions = engine._get_table_partitions(database_name, table_name)
        
        # 解析分区信息，提取分区键和值
        partition_info = []
        for partition in partitions:
            # partition格式通常是: dt=2023-12-01/hour=00
            partition_parts = {}
            for part in partition.split('/'):
                if '=' in part:
                    key, value = part.split('=', 1)
                    partition_parts[key] = value
            
            partition_info.append({
                'partition_spec': partition,
                'partition_keys': partition_parts
            })
        
        return {
            "table_name": table_name,
            "is_partitioned": True,
            "partition_count": len(partitions),
            "partitions": partition_info[:100],  # 最多返回100个分区
            "total_partitions": len(partitions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get partitions: {str(e)}")

@router.get("/{cluster_id}/{database_name}/{table_name}/partition-stats")
async def get_partition_file_stats(
    cluster_id: int,
    database_name: str, 
    table_name: str,
    partition_spec: str = Query(None, description="分区规格，如 dt='2023-12-01'"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取分区的文件统计信息"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        from app.engines.safe_hive_engine import SafeHiveMergeEngine
        engine = SafeHiveMergeEngine(cluster)
        
        # 检查表是否存在
        if not engine._table_exists(database_name, table_name):
            raise HTTPException(status_code=404, detail="Table not found")
        
        # 获取文件统计
        if partition_spec:
            file_count = engine._get_file_count(database_name, table_name, partition_spec)
            target_partition = partition_spec
        else:
            file_count = engine._get_file_count(database_name, table_name)
            target_partition = "整个表"
        
        # 估算小文件数量（简化算法）
        small_file_count = int(file_count * 0.7)  # 假设70%是小文件
        
        # 估算存储统计
        avg_file_size = 32 * 1024 * 1024  # 假设平均32MB
        total_size = file_count * avg_file_size
        
        return {
            "table_name": table_name,
            "partition_spec": target_partition,
            "file_stats": {
                "total_files": file_count,
                "estimated_small_files": small_file_count,
                "small_file_ratio": 70.0 if file_count > 0 else 0,
                "estimated_total_size": total_size,
                "avg_file_size": avg_file_size
            },
            "merge_recommendation": {
                "should_merge": file_count > 50,
                "priority": "HIGH" if small_file_count > 100 else "MEDIUM" if small_file_count > 50 else "LOW",
                "estimated_improvement": f"可减少约 {int(small_file_count * 0.8)} 个文件" if file_count > 0 else "无需合并"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get partition stats: {str(e)}")

@router.post("/{cluster_id}/{database_name}/{table_name}/merge-preview")
async def get_merge_preview(
    cluster_id: int,
    database_name: str,
    table_name: str,
    partition_filter: str = Query(None, description="分区过滤器，如 dt='2023-12-01'"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取合并预览信息"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        from app.engines.safe_hive_engine import SafeHiveMergeEngine
        from app.models.merge_task import MergeTask
        
        # 创建临时任务对象用于预览
        temp_task = MergeTask(
            cluster_id=cluster_id,
            database_name=database_name,
            table_name=table_name,
            partition_filter=partition_filter,
            merge_strategy='safe_merge',
            task_name=f"Preview for {database_name}.{table_name}"
        )
        
        engine = SafeHiveMergeEngine(cluster)
        
        # 获取预览信息
        preview = engine.get_merge_preview(temp_task)
        
        return {
            "table_name": table_name,
            "partition_filter": partition_filter,
            "preview": preview,
            "recommendations": {
                "engine_type": "safe_hive",
                "strategy": "safe_merge",
                "description": "使用临时表+原子重命名策略，确保零停机时间",
                "estimated_downtime_seconds": 10,  # 只有重命名时的短暂停机
                "rollback_available": True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")

@router.get("/{cluster_id}/{database_name}/{table_name}/info")
async def get_table_info(
    cluster_id: int,
    database_name: str,
    table_name: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取表的详细信息，包括分区状态"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        from app.engines.safe_hive_engine import SafeHiveMergeEngine
        engine = SafeHiveMergeEngine(cluster)
        
        # 检查表是否存在
        if not engine._table_exists(database_name, table_name):
            raise HTTPException(status_code=404, detail="Table not found")
        
        # 检查是否为分区表
        is_partitioned = engine._is_partitioned_table(database_name, table_name)

        # 合并支持性检查（Hudi/Iceberg/Delta/ACID 等不支持）
        fmt = engine._get_table_format_info(database_name, table_name)
        unsupported = engine._is_unsupported_table_type(fmt)
        reason = engine._unsupported_reason(fmt) if unsupported else None

        # 获取基本信息
        table_info = {
            "database_name": database_name,
            "table_name": table_name,
            "is_partitioned": is_partitioned,
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "merge_supported": not unsupported,
            "unsupported_reason": reason,
            "storage_format": fmt.get('input_format') or fmt.get('serde_lib') or None
        }
        
        if is_partitioned:
            partitions = engine._get_table_partitions(database_name, table_name)
            table_info.update({
                "partition_count": len(partitions),
                "sample_partitions": partitions[:5],  # 显示前5个分区作为样例
                "merge_strategy_recommendation": "按分区合并，建议选择特定分区进行合并"
            })
        else:
            table_info.update({
                "partition_count": 0,
                "merge_strategy_recommendation": "整表合并，建议在业务低峰期执行"
            })
        
        return table_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get table info: {str(e)}")

@router.get("/{cluster_id}/{database_name}/{table_name}/partitions")
async def get_table_partitions_list(
    cluster_id: int,
    database_name: str,
    table_name: str,
    db: Session = Depends(get_db)
):
    """返回表的分区列表（简单字符串列表：key=val[/key2=val2]）。

    说明：该接口仅用于前端分区选择，不做复杂分页；如分区很多，建议后续改造为分页/模糊查询。
    """
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        from app.engines.safe_hive_engine import SafeHiveMergeEngine
        engine = SafeHiveMergeEngine(cluster)

        if not engine._table_exists(database_name, table_name):
            raise HTTPException(status_code=404, detail="Table not found")

        parts = engine._get_table_partitions(database_name, table_name) or []
        return {"partitions": parts}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get partitions: {str(e)}")

@router.post("/scan-all-databases/{cluster_id}")
async def scan_all_databases(
    cluster_id: int,
    max_tables_per_db: int = Query(20, description="Maximum number of tables to scan per database"),
    db: Session = Depends(get_db)
):
    """批量扫描集群中的所有数据库，支持进度监控"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        # 获取所有数据库列表
        with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as connector:
            databases = connector.get_databases()
        
        start_time = time.time()
        total_databases = len(databases)
        completed_databases = 0
        total_tables_scanned = 0
        total_files_found = 0
        total_small_files = 0
        database_results = []
        errors = []
        
        scanner = HybridTableScanner(cluster)
        
        for i, database_name in enumerate(databases, 1):
            database_start_time = time.time()
            
            try:
                print(f"[{i}/{total_databases}] 开始扫描数据库: {database_name}")
                
                # 扫描数据库
                result = scanner.scan_database_tables(
                    db, 
                    database_name, 
                    table_filter=None, 
                    max_tables=max_tables_per_db
                )
                
                # 累计统计
                completed_databases += 1
                total_tables_scanned += result['tables_scanned']
                total_files_found += result['total_files']
                total_small_files += result['total_small_files']
                
                # 记录数据库结果
                database_result = {
                    "database_name": database_name,
                    "tables_scanned": result['tables_scanned'],
                    "total_files": result['total_files'],
                    "total_small_files": result['total_small_files'],
                    "scan_duration": time.time() - database_start_time,
                    "hdfs_mode": result.get('hdfs_mode', 'unknown'),
                    "errors": result.get('errors', [])
                }
                database_results.append(database_result)
                
                print(f"✅ 数据库 {database_name} 扫描完成: {result['tables_scanned']}表, "
                      f"{result['total_files']}文件, {result['total_small_files']}小文件")
                      
            except Exception as e:
                error_msg = f"Database {database_name} scan failed: {str(e)}"
                errors.append(error_msg)
                print(f"❌ 数据库 {database_name} 扫描失败: {str(e)}")
                
                # 即使失败也记录结果
                database_results.append({
                    "database_name": database_name,
                    "tables_scanned": 0,
                    "total_files": 0,
                    "total_small_files": 0,
                    "scan_duration": time.time() - database_start_time,
                    "hdfs_mode": "error",
                    "errors": [error_msg]
                })
        
        # 计算总体统计
        total_duration = time.time() - start_time
        success_rate = completed_databases / total_databases * 100
        
        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "summary": {
                "total_databases": total_databases,
                "completed_databases": completed_databases,
                "total_tables_scanned": total_tables_scanned,
                "total_files_found": total_files_found,
                "total_small_files": total_small_files,
                "small_file_ratio": round(total_small_files / max(total_files_found, 1) * 100, 2),
                "success_rate": round(success_rate, 2),
                "total_scan_duration": round(total_duration, 2),
                "avg_duration_per_database": round(total_duration / total_databases, 2)
            },
            "database_results": database_results,
            "errors": errors,
            "status": "completed",
            "scan_timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch scan failed: {str(e)}")

@router.get("/scan-progress/{task_id}", response_model=ScanTaskProgress)
async def get_scan_task_progress(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取扫描任务的实时进度"""
    task = scan_task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    logs = scan_task_manager.get_task_logs(task_id)
    
    return ScanTaskProgress(
        task_id=task_id,
        status=task.status,
        progress_percentage=task.progress_percentage,
        current_item=task.current_item,
        completed_items=task.completed_items,
        total_items=task.total_items,
        estimated_remaining_seconds=task.estimated_remaining_seconds,
        logs=logs
    )

@router.get("/scan-progress/cluster/{cluster_id}")
async def get_scan_progress(
    cluster_id: int,
    db: Session = Depends(get_db)
):
    """获取扫描进度状态（简单实现）"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    # 统计已扫描的数据库和表数量
    metrics = db.query(TableMetric).filter(TableMetric.cluster_id == cluster_id).all()
    
    # 按数据库统计
    database_stats = {}
    total_tables = len(metrics)
    total_files = sum(m.total_files for m in metrics)
    total_small_files = sum(m.small_files for m in metrics)
    
    for metric in metrics:
        db_name = metric.database_name
        if db_name not in database_stats:
            database_stats[db_name] = {
                "tables": 0,
                "files": 0, 
                "small_files": 0,
                "last_scan": None
            }
        
        database_stats[db_name]["tables"] += 1
        database_stats[db_name]["files"] += metric.total_files
        database_stats[db_name]["small_files"] += metric.small_files
        
        if (database_stats[db_name]["last_scan"] is None or 
            metric.scan_time > database_stats[db_name]["last_scan"]):
            database_stats[db_name]["last_scan"] = metric.scan_time
    
    return {
        "cluster_id": cluster_id,
        "cluster_name": cluster.name,
        "overall_progress": {
            "total_databases_scanned": len(database_stats),
            "total_tables_scanned": total_tables,
            "total_files_found": total_files,
            "total_small_files": total_small_files,
            "small_file_ratio": round(total_small_files / max(total_files, 1) * 100, 2)
        },
        "database_progress": database_stats,
        "status": "idle" if total_tables > 0 else "no_data"
    }
