from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TableMetricBase(BaseModel):
    database_name: str
    table_name: str
    table_path: str
    
    # Enhanced metadata fields
    table_type: Optional[str] = None
    storage_format: Optional[str] = None
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    serde_lib: Optional[str] = None
    table_owner: Optional[str] = None
    table_create_time: Optional[datetime] = None
    partition_columns: Optional[str] = None
    
    # File metrics
    total_files: int = 0
    small_files: int = 0
    total_size: int = 0
    avg_file_size: float = 0.0
    
    # Partition info
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