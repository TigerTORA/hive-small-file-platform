from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ClusterBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    hive_host: str = Field(..., max_length=255)
    hive_port: int = Field(default=10000, ge=1, le=65535)
    hive_database: str = Field(default="default", max_length=100)
    hive_metastore_url: str = Field(..., max_length=500)
    hdfs_namenode_url: str = Field(..., max_length=500)
    hdfs_user: str = Field(default="hdfs", max_length=100)
    small_file_threshold: int = Field(default=128*1024*1024, ge=1024)
    scan_enabled: bool = True

class ClusterCreate(ClusterBase):
    pass

class ClusterUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    hive_host: Optional[str] = Field(None, max_length=255)
    hive_port: Optional[int] = Field(None, ge=1, le=65535)
    hive_database: Optional[str] = Field(None, max_length=100)
    hive_metastore_url: Optional[str] = Field(None, max_length=500)
    hdfs_namenode_url: Optional[str] = Field(None, max_length=500)
    hdfs_user: Optional[str] = Field(None, max_length=100)
    small_file_threshold: Optional[int] = Field(None, ge=1024)
    scan_enabled: Optional[bool] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive|error)$")

class ClusterResponse(ClusterBase):
    id: int
    status: str
    created_time: datetime
    updated_time: datetime
    
    class Config:
        from_attributes = True