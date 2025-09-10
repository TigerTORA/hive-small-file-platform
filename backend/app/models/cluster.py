from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class Cluster(Base):
    __tablename__ = "clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Hive connection info
    hive_host = Column(String(255), nullable=False)
    hive_port = Column(Integer, default=10000)
    hive_database = Column(String(100), default="default")
    hive_metastore_url = Column(String(500), nullable=False)
    
    # HDFS connection info
    hdfs_namenode_url = Column(String(500), nullable=False)
    hdfs_user = Column(String(100), default="hdfs")
    hdfs_password = Column(String(255), nullable=True)  # 用于Kerberos认证
    
    # Status and timestamps
    status = Column(String(20), default="active")  # active, inactive, error
    created_time = Column(DateTime(timezone=True), server_default=func.now())
    updated_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Configuration
    small_file_threshold = Column(Integer, default=128*1024*1024)  # 128MB
    scan_enabled = Column(Boolean, default=True)
    
    # Relationships
    table_metrics = relationship("TableMetric", back_populates="cluster")
    merge_tasks = relationship("MergeTask", back_populates="cluster")