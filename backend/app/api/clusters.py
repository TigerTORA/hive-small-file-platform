from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.cluster import Cluster
from app.schemas.cluster import ClusterCreate, ClusterResponse
from app.monitor.mock_table_scanner import MockTableScanner

router = APIRouter()

@router.get("/", response_model=list[ClusterResponse])
async def list_clusters(db: Session = Depends(get_db)):
    """List all clusters"""
    clusters = db.query(Cluster).all()
    return clusters

@router.post("/", response_model=ClusterResponse)
async def create_cluster(cluster: ClusterCreate, db: Session = Depends(get_db)):
    """Create a new cluster"""
    db_cluster = Cluster(**cluster.dict())
    db.add(db_cluster)
    db.commit()
    db.refresh(db_cluster)
    return db_cluster

@router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(cluster_id: int, db: Session = Depends(get_db)):
    """Get cluster by ID"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster

@router.post("/{cluster_id}/test")
async def test_cluster_connection(cluster_id: int, db: Session = Depends(get_db)):
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

@router.get("/health-check")
async def check_all_clusters_health(db: Session = Depends(get_db)):
    """Check health of all clusters - DRAFT VERSION"""
    all_clusters = db.query(Cluster).all()
    health_results = []
    
    for cluster in all_clusters:
        try:
            scanner = MockTableScanner(cluster)
            test_results = scanner.test_connections()
            
            # Simple logic to determine health
            metastore_healthy = test_results.get("metastore_connection", False)
            hdfs_healthy = test_results.get("hdfs_connection", False)
            overall_healthy = metastore_healthy and hdfs_healthy
            
            health_status = {
                "cluster_id": cluster.id,
                "cluster_name": cluster.name,
                "overall_health": "healthy" if overall_healthy else "unhealthy",
                "metastore_status": "ok" if metastore_healthy else "failed",
                "hdfs_status": "ok" if hdfs_healthy else "failed",
                "last_check": "2025-01-08T10:00:00Z",  # hardcoded for now
                "details": test_results
            }
            
        except Exception as e:
            health_status = {
                "cluster_id": cluster.id,
                "cluster_name": cluster.name,
                "overall_health": "error",
                "metastore_status": "error",
                "hdfs_status": "error", 
                "last_check": "2025-01-08T10:00:00Z",
                "error_message": str(e)
            }
            
        health_results.append(health_status)
    
    return {
        "total_clusters": len(all_clusters),
        "healthy_count": len([r for r in health_results if r["overall_health"] == "healthy"]),
        "clusters": health_results
    }