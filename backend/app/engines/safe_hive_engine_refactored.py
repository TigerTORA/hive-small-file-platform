"""
重构后的安全Hive合并引擎
作为主控制器，协调各个专门的服务模块
"""

import logging
from typing import Any, Callable, Dict

from sqlalchemy.orm import Session

from app.engines.base_engine import BaseMergeEngine
from app.engines.connection_manager import HiveConnectionManager
from app.engines.merge_executor import MergeTaskExecutor
from app.engines.merge_progress_tracker import MergeProgressTracker
from app.engines.validation_service import MergeTaskValidationService
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask

logger = logging.getLogger(__name__)


class SafeHiveMergeEngine(BaseMergeEngine):
    """
    重构后的安全Hive合并引擎
    采用模块化架构，职责分离清晰
    """

    def __init__(self, cluster: Cluster):
        super().__init__(cluster)

        # 初始化各个服务模块
        self.connection_manager = HiveConnectionManager(cluster)
        self.validation_service = MergeTaskValidationService(self.connection_manager)
        self.executor = MergeTaskExecutor(self.connection_manager)
        self.progress_tracker = MergeProgressTracker(self.connection_manager)

    def set_progress_callback(self, callback: Callable[[str, str], None]):
        """设置进度回调函数"""
        self.executor.set_progress_callback(callback)

    def validate_task(self, task: MergeTask) -> Dict[str, Any]:
        """验证合并任务是否可执行"""
        return self.validation_service.validate_task(task)

    def execute_merge(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
        """执行合并任务"""
        return self.executor.execute_merge(task, db_session)

    def get_merge_preview(self, task: MergeTask) -> Dict[str, Any]:
        """获取合并预览信息"""
        return self.progress_tracker.get_merge_preview(task)

    def estimate_duration(self, task: MergeTask) -> int:
        """估算合并任务执行时间（秒）"""
        return self.progress_tracker.estimate_duration(task)

    # 为了保持向后兼容性，保留这些存根方法
    def _execute_concatenate(
        self, task: MergeTask, db_session: Session
    ) -> Dict[str, Any]:
        """向后兼容的CONCATENATE执行方法"""
        task.merge_strategy = "CONCATENATE"
        return self.executor.execute_merge(task, db_session)

    def _execute_insert_overwrite(
        self, task: MergeTask, db_session: Session
    ) -> Dict[str, Any]:
        """向后兼容的INSERT OVERWRITE执行方法"""
        task.merge_strategy = "INSERT_OVERWRITE"
        return self.executor.execute_merge(task, db_session)

    def _execute_safe_merge(
        self, task: MergeTask, db_session: Session
    ) -> Dict[str, Any]:
        """向后兼容的安全合并执行方法"""
        task.merge_strategy = "SAFE_MERGE"
        return self.executor.execute_merge(task, db_session)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if self.connection_manager:
            self.connection_manager.cleanup_connections()


# 为了向后兼容，保留原始类名的别名
SafeHiveMergeEngineRefactored = SafeHiveMergeEngine
