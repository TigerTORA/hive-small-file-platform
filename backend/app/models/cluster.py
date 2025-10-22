from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base

# 确保相关模型在映射配置前已注册到同一 Base（避免关系解析失败）
from . import cluster_status_history as _cluster_status_history  # noqa: F401
from . import merge_task as _merge_task  # noqa: F401
from . import scan_task as _scan_task  # noqa: F401
from . import table_metric as _table_metric  # noqa: F401


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Hive connection info
    hive_host = Column(String(255), nullable=False)
    hive_port = Column(Integer, default=10000)
    hive_database = Column(String(100), default="default")
    hive_metastore_url = Column(String(500), nullable=False)

    # HDFS connection info
    hdfs_namenode_url = Column(String(500), nullable=False)
    hdfs_user = Column(String(100), default="hdfs")
    hdfs_password = Column(String(255), nullable=True)  # TODO replace when Kerberos fully enabled

    # Hive LDAP authentication info
    auth_type = Column(String(20), default="NONE")  # NONE, LDAP, KERBEROS
    hive_username = Column(String(100), nullable=True)  # Hive LDAP用户名
    hive_password = Column(String(500), nullable=True)  # Hive LDAP密码(加密存储)
    kerberos_principal = Column(String(200), nullable=True)
    kerberos_keytab_path = Column(String(500), nullable=True)
    kerberos_realm = Column(String(100), nullable=True)
    kerberos_ticket_cache = Column(String(200), nullable=True)

    # YARN monitoring info
    yarn_resource_manager_url = Column(String(200), nullable=True)  # YARN RM地址

    # Status and timestamps
    status = Column(
        String(20), default="active"
    )  # active, inactive, error, testing, maintenance
    health_status = Column(
        String(20), default="unknown"
    )  # healthy, degraded, unhealthy, unknown
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    created_time = Column(DateTime(timezone=True), server_default=func.now())
    updated_time = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Configuration
    small_file_threshold = Column(Integer, default=128 * 1024 * 1024)  # 128MB
    scan_enabled = Column(Boolean, default=True)

    # Archive configuration
    archive_enabled = Column(Boolean, default=False)  # 是否启用归档功能
    archive_root_path = Column(String(500), default="/archive")  # 归档根目录路径
    cold_data_threshold_days = Column(Integer, default=90)  # 冷数据天数阈值
    auto_archive_enabled = Column(Boolean, default=False)  # 是否启用自动归档
    archive_compression_enabled = Column(Boolean, default=True)  # 归档时是否压缩

    # Relationships
    table_metrics = relationship("TableMetric", back_populates="cluster")
    merge_tasks = relationship("MergeTask", back_populates="cluster")
    scan_tasks = relationship("ScanTask", back_populates="cluster")
    status_history = relationship(
        "ClusterStatusHistory",
        back_populates="cluster",
        order_by="ClusterStatusHistory.created_at.desc()",
    )
