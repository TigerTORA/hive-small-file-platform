from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TableMetricBase(BaseModel):
    database_name: str
    table_name: str
    table_path: Optional[str] = None

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
    total_files: Optional[int] = 0
    small_files: Optional[int] = 0
    total_size: Optional[int] = 0
    avg_file_size: Optional[float] = 0.0

    # Partition info
    is_partitioned: Optional[bool] = False
    partition_count: Optional[int] = 0


class TableMetricResponse(TableMetricBase):
    id: int
    cluster_id: int
    scan_time: Optional[datetime] = None
    scan_duration: Optional[float] = 0.0

    class Config:
        from_attributes = True


class ScanRequest(BaseModel):
    cluster_id: int
    database_name: Optional[str] = None
    table_name: Optional[str] = None
