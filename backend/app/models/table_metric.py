from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base

class TableMetric(Base):
    __tablename__ = "table_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False, index=True)
    
    # Table identification
    database_name = Column(String(100), nullable=False, index=True)
    table_name = Column(String(200), nullable=False, index=True)
    table_path = Column(String(500), nullable=False)
    
    # File metrics
    total_files = Column(Integer, default=0)
    small_files = Column(Integer, default=0)
    total_size = Column(BigInteger, default=0)  # bytes
    avg_file_size = Column(Float, default=0.0)  # bytes
    
    # Partition info
    is_partitioned = Column(Integer, default=0)  # boolean as int
    partition_count = Column(Integer, default=0)
    
    # Scan metadata
    scan_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    scan_duration = Column(Float, default=0.0)  # seconds
    
    # Relationships
    cluster = relationship("Cluster", back_populates="table_metrics")
    partition_metrics = relationship("PartitionMetric", back_populates="table_metric", lazy="dynamic")