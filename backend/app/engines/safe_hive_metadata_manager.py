"""
Hive元数据管理器
负责表元数据的查询、验证和格式信息管理
"""
import logging
import re
from typing import Any, Dict, List, Optional

from pyhive import hive
from app.models.cluster import Cluster
from app.services.path_resolver import PathResolver
from app.utils.merge_logger import MergeLogLevel, MergePhase

logger = logging.getLogger(__name__)


class HiveMetadataManager:
    """Hive表元数据管理器"""
    
    def __init__(self, cluster: Cluster, hive_password: Optional[str] = None):
        """
        初始化元数据管理器
        
        Args:
            cluster: 集群配置对象
            hive_password: 解密后的Hive密码(可选)
        """
        self.cluster = cluster
        self.hive_password = hive_password
        
        # 格式关键字
        self._FORMAT_KEYWORDS = {
            "PARQUET": ["parquet"],
            "ORC": ["orc"],
            "AVRO": ["avro"],
            "RCFILE": ["rcfile"],
        }
        
        # 压缩编解码器
        self._COMPRESSION_CODECS = {
            "SNAPPY": "org.apache.hadoop.io.compress.SnappyCodec",
            "GZIP": "org.apache.hadoop.io.compress.GzipCodec",
            "LZ4": "org.apache.hadoop.io.compress.Lz4Codec",
        }
        
        self._PARQUET_COMPRESSION = {
            "SNAPPY": "SNAPPY",
            "GZIP": "GZIP",
            "LZ4": "LZ4",
            "NONE": "UNCOMPRESSED",
        }
        
        self._ORC_COMPRESSION = {
            "SNAPPY": "SNAPPY",
            "GZIP": "ZLIB",
            "LZ4": "LZ4",
            "NONE": "NONE",
        }

    def _create_hive_connection(self, database_name: str = None):
        """创建Hive连接（支持LDAP认证）"""
        hive_conn_params = {
            "host": self.cluster.hive_host,
            "port": self.cluster.hive_port,
            "database": database_name or self.cluster.hive_database or "default",
        }

        # 如果配置了LDAP认证
        if self.cluster.auth_type == "LDAP" and self.cluster.hive_username:
            hive_conn_params["username"] = self.cluster.hive_username
            if self.hive_password:
                hive_conn_params["password"] = self.hive_password
            hive_conn_params["auth"] = "LDAP"
            logger.debug(
                f"Creating LDAP connection for user: {self.cluster.hive_username}"
            )

        return hive.Connection(**hive_conn_params)

    def _get_table_location(self, database_name: str, table_name: str) -> Optional[str]:
        """获取表的HDFS位置（优先MetaStore，其次HS2，最后默认路径）"""
        try:
            return PathResolver.get_table_location(
                self.cluster, database_name, table_name
            )
        except Exception as e:
            logger.error(f"Failed to resolve table location: {e}")
            return None

    def _table_exists(self, database_name: str, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f'SHOW TABLES LIKE "{table_name}"')
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result is not None
        except Exception:
            return False

    def _is_partitioned_table(self, database: str, table: str) -> bool:
        """检测表是否为分区表(使用SHOW PARTITIONS检测)"""
        try:
            conn = self._create_hive_connection(database)
            cursor = conn.cursor()
            try:
                cursor.execute(f"SHOW PARTITIONS {database}.{table}")
                return True  # 执行成功说明是分区表
            except Exception:
                return False  # 报错说明不是分区表
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            logger.error(f"Failed to check if table is partitioned: {e}")
            return False

    def _get_table_partitions(self, database_name: str, table_name: str) -> List[str]:
        """获取表的分区列表"""
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f"SHOW PARTITIONS {table_name}")
            partitions = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return partitions
        except Exception as e:
            logger.error(f"Failed to get table partitions: {e}")
            return []

    def _get_table_format_info(
        self, database_name: str, table_name: str
    ) -> Dict[str, Any]:
        """获取表的格式/属性信息，用于安全校验。
        返回：{'input_format': str, 'serde_lib': str, 'storage_handler': str, 'tblproperties': {k:v}}
        """
        info: Dict[str, Any] = {
            "input_format": "",
            "output_format": "",
            "serde_lib": "",
            "storage_handler": "",
            "tblproperties": {},
            "table_type": "",
        }
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            # 读取格式信息
            cursor.execute(f"DESCRIBE FORMATTED {table_name}")
            rows = cursor.fetchall()
            for row in rows:
                if not row or len(row) < 2:
                    continue
                k = str(row[0]).strip()
                v = str(row[1]).strip() if row[1] is not None else ""
                if "InputFormat" in k:
                    info["input_format"] = v
                elif "OutputFormat" in k:
                    info["output_format"] = v
                elif "SerDe Library" in k:
                    info["serde_lib"] = v
                elif "Storage Handler" in k:
                    info["storage_handler"] = v
                elif "Table Type" in k or k.lower().startswith("type"):
                    # values like EXTERNAL_TABLE / MANAGED_TABLE
                    info["table_type"] = v
            # 读取表属性
            try:
                cursor.execute(f"SHOW TBLPROPERTIES {table_name}")
                props = cursor.fetchall()
                for pr in props:
                    # 常见返回为 (key, value)
                    if len(pr) >= 2:
                        info["tblproperties"][str(pr[0]).strip()] = str(pr[1]).strip()
            except Exception:
                pass
            cursor.close()
            conn.close()
        except Exception:
            pass
        return info

    def _infer_storage_format_name(self, fmt: Dict[str, Any]) -> str:
        input_fmt = str(fmt.get("input_format", "")).lower()
        serde = str(fmt.get("serde_lib", "")).lower()
        for fmt_name, keywords in self._FORMAT_KEYWORDS.items():
            if any(keyword in input_fmt for keyword in keywords):
                return fmt_name
            if any(keyword in serde for keyword in keywords):
                return fmt_name
        return "TEXTFILE"

    def _infer_table_compression(
        self, fmt: Dict[str, Any], storage_format: str
    ) -> str:
        props = {
            str(k).lower(): str(v).upper()
            for k, v in fmt.get("tblproperties", {}).items()
        }
        if storage_format == "ORC":
            value = props.get("orc.compress") or props.get("orc.default.compress")
            if value:
                return value.upper()
            return "ZLIB"
        if storage_format == "PARQUET":
            value = props.get("parquet.compression")
            if value:
                return value.upper()
            return "SNAPPY"
        if storage_format == "TEXTFILE":
            value = props.get("compression") or props.get("fileoutputformat.compress")
            if value:
                return value.upper()
            codec = props.get("mapreduce.output.fileoutputformat.compress.codec")
            if codec:
                codec = codec.rsplit('.', 1)[-1]
                return codec.upper()
            return "NONE"
        return "DEFAULT"

    def _apply_output_settings(
        self,
        cursor,
        merge_logger,
        sql_statements: List[str],
        storage_format: str,
        compression: Optional[str],
    ) -> None:
        if not compression:
            return
        codec = compression.upper()
        if codec in {"DEFAULT", ""}:
            return
        if codec == "KEEP":
            return

        def _exec(setting: str) -> None:
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

        if codec == "NONE":
            _exec("SET hive.exec.compress.output=false")
            _exec("SET mapreduce.output.fileoutputformat.compress=false")
        else:
            codec_class = self._COMPRESSION_CODECS.get(codec)
            if codec_class:
                _exec("SET hive.exec.compress.output=true")
                _exec("SET mapreduce.output.fileoutputformat.compress=true")
                _exec(
                    f"SET mapreduce.output.fileoutputformat.compress.codec={codec_class}"
                )
        if storage_format == "ORC":
            target = self._ORC_COMPRESSION.get(codec, self._ORC_COMPRESSION.get("NONE"))
            if target:
                _exec(f"SET hive.exec.orc.default.compress={target}")
        elif storage_format == "PARQUET":
            target = self._PARQUET_COMPRESSION.get(
                codec, self._PARQUET_COMPRESSION.get("NONE")
            )
            if target:
                _exec(f"SET parquet.compression={target}")

    def _update_active_table_format(
        self,
        database_name: str,
        table_name: str,
        storage_format: str,
        compression: Optional[str],
        merge_logger,
    ) -> None:
        comp = (compression or "").upper()
        if comp in {"DEFAULT", ""}:
            comp = None
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f"ALTER TABLE {table_name} SET FILEFORMAT {storage_format}")
            merge_logger.log_sql_execution(
                f"ALTER TABLE {table_name} SET FILEFORMAT {storage_format}",
                MergePhase.COMPLETION,
                success=True,
            )
            if comp and comp != "KEEP":
                props = {}
                if storage_format == "ORC":
                    mapped = self._ORC_COMPRESSION.get(comp)
                    if mapped:
                        props["orc.compress"] = mapped
                elif storage_format == "PARQUET":
                    mapped = self._PARQUET_COMPRESSION.get(comp)
                    if mapped:
                        props["parquet.compression"] = mapped
                elif storage_format in {"TEXTFILE", "AVRO", "RCFILE"}:
                    if comp == "NONE":
                        props["compression"] = "UNCOMPRESSED"
                    else:
                        props["compression"] = comp
                for key, value in props.items():
                    cursor.execute(
                        f"ALTER TABLE {table_name} SET TBLPROPERTIES('{key}'='{value}')"
                    )
                    merge_logger.log_sql_execution(
                        f"ALTER TABLE {table_name} SET TBLPROPERTIES('{key}'='{value}')",
                        MergePhase.COMPLETION,
                        success=True,
                    )
            cursor.close()
            conn.close()
        except Exception as exc:  # pragma: no cover - metadata updates best effort
            merge_logger.log(
                MergePhase.COMPLETION,
                MergeLogLevel.WARNING,
                f"更新表文件格式/压缩信息失败: {exc}",
                details={"code": "W902"},
            )

    def _detect_table_type(self, fmt: Dict[str, Any]) -> Optional[str]:
        """检测表类型,返回类型名称或None"""
        input_fmt = str(fmt.get("input_format", "")).lower()
        serde_lib = str(fmt.get("serde_lib", "")).lower()
        storage_handler = str(fmt.get("storage_handler", "")).lower()
        props = {str(k).lower(): str(v).lower() for k, v in fmt.get("tblproperties", {}).items()}

        # Hudi检测
        if ("hudi" in input_fmt or "hudi" in serde_lib or "hudi" in storage_handler or
            any(k.startswith("hoodie.") for k in props.keys())):
            return "hudi"
        # Iceberg检测
        if "iceberg" in input_fmt or "iceberg" in storage_handler or "iceberg" in serde_lib:
            return "iceberg"
        # Delta检测
        if "delta" in input_fmt or "delta" in storage_handler or "delta" in serde_lib:
            return "delta"
        # ACID事务表检测
        if props.get("transactional") == "true" or "acid" in storage_handler:
            return "acid"
        return None

    def _is_unsupported_table_type(self, fmt: Dict[str, Any]) -> bool:
        """识别不受支持的表类型（Hudi/Iceberg/Delta/ACID等）"""
        return self._detect_table_type(fmt) is not None

    def _unsupported_reason(self, fmt: Dict[str, Any]) -> str:
        """返回不受支持表类型的详细原因"""
        table_type = self._detect_table_type(fmt)
        reasons = {
            "hudi": "目标表为 Hudi 表，当前合并引擎不支持对 Hudi 表执行合并，请使用 Hudi 自带的压缩/合并机制（如 compaction/cluster）",
            "iceberg": "目标表为 Iceberg 表，当前合并引擎不支持该表的合并操作",
            "delta": "目标表为 Delta 表，当前合并引擎不支持该表的合并操作",
            "acid": "目标表为 ACID/事务表，当前合并引擎不支持该表的合并操作"
        }
        return reasons.get(table_type, "目标表类型不受支持，已阻止合并操作")

    def _parse_describe_formatted(self, database: str, table: str) -> (List[str], List[str]):
        """解析DESCRIBE FORMATTED结果,返回(非分区列,分区列)"""
        try:
            conn = self._create_hive_connection(database)
            cursor = conn.cursor()
            cursor.execute(f"DESCRIBE FORMATTED {database}.{table}")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            nonpart, parts, in_part = [], [], False
            for row in rows:
                if not row or not row[0]:
                    continue
                col = str(row[0]).strip()
                if not col or col.lower() in ('col_name', '') or col.lower().startswith('name'):
                    continue
                if col.startswith('#'):
                    if 'Partition Information' in col:
                        in_part = True
                    continue
                if ':' in col:  # 详细信息部分
                    break
                (parts if in_part else nonpart).append(col)

            return [c for c in nonpart if c != 'col_name'], [c for c in parts if c != 'col_name']
        except Exception:
            return [], []

    def _get_table_columns(self, database_name: str, table_name: str) -> (List[str], List[str]):
        """获取表的字段列表（非分区列、分区列）"""
        return self._parse_describe_formatted(database_name, table_name)

    def _get_partition_columns(self, database: str, table: str) -> list[str]:
        """获取表的分区列名列表"""
        try:
            _, part_cols = self._parse_describe_formatted(database, table)
            return part_cols
        except Exception as e:
            logger.error(f"Failed to get partition columns: {e}")
            return []

    def _list_all_partitions(self, database: str, table: str) -> list[str]:
        """
        获取表的所有分区规格列表

        Args:
            database: 数据库名
            table: 表名

        Returns:
            分区规格列表,如: ["partition_id='p1'", "partition_id='p2'"]
        """
        try:
            conn = self._create_hive_connection(database)
            cursor = conn.cursor()

            cursor.execute(f"SHOW PARTITIONS {database}.{table}")
            partitions = cursor.fetchall()
            cursor.close()
            conn.close()

            # partitions格式: [('partition_id=p1',), ('partition_id=p2',)]
            partition_specs = []
            for partition_tuple in partitions:
                if partition_tuple and partition_tuple[0]:
                    # 转换 'partition_id=p1' 为 "partition_id='p1'"
                    raw_spec = partition_tuple[0]
                    # 分割key=value对
                    parts = []
                    for part in raw_spec.split('/'):
                        if '=' in part:
                            key, value = part.split('=', 1)
                            parts.append(f"{key}='{value}'")
                    if parts:
                        partition_specs.append(', '.join(parts))

            return partition_specs

        except Exception as e:
            logger.error(f"Failed to list partitions: {e}")
            return []

    def _parse_table_schema_from_show_create(self, database: str, table: str) -> Dict[str, Any]:
        """通过SHOW CREATE TABLE解析表结构,避免继承ACID属性"""
        try:
            conn = self._create_hive_connection(database)
            cursor = conn.cursor()
            cursor.execute(f"SHOW CREATE TABLE {database}.{table}")
            result = cursor.fetchall()
            cursor.close()
            conn.close()

            # 拼接完整DDL
            ddl = '\n'.join([row[0] for row in result if row and row[0]])

            # 定义提取规则
            def extract_columns(section):
                """提取列定义"""
                col_pattern = r'`(\w+)`\s+(\w+(?:\([^)]+\))?)'
                return [(m.groups()[0], m.groups()[1]) for m in re.finditer(col_pattern, section)]

            def extract_value(pattern, default=''):
                """提取单个值"""
                match = re.search(pattern, ddl, re.IGNORECASE)
                return match.group(1) if match else default

            # 解析各部分
            create_match = re.search(r'CREATE.*?TABLE.*?\((.*?)(?:PARTITIONED BY|\))', ddl, re.DOTALL | re.IGNORECASE)
            columns = extract_columns(create_match.group(1)) if create_match else []

            part_match = re.search(r'PARTITIONED BY\s*\((.*?)\)', ddl, re.DOTALL | re.IGNORECASE)
            partition_columns = extract_columns(part_match.group(1)) if part_match else []

            return {
                'columns': columns,
                'partition_columns': partition_columns,
                'serde': extract_value(r"ROW FORMAT SERDE\s+'([^']+)'", 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'),
                'input_format': extract_value(r"STORED AS INPUTFORMAT\s+'([^']+)'", 'org.apache.hadoop.mapred.TextInputFormat'),
                'output_format': extract_value(r"OUTPUTFORMAT\s+'([^']+)'", 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'),
                'location': extract_value(r"LOCATION\s+'([^']+)'") or None
            }

        except Exception as e:
            logger.error(f"Failed to parse table schema: {e}")
            raise Exception(f"Cannot parse table schema for {database}.{table}: {e}")

