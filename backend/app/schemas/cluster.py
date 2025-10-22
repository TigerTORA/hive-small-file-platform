from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ClusterBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    hive_host: str = Field(..., max_length=255)
    hive_port: int = Field(default=10000, ge=1, le=65535)
    hive_database: str = Field(default="default", max_length=100)
    hive_metastore_url: str = Field(..., max_length=500)
    hdfs_namenode_url: str = Field(..., max_length=500)
    hdfs_user: str = Field(default="hdfs", max_length=100)
    hdfs_password: Optional[str] = Field(None, max_length=255)
    kerberos_principal: Optional[str] = Field(None, max_length=200)
    kerberos_keytab_path: Optional[str] = Field(None, max_length=500)
    kerberos_realm: Optional[str] = Field(None, max_length=100)
    kerberos_ticket_cache: Optional[str] = Field(None, max_length=200)

    # Hive LDAP authentication (tolerate null in DB records)
    auth_type: Optional[str] = Field(default="NONE", pattern="^(NONE|LDAP|KERBEROS)$")
    hive_username: Optional[str] = Field(None, max_length=100)
    hive_password: Optional[str] = Field(None, max_length=500)

    # YARN monitoring
    yarn_resource_manager_url: Optional[str] = Field(None, max_length=200)

    small_file_threshold: int = Field(default=128 * 1024 * 1024, ge=1024)
    scan_enabled: bool = True

    @model_validator(mode="after")
    def _validate_kerberos_requirements(self):
        auth = (self.auth_type or "NONE").upper()
        if auth == "KERBEROS":
            missing = []
            if not (self.kerberos_principal or "").strip():
                missing.append("kerberos_principal")
            if not (self.kerberos_keytab_path or "").strip():
                missing.append("kerberos_keytab_path")
            if missing:
                raise ValueError(
                    "Kerberos configuration requires: " + ", ".join(missing)
                )
        return self


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
    hdfs_password: Optional[str] = Field(None, max_length=255)
    kerberos_principal: Optional[str] = Field(None, max_length=200)
    kerberos_keytab_path: Optional[str] = Field(None, max_length=500)
    kerberos_realm: Optional[str] = Field(None, max_length=100)
    kerberos_ticket_cache: Optional[str] = Field(None, max_length=200)

    # Hive LDAP authentication
    auth_type: Optional[str] = Field(None, pattern="^(NONE|LDAP|KERBEROS)$")
    hive_username: Optional[str] = Field(None, max_length=100)
    hive_password: Optional[str] = Field(None, max_length=500)

    # YARN monitoring
    yarn_resource_manager_url: Optional[str] = Field(None, max_length=200)

    small_file_threshold: Optional[int] = Field(None, ge=1024)
    scan_enabled: Optional[bool] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive|error)$")

    @model_validator(mode="after")
    def _validate_kerberos_update(self):
        if (self.auth_type or "").upper() == "KERBEROS":
            principal = (
                self.kerberos_principal
                if self.kerberos_principal is not None
                else ""
            ).strip()
            keytab = (
                self.kerberos_keytab_path
                if self.kerberos_keytab_path is not None
                else ""
            ).strip()
            if not principal or not keytab:
                raise ValueError(
                    "Updating auth_type to KERBEROS requires kerberos_principal and kerberos_keytab_path"
                )
        return self


class ClusterResponse(ClusterBase):
    id: int
    status: str
    health_status: Optional[str] = None
    last_health_check: Optional[datetime] = None
    created_time: datetime
    updated_time: datetime

    class Config:
        from_attributes = True
