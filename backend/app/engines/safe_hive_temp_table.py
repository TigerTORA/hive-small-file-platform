"""
Hive临时表管理器
负责临时表的创建、验证和清理
"""

import logging
import time
from typing import Any, Dict, List, Optional

from pyhive import hive
from sqlalchemy.orm import Session

from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.utils.merge_logger import MergeLogLevel, MergePhase

logger = logging.getLogger(__name__)


class HiveTempTableManager:
    """Hive临时表管理器,负责临时表的生命周期管理"""

    def __init__(self, cluster: Cluster, hive_password: Optional[str] = None):
        """
        初始化临时表管理器

        Args:
            cluster: 集群配置对象
            hive_password: 解密后的Hive密码(可选)
        """
        self.cluster = cluster
        self.hive_password = hive_password

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

    def _generate_temp_table_name(self, table_name: str) -> str:
        """生成临时表名"""
        timestamp = int(time.time())
        return f"{table_name}_merge_temp_{timestamp}"

    def _generate_backup_table_name(self, table_name: str) -> str:
        """生成备份表名"""
        timestamp = int(time.time())
        return f"{table_name}_backup_{timestamp}"

    def _create_temp_table(self, task: MergeTask, temp_table_name: str) -> List[str]:
        """创建临时表并执行合并"""
        sql_statements = []

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 设置 Hive 合并参数
            merge_settings = [
                "SET hive.merge.mapfiles=true",
                "SET hive.merge.mapredfiles=true",
                "SET hive.merge.size.per.task=268435456",  # 256MB
                "SET hive.exec.dynamic.partition=true",
                "SET hive.exec.dynamic.partition.mode=nonstrict",
                "SET mapred.reduce.tasks=1",  # 减少输出文件数
            ]

            for setting in merge_settings:
                cursor.execute(setting)
                sql_statements.append(setting)

            # 删除可能存在的临时表
            drop_temp_sql = f"DROP TABLE IF EXISTS {temp_table_name}"
            cursor.execute(drop_temp_sql)
            sql_statements.append(drop_temp_sql)

            # 创建临时表并执行合并
            if task.partition_filter:
                create_sql = f"""
                CREATE TABLE {temp_table_name} 
                AS SELECT * FROM {task.table_name} 
                WHERE {task.partition_filter}
                """
            else:
                create_sql = f"""
                CREATE TABLE {temp_table_name} 
                AS SELECT * FROM {task.table_name}
                """

            cursor.execute(create_sql)
            sql_statements.append(create_sql)

            cursor.close()
            conn.close()

            logger.info(f"Temporary table {temp_table_name} created successfully")

        except Exception as e:
            logger.error(f"Failed to create temporary table: {e}")
            raise

        return sql_statements

    def _create_temp_table_with_logging(
        self,
        task: MergeTask,
        temp_table_name: str,
        merge_logger,
        db_session: Session,
        target_format: str,
        job_compression: Optional[str],
        original_format: str,
        original_compression: str,
    ) -> List[str]:
        """带详细日志记录的临时表创建"""
        sql_statements = []

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 设置 Hive 合并参数
            merge_settings = [
                "SET hive.merge.mapfiles=true",
                "SET hive.merge.mapredfiles=true",
                "SET hive.merge.size.per.task=268435456",  # 256MB
                "SET hive.exec.dynamic.partition=true",
                "SET hive.exec.dynamic.partition.mode=nonstrict",
                # 关键：禁止 Tez 自动并行，配合单 reducer 强制减少输出文件数
                "SET hive.tez.auto.reducer.parallelism=false",
                "SET mapred.reduce.tasks=1",  # 减少输出文件数
            ]

            for setting in merge_settings:
                # 设置项较快，直接记录执行成功
                merge_logger.log(
                    MergePhase.TEMP_TABLE_CREATION,
                    MergeLogLevel.INFO,
                    f"SQL开始执行: {setting}",
                    details={"full_sql": setting},
                )
                cursor.execute(setting)
                merge_logger.log_sql_execution(
                    setting, MergePhase.TEMP_TABLE_CREATION, success=True
                )
                sql_statements.append(setting)

            self._apply_output_settings(
                cursor,
                merge_logger,
                sql_statements,
                target_format,
                job_compression,
            )

            # 删除可能存在的临时表
            drop_temp_sql = f"DROP TABLE IF EXISTS {temp_table_name}"
            merge_logger.log(
                MergePhase.TEMP_TABLE_CREATION,
                MergeLogLevel.INFO,
                f"SQL开始执行: {drop_temp_sql}",
                details={"full_sql": drop_temp_sql},
            )
            cursor.execute(drop_temp_sql)
            merge_logger.log_sql_execution(
                drop_temp_sql, MergePhase.TEMP_TABLE_CREATION, success=True
            )
            sql_statements.append(drop_temp_sql)

            # 创建临时表并执行合并
            # 读取原表是否为 EXTERNAL（用于保持表类型与路径）
            fmt_info = self._get_table_format_info(task.database_name, task.table_name)
            table_type = str(fmt_info.get("table_type", "")).upper()
            is_external = "EXTERNAL" in table_type
            original_location = (
                self._get_table_location(task.database_name, task.table_name) or ""
            )
            # 影子目录：在原父目录下使用固定根 ".merge_shadow"，并在其下创建按时间戳命名的子目录
            # 例如：hdfs://.../parent/.merge_shadow/<ts>
            ts_id = int(time.time())
            # 将影子目录切回原父目录，避免 /warehouse 路径的 HttpFS 限制
            parent_dir = (
                "/".join([p for p in original_location.rstrip("/").split("/")[:-1]])
                if original_location
                else ""
            )
            shadow_root = f"{parent_dir}/.merge_shadow" if parent_dir else ""
            shadow_dir = f"{shadow_root}/{ts_id}" if shadow_root else ""

            # 外部表：预创建影子目标目录，优先通过 HS2 执行 dfs，失败再回退 WebHDFS
            if is_external and shadow_dir:
                hs2_ok = False
                try:
                    try:
                        # 先确保根目录存在并开放权限，再创建本次会话的子目录
                        cursor.execute(f"dfs -mkdir -p {shadow_root}")
                        cursor.execute(f"dfs -chmod 777 {shadow_root}")
                        cursor.execute(f"dfs -mkdir -p {shadow_dir}")
                        cursor.execute(f"dfs -chmod 777 {shadow_dir}")
                        hs2_ok = True
                        merge_logger.log(
                            MergePhase.TEMP_TABLE_CREATION,
                            MergeLogLevel.INFO,
                            f"HS2 已创建影子目录并授权: {shadow_dir}",
                        )
                    except Exception as e:
                        merge_logger.log(
                            MergePhase.TEMP_TABLE_CREATION,
                            MergeLogLevel.WARNING,
                            f"HS2 创建影子目录失败，回退 WebHDFS: {e}",
                        )
                    if not hs2_ok:
                        # 先确保根目录存在
                        ok_root, msg_root = self.webhdfs_client.create_directory(
                            shadow_root, permission="777"
                        )
                        if not ok_root and "File exists" not in str(msg_root):
                            raise RuntimeError(f"创建影子根目录失败: {msg_root}")
                        merge_logger.log_hdfs_operation(
                            "mkdir",
                            shadow_root,
                            MergePhase.TEMP_TABLE_CREATION,
                            success=ok_root,
                            error_message=None if ok_root else str(msg_root),
                        )
                        # 再创建本次使用的子目录
                        ok_mkdir, msg_mkdir = self.webhdfs_client.create_directory(
                            shadow_dir, permission="777"
                        )
                        if not ok_mkdir and "File exists" not in str(msg_mkdir):
                            raise RuntimeError(f"创建影子目录失败: {msg_mkdir}")
                        merge_logger.log_hdfs_operation(
                            "mkdir",
                            shadow_dir,
                            MergePhase.TEMP_TABLE_CREATION,
                            success=ok_mkdir,
                            error_message=None if ok_mkdir else str(msg_mkdir),
                        )
                except Exception as e:
                    merge_logger.log_hdfs_operation(
                        "mkdir",
                        shadow_dir,
                        MergePhase.TEMP_TABLE_CREATION,
                        success=False,
                        error_message=str(e),
                    )
                    raise

            effective_format = target_format or original_format or "TEXTFILE"

            if is_external:
                fmt_clause = ""
                if effective_format in {"PARQUET", "ORC", "AVRO", "RCFILE"}:
                    fmt_clause = f" STORED AS {effective_format}"
                # 1) 预创建影子目录（上方已 mkdir），2) 写入影子目录
                insert_dir_sql = f"INSERT OVERWRITE DIRECTORY '{shadow_dir}'{fmt_clause} SELECT * FROM {task.table_name}"
                # 3) 创建外部临时表映射影子目录
                create_like_sql = f"CREATE EXTERNAL TABLE {temp_table_name} LIKE {task.table_name} LOCATION '{shadow_dir}'"

                self._apply_output_settings(
                    cursor,
                    merge_logger,
                    sql_statements,
                    effective_format,
                    job_compression,
                )

                # 执行：先写目录（长时 SQL 心跳），再建映射表
                self._execute_sql_with_heartbeat(
                    cursor=cursor,
                    sql=insert_dir_sql,
                    phase=MergePhase.TEMP_TABLE_CREATION,
                    merge_logger=merge_logger,
                    task=task,
                    db_session=db_session,
                    op_desc=f"写入影子目录: {shadow_dir}",
                    execution_phase_name="temp_table_creation",
                )
                sql_statements.append(insert_dir_sql)
                merge_logger.log_sql_execution(
                    create_like_sql, MergePhase.TEMP_TABLE_CREATION
                )
                cursor.execute(create_like_sql)
                sql_statements.append(create_like_sql)
                if effective_format and effective_format != original_format:
                    alter_temp_fmt = f"ALTER TABLE {temp_table_name} SET FILEFORMAT {effective_format}"
                    merge_logger.log_sql_execution(
                        alter_temp_fmt, MergePhase.TEMP_TABLE_CREATION
                    )
                    cursor.execute(alter_temp_fmt)
                    sql_statements.append(alter_temp_fmt)
                if job_compression and job_compression not in {None, "KEEP"}:
                    mapped_prop = None
                    if effective_format == "ORC":
                        mapped_prop = self._ORC_COMPRESSION.get(
                            job_compression, self._ORC_COMPRESSION.get("NONE")
                        )
                        if mapped_prop:
                            tbl_sql = f"ALTER TABLE {temp_table_name} SET TBLPROPERTIES('orc.compress'='{mapped_prop}')"
                            cursor.execute(tbl_sql)
                            merge_logger.log_sql_execution(
                                tbl_sql, MergePhase.TEMP_TABLE_CREATION
                            )
                            sql_statements.append(tbl_sql)
                    elif effective_format == "PARQUET":
                        mapped_prop = self._PARQUET_COMPRESSION.get(
                            job_compression, self._PARQUET_COMPRESSION.get("NONE")
                        )
                        if mapped_prop:
                            tbl_sql = f"ALTER TABLE {temp_table_name} SET TBLPROPERTIES('parquet.compression'='{mapped_prop}')"
                            cursor.execute(tbl_sql)
                            merge_logger.log_sql_execution(
                                tbl_sql, MergePhase.TEMP_TABLE_CREATION
                            )
                            sql_statements.append(tbl_sql)
            else:
                # 非外部表：保留 CTAS 临时表
                storage_clause = (
                    f" STORED AS {effective_format}"
                    if effective_format in {"PARQUET", "ORC", "AVRO", "RCFILE"}
                    else ""
                )
                properties = ["'transactional'='false'"]
                effective_compression = job_compression
                if effective_compression == "KEEP":
                    effective_compression = None
                if effective_compression and effective_compression != "NONE":
                    if effective_format == "ORC":
                        mapped = self._ORC_COMPRESSION.get(
                            effective_compression, self._ORC_COMPRESSION.get("SNAPPY")
                        )
                        if mapped:
                            properties.append(f"'orc.compress'='{mapped}'")
                    elif effective_format == "PARQUET":
                        mapped = self._PARQUET_COMPRESSION.get(
                            effective_compression,
                            self._PARQUET_COMPRESSION.get("SNAPPY"),
                        )
                        if mapped:
                            properties.append(f"'parquet.compression'='{mapped}'")
                elif effective_compression == "NONE":
                    if effective_format == "ORC":
                        properties.append("'orc.compress'='NONE'")
                    elif effective_format == "PARQUET":
                        properties.append("'parquet.compression'='UNCOMPRESSED'")
                props_clause = f" TBLPROPERTIES({', '.join(properties)})"
                select_sql = (
                    f"SELECT * FROM {task.table_name} WHERE {task.partition_filter} DISTRIBUTE BY 1"
                    if task.partition_filter
                    else f"SELECT * FROM {task.table_name} DISTRIBUTE BY 1"
                )
                create_sql = f"CREATE TABLE {temp_table_name}{storage_clause}{props_clause} AS {select_sql}"
                # 长时 SQL：增加心跳日志
                self._execute_sql_with_heartbeat(
                    cursor=cursor,
                    sql=create_sql,
                    phase=MergePhase.TEMP_TABLE_CREATION,
                    merge_logger=merge_logger,
                    task=task,
                    db_session=db_session,
                    op_desc=f"创建临时表并写入数据: {temp_table_name}",
                    execution_phase_name="temp_table_creation",
                )
                sql_statements.append(create_sql)

            cursor.close()
            conn.close()

            merge_logger.log(
                MergePhase.TEMP_TABLE_CREATION,
                MergeLogLevel.INFO,
                f"临时表{temp_table_name}创建成功",
                details={
                    "temp_table": temp_table_name,
                    "sql_count": len(sql_statements),
                },
            )

        except Exception as e:
            merge_logger.log_sql_execution(
                create_sql if "create_sql" in locals() else "CREATE TABLE ...",
                MergePhase.TEMP_TABLE_CREATION,
                success=False,
                error_message=str(e),
            )
            raise

        return sql_statements

    def _validate_temp_table_data(
        self, task: MergeTask, temp_table_name: str
    ) -> Dict[str, Any]:
        """验证临时表数据完整性"""
        result = {
            "valid": True,
            "message": "Validation passed",
            "original_count": 0,
            "temp_count": 0,
        }

        try:
            conn = self._create_hive_connection(task.database_name)
            cursor = conn.cursor()

            # 检查原表行数
            if task.partition_filter:
                count_original_sql = f"SELECT COUNT(*) FROM {task.table_name} WHERE {task.partition_filter}"
            else:
                count_original_sql = f"SELECT COUNT(*) FROM {task.table_name}"

            cursor.execute(count_original_sql)
            original_count = cursor.fetchone()[0]
            result["original_count"] = original_count

            # 检查临时表行数
            count_temp_sql = f"SELECT COUNT(*) FROM {temp_table_name}"
            cursor.execute(count_temp_sql)
            temp_count = cursor.fetchone()[0]
            result["temp_count"] = temp_count

            # 验证行数是否一致
            if original_count != temp_count:
                result["valid"] = False
                result["message"] = (
                    f"Row count mismatch: original={original_count}, temp={temp_count}"
                )

            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to validate temp table data: {e}")
            result["valid"] = False
            result["message"] = str(e)

        return result
