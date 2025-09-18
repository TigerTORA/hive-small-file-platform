"""
WebSocket 实时推送服务
负责向前端推送集群状态变更、连接测试结果等实时数据
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WebSocketMessage:
    """WebSocket消息结构"""
    type: str  # connection_status, cluster_stats, health_update, scan_progress, task_update
    data: Dict[str, Any]
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp
        }


class WebSocketManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 活跃连接：user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # 订阅：user_id -> Set[topic]
        self.subscriptions: Dict[str, Set[str]] = {}
        # 连接元数据
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: str = "anonymous") -> bool:
        """建立WebSocket连接"""
        try:
            await websocket.accept()

            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
                self.subscriptions[user_id] = set()

            self.active_connections[user_id].add(websocket)
            self.connection_metadata[websocket] = {
                "user_id": user_id,
                "connected_at": datetime.now().isoformat(),
                "last_ping": datetime.now().isoformat()
            }

            logger.info(f"WebSocket connected: user={user_id}, total_connections={self._get_total_connections()}")

            # 发送连接确认消息
            await self._send_to_websocket(websocket, WebSocketMessage(
                type="connection_established",
                data={
                    "user_id": user_id,
                    "server_time": datetime.now().isoformat(),
                    "available_topics": [
                        "cluster_status",
                        "connection_test",
                        "scan_progress",
                        "task_updates",
                        "health_check"
                    ]
                }
            ))
            return True

        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            return False

    async def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        try:
            metadata = self.connection_metadata.get(websocket, {})
            user_id = metadata.get("user_id", "unknown")

            # 清理连接
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    del self.subscriptions[user_id]

            self.connection_metadata.pop(websocket, None)

            logger.info(f"WebSocket disconnected: user={user_id}, total_connections={self._get_total_connections()}")

        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")

    async def subscribe(self, user_id: str, topics: List[str]):
        """订阅指定主题"""
        if user_id in self.subscriptions:
            self.subscriptions[user_id].update(topics)
            logger.info(f"User {user_id} subscribed to topics: {topics}")

    async def unsubscribe(self, user_id: str, topics: List[str]):
        """取消订阅指定主题"""
        if user_id in self.subscriptions:
            self.subscriptions[user_id] -= set(topics)
            logger.info(f"User {user_id} unsubscribed from topics: {topics}")

    async def broadcast_to_topic(self, topic: str, message: WebSocketMessage):
        """向订阅了指定主题的所有用户广播消息"""
        sent_count = 0
        failed_count = 0

        # Iterate over a snapshot to avoid mutation during disconnect()
        for user_id, subscribed_topics in list(self.subscriptions.items()):
            if topic in subscribed_topics and user_id in self.active_connections:
                for websocket in self.active_connections[user_id].copy():
                    try:
                        await self._send_to_websocket(websocket, message)
                        sent_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to send message to {user_id}: {e}")
                        await self.disconnect(websocket)
                        failed_count += 1

        logger.debug(f"Broadcast to topic '{topic}': sent={sent_count}, failed={failed_count}")

    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """向指定用户发送消息"""
        if user_id not in self.active_connections:
            logger.warning(f"User {user_id} not connected")
            return False

        sent_count = 0
        for websocket in self.active_connections[user_id].copy():
            try:
                await self._send_to_websocket(websocket, message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send message to {user_id}: {e}")
                await self.disconnect(websocket)

        return sent_count > 0

    async def _send_to_websocket(self, websocket: WebSocket, message: WebSocketMessage):
        """发送消息到指定WebSocket"""
        try:
            await websocket.send_text(json.dumps(message.to_dict()))
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise

    def _get_total_connections(self) -> int:
        """获取总连接数"""
        return sum(len(connections) for connections in self.active_connections.values())

    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        total_connections = self._get_total_connections()
        total_users = len(self.active_connections)

        topic_stats = {}
        for user_id, topics in self.subscriptions.items():
            for topic in topics:
                topic_stats[topic] = topic_stats.get(topic, 0) + 1

        return {
            "total_connections": total_connections,
            "total_users": total_users,
            "topic_subscriptions": topic_stats,
            "avg_connections_per_user": total_connections / max(total_users, 1)
        }


class RealTimeNotificationService:
    """实时通知服务"""

    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager

    async def notify_connection_status_changed(self, cluster_id: int, cluster_name: str,
                                             connection_results: Dict[str, Any]):
        """通知连接状态变更"""
        message = WebSocketMessage(
            type="connection_status",
            data={
                "cluster_id": cluster_id,
                "cluster_name": cluster_name,
                "status": connection_results.get("overall_status"),
                "tests": connection_results.get("tests", {}),
                "suggestions": connection_results.get("suggestions", [])
            }
        )
        await self.ws_manager.broadcast_to_topic("cluster_status", message)

    async def notify_health_check_completed(self, cluster_id: int, health_status: str,
                                          details: Optional[Dict] = None):
        """通知健康检查完成"""
        message = WebSocketMessage(
            type="health_update",
            data={
                "cluster_id": cluster_id,
                "health_status": health_status,
                "details": details or {},
                "check_time": datetime.now().isoformat()
            }
        )
        await self.ws_manager.broadcast_to_topic("health_check", message)

    async def notify_scan_progress(self, cluster_id: int, scan_task_id: int,
                                 progress: float, current_table: str = None):
        """通知扫描进度更新"""
        message = WebSocketMessage(
            type="scan_progress",
            data={
                "cluster_id": cluster_id,
                "scan_task_id": scan_task_id,
                "progress": progress,
                "current_table": current_table
            }
        )
        await self.ws_manager.broadcast_to_topic("scan_progress", message)

    async def notify_task_status_changed(self, task_id: int, task_type: str,
                                       new_status: str, progress: float = None):
        """通知任务状态变更"""
        message = WebSocketMessage(
            type="task_update",
            data={
                "task_id": task_id,
                "task_type": task_type,
                "status": new_status,
                "progress": progress
            }
        )
        await self.ws_manager.broadcast_to_topic("task_updates", message)

    async def notify_cluster_stats_updated(self, cluster_id: int, stats: Dict[str, Any]):
        """通知集群统计数据更新"""
        message = WebSocketMessage(
            type="cluster_stats",
            data={
                "cluster_id": cluster_id,
                "stats": stats,
                "updated_at": datetime.now().isoformat()
            }
        )
        await self.ws_manager.broadcast_to_topic("cluster_status", message)


# 全局实例
websocket_manager = WebSocketManager()
notification_service = RealTimeNotificationService(websocket_manager)
