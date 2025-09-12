from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.config.database import Base
from datetime import datetime
import uuid


class ScanTask(Base):
    """扫描任务模型"""
    __tablename__ = "scan_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    task_type = Column(String(50), nullable=False)  # 'database', 'table', 'cluster'
    task_name = Column(String(255), nullable=False)
    status = Column(String(50), default='pending')  # pending, running, completed, failed
    
    # 进度信息
    total_items = Column(Integer, default=0)  # 总数据库/表数
    completed_items = Column(Integer, default=0)  # 已完成数
    current_item = Column(String(255))  # 当前处理的项目
    
    # 结果统计
    total_tables_scanned = Column(Integer, default=0)
    total_files_found = Column(Integer, default=0)
    total_small_files = Column(Integer, default=0)
    
    # 时间信息
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    duration = Column(Float)  # 秒
    
    # 错误信息
    error_message = Column(Text)
    warnings = Column(Text)  # JSON格式的警告信息
    
    # 关联
    cluster = relationship("Cluster", back_populates="scan_tasks")
    
    def __init__(self, **kwargs):
        if 'task_id' not in kwargs:
            kwargs['task_id'] = str(uuid.uuid4())
        super().__init__(**kwargs)
    
    @property 
    def progress_percentage(self) -> float:
        """计算进度百分比"""
        if self.total_items == 0:
            return 0.0
        return round(self.completed_items / self.total_items * 100, 2)
    
    @property
    def estimated_remaining_seconds(self) -> float:
        """估算剩余时间"""
        if self.completed_items == 0 or not self.start_time:
            return 0.0
        
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        avg_time_per_item = elapsed / self.completed_items
        remaining_items = self.total_items - self.completed_items
        
        return round(remaining_items * avg_time_per_item, 1)