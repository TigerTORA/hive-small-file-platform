"""
WebSocket API 端点
提供实时数据推送功能
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.websocket_service import (
    WebSocketMessage,
    notification_service,
    websocket_manager,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = Query(default="anonymous", description="用户ID"),
    topics: Optional[str] = Query(default="", description="订阅主题，用逗号分隔"),
):
    """
    WebSocket连接端点

    支持的查询参数：
    - user_id: 用户标识符（可选）
    - topics: 要订阅的主题列表，用逗号分隔（可选）

    支持的主题：
    - cluster_status: 集群状态变更
    - connection_test: 连接测试结果
    - scan_progress: 扫描进度更新
    - task_updates: 任务状态变更
    - health_check: 健康检查结果
    """
    connected = await websocket_manager.connect(websocket, user_id)
    if not connected:
        return

    # 处理初始订阅
    if topics:
        topic_list = [topic.strip() for topic in topics.split(",") if topic.strip()]
        await websocket_manager.subscribe(user_id, topic_list)

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await handle_client_message(websocket, user_id, message)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client {user_id}: {data}")
                await websocket_manager._send_to_websocket(
                    websocket,
                    WebSocketMessage(
                        type="error", data={"message": "Invalid JSON format"}
                    ),
                )
            except Exception as e:
                logger.error(f"Error handling client message: {e}")
                await websocket_manager._send_to_websocket(
                    websocket,
                    WebSocketMessage(
                        type="error", data={"message": "Internal server error"}
                    ),
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally: user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await websocket_manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, user_id: str, message: dict):
    """处理客户端消息"""
    message_type = message.get("type")
    data = message.get("data", {})

    if message_type == "subscribe":
        # 订阅主题
        topics = data.get("topics", [])
        await websocket_manager.subscribe(user_id, topics)

        await websocket_manager._send_to_websocket(
            websocket,
            WebSocketMessage(type="subscription_confirmed", data={"topics": topics}),
        )

    elif message_type == "unsubscribe":
        # 取消订阅
        topics = data.get("topics", [])
        await websocket_manager.unsubscribe(user_id, topics)

        await websocket_manager._send_to_websocket(
            websocket,
            WebSocketMessage(type="unsubscription_confirmed", data={"topics": topics}),
        )

    elif message_type == "ping":
        # 心跳检测
        await websocket_manager._send_to_websocket(
            websocket,
            WebSocketMessage(type="pong", data={"timestamp": data.get("timestamp")}),
        )

    elif message_type == "get_status":
        # 请求状态信息
        stats = websocket_manager.get_connection_stats()
        await websocket_manager._send_to_websocket(
            websocket, WebSocketMessage(type="status_response", data=stats)
        )

    else:
        logger.warning(f"Unknown message type from {user_id}: {message_type}")
        await websocket_manager._send_to_websocket(
            websocket,
            WebSocketMessage(
                type="error", data={"message": f"Unknown message type: {message_type}"}
            ),
        )


@router.get("/ws/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计信息"""
    return websocket_manager.get_connection_stats()


@router.post("/ws/broadcast")
async def broadcast_message(topic: str, message_type: str, data: dict):
    """
    手动广播消息（用于测试和管理）
    """
    message = WebSocketMessage(type=message_type, data=data)

    await websocket_manager.broadcast_to_topic(topic, message)

    return {
        "status": "success",
        "message": f"Broadcasted to topic '{topic}'",
        "stats": websocket_manager.get_connection_stats(),
    }


# 导出通知服务，供其他模块使用
__all__ = ["router", "notification_service"]
