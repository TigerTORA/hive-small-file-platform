from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class MergeTaskBase(BaseModel):
    task_name: str = Field(..., max_length=200)
    table_name: str = Field(..., max_length=200)
    database_name: str = Field(..., max_length=100)
    partition_filter: Optional[str] = Field(None, max_length=500)
    merge_strategy: str = Field(default="safe_merge", pattern="^(concatenate|insert_overwrite|safe_merge)$")
    target_file_size: Optional[int] = Field(None, ge=1024)

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
    
    class Config:
        from_attributes = True