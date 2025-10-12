"""
Safe Hive Metadata Manager Module

从 safe_hive_engine.py 提取的元数据管理模块 (Epic-6 Story 6.1)
负责表元数据的获取、格式识别和验证

提取日期: 2025-10-12
原始文件: safe_hive_engine.py (4228行 → 提取后约3300行)

重要: 此模块的所有方法签名必须100%匹配原始文件,避免上次重构失败的错误
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from pyhive import hive

from app.services.path_resolver import PathResolver
from app.models.cluster import Cluster

logger = logging.getLogger(__name__)


class SafeHiveMetadataManager:
    """
    Hive表元数据管理器
    
    职责:
    - 表元数据查询 (location, columns, partitions)
    - 表格式识别 (Parquet/ORC/AVRO等)
    - 表类型验证 (检测Hudi/Iceberg/Delta等不支持类型)
    - 压缩格式推断
    
    依赖:
    - Cluster: 集群配置 (Hive连接信息)
    - PathResolver: HDFS路径解析
    - pyhive: Hive连接库
    """
    
    # 格式关键字映射 (用于识别表存储格式)
    _FORMAT_KEYWORDS = {
        "PARQUET": ["parquet"],
        "ORC": ["orc"],
        "AVRO": ["avro"],
        "RCFILE": ["rcfile"],
    }
    
    # 压缩编解码器映射
    _COMPRESSION_CODECS = {
        "SNAPPY": "org.apache.hadoop.io.compress.SnappyCodec",
        "GZIP": "org.apache.hadoop.io.compress.GzipCodec",
        "LZ4": "org.apache.hadoop.io.compress.Lz4Codec",
    }
    
    # Parquet压缩格式映射
    _PARQUET_COMPRESSION = {
        "SNAPPY": "SNAPPY",
        "GZIP": "GZIP",
        "LZ4": "LZ4",
        "NONE": "UNCOMPRESSED",
    }
    
    # ORC压缩格式映射
    _ORC_COMPRESSION = {
        "SNAPPY": "SNAPPY",
        "GZIP": "ZLIB",
        "LZ4": "LZ4",
        "NONE": "NONE",
    }
    
    def __init__(self, cluster: Cluster, hive_password: Optional[str] = None):
        """
        初始化元数据管理器
        
        Args:
            cluster: 集群配置对象 (包含Hive连接信息)
            hive_password: Hive LDAP密码 (可选)
        """
        self.cluster = cluster
        self.hive_password = hive_password
    
    def _create_hive_connection(self, database_name: Optional[str] = None):
        """
        创建Hive连接（支持LDAP认证）

        Args:
            database_name: 数据库名 (可选,默认使用cluster配置的数据库)

        Returns:
            pyhive.hive.Connection: Hive连接对象
        """
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
    
    # ==================== 核心元数据方法 (10个) ====================
    # 重要: 所有方法签名必须100%匹配safe_hive_engine.py,避免上次重构失败的错误
    
    def _get_table_location(self, database_name: str, table_name: str) -> Optional[str]:
        """
        获取表的HDFS位置（优先MetaStore，其次HS2，最后默认路径）
        
        Args:
            database_name: 数据库名
            table_name: 表名
        
        Returns:
            Optional[str]: 表的HDFS路径,失败返回None
        """
        try:
            return PathResolver.get_table_location(
                self.cluster, database_name, table_name
            )
        except Exception as e:
            logger.error(f"Failed to resolve table location: {e}")
            return None
    
    def _table_exists(self, database_name: str, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            database_name: 数据库名
            table_name: 表名
        
        Returns:
            bool: True表示表存在,False表示不存在
        """
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
    
    def _is_partitioned_table(self, database_name: str, table_name: str) -> bool:
        """
        检查表是否为分区表
        
        Args:
            database_name: 数据库名
            table_name: 表名
        
        Returns:
            bool: True表示分区表,False表示非分区表
        """
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f"DESCRIBE FORMATTED {table_name}")
            
            rows = cursor.fetchall()
            is_partitioned = False
            
            for row in rows:
                if len(row) >= 2 and row[0] and "Partition Information" in str(row[0]):
                    is_partitioned = True
                    break
            
            cursor.close()
            conn.close()
            return is_partitioned
        except Exception as e:
            logger.error(f"Failed to check if table is partitioned: {e}")
            return False
    
    def _get_table_partitions(self, database_name: str, table_name: str) -> List[str]:
        """
        获取表的分区列表
        
        Args:
            database_name: 数据库名
            table_name: 表名
        
        Returns:
            List[str]: 分区列表,例如 ['dt=2024-01-01', 'dt=2024-01-02']
        """
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
        """
        获取表的格式/属性信息,用于安全校验
        
        Args:
            database_name: 数据库名
            table_name: 表名
        
        Returns:
            Dict[str, Any]: 格式信息字典,包含:
                - input_format: InputFormat类名
                - output_format: OutputFormat类名
                - serde_lib: SerDe库类名
                - storage_handler: Storage Handler类名
                - tblproperties: 表属性字典
                - table_type: 表类型 (EXTERNAL_TABLE/MANAGED_TABLE)
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
    
    def _get_table_columns(
        self, database_name: str, table_name: str
    ) -> Tuple[List[str], List[str]]:
        """
        获取表的字段列表（非分区列、分区列）
        
        Args:
            database_name: 数据库名
            table_name: 表名
        
        Returns:
            Tuple[List[str], List[str]]: (非分区列列表, 分区列列表)
        """
        try:
            conn = self._create_hive_connection(database_name)
            cursor = conn.cursor()
            cursor.execute(f"DESCRIBE FORMATTED {table_name}")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            nonpart: List[str] = []
            parts: List[str] = []
            in_part = False
            for row in rows:
                if not row or len(row) < 1:
                    continue
                first = str(row[0]).strip()
                if not first:
                    continue
                if first.startswith("#"):
                    if "Partition Information" in first:
                        in_part = True
                    continue
                if first.lower() == "col_name" or first.lower().startswith("name"):
                    continue
                # 过滤非字段行（如详细信息）
                if ":" in first:
                    # 进入详细信息部分
                    break
                if in_part:
                    parts.append(first)
                else:
                    nonpart.append(first)
            # 去掉可能的空白/无效项
            nonpart = [c for c in nonpart if c and c != "col_name"]
            parts = [c for c in parts if c and c != "col_name"]
            return nonpart, parts
        except Exception:
            return [], []
    
    def _is_unsupported_table_type(self, fmt: Dict[str, Any]) -> bool:
        """
        识别不受支持的表类型（Hudi/Iceberg/Delta/ACID等）
        
        Args:
            fmt: 表格式信息字典 (来自 _get_table_format_info)
        
        Returns:
            bool: True表示不支持,False表示支持
        """
        input_fmt = str(fmt.get("input_format", "")).lower()
        serde_lib = str(fmt.get("serde_lib", "")).lower()
        storage_handler = str(fmt.get("storage_handler", "")).lower()
        props = {
            str(k).lower(): str(v).lower()
            for k, v in fmt.get("tblproperties", {}).items()
        }
        
        # Hudi 检测：handler/serde/input 或 hoodie.* 属性
        if (
            "hudi" in input_fmt
            or "hudi" in serde_lib
            or "hudi" in storage_handler
            or any(k.startswith("hoodie.") for k in props.keys())
        ):
            return True
        # Iceberg 检测
        if (
            "iceberg" in input_fmt
            or "iceberg" in storage_handler
            or "iceberg" in serde_lib
        ):
            return True
        # Delta 检测
        if "delta" in input_fmt or "delta" in storage_handler or "delta" in serde_lib:
            return True
        # ACID 事务表：必须 transactional=true 或 storage handler 含 acid
        if props.get("transactional") == "true" or "acid" in storage_handler:
            return True
        return False
    
    def _unsupported_reason(self, fmt: Dict[str, Any]) -> str:
        """
        返回不支持的表类型的具体原因
        
        Args:
            fmt: 表格式信息字典 (来自 _get_table_format_info)
        
        Returns:
            str: 不支持的原因说明
        """
        input_fmt = str(fmt.get("input_format", "")).lower()
        serde_lib = str(fmt.get("serde_lib", "")).lower()
        storage_handler = str(fmt.get("storage_handler", "")).lower()
        props = {
            str(k).lower(): str(v).lower()
            for k, v in fmt.get("tblproperties", {}).items()
        }
        
        if (
            "hudi" in input_fmt
            or "hudi" in serde_lib
            or "hudi" in storage_handler
            or any(k.startswith("hoodie.") for k in props.keys())
        ):
            return "目标表为 Hudi 表，当前合并引擎不支持对 Hudi 表执行合并，请使用 Hudi 自带的压缩/合并机制（如 compaction/cluster）"
        if (
            "iceberg" in input_fmt
            or "iceberg" in storage_handler
            or "iceberg" in serde_lib
        ):
            return "目标表为 Iceberg 表，当前合并引擎不支持该表的合并操作"
        if "delta" in input_fmt or "delta" in storage_handler or "delta" in serde_lib:
            return "目标表为 Delta 表，当前合并引擎不支持该表的合并操作"
        if props.get("transactional") == "true" or "acid" in storage_handler:
            return "目标表为 ACID/事务表，当前合并引擎不支持该表的合并操作"
        return "目标表类型不受支持，已阻止合并操作"
    
    def _infer_storage_format_name(self, fmt: Dict[str, Any]) -> str:
        """
        从格式信息推断存储格式名称
        
        Args:
            fmt: 表格式信息字典 (来自 _get_table_format_info)
        
        Returns:
            str: 存储格式名称 (PARQUET/ORC/AVRO/RCFILE/TEXTFILE)
        """
        input_fmt = str(fmt.get("input_format", "")).lower()
        serde = str(fmt.get("serde_lib", "")).lower()
        for fmt_name, keywords in self._FORMAT_KEYWORDS.items():
            if any(keyword in input_fmt for keyword in keywords):
                return fmt_name
            if any(keyword in serde for keyword in keywords):
                return fmt_name
        return "TEXTFILE"
    
    def _infer_table_compression(self, fmt: Dict[str, Any], storage_format: str) -> str:
        """
        从格式信息和存储格式推断压缩格式
        
        Args:
            fmt: 表格式信息字典 (来自 _get_table_format_info)
            storage_format: 存储格式名称 (PARQUET/ORC/TEXTFILE等)
        
        Returns:
            str: 压缩格式 (SNAPPY/GZIP/LZ4/ZLIB/NONE/DEFAULT)
        """
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
                codec = codec.rsplit(".", 1)[-1]
                return codec.upper()
            return "NONE"
        return "DEFAULT"
