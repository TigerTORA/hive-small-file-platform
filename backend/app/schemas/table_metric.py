from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TableMetricBase(BaseModel):
    database_name: str
    table_name: str
    table_path: str
    total_files: int = 0
    small_files: int = 0
    total_size: int = 0
    avg_file_size: float = 0.0
    is_partitioned: bool = False
    partition_count: int = 0

class TableMetricResponse(TableMetricBase):
    id: int
    cluster_id: int
    scan_time: datetime
    scan_duration: float
    
    class Config:
        from_attributes = True

class ScanRequest(BaseModel):
    cluster_id: int
    database_name: Optional[str] = None
    table_name: Optional[str] = None