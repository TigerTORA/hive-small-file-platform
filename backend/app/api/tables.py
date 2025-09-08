from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.table_metric import TableMetric
from app.models.cluster import Cluster
from app.schemas.table_metric import TableMetricResponse, ScanRequest
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.monitor.mock_table_scanner import MockTableScanner

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
    """Scan all tables in a database for small files"""
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
    """Test cluster connections"""
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