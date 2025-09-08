from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base

class MergeTask(Base):
    __tablename__ = "merge_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False, index=True)
    
    # Task identification
    task_name = Column(String(200), nullable=False)
    table_name = Column(String(200), nullable=False, index=True)
    database_name = Column(String(100), nullable=False, index=True)
    partition_filter = Column(String(500), nullable=True)  # e.g., "dt='2023-01-01'"
    
    # Task configuration
    merge_strategy = Column(String(50), default="concatenate")  # concatenate, insert_overwrite
    target_file_size = Column(Integer, nullable=True)  # target file size in bytes
    
    # Task status
    status = Column(String(20), default="pending", index=True)  # pending, running, success, failed
    celery_task_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Execution info
    files_before = Column(Integer, nullable=True)
    files_after = Column(Integer, nullable=True)
    size_saved = Column(Integer, nullable=True)  # bytes saved
    
    # Timestamps
    created_time = Column(DateTime(timezone=True), server_default=func.now())
    started_time = Column(DateTime(timezone=True), nullable=True)
    completed_time = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    cluster = relationship("Cluster", back_populates="merge_tasks")
    task_logs = relationship("TaskLog", back_populates="merge_task")