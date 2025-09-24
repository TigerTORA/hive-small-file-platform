from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base


class PartitionMetric(Base):
    __tablename__ = "partition_metrics"

    id = Column(Integer, primary_key=True, index=True)
    table_metric_id = Column(
        Integer, ForeignKey("table_metrics.id"), nullable=False, index=True
    )

    # Partition identification
    partition_name = Column(String(500), nullable=False)
    partition_path = Column(String(1000), nullable=False)

    # File metrics
    file_count = Column(Integer, default=0)
    small_file_count = Column(Integer, default=0)
    total_size = Column(BigInteger, default=0)  # bytes
    avg_file_size = Column(Float, default=0.0)  # bytes

    # Scan metadata
    scan_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Cold data archive fields
    last_access_time = Column(DateTime(timezone=True), nullable=True, index=True)
    days_since_last_access = Column(Integer, nullable=True)
    is_cold_data = Column(Integer, default=0)  # boolean as int for compatibility
    archive_status = Column(
        String(50), default="active", index=True
    )  # active, archived, restored
    archive_location = Column(String(1000), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    table_metric = relationship("TableMetric", back_populates="partition_metrics")
