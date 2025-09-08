from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.table_metric import TableMetric
from app.models.cluster import Cluster
from app.schemas.table_metric import TableMetricResponse, ScanRequest
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.monitor.mock_table_scanner import MockTableScanner
from app.monitor.hybrid_table_scanner import HybridTableScanner

router = APIRouter()

@router.get("/metrics", response_model=list[TableMetricResponse])
async def get_table_metrics(
    cluster_id: int = Query(...),
    database_name: str = Query(None),
    db: Session = Depends(get_db)
):
    """Get table metrics for a cluster"""
    query = db.query(TableMetric).filter(TableMetric.cluster_id == cluster_id)
    if database_name:
        query = query.filter(TableMetric.database_name == database_name)
    
    metrics = query.order_by(TableMetric.scan_time.desc()).all()
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
    db: Session = Depends(get_db)
):
    """Unified scan endpoint for tables - can scan single table or database"""
    cluster = db.query(Cluster).filter(Cluster.id == scan_request.cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        scanner = MockTableScanner(cluster)
        
        if scan_request.table_name and scan_request.database_name:
            # Scan single table
            with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as connector:
                tables = connector.get_tables(scan_request.database_name)
                table_info = next((t for t in tables if t['table_name'] == scan_request.table_name), None)
                if not table_info:
                    raise HTTPException(status_code=404, detail="Table not found")
            
            if not scanner.hive_connector.connect():
                raise Exception("Failed to connect to MetaStore")
            if not scanner.hdfs_scanner.connect():
                raise Exception("Failed to connect to HDFS")
            
            try:
                table_result = scanner.scan_table(db, scan_request.database_name, table_info)
                return {
                    "cluster_id": scan_request.cluster_id,
                    "database_name": scan_request.database_name,
                    "table_name": scan_request.table_name,
                    "scan_result": table_result,
                    "status": "completed"
                }
            finally:
                scanner.hive_connector.disconnect()
                scanner.hdfs_scanner.disconnect()
        
        elif scan_request.database_name:
            # Scan database
            result = scanner.scan_database_tables(db, scan_request.database_name)
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
        scanner = MockTableScanner(cluster)
        result = scanner.scan_database_tables(db, database_name, table_filter)
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
    max_tables: int = Query(10, description="Maximum number of tables to scan"),
    db: Session = Depends(get_db)
):
    """Scan tables using real MetaStore and intelligent HDFS connection"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        scanner = HybridTableScanner(cluster)
        result = scanner.scan_database_tables(db, database_name, table_filter, max_tables)
        return {
            "cluster_id": cluster_id,
            "database_name": database_name,
            "scan_result": result,
            "status": "completed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Real scan failed: {str(e)}")

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
        scanner = MockTableScanner(cluster)
        if not scanner.hive_connector.connect():
            raise Exception("Failed to connect to MetaStore")
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

@router.get("/test-connection/{cluster_id}")
async def test_cluster_connections(cluster_id: int, db: Session = Depends(get_db)):
    """Test cluster connections (Mock mode)"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        scanner = MockTableScanner(cluster)
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