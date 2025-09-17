from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ScanTaskCreate(BaseModel):
    """创建扫描任务的请求模式"""
    cluster_id: int
    task_type: str  # 'database', 'table', 'cluster'
    task_name: str
    target_database: Optional[str] = None
    target_table: Optional[str] = None
    max_tables_per_db: Optional[int] = 20


class ScanTaskUpdate(BaseModel):
    """更新扫描任务状态的模式"""
    status: str
    completed_items: int
    current_item: Optional[str] = None
    error_message: Optional[str] = None
    total_tables_scanned: Optional[int] = None
    total_files_found: Optional[int] = None
    total_small_files: Optional[int] = None


class ScanTaskResponse(BaseModel):
    """扫描任务响应模式"""
    id: int
    task_id: str
    cluster_id: int
    task_type: str
    task_name: str
    status: str
    
    # 进度信息
    total_items: int
    completed_items: int
    current_item: Optional[str] = None
    progress_percentage: float
    estimated_remaining_seconds: float
    
    # 结果统计
    total_tables_scanned: int
    total_files_found: int
    total_small_files: int
    
    # 时间信息
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    
    # 错误信息
    error_message: Optional[str] = None
    warnings: Optional[str] = None
    # 最近更新时间（派生：取最新日志时间，若无则 end_time 或 start_time）
    last_update: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ScanTaskLog(BaseModel):
    """扫描任务日志条目"""
    timestamp: datetime
    level: str  # INFO, WARNING, ERROR
    message: str
    database_name: Optional[str] = None
    table_name: Optional[str] = None


class ScanTaskProgress(BaseModel):
    """实时进度响应"""
    task_id: str
    status: str
    progress_percentage: float
    current_item: Optional[str] = None
    completed_items: int
    total_items: int
    estimated_remaining_seconds: float
    logs: List[ScanTaskLog] = []
