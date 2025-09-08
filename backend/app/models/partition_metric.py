from sqlalchemy import Column, Integer, String, BigInteger, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.config.database import Base

class PartitionMetric(Base):
    __tablename__ = "partition_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    table_metric_id = Column(Integer, ForeignKey("table_metrics.id"), nullable=False, index=True)
    
    # Partition identification
    partition_name = Column(String(500), nullable=False)
    partition_path = Column(String(1000), nullable=False)
    
    # File metrics
    file_count = Column(Integer, default=0)
    small_file_count = Column(Integer, default=0)
    total_size = Column(BigInteger, default=0)  # bytes
    avg_file_size = Column(Float, default=0.0)  # bytes
    
    # Relationships
    table_metric = relationship("TableMetric", back_populates="partition_metrics")