from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base

class TaskLog(Base):
    __tablename__ = "task_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("merge_tasks.id"), nullable=False, index=True)
    
    # Log content
    log_level = Column(String(20), nullable=False, index=True)  # INFO, WARNING, ERROR, DEBUG, CRITICAL
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)  # JSON structured details
    
    # Execution phase and timing
    phase = Column(String(50), nullable=True, index=True)  # initialization, connection_test, file_analysis, etc.
    duration_ms = Column(Integer, nullable=True)  # Duration in milliseconds
    
    # SQL execution details
    sql_statement = Column(Text, nullable=True)  # Full SQL statement
    affected_rows = Column(Integer, nullable=True)  # Number of affected rows
    
    # File operation details
    files_before = Column(Integer, nullable=True)  # Files before operation
    files_after = Column(Integer, nullable=True)  # Files after operation
    hdfs_stats = Column(JSON, nullable=True)  # HDFS statistics JSON
    
    # YARN monitoring
    yarn_application_id = Column(String(100), nullable=True)  # YARN application ID
    
    # Progress tracking
    progress_percentage = Column(Float, nullable=True)  # Progress percentage
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    merge_task = relationship("MergeTask", back_populates="task_logs")