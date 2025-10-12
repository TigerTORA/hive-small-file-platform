"""
Hive原子交换管理器
负责表的原子性切换、回滚等操作
"""

import logging
import socket
import threading
import time
from typing import Any, Dict, List, Optional

from pyhive import hive
from sqlalchemy.orm import Session

from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.utils.merge_logger import MergeLogLevel, MergePhase, MergeTaskLogger
from app.utils.webhdfs_client import WebHDFSClient
from app.utils.yarn_monitor import YarnResourceManagerMonitor

logger = logging.getLogger(__name__)


class HiveAtomicSwapManager:
    """Hive原子交换管理器,负责表的原子性切换操作"""

    def __init__(
        self,
        cluster: Cluster,
        webhdfs_client: WebHDFSClient,
        yarn_monitor: Optional[YarnResourceManagerMonitor] = None,
        hive_password: Optional[str] = None,
        extract_error_detail_func=None,
        update_task_progress_func=None,
    ):
        """
        初始化原子交换管理器

        Args:
            cluster: 集群配置对象
            webhdfs_client: WebHDFS客户端实例
            yarn_monitor: YARN资源监控器(可选)
            hive_password: 解密后的Hive密码(可选)
            extract_error_detail_func: 错误提取函数
            update_task_progress_func: 任务进度更新函数
        """
        self.cluster = cluster
        self.webhdfs_client = webhdfs_client
        self.yarn_monitor = yarn_monitor
        self.hive_password = hive_password
        self._extract_error_detail = extract_error_detail_func
        self._update_task_progress = update_task_progress_func

    def _create_hive_connection(self, database_name: str = None):
        """创建Hive连接(支持LDAP认证)"""
        hive_conn_params = {
            "host": self.cluster.hive_host,
            "port": self.cluster.hive_port,
            "database": database_name or self.cluster.hive_database or "default",
        }

        if self.cluster.auth_type == "LDAP" and self.cluster.hive_username:
            hive_conn_params["username"] = self.cluster.hive_username
            if self.hive_password:
                hive_conn_params["password"] = self.hive_password
            hive_conn_params["auth"] = "LDAP"

        return hive.Connection(**hive_conn_params)

    def _test_connections(
        self,
        *,
        merge_logger: Optional[MergeTaskLogger] = None,
        task: Optional[MergeTask] = None,
        db_session: Optional[Session] = None,
        timeout_sec: int = 10,
    ) -> bool:
        """测试连接：输出更详细的日志并增加心跳，Hive 必须成功。

        过程：
        1) WebHDFS 自检（失败仅告警）
        2) Hive TCP 探测（3s 超时）
        3) HiveServer2 连接 + SELECT 1（超时 + 心跳日志）
        """
        # 1) HDFS/HttpFS（不作为阻塞条件）
        try:
            if merge_logger:
                merge_logger.log(
                    MergePhase.CONNECTION_TEST,
                    MergeLogLevel.INFO,
                    "开始测试 WebHDFS 连接",
                    details={"namenode": self.cluster.hdfs_namenode_url},
                )
            ok, msg = self.webhdfs_client.test_connection()
            if not ok:
                logger.error(f"WebHDFS test failed: {msg}")
                if merge_logger:
                    merge_logger.log_hdfs_operation(
                        "connect",
                        self.cluster.hdfs_namenode_url,
                        MergePhase.CONNECTION_TEST,
                        success=False,
                        error_message=str(msg),
                    )
                return False
            else:
                if merge_logger:
                    merge_logger.log_hdfs_operation(
                        "connect",
                        self.cluster.hdfs_namenode_url,
                        MergePhase.CONNECTION_TEST,
                        stats={"ok": True},
                        success=True,
                    )
        except Exception as e:
            logger.error(f"WebHDFS test exception: {e}")
            if merge_logger:
                merge_logger.log(
                    MergePhase.CONNECTION_TEST,
                    MergeLogLevel.ERROR,
                    f"WebHDFS 测试异常: {e}",
                    details={"namenode": self.cluster.hdfs_namenode_url},
                )
            return False

        # 2) Hive（必须成功）
        try:
            hive_conn_params = {
                "host": self.cluster.hive_host,
                "port": self.cluster.hive_port,
                "database": self.cluster.hive_database or "default",
            }
            if (
                self.cluster.auth_type or ""
            ).upper() == "LDAP" and self.cluster.hive_username:
                hive_conn_params["username"] = self.cluster.hive_username
                if self.hive_password:
                    hive_conn_params["password"] = self.hive_password
                hive_conn_params["auth"] = "LDAP"
                logger.info(
                    f"Using LDAP authentication for user: {self.cluster.hive_username}"
                )

            # 2.1 TCP 快速探测（3s）
            if merge_logger:
                merge_logger.log(
                    MergePhase.CONNECTION_TEST,
                    MergeLogLevel.INFO,
                    f"测试 Hive TCP 连接: {hive_conn_params['host']}:{hive_conn_params['port']}",
                    details={
                        "host": hive_conn_params["host"],
                        "port": hive_conn_params["port"],
                    },
                )
            try:
                with socket.create_connection(
                    (hive_conn_params["host"], hive_conn_params["port"]), timeout=3
                ):
                    pass
            except Exception as se:
                if merge_logger:
                    merge_logger.log(
                        MergePhase.CONNECTION_TEST,
                        MergeLogLevel.ERROR,
                        f"Hive TCP 连接失败: {se}",
                        details={
                            "host": hive_conn_params["host"],
                            "port": hive_conn_params["port"],
                        },
                    )
                logger.error(f"Hive TCP connectivity failed: {se}")
                return False

            # 2.2 HS2 连接 + SELECT 1（超时 + 心跳）
            if merge_logger:
                merge_logger.start_phase(
                    MergePhase.CONNECTION_TEST, "连接 HiveServer2 并校验查询"
                )

            done_flag = {"ok": False, "err": None}

            def _connect_and_query():
                try:
                    conn = hive.Connection(**hive_conn_params)
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchall()
                    cursor.close()
                    conn.close()
                    done_flag["ok"] = True
                except Exception as ie:
                    done_flag["err"] = ie

            th = threading.Thread(target=_connect_and_query, daemon=True)
            th.start()

            waited = 0
            while th.is_alive() and waited < timeout_sec:
                if merge_logger and task and db_session:
                    merge_logger.log(
                        MergePhase.CONNECTION_TEST,
                        MergeLogLevel.INFO,
                        "正在连接 HiveServer2 ...",
                        details={"elapsed_s": waited},
                    )
                    try:
                        self._update_task_progress(
                            task,
                            db_session,
                            execution_phase="connection_test",
                            current_operation=f"连接 HiveServer2 中 (已等待{waited}s)",
                        )
                    except Exception:
                        pass
                waited += 2
                th.join(timeout=2)

            if th.is_alive():
                if merge_logger:
                    merge_logger.end_phase(
                        MergePhase.CONNECTION_TEST,
                        f"HiveServer2 连接超时({timeout_sec}s)",
                        success=False,
                    )
                logger.error("Hive connection test timeout")
                return False

            if done_flag["ok"] and not done_flag["err"]:
                if merge_logger:
                    merge_logger.end_phase(
                        MergePhase.CONNECTION_TEST, "Hive 连接与校验通过", success=True
                    )
                logger.info("Hive connection test passed")
                return True
            else:
                err = done_flag["err"]
                if merge_logger:
                    merge_logger.end_phase(
                        MergePhase.CONNECTION_TEST,
                        f"Hive 校验失败: {err}",
                        success=False,
                    )
                logger.error(f"Hive connection test failed: {err}")
                return False
        except Exception as e:
            logger.error(f"Hive connection test failed: {e}")
            return False

    def _execute_sql_with_heartbeat(
        self,
        *,
        cursor,
        sql: str,
        phase: MergePhase,
        merge_logger: MergeTaskLogger,
        task: MergeTask,
        db_session: Session,
        op_desc: str,
        execution_phase_name: str,
        interval: int = 10,
    ) -> None:
        """执行可能耗时较长的 SQL，期间定时输出心跳日志并刷新当前操作。

        - 在执行前记录“开始执行”日志
        - 执行结束后记录“执行成功/失败”日志
        - 执行期间每 `interval` 秒输出一次 INFO 心跳，包含已等待时长
        - 同步更新任务 `current_operation`，避免前端长时间静默
        """
        import threading

        stop = threading.Event()
        start_ts = time.time()

        def _heartbeat():
            i = 0
            while not stop.wait(interval):
                i += 1
                waited = int(time.time() - start_ts)
                merge_logger.log(
                    phase=phase,
                    level=MergeLogLevel.INFO,
                    message=f"正在执行: {op_desc}",
                    details={"elapsed_s": waited, "full_sql": sql[:200]},
                )
                # 仅刷新当前操作，避免误导性的进度上涨
                try:
                    cur_op = f"{op_desc} (已等待{waited}s)"
                    yarn_id = None
                    # 附带 YARN 应用心跳（如果配置了 RM）
                    if self.yarn_monitor is not None:
                        try:
                            # 拉取更宽的范围，包含 RUNNING/ACCEPTED/SUBMITTED，避免 RM 还未进入 RUNNING 时拿不到应用
                            apps = self.yarn_monitor.get_applications(limit=20)
                            apps = [
                                a
                                for a in apps
                                if str(getattr(a, "application_type", "")).upper()
                                in ("TEZ", "MAPREDUCE")
                            ]
                            # 选择最新启动的应用，优先匹配已记录的ID
                            app = None
                            if task.yarn_application_id:
                                for a in apps:
                                    if a.id == task.yarn_application_id:
                                        app = a
                                        break
                            if app is None and apps:
                                app = sorted(
                                    apps, key=lambda a: a.start_time, reverse=True
                                )[0]
                            if app is not None:
                                yarn_id = app.id
                                # 记录 YARN 监控日志
                                merge_logger.log_yarn_monitoring(
                                    app.id,
                                    phase,
                                    progress=float(getattr(app, "progress", 0) or 0),
                                    state=str(app.state or ""),
                                    details={
                                        "queue": getattr(app, "queue", ""),
                                        "name": getattr(app, "name", ""),
                                        "tracking_url": getattr(app, "tracking_url", "")
                                        or getattr(app, "original_tracking_url", ""),
                                    },
                                )
                                # 把进度拼进 current_operation，便于用户识别
                                try:
                                    pct = int(getattr(app, "progress", 0) or 0)
                                    cur_op = f"{op_desc} - YARN {pct}% {getattr(app,'state','')} (队列:{getattr(app,'queue','')}) (已等待{waited}s)"
                                except Exception:
                                    pass
                        except Exception:
                            # 监控失败不影响主流程
                            pass

                    self._update_task_progress(
                        task,
                        db_session,
                        execution_phase=execution_phase_name,
                        yarn_application_id=yarn_id or task.yarn_application_id,
                        current_operation=cur_op,
                    )
                except Exception:
                    pass

        # 记录开始
        merge_logger.log(
            phase,
            MergeLogLevel.INFO,
            f"SQL开始执行: {op_desc}",
            details={"full_sql": sql},
        )
        hb = threading.Thread(target=_heartbeat, daemon=True)
        hb.start()
        try:
            cursor.execute(sql)
            stop.set()
            hb.join(timeout=0.2)
            merge_logger.log_sql_execution(sql, phase, success=True)
        except Exception as e:
            stop.set()
            hb.join(timeout=0.2)
            formatted_error = self._extract_error_detail(e)
            merge_logger.log_sql_execution(
                sql, phase, success=False, error_message=formatted_error
            )
            raise

    def _atomic_table_swap(
        self, task: MergeTask, temp_table_name: str, backup_table_name: str
    ) -> List[str]:
        """原子性地交换表"""
        sql_statements = []

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 第一步：将原表重命名为备份表
            rename_to_backup_sql = (
                f"ALTER TABLE {task.table_name} RENAME TO {backup_table_name}"
            )
            cursor.execute(rename_to_backup_sql)
            sql_statements.append(rename_to_backup_sql)

            # 第二步：将临时表重命名为原表名
            rename_temp_to_original_sql = (
                f"ALTER TABLE {temp_table_name} RENAME TO {task.table_name}"
            )
            cursor.execute(rename_temp_to_original_sql)
            sql_statements.append(rename_temp_to_original_sql)

            cursor.close()
            conn.close()

            logger.info(
                f"Atomic table swap completed: {task.table_name} -> {backup_table_name}, {temp_table_name} -> {task.table_name}"
            )

        except Exception as e:
            logger.error(f"Failed to perform atomic table swap: {e}")
            raise

        return sql_statements

    def _atomic_table_swap_with_logging(
        self,
        task: MergeTask,
        temp_table_name: str,
        backup_table_name: str,
        merge_logger,
    ) -> List[str]:
        """带详细日志记录的原子表切换"""
        sql_statements = []

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 第一步：将原表重命名为备份表
            rename_to_backup_sql = (
                f"ALTER TABLE {task.table_name} RENAME TO {backup_table_name}"
            )
            merge_logger.log_sql_execution(rename_to_backup_sql, MergePhase.ATOMIC_SWAP)
            cursor.execute(rename_to_backup_sql)
            sql_statements.append(rename_to_backup_sql)

            merge_logger.log(
                MergePhase.ATOMIC_SWAP,
                MergeLogLevel.INFO,
                f"原表重命名为备份表: {task.table_name} -> {backup_table_name}",
                details={
                    "original_table": task.table_name,
                    "backup_table": backup_table_name,
                },
            )

            # 第二步：将临时表重命名为原表名
            rename_temp_to_original_sql = (
                f"ALTER TABLE {temp_table_name} RENAME TO {task.table_name}"
            )
            merge_logger.log_sql_execution(
                rename_temp_to_original_sql, MergePhase.ATOMIC_SWAP
            )
            cursor.execute(rename_temp_to_original_sql)
            sql_statements.append(rename_temp_to_original_sql)

            merge_logger.log(
                MergePhase.ATOMIC_SWAP,
                MergeLogLevel.INFO,
                f"临时表重命名为原表: {temp_table_name} -> {task.table_name}",
                details={
                    "temp_table": temp_table_name,
                    "original_table": task.table_name,
                },
            )

            cursor.close()
            conn.close()

            merge_logger.log(
                MergePhase.ATOMIC_SWAP,
                MergeLogLevel.INFO,
                "原子表切换成功完成",
                details={
                    "swap_operations": 2,
                    "backup_created": backup_table_name,
                    "active_table": task.table_name,
                },
            )

        except Exception as e:
            merge_logger.log(
                MergePhase.ATOMIC_SWAP,
                MergeLogLevel.ERROR,
                f"原子表切换失败: {str(e)}",
                details={"error": str(e), "failed_operation": "table_rename"},
            )
            raise

        return sql_statements

    # ========== Hive原生分区合并辅助方法 ==========

    def _atomic_swap_table_location(
        self,
        database: str,
        original_table: str,
        temp_table: str,
        merge_logger: MergeTaskLogger,
    ) -> Dict[str, Any]:
        """
        原子交换表的HDFS位置

        流程:
        1. 获取原表和临时表的LOCATION
        2. 备份原表HDFS目录
        3. 移动临时表HDFS目录到原表位置
        4. 刷新Hive元数据
        5. 清理备份和临时表

        Args:
            database: 数据库名
            original_table: 原表名
            temp_table: 临时表名
            merge_logger: 日志记录器

        Returns:
            操作结果
        """
        ts = int(time.time())

        try:
            # Step 1: 获取LOCATION
            original_location = self._get_table_location(database, original_table)
            temp_location = self._get_table_location(database, temp_table)

            if not original_location or not temp_location:
                raise Exception("无法获取表的HDFS路径")

            # 去除hdfs://前缀,保留纯路径
            original_path = self.webhdfs_client._normalize_path(original_location)
            temp_path = self.webhdfs_client._normalize_path(temp_location)
            backup_path = f"{original_path}_backup_{ts}"

            merge_logger.log(
                MergePhase.ATOMIC_SWAP,
                MergeLogLevel.INFO,
                f"原表路径: {original_path}, 临时表路径: {temp_path}",
            )

            # Step 2: 备份原表目录
            if self.webhdfs_client.exists(original_path):
                merge_logger.log(
                    MergePhase.ATOMIC_SWAP,
                    MergeLogLevel.INFO,
                    f"备份原表数据: {original_path} -> {backup_path}",
                )

                success, msg = self.webhdfs_client.move_file(original_path, backup_path)
                if not success:
                    raise Exception(f"备份失败: {msg}")

            # Step 3: 移动临时表到原表位置
            merge_logger.log(
                MergePhase.ATOMIC_SWAP,
                MergeLogLevel.INFO,
                f"移动合并后数据: {temp_path} -> {original_path}",
            )

            success, msg = self.webhdfs_client.move_file(temp_path, original_path)
            if not success:
                # 回滚
                merge_logger.log(
                    MergePhase.ATOMIC_SWAP,
                    MergeLogLevel.ERROR,
                    f"移动失败,回滚备份: {msg}",
                )
                if self.webhdfs_client.exists(backup_path):
                    self.webhdfs_client.move_file(backup_path, original_path)
                raise Exception(f"数据移动失败: {msg}")

            # Step 4: 刷新元数据
            merge_logger.log(
                MergePhase.ATOMIC_SWAP, MergeLogLevel.INFO, "刷新Hive元数据"
            )

            conn = self._create_hive_connection(database)
            cursor = conn.cursor()

            try:
                # 刷新分区
                cursor.execute(f"MSCK REPAIR TABLE {database}.{original_table}")

                # 验证表可查询
                cursor.execute(f"SELECT 1 FROM {database}.{original_table} LIMIT 1")
                cursor.fetchone()

                merge_logger.log(
                    MergePhase.ATOMIC_SWAP,
                    MergeLogLevel.INFO,
                    "元数据刷新完成,表验证通过",
                )

            finally:
                cursor.close()
                conn.close()

            # Step 5: 清理
            merge_logger.log(
                MergePhase.ATOMIC_SWAP, MergeLogLevel.INFO, "清理备份和临时表"
            )

            # 删除备份
            if self.webhdfs_client.exists(backup_path):
                self.webhdfs_client.delete_file(backup_path, recursive=True)

            # 删除临时表元数据
            conn = self._create_hive_connection(database)
            cursor = conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {database}.{temp_table}")
            cursor.close()
            conn.close()

            merge_logger.log(MergePhase.ATOMIC_SWAP, MergeLogLevel.INFO, "原子交换完成")

            return {
                "success": True,
                "original_location": original_path,
                "backup_location": backup_path,
            }

        except Exception as e:
            merge_logger.log(
                MergePhase.ATOMIC_SWAP, MergeLogLevel.ERROR, f"原子交换失败: {e}"
            )
            raise

    def _hdfs_rename_with_fallback(
        self,
        *,
        src: str,
        dst: str,
        merge_logger: MergeTaskLogger,
        phase: MergePhase,
        task: MergeTask,
        db_session: Session,
    ) -> tuple[bool, str]:
        """先尝试 WebHDFS rename，失败则回退 HS2 dfs -mv。

        返回: (ok, message)
        """
        ok = False
        last_msg = ""
        # 1) WebHDFS 优先
        try:
            ok, msg = self.webhdfs_client.move_file(src, dst)
            if ok:
                merge_logger.log_hdfs_operation(
                    "rename", src, phase, success=True, stats={"to": dst}
                )
                return True, ""
            last_msg = str(msg)
            merge_logger.log_hdfs_operation(
                "rename", src, phase, success=False, error_message=str(msg)
            )
        except Exception as e:
            last_msg = str(e)
            merge_logger.log_hdfs_operation(
                "rename", src, phase, success=False, error_message=str(e)
            )

        # 2) 回退 HS2 dfs -mv
        try:
            conn = self._create_hive_connection(task.database_name)
            cur = conn.cursor()
            cur.execute(f"dfs -mv {src} {dst}")
            try:
                cur.close()
                conn.close()
            except Exception:
                pass
            merge_logger.log_hdfs_operation(
                "rename",
                src,
                phase,
                success=True,
                stats={"to": dst, "fallback": "hs2-dfs-mv"},
            )
            # 刷新当前操作提示（非关键）
            try:
                self._update_task_progress(
                    task,
                    db_session,
                    current_operation=f"目录移动(回退HS2): {src} -> {dst}",
                )
            except Exception:
                pass
            return True, ""
        except Exception as e2:
            merge_logger.log_hdfs_operation(
                "rename",
                src,
                phase,
                success=False,
                error_message=f"hs2-dfs-mv failed: {e2}",
            )
            return False, f"WebHDFS failed: {last_msg}; HS2 failed: {e2}"

    def _rollback_merge(
        self, task: MergeTask, temp_table_name: str, backup_table_name: str
    ) -> List[str]:
        """回滚合并操作"""
        sql_statements = []

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 检查备份表是否存在，如果存在则恢复
            if self._table_exists(task.database_name, backup_table_name):
                # 删除可能存在的损坏的原表
                drop_damaged_sql = f"DROP TABLE IF EXISTS {task.table_name}"
                cursor.execute(drop_damaged_sql)
                sql_statements.append(drop_damaged_sql)

                # 将备份表恢复为原表
                restore_sql = (
                    f"ALTER TABLE {backup_table_name} RENAME TO {task.table_name}"
                )
                cursor.execute(restore_sql)
                sql_statements.append(restore_sql)

            # 清理临时表
            drop_temp_sql = f"DROP TABLE IF EXISTS {temp_table_name}"
            cursor.execute(drop_temp_sql)
            sql_statements.append(drop_temp_sql)

            cursor.close()
            conn.close()

            logger.info("Rollback completed successfully")

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise

        return sql_statements
