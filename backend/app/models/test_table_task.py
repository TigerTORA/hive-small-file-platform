"""
测试表任务数据模型
"""

import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.config.database import Base


class TestTableTask(Base):
    """测试表生成任务模型"""

    __tablename__ = "test_table_tasks"

    id = Column(String(36), primary_key=True, comment="任务ID")
    cluster_id = Column(Integer, nullable=False, comment="集群ID")
    status = Column(String(50), nullable=False, default="pending", comment="任务状态")
    config = Column(Text, nullable=False, comment="任务配置(JSON)")

    created_time = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    started_time = Column(DateTime, nullable=True, comment="开始时间")
    completed_time = Column(DateTime, nullable=True, comment="完成时间")
    last_heartbeat = Column(DateTime, nullable=True, comment="最后心跳时间")

    error_message = Column(Text, nullable=True, comment="错误信息")
    progress_percentage = Column(Float, default=0.0, comment="进度百分比")
    current_phase = Column(String(100), nullable=True, comment="当前阶段")
    current_operation = Column(String(255), nullable=True, comment="当前操作")

    # 结果统计字段
    hdfs_files_created = Column(Integer, nullable=True, comment="创建的HDFS文件数")
    hive_partitions_added = Column(Integer, nullable=True, comment="添加的Hive分区数")
    total_size_mb = Column(Float, nullable=True, comment="总大小(MB)")

    def get_config_dict(self) -> dict:
        """获取配置字典"""
        if not self.config:
            return {}
        try:
            return json.loads(self.config)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_config_dict(self, config_dict: dict):
        """设置配置字典"""
        self.config = json.dumps(config_dict, ensure_ascii=False)

    @property
    def table_name(self) -> str:
        """获取表名"""
        config = self.get_config_dict()
        return config.get("table_name", "test_table")

    @property
    def database_name(self) -> str:
        """获取数据库名"""
        config = self.get_config_dict()
        return config.get("database_name", "test_db")

    @property
    def task_name(self) -> str:
        """获取任务名称"""
        return f"生成测试表: {self.database_name}.{self.table_name}"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "cluster_id": self.cluster_id,
            "status": self.status,
            "config": self.get_config_dict(),
            "task_name": self.task_name,
            "database_name": self.database_name,
            "table_name": self.table_name,
            "created_time": self.created_time,
            "started_time": self.started_time,
            "completed_time": self.completed_time,
            "error_message": self.error_message,
            "progress_percentage": self.progress_percentage,
            "current_phase": self.current_phase,
            "current_operation": self.current_operation,
            "hdfs_files_created": self.hdfs_files_created,
            "hive_partitions_added": self.hive_partitions_added,
            "total_size_mb": self.total_size_mb,
        }
