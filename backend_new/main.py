from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from models import Cluster, TableMetric, create_tables, get_db
from scanner import HiveScanner

# Create tables on startup
create_tables()

app = FastAPI(title="Hive Small File Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schemas
class ClusterCreate(BaseModel):
    name: str
    hive_metastore_url: str
    hdfs_namenode_url: str
    small_file_threshold: Optional[int] = 128*1024*1024

class ScanRequest(BaseModel):
    cluster_id: int
    database_name: str
    table_name: Optional[str] = None

# Health endpoints
@app.get("/")
def root():
    return {"message": "Hive Small File Platform v2.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# Cluster management
@app.get("/api/clusters")
def list_clusters(db: Session = Depends(get_db)):
    return db.query(Cluster).all()

@app.post("/api/clusters")
def create_cluster(cluster: ClusterCreate, db: Session = Depends(get_db)):
    db_cluster = Cluster(**cluster.dict())
    db.add(db_cluster)
    db.commit()
    db.refresh(db_cluster)
    return db_cluster

@app.get("/api/clusters/{cluster_id}")
def get_cluster(cluster_id: int, db: Session = Depends(get_db)):
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster

@app.delete("/api/clusters/{cluster_id}")
def delete_cluster(cluster_id: int, db: Session = Depends(get_db)):
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    # Delete related metrics
    db.query(TableMetric).filter(TableMetric.cluster_id == cluster_id).delete()
    db.delete(cluster)
    db.commit()
    return {"message": "Cluster deleted"}

# Connection testing
@app.post("/api/clusters/{cluster_id}/test")
def test_cluster(cluster_id: int, db: Session = Depends(get_db)):
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    scanner = HiveScanner(cluster)
    results = scanner.test_connections()
    
    return {
        "cluster_id": cluster_id,
        "cluster_name": cluster.name,
        "connections": results
    }

# Database and table discovery
@app.get("/api/clusters/{cluster_id}/databases")
def get_databases(cluster_id: int, db: Session = Depends(get_db)):
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    scanner = HiveScanner(cluster)
    databases = scanner.get_databases()
    return {"databases": databases}

@app.get("/api/clusters/{cluster_id}/databases/{database_name}/tables")
def get_tables(cluster_id: int, database_name: str, db: Session = Depends(get_db)):
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    scanner = HiveScanner(cluster)
    tables = scanner.get_tables(database_name)
    return {"database": database_name, "tables": tables}

# File scanning
@app.post("/api/scan")
def scan_tables(scan_request: ScanRequest, db: Session = Depends(get_db)):
    cluster = db.query(Cluster).filter(Cluster.id == scan_request.cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    scanner = HiveScanner(cluster)
    
    if scan_request.table_name:
        # Scan single table
        tables = scanner.get_tables(scan_request.database_name)
        table_info = next((t for t in tables if t['table_name'] == scan_request.table_name), None)
        if not table_info:
            raise HTTPException(status_code=404, detail="Table not found")
        
        result = scanner.scan_table(db, scan_request.database_name, table_info)
        return {
            "cluster_id": scan_request.cluster_id,
            "database_name": scan_request.database_name,
            "table_name": scan_request.table_name,
            "result": result
        }
    else:
        # Scan entire database
        result = scanner.scan_database(db, scan_request.database_name)
        return {
            "cluster_id": scan_request.cluster_id,
            "result": result
        }

# Metrics retrieval
@app.get("/api/metrics")
def get_metrics(
    cluster_id: int = Query(...),
    database_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(TableMetric).filter(TableMetric.cluster_id == cluster_id)
    if database_name:
        query = query.filter(TableMetric.database_name == database_name)
    
    metrics = query.order_by(TableMetric.scan_time.desc()).all()
    return {"metrics": metrics}

@app.get("/api/metrics/summary")
def get_summary(cluster_id: int = Query(...), db: Session = Depends(get_db)):
    from sqlalchemy import func
    
    result = db.query(
        func.count(TableMetric.id).label("total_tables"),
        func.sum(TableMetric.total_files).label("total_files"),
        func.sum(TableMetric.small_files).label("total_small_files"),
        func.avg(TableMetric.avg_file_size).label("avg_file_size")
    ).filter(TableMetric.cluster_id == cluster_id).first()
    
    total_files = result.total_files or 0
    total_small_files = result.total_small_files or 0
    
    return {
        "total_tables": result.total_tables or 0,
        "total_files": total_files,
        "total_small_files": total_small_files,
        "avg_file_size": float(result.avg_file_size or 0),
        "small_file_ratio": (total_small_files / total_files * 100) if total_files > 0 else 0
    }

# Small file analysis
@app.get("/api/analysis/{cluster_id}")
def analyze_small_files(cluster_id: int, db: Session = Depends(get_db)):
    metrics = db.query(TableMetric).filter(TableMetric.cluster_id == cluster_id).all()
    
    if not metrics:
        return {"message": "No data found", "tables": []}
    
    analysis = []
    for metric in metrics:
        if metric.total_files > 0:
            ratio = (metric.small_files / metric.total_files) * 100
            priority = (
                "CRITICAL" if ratio > 80 else
                "HIGH" if ratio > 60 else
                "MEDIUM" if ratio > 40 else
                "LOW"
            )
            
            analysis.append({
                "database_name": metric.database_name,
                "table_name": metric.table_name,
                "total_files": metric.total_files,
                "small_files": metric.small_files,
                "small_file_ratio": round(ratio, 2),
                "priority": priority,
                "total_size_gb": round(metric.total_size / (1024**3), 2),
                "avg_file_size_mb": round(metric.avg_file_size / (1024**2), 2),
                "last_scan": metric.scan_time.isoformat()
            })
    
    # Sort by priority and ratio
    priority_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    analysis.sort(key=lambda x: (priority_order.get(x["priority"], 0), x["small_file_ratio"]), reverse=True)
    
    # Summary stats
    total_tables = len(analysis)
    critical_tables = len([t for t in analysis if t["priority"] == "CRITICAL"])
    high_priority = len([t for t in analysis if t["priority"] == "HIGH"])
    
    return {
        "cluster_id": cluster_id,
        "summary": {
            "total_tables": total_tables,
            "critical_tables": critical_tables,
            "high_priority_tables": high_priority
        },
        "tables": analysis
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)