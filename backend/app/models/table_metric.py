from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base


class TableMetric(Base):
    __tablename__ = "table_metrics"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False, index=True)

    # Table identification
    database_name = Column(String(100), nullable=False, index=True)
    table_name = Column(String(200), nullable=False, index=True)
    table_path = Column(String(500), nullable=True)

    # Table metadata (enhanced)
    table_type = Column(
        String(50), nullable=True
    )  # EXTERNAL_TABLE, MANAGED_TABLE, VIEW
    storage_format = Column(String(50), nullable=True)  # PARQUET, ORC, TEXT, AVRO
    input_format = Column(String(200), nullable=True)  # Full input format class
    output_format = Column(String(200), nullable=True)  # Full output format class
    serde_lib = Column(String(200), nullable=True)  # Serialization library
    table_owner = Column(String(100), nullable=True)  # Table owner
    table_create_time = Column(
        DateTime(timezone=True), nullable=True
    )  # Table creation time

    # File metrics
    total_files = Column(Integer, default=0)
    small_files = Column(Integer, default=0)
    total_size = Column(BigInteger, default=0)  # bytes
    avg_file_size = Column(Float, default=0.0)  # bytes

    # Partition info
    is_partitioned = Column(Integer, default=0)  # boolean as int
    partition_count = Column(Integer, default=0)
    partition_columns = Column(
        String(500), nullable=True
    )  # JSON string of partition column info

    # Scan metadata
    scan_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    scan_duration = Column(Float, default=0.0)  # seconds

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
    cluster = relationship("Cluster", back_populates="table_metrics")
    partition_metrics = relationship(
        "PartitionMetric", back_populates="table_metric", lazy="dynamic"
    )
