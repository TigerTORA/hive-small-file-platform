from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MergeTaskBase(BaseModel):
    task_name: str = Field(..., max_length=200)
    table_name: str = Field(..., max_length=200)
    database_name: str = Field(..., max_length=100)
    partition_filter: Optional[str] = Field(None, max_length=500)
    target_file_size: Optional[int] = Field(None, ge=1024)
    target_storage_format: Optional[str] = Field(
        None, max_length=50, pattern="^(?i)(orc|parquet|textfile|rcfile|avro)$"
    )
    target_compression: Optional[str] = Field(
        None, max_length=50, pattern="^(?i)(snappy|gzip|lz4|none|default|keep)$"
    )
    use_ec: bool = Field(default=False)


class MergeTaskCreate(MergeTaskBase):
    cluster_id: int


class MergeTaskResponse(MergeTaskBase):
    id: int
    cluster_id: int
    status: str
    celery_task_id: Optional[str]
    error_message: Optional[str]
    files_before: Optional[int]
    files_after: Optional[int]
    size_saved: Optional[int]
    created_time: datetime
    started_time: Optional[datetime]
    completed_time: Optional[datetime]

    # 详细进度跟踪字段
    execution_phase: Optional[str] = None
    progress_percentage: Optional[float] = None
    estimated_remaining_time: Optional[int] = None
    processed_files_count: Optional[int] = None
    total_files_count: Optional[int] = None
    yarn_application_id: Optional[str] = None
    current_operation: Optional[str] = None

    class Config:
        from_attributes = True
