from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.services.scan_service import _sanitize_log_text  # 复用统一日志清洗


class BaseMergeEngine(ABC):
    """
    文件合并引擎基类
    定义所有合并引擎必须实现的接口
    """

    def __init__(self, cluster: Cluster):
        self.cluster = cluster

    @abstractmethod
    def validate_task(self, task: MergeTask) -> Dict[str, Any]:
        """
        验证合并任务是否可执行
        Args:
            task: 合并任务对象
        Returns:
            验证结果字典，包含 valid 和 message 字段
        """
        pass

    @abstractmethod
    def execute_merge(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        """
        执行文件合并
        Args:
            task: 合并任务对象
            db_session: 数据库会话
        Returns:
            执行结果字典，包含状态、文件数量变化等信息
        """
        pass

    @abstractmethod
    def get_merge_preview(self, task: MergeTask) -> Dict[str, Any]:
        """
        获取合并预览信息（不实际执行）
        Args:
            task: 合并任务对象
        Returns:
            预览信息字典，包含预计的文件数量变化等
        """
        pass

    @abstractmethod
    def estimate_duration(self, task: MergeTask) -> int:
        """
        估算任务执行时间
        Args:
            task: 合并任务对象
        Returns:
            预计执行时间（秒）
        """
        pass

    def log_task_event(
        self,
        task: MergeTask,
        level: str,
        message: str,
        details: Optional[str] = None,
        db_session: Optional[Session] = None,
    ):
        """
        记录任务执行日志
        Args:
            task: 合并任务对象
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
            message: 日志消息
            details: 详细信息（可选）
            db_session: 数据库会话（可选）
        """

        # 结构化消息（可选）：若 details 为 dict，支持 phase/code/kv
        def _format_structured_msg(msg: str, details_obj):
            try:
                phase = None
                code = None
                kv: Dict[str, object] = {}
                if isinstance(details_obj, dict):
                    phase = details_obj.get("phase")
                    code = details_obj.get("code")
                    kv = {
                        k: v
                        for k, v in details_obj.items()
                        if k not in ("phase", "code") and v is not None
                    }
                parts = []
                if phase:
                    parts.append(f"[{str(phase).upper()}]")
                if code:
                    parts.append(str(code))
                parts.append(msg)
                if kv:
                    parts.append(" ".join(f"{k}={v}" for k, v in kv.items()))
                return " ".join(parts)
            except Exception:
                return msg

        message_fmt = _format_structured_msg(message, details)

        if db_session:
            from app.models.task_log import TaskLog

            msg = _sanitize_log_text(message_fmt)
            det = _sanitize_log_text(details) if isinstance(details, str) else details
            log_entry = TaskLog(
                task_id=task.id, log_level=level, message=msg, details=det
            )
            db_session.add(log_entry)
            db_session.commit()
        else:
            # 如果没有数据库会话，至少记录到应用日志
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"Task {task.id} [{level}]: {_sanitize_log_text(message_fmt)}")

    def update_task_status(
        self,
        task: MergeTask,
        status: str,
        error_message: Optional[str] = None,
        files_before: Optional[int] = None,
        files_after: Optional[int] = None,
        size_saved: Optional[int] = None,
        db_session: Optional[Session] = None,
    ):
        """
        更新任务状态
        Args:
            task: 合并任务对象
            status: 新状态
            error_message: 错误消息（可选）
            files_before: 合并前文件数量（可选）
            files_after: 合并后文件数量（可选）
            size_saved: 节省的存储空间（可选）
            db_session: 数据库会话（可选）
        """
        from datetime import datetime

        task.status = status
        if error_message:
            task.error_message = error_message
        if files_before is not None:
            task.files_before = files_before
        if files_after is not None:
            task.files_after = files_after
        if size_saved is not None:
            task.size_saved = size_saved

        if status == "running" and not task.started_time:
            task.started_time = datetime.utcnow()
        elif status in ["success", "failed"] and not task.completed_time:
            task.completed_time = datetime.utcnow()

        if db_session:
            db_session.commit()

    def _build_table_path(self, database_name: str, table_name: str) -> str:
        """
        构建表的 HDFS 路径（子类可以重写此方法）
        Args:
            database_name: 数据库名
            table_name: 表名
        Returns:
            表的 HDFS 路径
        """
        # 默认实现，假设标准的 Hive 仓库结构
        return f"/warehouse/tablespace/managed/hive/{database_name}.db/{table_name}"
