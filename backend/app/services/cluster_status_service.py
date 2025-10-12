"""
集群状态管理服务
负责集群状态监控、状态变更历史记录、连接状态缓存等功能
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.cluster import Cluster
from app.models.cluster_status_history import ClusterStatusHistory
from app.services.enhanced_connection_service import (
    ConnectionType,
    enhanced_connection_service,
)


class ClusterStatusService:
    """集群状态管理服务"""

    def __init__(self):
        # 连接状态缓存: cluster_id -> {service: status, timestamp}
        self._connection_cache: Dict[int, Dict[str, Dict]] = {}
        # 缓存过期时间（秒）
        self._cache_ttl = 300  # 5分钟

    def record_status_change(
        self,
        db: Session,
        cluster_id: int,
        new_status: str,
        reason: str = None,
        message: str = None,
        connection_test_result: Dict = None,
    ) -> ClusterStatusHistory:
        """记录集群状态变更历史"""
        # 获取当前集群状态
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        old_status = cluster.status

        # 创建状态变更记录
        status_history = ClusterStatusHistory(
            cluster_id=cluster_id,
            from_status=old_status,
            to_status=new_status,
            reason=reason,
            message=message,
            connection_test_result=(
                json.dumps(connection_test_result) if connection_test_result else None
            ),
        )

        db.add(status_history)

        # 更新集群状态
        cluster.status = new_status
        cluster.updated_time = func.now()

        db.commit()
        return status_history

    def update_health_status(
        self,
        db: Session,
        cluster_id: int,
        health_status: str,
        connection_test_result: Dict = None,
    ) -> bool:
        """更新集群健康状态"""
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            return False

        old_health = cluster.health_status
        cluster.health_status = health_status
        cluster.last_health_check = func.now()

        # 如果健康状态发生变化，记录历史
        if old_health != health_status:
            self.record_status_change(
                db,
                cluster_id,
                cluster.status,  # 保持原有状态
                reason="health_check",
                message=f"Health status changed from {old_health} to {health_status}",
                connection_test_result=connection_test_result,
            )

        db.commit()
        return True

    def get_cluster_status_history(
        self, db: Session, cluster_id: int, limit: int = 50
    ) -> List[ClusterStatusHistory]:
        """获取集群状态变更历史"""
        return (
            db.query(ClusterStatusHistory)
            .filter(ClusterStatusHistory.cluster_id == cluster_id)
            .order_by(desc(ClusterStatusHistory.created_at))
            .limit(limit)
            .all()
        )

    def get_connection_status_cached(
        self, cluster_id: int, service: str
    ) -> Optional[Dict]:
        """从缓存获取连接状态"""
        if cluster_id not in self._connection_cache:
            return None

        service_cache = self._connection_cache[cluster_id].get(service)
        if not service_cache:
            return None

        # 检查缓存是否过期
        cache_time = service_cache.get("timestamp")
        if not cache_time:
            return None

        if datetime.now() - cache_time > timedelta(seconds=self._cache_ttl):
            # 缓存过期，删除缓存项
            del self._connection_cache[cluster_id][service]
            if not self._connection_cache[cluster_id]:
                del self._connection_cache[cluster_id]
            return None

        return service_cache

    def cache_connection_status(
        self, cluster_id: int, service: str, status: str, details: Dict = None
    ):
        """缓存连接状态"""
        if cluster_id not in self._connection_cache:
            self._connection_cache[cluster_id] = {}

        self._connection_cache[cluster_id][service] = {
            "status": status,
            "details": details or {},
            "timestamp": datetime.now(),
        }

    async def test_cluster_connections(
        self,
        db: Session,
        cluster_id: int,
        force_refresh: bool = False,
        connection_types: List[str] = None,
    ) -> Dict:
        """测试集群连接状态（支持缓存和增强检测）"""
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        # 如果不强制刷新，先检查缓存
        if not force_refresh:
            cached_result = self._get_cached_cluster_test_result(cluster_id)
            if cached_result:
                return cached_result

        # 转换连接类型参数
        if connection_types:
            conn_types = []
            for conn_type in connection_types:
                if conn_type == "metastore":
                    conn_types.append(ConnectionType.METASTORE)
                elif conn_type == "hdfs":
                    conn_types.append(ConnectionType.HDFS)
                elif conn_type == "hiveserver2":
                    conn_types.append(ConnectionType.HIVESERVER2)
        else:
            conn_types = None

        # 执行增强的连接测试
        try:
            test_results = await enhanced_connection_service.test_cluster_connections(
                cluster, conn_types
            )

            # 解析测试结果并缓存各服务状态
            tests = test_results.get("tests", {})

            # 缓存各服务状态
            for service_name, service_result in tests.items():
                self.cache_connection_status(
                    cluster_id,
                    service_name,
                    service_result.get("status", "unknown"),
                    service_result,
                )

            # 根据连接测试结果更新健康状态
            overall_status = test_results.get("overall_status", "unknown")
            health_mapping = {
                "success": "healthy",
                "partial": "degraded",
                "failed": "unhealthy",
                "unknown": "unknown",
            }
            health_status = health_mapping.get(overall_status, "unknown")

            self.update_health_status(db, cluster_id, health_status, test_results)

            return test_results

        except Exception as e:
            # 测试失败时也要记录状态
            error_result = {
                "overall_status": "failed",
                "error": str(e),
                "test_time": datetime.now().isoformat(),
                "tests": {},
                "logs": [
                    {"level": "ERROR", "message": f"Connection test failed: {str(e)}"}
                ],
                "suggestions": [
                    "检查集群配置是否正确",
                    "确认网络连接正常",
                    "验证服务状态",
                ],
            }

            self.update_health_status(db, cluster_id, "unhealthy", error_result)

            # 缓存失败状态
            for service in ["metastore", "hdfs", "hiveserver2"]:
                self.cache_connection_status(
                    cluster_id, service, "error", {"error": str(e)}
                )

            return error_result

    def _get_cached_cluster_test_result(self, cluster_id: int) -> Optional[Dict]:
        """获取集群完整的缓存测试结果"""
        if cluster_id not in self._connection_cache:
            return None

        cache_data = self._connection_cache[cluster_id]

        # 检查是否有足够的缓存数据
        required_services = ["metastore", "hdfs"]
        if not all(service in cache_data for service in required_services):
            return None

        # 构建缓存结果
        tests = {}
        overall_status = "success"

        for service, service_cache in cache_data.items():
            tests[service] = {
                "status": service_cache["status"],
                "cached": True,
                **service_cache["details"],
            }

            # 如果任何服务失败，整体状态为失败
            if service_cache["status"] in ["error", "failed"]:
                overall_status = "failed"
            elif service_cache["status"] == "unknown" and overall_status == "success":
                overall_status = "partial"

        return {
            "overall_status": overall_status,
            "test_time": datetime.now().isoformat(),
            "tests": tests,
            "cached": True,
        }

    def get_cluster_connection_summary(self, db: Session, cluster_id: int) -> Dict:
        """获取集群连接状态摘要"""
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        # 获取缓存的连接状态
        connection_status = {}
        services = ["metastore", "hdfs", "hiveserver2"]

        for service in services:
            cached = self.get_connection_status_cached(cluster_id, service)
            if cached:
                connection_status[service] = {
                    "status": cached["status"],
                    "last_check": cached["timestamp"].isoformat(),
                    "cached": True,
                }
            else:
                connection_status[service] = {
                    "status": "unknown",
                    "last_check": None,
                    "cached": False,
                }

        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "status": cluster.status,
            "health_status": cluster.health_status,
            "last_health_check": (
                cluster.last_health_check.isoformat()
                if cluster.last_health_check
                else None
            ),
            "connections": connection_status,
        }

    async def batch_health_check(
        self, db: Session, cluster_ids: List[int] = None, parallel_limit: int = 5
    ) -> Dict:
        """批量健康检查"""
        if cluster_ids is None:
            # 获取所有活跃集群
            clusters = (
                db.query(Cluster)
                .filter(Cluster.status.in_(["active", "testing"]))
                .all()
            )
            cluster_ids = [c.id for c in clusters]

        results = {}

        # 分批并行处理
        for i in range(0, len(cluster_ids), parallel_limit):
            batch = cluster_ids[i : i + parallel_limit]

            # 创建并行任务
            tasks = [
                self.test_cluster_connections(db, cluster_id) for cluster_id in batch
            ]

            # 等待批次完成
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for cluster_id, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results[cluster_id] = {
                        "overall_status": "error",
                        "error": str(result),
                    }
                else:
                    results[cluster_id] = result

        return results

    def get_cluster_health_metrics(self, db: Session, days: int = 7) -> Dict:
        """获取集群健康指标统计"""
        since_date = datetime.now() - timedelta(days=days)

        # 统计各状态的集群数量
        status_counts = (
            db.query(Cluster.status, func.count(Cluster.id).label("count"))
            .group_by(Cluster.status)
            .all()
        )

        health_counts = (
            db.query(Cluster.health_status, func.count(Cluster.id).label("count"))
            .group_by(Cluster.health_status)
            .all()
        )

        # 统计最近的状态变更
        recent_changes = (
            db.query(func.count(ClusterStatusHistory.id))
            .filter(ClusterStatusHistory.created_at >= since_date)
            .scalar()
            or 0
        )

        return {
            "status_distribution": {row.status: row.count for row in status_counts},
            "health_distribution": {
                row.health_status: row.count for row in health_counts
            },
            "recent_status_changes": recent_changes,
            "reporting_period_days": days,
        }

    def clear_connection_cache(self, cluster_id: int = None):
        """清除连接状态缓存"""
        if cluster_id is None:
            self._connection_cache.clear()
        else:
            self._connection_cache.pop(cluster_id, None)


# 全局服务实例
cluster_status_service = ClusterStatusService()
