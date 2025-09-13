"""
合并任务详尽日志记录系统
提供结构化、多级别的日志记录，确保数据操作的完整可追溯性
"""
import logging
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from sqlalchemy.orm import Session

from app.models.merge_task import MergeTask

class MergeLogLevel(Enum):
    """合并日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class MergePhase(Enum):
    """合并阶段枚举"""
    INITIALIZATION = "initialization"
    CONNECTION_TEST = "connection_test"
    PRE_VALIDATION = "pre_validation"
    FILE_ANALYSIS = "file_analysis"
    TEMP_TABLE_CREATION = "temp_table_creation"
    DATA_VALIDATION = "data_validation"
    ATOMIC_SWAP = "atomic_swap"
    POST_VALIDATION = "post_validation"
    CLEANUP = "cleanup"
    ROLLBACK = "rollback"
    COMPLETION = "completion"

@dataclass
class MergeLogEntry:
    """合并日志条目"""
    timestamp: str
    task_id: int
    phase: str
    level: str
    message: str
    details: Dict[str, Any]
    duration_ms: Optional[int] = None
    sql_statement: Optional[str] = None
    affected_rows: Optional[int] = None
    files_before: Optional[int] = None
    files_after: Optional[int] = None
    hdfs_stats: Optional[Dict[str, Any]] = None
    yarn_application_id: Optional[str] = None

class MergeTaskLogger:
    """合并任务详尽日志记录器"""
    
    def __init__(self, task: MergeTask, db_session: Session):
        self.task = task
        self.db_session = db_session
        self.logger = logging.getLogger(f"merge_task_{task.id}")
        
        # 创建任务专用的日志处理器
        self.setup_task_logger()
        
        # 记录任务开始
        self.phase_start_times = {}
        self.log_entries: List[MergeLogEntry] = []
        
        # 记录任务开始
        self.log_task_start()
    
    def setup_task_logger(self):
        """设置任务专用的日志处理器"""
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - TASK[%(name)s] - %(levelname)s - %(message)s'
        )
        
        # 创建文件处理器
        log_filename = f"/tmp/merge_task_{self.task.id}_{int(time.time())}.log"
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # 添加到日志器
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.DEBUG)
        
        # 记录日志文件路径
        self.log_file_path = log_filename
    
    def log_task_start(self):
        """记录任务开始"""
        self.log(
            phase=MergePhase.INITIALIZATION,
            level=MergeLogLevel.INFO,
            message="合并任务开始执行",
            details={
                "cluster_id": self.task.cluster_id,
                "database_name": self.task.database_name,
                "table_name": self.task.table_name,
                "partition_filter": self.task.partition_filter,
                "merge_strategy": self.task.merge_strategy,
                "created_by": getattr(self.task, 'created_by', 'system'),
                "priority": getattr(self.task, 'priority', 'normal')
            }
        )
    
    def start_phase(self, phase: MergePhase, message: str, details: Dict[str, Any] = None):
        """开始执行阶段"""
        self.phase_start_times[phase.value] = time.time()
        
        self.log(
            phase=phase,
            level=MergeLogLevel.INFO,
            message=f"开始阶段: {message}",
            details=details or {}
        )
    
    def end_phase(self, phase: MergePhase, message: str, success: bool = True, 
                  details: Dict[str, Any] = None):
        """结束执行阶段"""
        start_time = self.phase_start_times.get(phase.value)
        duration_ms = None
        
        if start_time:
            duration_ms = int((time.time() - start_time) * 1000)
        
        level = MergeLogLevel.INFO if success else MergeLogLevel.ERROR
        status = "完成" if success else "失败"
        
        self.log(
            phase=phase,
            level=level,
            message=f"阶段{status}: {message}",
            details=details or {},
            duration_ms=duration_ms
        )
    
    def log(self, phase: MergePhase, level: MergeLogLevel, message: str,
            details: Dict[str, Any] = None, duration_ms: Optional[int] = None,
            sql_statement: Optional[str] = None, affected_rows: Optional[int] = None,
            files_before: Optional[int] = None, files_after: Optional[int] = None,
            hdfs_stats: Optional[Dict[str, Any]] = None, 
            yarn_application_id: Optional[str] = None):
        """记录详细日志"""
        
        # 创建日志条目
        log_entry = MergeLogEntry(
            timestamp=datetime.now().isoformat(),
            task_id=self.task.id,
            phase=phase.value,
            level=level.value,
            message=message,
            details=details or {},
            duration_ms=duration_ms,
            sql_statement=sql_statement,
            affected_rows=affected_rows,
            files_before=files_before,
            files_after=files_after,
            hdfs_stats=hdfs_stats,
            yarn_application_id=yarn_application_id
        )
        
        # 添加到日志条目列表
        self.log_entries.append(log_entry)
        
        # 写入Python日志系统
        log_message = self._format_log_message(log_entry)
        
        if level == MergeLogLevel.DEBUG:
            self.logger.debug(log_message)
        elif level == MergeLogLevel.INFO:
            self.logger.info(log_message)
        elif level == MergeLogLevel.WARNING:
            self.logger.warning(log_message)
        elif level == MergeLogLevel.ERROR:
            self.logger.error(log_message)
        elif level == MergeLogLevel.CRITICAL:
            self.logger.critical(log_message)
        
        # 保存到数据库
        self._save_to_database(log_entry)
    
    def log_sql_execution(self, sql_statement: str, phase: MergePhase, 
                         affected_rows: Optional[int] = None, 
                         success: bool = True, error_message: str = None):
        """记录SQL执行详情"""
        level = MergeLogLevel.INFO if success else MergeLogLevel.ERROR
        message = f"SQL执行{'成功' if success else '失败'}: {sql_statement[:100]}..."
        
        details = {
            "full_sql": sql_statement,
            "sql_length": len(sql_statement),
            "execution_success": success
        }
        
        if error_message:
            details["error_message"] = error_message
        
        self.log(
            phase=phase,
            level=level,
            message=message,
            details=details,
            sql_statement=sql_statement,
            affected_rows=affected_rows
        )
    
    def log_hdfs_operation(self, operation: str, path: str, phase: MergePhase,
                          stats: Dict[str, Any] = None, success: bool = True,
                          error_message: str = None):
        """记录HDFS操作详情"""
        level = MergeLogLevel.INFO if success else MergeLogLevel.ERROR
        message = f"HDFS操作{'成功' if success else '失败'}: {operation} - {path}"
        
        details = {
            "hdfs_operation": operation,
            "hdfs_path": path,
            "operation_success": success
        }
        
        if error_message:
            details["error_message"] = error_message
        
        self.log(
            phase=phase,
            level=level,
            message=message,
            details=details,
            hdfs_stats=stats
        )
    
    def log_yarn_monitoring(self, application_id: str, phase: MergePhase,
                           progress: float = None, state: str = None,
                           details: Dict[str, Any] = None):
        """记录YARN任务监控详情"""
        message = f"YARN任务监控: {application_id}"
        if progress is not None:
            message += f" - 进度: {progress}%"
        if state:
            message += f" - 状态: {state}"
        
        yarn_details = {
            "yarn_application_id": application_id,
            "yarn_progress": progress,
            "yarn_state": state
        }
        
        if details:
            yarn_details.update(details)
        
        self.log(
            phase=phase,
            level=MergeLogLevel.INFO,
            message=message,
            details=yarn_details,
            yarn_application_id=application_id
        )
    
    def log_file_statistics(self, phase: MergePhase, table_name: str,
                           files_before: int = None, files_after: int = None,
                           hdfs_stats: Dict[str, Any] = None):
        """记录文件统计信息"""
        message = f"文件统计 - 表: {table_name}"
        if files_before is not None:
            message += f" - 合并前: {files_before}个文件"
        if files_after is not None:
            message += f" - 合并后: {files_after}个文件"
        
        details = {
            "table_name": table_name,
            "files_before": files_before,
            "files_after": files_after
        }
        
        if hdfs_stats:
            details.update(hdfs_stats)
        
        self.log(
            phase=phase,
            level=MergeLogLevel.INFO,
            message=message,
            details=details,
            files_before=files_before,
            files_after=files_after,
            hdfs_stats=hdfs_stats
        )
    
    def log_data_validation(self, phase: MergePhase, validation_type: str,
                           original_count: int, new_count: int, success: bool,
                           details: Dict[str, Any] = None):
        """记录数据验证结果"""
        level = MergeLogLevel.INFO if success else MergeLogLevel.ERROR
        message = f"数据验证 - {validation_type}: 原始={original_count}, 新={new_count}, {'通过' if success else '失败'}"
        
        validation_details = {
            "validation_type": validation_type,
            "original_count": original_count,
            "new_count": new_count,
            "validation_success": success,
            "count_match": original_count == new_count
        }
        
        if details:
            validation_details.update(details)
        
        self.log(
            phase=phase,
            level=level,
            message=message,
            details=validation_details
        )
    
    def log_task_completion(self, success: bool, total_duration_ms: int,
                           final_stats: Dict[str, Any] = None):
        """记录任务完成"""
        level = MergeLogLevel.INFO if success else MergeLogLevel.ERROR
        status = "成功完成" if success else "执行失败"
        message = f"合并任务{status} - 总耗时: {total_duration_ms}ms"
        
        details = {
            "task_success": success,
            "total_duration_ms": total_duration_ms,
            "total_log_entries": len(self.log_entries)
        }
        
        if final_stats:
            details.update(final_stats)
        
        self.log(
            phase=MergePhase.COMPLETION,
            level=level,
            message=message,
            details=details,
            duration_ms=total_duration_ms
        )
    
    def get_log_summary(self) -> Dict[str, Any]:
        """获取日志摘要"""
        phase_stats = {}
        error_count = 0
        warning_count = 0
        
        for entry in self.log_entries:
            # 统计各阶段
            if entry.phase not in phase_stats:
                phase_stats[entry.phase] = {"count": 0, "duration_ms": 0}
            
            phase_stats[entry.phase]["count"] += 1
            if entry.duration_ms:
                phase_stats[entry.phase]["duration_ms"] += entry.duration_ms
            
            # 统计错误和警告
            if entry.level == MergeLogLevel.ERROR.value:
                error_count += 1
            elif entry.level == MergeLogLevel.WARNING.value:
                warning_count += 1
        
        return {
            "task_id": self.task.id,
            "total_entries": len(self.log_entries),
            "error_count": error_count,
            "warning_count": warning_count,
            "phase_statistics": phase_stats,
            "log_file_path": self.log_file_path
        }
    
    def export_logs_to_json(self) -> str:
        """导出日志到JSON格式"""
        logs_data = {
            "task_info": {
                "id": self.task.id,
                "cluster_id": self.task.cluster_id,
                "database_name": self.task.database_name,
                "table_name": self.task.table_name,
                "created_at": self.task.created_time.isoformat() if self.task.created_time else None
            },
            "log_entries": [asdict(entry) for entry in self.log_entries],
            "summary": self.get_log_summary()
        }
        
        return json.dumps(logs_data, indent=2, ensure_ascii=False)
    
    def _format_log_message(self, entry: MergeLogEntry) -> str:
        """格式化日志消息"""
        message = f"[{entry.phase.upper()}] {entry.message}"
        
        if entry.details:
            # 只显示关键详情，避免日志过于冗长
            key_details = []
            for key in ["duration_ms", "affected_rows", "files_before", "files_after"]:
                if key in entry.details and entry.details[key] is not None:
                    key_details.append(f"{key}={entry.details[key]}")
            
            if key_details:
                message += f" ({', '.join(key_details)})"
        
        return message
    
    def _save_to_database(self, entry: MergeLogEntry):
        """保存日志条目到数据库"""
        try:
            # 导入TaskLog模型
            from app.models.task_log import TaskLog
            import json
            
            # 创建数据库日志条目
            task_log = TaskLog(
                task_id=entry.task_id,
                log_level=entry.level,
                message=entry.message,
                details=json.dumps(entry.details, ensure_ascii=False) if entry.details else None,
                phase=entry.phase,
                duration_ms=entry.duration_ms,
                sql_statement=entry.sql_statement,
                affected_rows=entry.affected_rows,
                files_before=entry.files_before,
                files_after=entry.files_after,
                hdfs_stats=json.dumps(entry.hdfs_stats, ensure_ascii=False) if entry.hdfs_stats else None,
                yarn_application_id=entry.yarn_application_id,
                progress_percentage=None  # 可以从details中提取
            )
            
            # 添加到数据库会话
            self.db_session.add(task_log)
            self.db_session.commit()
            
        except Exception as e:
            # 日志保存失败不应该影响主要流程
            self.logger.error(f"Failed to save log entry to database: {e}")
            # 回滚以保持会话状态
            self.db_session.rollback()


# 测试函数
if __name__ == "__main__":
    # 测试合并任务日志记录器
    from app.models.merge_task import MergeTask
    from app.models.cluster import Cluster
    
    # 创建测试任务
    cluster = Cluster(id=1, name="test-cluster")
    task = MergeTask(
        id=1,
        cluster_id=1,
        cluster=cluster,
        database_name="test_db",
        table_name="test_table",
        merge_strategy="safe_merge"
    )
    
    # 创建日志记录器（模拟Session）
    logger = MergeTaskLogger(task, None)
    
    # 模拟合并过程的日志记录
    logger.start_phase(MergePhase.CONNECTION_TEST, "测试数据库连接")
    time.sleep(0.1)
    logger.end_phase(MergePhase.CONNECTION_TEST, "连接测试完成", success=True)
    
    logger.log_sql_execution(
        "CREATE TABLE temp_table AS SELECT * FROM original_table",
        MergePhase.TEMP_TABLE_CREATION,
        affected_rows=1000000,
        success=True
    )
    
    logger.log_file_statistics(
        MergePhase.FILE_ANALYSIS,
        "test_table",
        files_before=500,
        files_after=10,
        hdfs_stats={"total_size": 1024*1024*1024, "small_files_count": 450}
    )
    
    logger.log_task_completion(True, 30000, {"files_saved": 490})
    
    # 输出日志摘要
    print("日志摘要:")
    print(json.dumps(logger.get_log_summary(), indent=2, ensure_ascii=False))
    
    # 导出JSON日志
    json_logs = logger.export_logs_to_json()
    print("\n导出的JSON日志:")
    print(json_logs[:500] + "..." if len(json_logs) > 500 else json_logs)