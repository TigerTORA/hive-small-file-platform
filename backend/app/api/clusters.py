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