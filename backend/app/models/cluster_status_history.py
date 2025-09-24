from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.database import Base


class ClusterStatusHistory(Base):
    """集群状态变更历史记录"""

    __tablename__ = "cluster_status_history"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False, index=True)

    # 状态变更信息
    from_status = Column(String(20), nullable=True)  # 原状态
    to_status = Column(String(20), nullable=False)  # 新状态

    # 变更原因和详情
    reason = Column(
        String(100), nullable=True
    )  # 变更原因 (health_check, manual, connection_test, etc.)
    message = Column(Text, nullable=True)  # 详细信息

    # 连接测试相关数据
    connection_test_result = Column(Text, nullable=True)  # JSON格式的连接测试结果

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    cluster = relationship("Cluster", back_populates="status_history")
