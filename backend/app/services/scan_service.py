import re
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.models.cluster import Cluster
from app.models.scan_task import ScanTask
from app.monitor.hybrid_table_scanner import HybridTableScanner
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.schemas.scan_task import ScanTaskLog


class ScanTaskManager:
    """扫描任务管理器，支持进度追踪和日志记录"""

    def __init__(self):
        self.active_tasks: Dict[str, ScanTask] = {}
        self.task_logs: Dict[str, List[ScanTaskLog]] = {}
        self._lock = threading.Lock()
        self._cancelled: set[str] = set()

    def create_scan_task(
        self,
        db: Session,
        cluster_id: int,
        task_type: str,
        task_name: str,
        target_database: Optional[str] = None,
        target_table: Optional[str] = None,
    ) -> ScanTask:
        """创建扫描任务"""
        task = ScanTask(
            cluster_id=cluster_id,
            task_type=task_type,
            task_name=task_name,
            status="pending",
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        with self._lock:
            self.active_tasks[task.task_id] = task
            self.task_logs[task.task_id] = []

        return task

    def get_task(self, task_id: str) -> Optional[ScanTask]:
        """获取任务状态"""
        with self._lock:
            return self.active_tasks.get(task_id)

    def get_task_logs(self, task_id: str) -> List[ScanTaskLog]:
        """获取任务日志"""
        with self._lock:
            logs = self.task_logs.get(task_id, [])
            # 兜底清洗，保证历史内存日志不含图标符号
            cleaned: List[ScanTaskLog] = []
            for le in logs:
                try:
                    cleaned.append(
                        ScanTaskLog(
                            timestamp=le.timestamp,
                            level=le.level,
                            message=_sanitize_log_text(le.message),
                            database_name=le.database_name,
                            table_name=le.table_name,
                        )
                    )
                except Exception:
                    cleaned.append(le)
            return cleaned

    def request_cancel(self, db: Session, task_id: str) -> bool:
        """请求取消任务：设置标记并记录日志"""
        with self._lock:
            self._cancelled.add(task_id)
        try:
            self.add_log(task_id, "INFO", "收到取消请求，正在停止扫描…", db=db)
        except Exception:
            pass
        return True

    def _is_cancelled(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._cancelled

    def _cleanup_task(self, task_id: str):
        with self._lock:
            self.active_tasks.pop(task_id, None)
            self.task_logs.pop(task_id, None)
            self._cancelled.discard(task_id)

    def add_log(
        self,
        task_id: str,
        level: str,
        message: str,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
        db: Optional[Session] = None,
    ):
        """添加任务日志（内存 + 可选持久化）"""
        # 移除表情/图标，满足“日志中不出现图标符号”的要求
        message_clean = _sanitize_log_text(message)
        log_entry = ScanTaskLog(
            timestamp=datetime.utcnow(),
            level=level,
            message=message_clean,
            database_name=database_name,
            table_name=table_name,
        )

        with self._lock:
            if task_id in self.task_logs:
                self.task_logs[task_id].append(log_entry)
                # 只保留最近100条日志
                if len(self.task_logs[task_id]) > 100:
                    self.task_logs[task_id] = self.task_logs[task_id][-100:]

        # 可选持久化到数据库
        if db is not None:
            try:
                from app.models.scan_task import ScanTask as ScanTaskModel
                from app.models.scan_task_log import ScanTaskLogDB

                db_task = (
                    db.query(ScanTaskModel)
                    .filter(ScanTaskModel.task_id == task_id)
                    .first()
                )
                if db_task:
                    db_row = ScanTaskLogDB(
                        scan_task_id=db_task.id,
                        level=level,
                        message=message_clean,
                        database_name=database_name,
                        table_name=table_name,
                        # 使用与内存日志相同的时间，避免“内存 + 持久化”合并时出现重复
                        timestamp=log_entry.timestamp,
                    )
                    db.add(db_row)
                    db.commit()
            except Exception:
                # 持久化失败不影响主流程
                pass

    # ---- Structured logging helpers (no emoji, consistent format) ----
    def _format_msg(
        self,
        code: str,
        title: str,
        phase: Optional[str] = None,
        ctx: Optional[Dict[str, object]] = None,
    ) -> str:
        parts = []
        if phase:
            parts.append(f"[{phase.upper()}]")
        if code:
            parts.append(code)
        parts.append(title)
        if ctx:
            kv = " ".join(f"{k}={v}" for k, v in ctx.items() if v is not None)
            if kv:
                parts.append(kv)
        return " ".join(parts)

    def info(
        self,
        task_id: str,
        code: str,
        title: str,
        db: Optional[Session] = None,
        phase: Optional[str] = None,
        ctx: Optional[Dict[str, object]] = None,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
    ):
        self.add_log(
            task_id,
            "INFO",
            self._format_msg(code, title, phase, ctx),
            database_name=database_name,
            table_name=table_name,
            db=db,
        )

    def warn(
        self,
        task_id: str,
        code: str,
        title: str,
        db: Optional[Session] = None,
        phase: Optional[str] = None,
        ctx: Optional[Dict[str, object]] = None,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
    ):
        self.add_log(
            task_id,
            "WARN",
            self._format_msg(code, title, phase, ctx),
            database_name=database_name,
            table_name=table_name,
            db=db,
        )

    def error(
        self,
        task_id: str,
        code: str,
        title: str,
        db: Optional[Session] = None,
        phase: Optional[str] = None,
        ctx: Optional[Dict[str, object]] = None,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
    ):
        self.add_log(
            task_id,
            "ERROR",
            self._format_msg(code, title, phase, ctx),
            database_name=database_name,
            table_name=table_name,
            db=db,
        )

    def update_task_progress(
        self,
        db: Session,
        task_id: str,
        completed_items: int = None,
        current_item: str = None,
        total_items: int = None,
        status: str = None,
        error_message: str = None,
        total_tables_scanned: int = None,
        total_files_found: int = None,
        total_small_files: int = None,
        estimated_remaining_seconds: int = None,
    ):
        """更新任务进度"""
        with self._lock:
            task = self.active_tasks.get(task_id)
            if not task:
                return

            if completed_items is not None:
                task.completed_items = completed_items
            if current_item is not None:
                task.current_item = current_item
            if total_items is not None:
                task.total_items = total_items
            if status is not None:
                task.status = status
            if error_message is not None:
                task.error_message = error_message
            if total_tables_scanned is not None:
                task.total_tables_scanned = total_tables_scanned
            if total_files_found is not None:
                task.total_files_found = total_files_found
            if total_small_files is not None:
                task.total_small_files = total_small_files

            # 更新数据库
            db_task = db.query(ScanTask).filter(ScanTask.task_id == task_id).first()
            if db_task:
                for key, value in task.__dict__.items():
                    if not key.startswith("_") and value is not None:
                        setattr(db_task, key, value)
                db.commit()

    def safe_update_progress(self, db: Session, task_id: str, **kwargs):
        """安全更新进度：
        - 仅透传已支持字段
        - 忽略未知字段并记录 WARN 日志
        - 任意异常将被捕获并记录，不中断主流程
        """
        allowed = {
            "completed_items",
            "current_item",
            "total_items",
            "status",
            "error_message",
            "total_tables_scanned",
            "total_files_found",
            "total_small_files",
            "estimated_remaining_seconds",
        }
        passed = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        ignored = [k for k in kwargs.keys() if k not in allowed]
        if ignored:
            try:
                self.add_log(
                    task_id,
                    "WARN",
                    f"safe_update_progress 忽略未知字段: {ignored}",
                    db=db,
                )
            except Exception:
                pass
        try:
            return self.update_task_progress(db, task_id, **passed)
        except Exception as e:
            try:
                self.add_log(
                    task_id, "WARN", f"safe_update_progress 更新失败: {e}", db=db
                )
            except Exception:
                pass
            return None

    def complete_task(
        self, db: Session, task_id: str, success: bool = True, error_message: str = None
    ):
        """完成任务"""
        with self._lock:
            task = self.active_tasks.get(task_id)
            if not task:
                return

            task.status = "completed" if success else "failed"
            task.end_time = datetime.utcnow()
            task.duration = (task.end_time - task.start_time).total_seconds()

            if error_message:
                task.error_message = error_message

            # 更新数据库
            db_task = db.query(ScanTask).filter(ScanTask.task_id == task_id).first()
            if db_task:
                db_task.status = task.status
                db_task.end_time = task.end_time
                db_task.duration = task.duration
                if error_message:
                    db_task.error_message = error_message
                db.commit()

    from typing import Optional

    def scan_cluster_with_progress(
        self,
        db: Session,
        cluster_id: int,
        max_tables_per_db: Optional[int] = None,
        strict_real: bool = False,
        include_cold: bool = False,
        cold_threshold_days: Optional[int] = None,
    ) -> str:
        """执行集群扫描（带进度追踪）"""
        # 获取集群信息
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise ValueError("Cluster not found")

        # 创建任务
        task = self.create_scan_task(
            db, cluster_id, "cluster", f"扫描集群: {cluster.name}"
        )

        # 在后台线程中执行扫描
        def run_scan():
            # 为后台线程创建独立的数据库会话，避免跨线程复用同一 Session 导致崩溃
            db_thread = SessionLocal()
            try:
                # 重新获取 cluster 与 task，确保在该会话上下文中托管
                cluster_t = (
                    db_thread.query(Cluster).filter(Cluster.id == cluster.id).first()
                    if cluster
                    else None
                )
                task_t = (
                    db_thread.query(ScanTask).filter(ScanTask.id == task.id).first()
                    if task
                    else None
                )
                if not cluster_t or not task_t:
                    raise RuntimeError(
                        "Failed to load task/cluster in thread-local session"
                    )

                self._execute_cluster_scan(
                    db_thread,
                    task_t,
                    cluster_t,
                    max_tables_per_db,
                    strict_real,
                    include_cold=include_cold,
                    cold_threshold_days=cold_threshold_days,
                )
            except Exception as e:
                try:
                    self.add_log(
                        task.task_id, "ERROR", f"扫描失败: {str(e)}", db=db_thread
                    )
                finally:
                    self.complete_task(
                        db_thread, task.task_id, success=False, error_message=str(e)
                    )
            finally:
                try:
                    db_thread.close()
                except Exception:
                    pass
                # 清理内存引用，避免泄漏
                self._cleanup_task(task.task_id)

        thread = threading.Thread(target=run_scan)
        thread.daemon = True
        thread.start()

        return task.task_id

    def _execute_cluster_scan(
        self,
        db: Session,
        task: ScanTask,
        cluster: Cluster,
        max_tables_per_db: Optional[int],
        strict_real: bool,
        include_cold: bool = False,
        cold_threshold_days: Optional[int] = None,
    ):
        """执行实际的集群扫描"""
        scan_start_time = time.time()
        self.info(
            task.task_id,
            "S001",
            "开始扫描集群",
            db=db,
            phase="init",
            ctx={"cluster": cluster.name},
        )
        self.safe_update_progress(db, task.task_id, status="running")

        try:
            # 步骤1: 测试连接
            self.info(
                task.task_id,
                "S101",
                "正在连接 MetaStore",
                db=db,
                phase="connect",
                ctx={"url": cluster.hive_metastore_url},
            )

            # 获取所有数据库
            databases = []
            metastore_connect_start = time.time()
            try:
                with MySQLHiveMetastoreConnector(
                    cluster.hive_metastore_url
                ) as connector:
                    databases = connector.get_databases()
                metastore_connect_time = time.time() - metastore_connect_start
                self.info(
                    task.task_id,
                    "S102",
                    "MetaStore 连接成功",
                    db=db,
                    phase="connect",
                    ctx={
                        "elapsed_s": f"{metastore_connect_time:.2f}",
                        "databases": len(databases),
                    },
                )
                if databases:
                    preview = ", ".join(databases[:5]) + (
                        "..." if len(databases) > 5 else ""
                    )
                    self.info(
                        task.task_id,
                        "S103",
                        "数据库列表",
                        db=db,
                        phase="connect",
                        ctx={"top": preview},
                    )
            except Exception as conn_error:
                self.error(
                    task.task_id,
                    "E101",
                    f"MetaStore 连接失败: {str(conn_error)}",
                    db=db,
                    phase="connect",
                )
                self.info(
                    task.task_id,
                    "H101",
                    "建议检查",
                    db=db,
                    phase="diagnose",
                    ctx={"1": "网络连通性", "2": "数据库服务状态", "3": "用户权限"},
                )
                raise conn_error

            # 步骤2: 初始化扫描器和HDFS连接
            self.info(
                task.task_id,
                "S110",
                "正在连接 HDFS",
                db=db,
                phase="connect",
                ctx={"url": cluster.hdfs_namenode_url},
            )
            scanner = HybridTableScanner(cluster)
            hdfs_connect_start = time.time()

            # 测试HDFS连接
            scanner._initialize_hdfs_scanner()
            hdfs_ok = False
            try:
                hdfs_ok = (
                    scanner.hdfs_scanner.connect() if scanner.hdfs_scanner else False
                )
                hdfs_connect_time = time.time() - hdfs_connect_start
                if hdfs_ok:
                    self.info(
                        task.task_id,
                        "S111",
                        "HDFS 连接成功",
                        db=db,
                        phase="connect",
                        ctx={"elapsed_s": f"{hdfs_connect_time:.2f}"},
                    )
                    scanner.hdfs_scanner.disconnect()
                else:
                    if strict_real:
                        raise Exception("HDFS连接失败（严格模式），中止扫描")
                    self.warn(
                        task.task_id,
                        "W110",
                        "HDFS 连接失败，启用 Mock 模式",
                        db=db,
                        phase="connect",
                    )
            except Exception as hdfs_error:
                if strict_real:
                    raise
                self.warn(
                    task.task_id,
                    "W111",
                    f"HDFS 连接失败: {str(hdfs_error)}",
                    db=db,
                    phase="connect",
                )
                self.info(
                    task.task_id,
                    "S112",
                    "启用 Mock HDFS 模式进行演示扫描",
                    db=db,
                    phase="connect",
                )

            # 步骤3: 开始批量扫描
            self.safe_update_progress(db, task.task_id, total_items=len(databases))
            estimated_total_time = len(databases) * 3  # 估算每个数据库3秒
            self.info(
                task.task_id,
                "S120",
                "预计总扫描时间",
                db=db,
                phase="plan",
                ctx={
                    "seconds": estimated_total_time,
                    "max_tables_per_db": max_tables_per_db,
                },
            )

            total_tables_scanned = 0
            total_files_found = 0
            total_small_files = 0
            successful_databases = 0
            failed_databases = 0

            # 扫描每个数据库
            for i, database_name in enumerate(databases, 1):
                # 支持随时取消
                if self._is_cancelled(task.task_id):
                    self.info(
                        task.task_id,
                        "S890",
                        "用户取消，停止后续数据库扫描",
                        db=db,
                        phase="cancel",
                    )
                    self.complete_task(
                        db,
                        task.task_id,
                        success=False,
                        error_message="Task cancelled by user",
                    )
                    return
                db_scan_start = time.time()
                self.safe_update_progress(
                    db,
                    task.task_id,
                    completed_items=i - 1,
                    current_item=f"扫描数据库: {database_name}",
                )
                self.info(
                    task.task_id,
                    "S201",
                    "开始扫描数据库",
                    db=db,
                    phase="scan",
                    ctx={"index": f"{i}/{len(databases)}", "database": database_name},
                    database_name=database_name,
                )

                try:
                    # 扫描数据库中的表
                    result = scanner.scan_database_tables(
                        db,
                        database_name,
                        max_tables=max_tables_per_db,
                        strict_real=strict_real,
                    )
                    db_scan_time = time.time() - db_scan_start

                    tables_scanned = result.get("tables_scanned", 0)
                    files_found = result.get("total_files", 0)
                    small_files = result.get("total_small_files", 0)
                    successful_tables = result.get("successful_tables", 0)
                    failed_tables = result.get("failed_tables", 0)
                    partitioned_tables = result.get("partitioned_tables", 0)
                    hdfs_mode = result.get("hdfs_mode", "unknown")
                    scan_errors = result.get("errors", [])
                    metastore_time = result.get("metastore_query_time", 0)
                    hdfs_connect_time = result.get("hdfs_connect_time", 0)
                    original_table_count = result.get("original_table_count", 0)
                    filtered_table_count = result.get("filtered_table_count", 0)
                    limited_by_count = result.get("limited_by_count", 0)
                    avg_table_scan_time = result.get("avg_table_scan_time", 0)

                    total_tables_scanned += tables_scanned
                    total_files_found += files_found
                    total_small_files += small_files

                    # 记录详细的扫描过程信息（结构化、无前缀符号）
                    self.info(
                        task.task_id,
                        "S204",
                        "MetaStore 查询",
                        db=db,
                        phase="scan",
                        ctx={
                            "elapsed_s": f"{metastore_time:.2f}",
                            "tables_found": original_table_count,
                        },
                        database_name=database_name,
                    )
                    if limited_by_count > 0:
                        self.info(
                            task.task_id,
                            "S205",
                            "表数量限制",
                            db=db,
                            phase="scan",
                            ctx={
                                "skipped": limited_by_count,
                                "max_tables_per_db": max_tables_per_db,
                            },
                            database_name=database_name,
                        )
                    if hdfs_mode != "real":
                        self.info(
                            task.task_id,
                            "S206",
                            "HDFS 连接",
                            db=db,
                            phase="scan",
                            ctx={
                                "elapsed_s": f"{hdfs_connect_time:.2f}",
                                "mode": hdfs_mode,
                            },
                            database_name=database_name,
                        )

                    # 计算小文件比例
                    small_file_ratio = (
                        (small_files / files_found * 100) if files_found > 0 else 0
                    )

                    # 生成详细的完成日志
                    status_parts = []
                    if successful_tables > 0:
                        status_parts.append(f"{successful_tables}表成功")
                    if failed_tables > 0:
                        status_parts.append(f"{failed_tables}表失败")
                    if partitioned_tables > 0:
                        status_parts.append(f"{partitioned_tables}个分区表")

                    log_message = f'数据库 {database_name} 扫描完成: {", ".join(status_parts)}, {files_found}文件, {small_files}小文件'
                    if files_found > 0:
                        log_message += f" ({small_file_ratio:.1f}%)"

                    if hdfs_mode == "mock":
                        log_message += " [Mock模式]"

                    log_message += f" (耗时: {db_scan_time:.1f}秒, 平均{avg_table_scan_time:.2f}秒/表)"

                    # 使用统一格式输出概要
                    self.info(
                        task.task_id,
                        "S202",
                        "数据库扫描完成",
                        db=db,
                        phase="scan",
                        ctx={
                            "database": database_name,
                            "tables": tables_scanned,
                            "files": files_found,
                            "small_files": small_files,
                            "ratio_pct": f"{small_file_ratio:.1f}",
                            "elapsed_s": f"{db_scan_time:.1f}",
                            "avg_per_table_s": f"{avg_table_scan_time:.2f}",
                            "mode": hdfs_mode,
                        },
                        database_name=database_name,
                    )

                    # 记录重要的警告和错误（过滤掉不重要的）
                    important_errors = [
                        e
                        for e in scan_errors
                        if any(
                            keyword in e
                            for keyword in ["失败", "错误", "过高", "Error", "Failed"]
                        )
                    ]
                    for error in important_errors[:3]:  # 只显示前3个重要错误
                        if "小文件比例过高" in error:
                            self.warn(
                                task.task_id,
                                "W201",
                                error,
                                database_name=database_name,
                                db=db,
                                phase="scan",
                            )
                        else:
                            self.error(
                                task.task_id,
                                "E201",
                                error,
                                database_name=database_name,
                                db=db,
                                phase="scan",
                            )

                    # 更新进度和剩余时间估算
                    remaining_dbs = len(databases) - i
                    avg_time_per_db = (time.time() - scan_start_time) / i
                    estimated_remaining = remaining_dbs * avg_time_per_db

                    self.safe_update_progress(
                        db,
                        task.task_id,
                        completed_items=i,
                        estimated_remaining_seconds=int(estimated_remaining),
                    )
                    # 确认该数据库扫描成功
                    successful_databases += 1

                except Exception as db_error:
                    failed_databases += 1
                    db_scan_time = time.time() - db_scan_start
                    self.error(
                        task.task_id,
                        "E202",
                        f"数据库扫描失败: {str(db_error)}",
                        database_name=database_name,
                        db=db,
                        phase="scan",
                        ctx={
                            "elapsed_s": f"{db_scan_time:.1f}",
                            "database": database_name,
                        },
                    )
                    # 提供具体的错误诊断建议
                    if "permission" in str(db_error).lower():
                        self.add_log(
                            task.task_id,
                            "INFO",
                            f"  💡 建议检查HDFS用户权限和访问策略",
                            database_name=database_name,
                            db=db,
                        )
                    elif "connection" in str(db_error).lower():
                        self.add_log(
                            task.task_id,
                            "INFO",
                            f"  💡 建议检查网络连通性和服务状态",
                            database_name=database_name,
                            db=db,
                        )

            # 最终统计和性能指标
            total_scan_time = time.time() - scan_start_time
            success_rate = (
                (successful_databases / len(databases)) * 100 if databases else 0
            )
            avg_time_per_db = total_scan_time / len(databases) if databases else 0
            avg_time_per_table = (
                total_scan_time / total_tables_scanned if total_tables_scanned else 0
            )

            self.safe_update_progress(
                db,
                task.task_id,
                completed_items=len(databases),
                total_tables_scanned=total_tables_scanned,
                total_files_found=total_files_found,
                total_small_files=total_small_files,
            )

            # 可选：追加冷数据扫描
            if include_cold:
                try:
                    threshold = (
                        cold_threshold_days
                        if isinstance(cold_threshold_days, int)
                        else 90
                    )
                    self.info(
                        task.task_id,
                        "S310",
                        "开始冷数据扫描",
                        db=db,
                        phase="scan",
                        ctx={"threshold_days": threshold},
                    )
                    # 复用 scanner 执行冷数据扫描
                    cold_result = scanner.scan_cold_data_for_cluster(db, threshold)
                    if isinstance(cold_result, dict) and "error" in cold_result:
                        self.error(
                            task.task_id,
                            "E310",
                            f"冷数据扫描失败: {cold_result.get('error')}",
                            db=db,
                            phase="scan",
                        )
                    else:
                        cold_count = (
                            cold_result.get("cold_tables_found")
                            if isinstance(cold_result, dict)
                            else None
                        )
                        self.info(
                            task.task_id,
                            "S311",
                            "冷数据扫描完成",
                            db=db,
                            phase="scan",
                            ctx={
                                "cold_tables_found": cold_count,
                                "threshold_days": threshold,
                            },
                        )
                except Exception as ce:
                    self.error(
                        task.task_id,
                        "E311",
                        f"冷数据扫描异常: {ce}",
                        db=db,
                        phase="scan",
                    )

            # 生成详细的完成报告
            overall_small_file_ratio = (
                (total_small_files / total_files_found * 100)
                if total_files_found > 0
                else 0
            )
            self.info(
                task.task_id,
                "S900",
                "集群扫描完成",
                db=db,
                phase="complete",
                ctx={
                    "tables": total_tables_scanned,
                    "files": total_files_found,
                    "small_files": total_small_files,
                    "small_ratio_pct": f"{overall_small_file_ratio:.1f}",
                },
            )

            # 性能统计
            self.info(
                task.task_id,
                "S901",
                "扫描统计",
                db=db,
                phase="complete",
                ctx={
                    "elapsed_s": f"{total_scan_time:.1f}",
                    "success_rate_pct": f"{success_rate:.1f}",
                    "avg_per_table_s": f"{avg_time_per_table:.2f}",
                },
            )
            self.info(
                task.task_id,
                "S902",
                "处理效率",
                db=db,
                phase="complete",
                ctx={
                    "databases_success": successful_databases,
                    "databases_failed": failed_databases,
                },
            )

            # 根据结果给出建议
            if overall_small_file_ratio > 70:
                self.warn(
                    task.task_id,
                    "W210",
                    f"小文件比例过高({overall_small_file_ratio:.1f}%)，建议执行合并优化",
                    db=db,
                    phase="advice",
                )
            elif overall_small_file_ratio > 50:
                self.info(
                    task.task_id,
                    "H201",
                    "建议对小文件比例较高的表进行合并处理",
                    db=db,
                    phase="advice",
                )

            self.complete_task(db, task.task_id, success=True)

        except Exception as e:
            total_scan_time = time.time() - scan_start_time
            error_msg = str(e)
            self.error(
                task.task_id,
                "E900",
                f"集群扫描失败: {error_msg}",
                db=db,
                phase="error",
                ctx={"elapsed_s": f"{total_scan_time:.1f}"},
            )

            # 根据错误类型提供具体建议
            if "Failed to connect to MetaStore" in error_msg:
                self.info(
                    task.task_id,
                    "H102",
                    "MetaStore 连接问题排查",
                    db=db,
                    phase="diagnose",
                )
                self.info(
                    task.task_id,
                    "H103",
                    f"检查网络连通性: ping {cluster.hive_metastore_url}",
                    db=db,
                    phase="diagnose",
                )
                self.info(
                    task.task_id,
                    "H104",
                    "验证数据库服务状态和端口开放",
                    db=db,
                    phase="diagnose",
                )
                self.info(
                    task.task_id,
                    "H105",
                    "确认用户名密码和数据库权限",
                    db=db,
                    phase="diagnose",
                )
            elif "timeout" in error_msg.lower():
                self.info(
                    task.task_id,
                    "H110",
                    "连接超时问题可能原因",
                    db=db,
                    phase="diagnose",
                )
                self.info(
                    task.task_id,
                    "H111",
                    "网络延迟过高或防火墙阻挡",
                    db=db,
                    phase="diagnose",
                )
                self.info(
                    task.task_id,
                    "H112",
                    "目标服务过载或响应缓慢",
                    db=db,
                    phase="diagnose",
                )

            self.complete_task(db, task.task_id, success=False, error_message=error_msg)


# 全局任务管理器实例
scan_task_manager = ScanTaskManager()

# ---------------- internal helpers ----------------
# Emoji/符号清洗：
#  - U+1F300–U+1FAFF (补充符号与图形等)
#  - U+2600–U+26FF (杂项符号)
#  - U+2700–U+27BF (装饰符)
# 以及常见组合符：变体选择符 U+FE0F、零宽连接符 U+200D、键帽 U+20E3
_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]"
)
_COMBINERS_RE = re.compile(r"[\u200D\uFE0F\u20E3]")


def _sanitize_log_text(text: str) -> str:
    try:
        if not isinstance(text, str):
            text = str(text)
        s = _EMOJI_RE.sub("", text)
        s = _COMBINERS_RE.sub("", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s
    except Exception:
        # 避免清洗异常影响主流程
        return text
