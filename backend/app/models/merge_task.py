from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, Boolean
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
    merge_strategy = Column(String(50), default="safe_merge")  # concatenate, insert_overwrite, safe_merge
    target_file_size = Column(Integer, nullable=True)  # target file size in bytes
    
    # Task status and state management
    status = Column(String(20), default="pending", index=True)  # pending, running, success, failed, cancelled
    celery_task_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Progress tracking
    progress = Column(Float, default=0.0)  # 0.0 - 100.0
    current_phase = Column(String(100), nullable=True)  # e.g., "preparing", "merging", "validating"
    
    # 详细进度跟踪字段
    execution_phase = Column(String(50), nullable=True)  # 当前执行阶段
    progress_percentage = Column(Float, default=0.0)  # 执行进度百分比
    estimated_remaining_time = Column(Integer, nullable=True)  # 预计剩余时间（秒）
    processed_files_count = Column(Integer, nullable=True)  # 已处理文件数
    total_files_count = Column(Integer, nullable=True)  # 总文件数
    yarn_application_id = Column(String(100), nullable=True)  # YARN任务ID
    current_operation = Column(String(500), nullable=True)  # 当前操作描述
    
    # Resource locking
    table_lock_acquired = Column(Boolean, default=False)
    lock_holder = Column(String(100), nullable=True)  # task ID or process ID that holds the lock
    
    # Strategy selection metadata
    strategy_reason = Column(Text, nullable=True)  # Explanation for strategy selection
    auto_selected = Column(Boolean, default=True)  # Whether strategy was auto-selected
    
    # Performance metrics
    estimated_duration = Column(Integer, nullable=True)  # Estimated duration in seconds
    
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