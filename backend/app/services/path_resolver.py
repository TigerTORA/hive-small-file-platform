from __future__ import annotations

"""
PathResolver: Unified way to resolve Hive table/partition HDFS locations.

Priority:
1) MetaStore (MySQL/PostgreSQL) via metastore connectors
2) HiveServer2 DESCRIBE FORMATTED (pyhive) as fallback
3) Default warehouse path as last resort
"""

import logging
from typing import List, Optional
from urllib.parse import urlparse

from app.monitor.hive_connector import HiveMetastoreConnector
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector

logger = logging.getLogger(__name__)


class PathResolver:
    @staticmethod
    def _resolve_via_metastore(
        metastore_url: str, database_name: str, table_name: str
    ) -> Optional[str]:
        try:
            scheme = (urlparse(metastore_url).scheme or "").lower()
            if scheme.startswith("mysql"):
                connector = MySQLHiveMetastoreConnector(metastore_url)
            else:
                connector = HiveMetastoreConnector(metastore_url)

            with connector as conn:
                loc = None
                # 优先使用“单表查询”，避免全库枚举
                if hasattr(conn, "get_table_location"):
                    loc = conn.get_table_location(database_name, table_name)  # type: ignore
                if loc:
                    return loc
                # 兜底：全量枚举后过滤（不推荐，但尽力）
                tables = conn.get_tables(database_name)
                for t in tables:
                    if t.get("table_name") == table_name and t.get("table_path"):
                        return t.get("table_path")
        except Exception as e:
            logger.warning(f"PathResolver metastore fallback failed: {e}")
        return None

    @staticmethod
    def _resolve_via_hs2(cluster, database_name: str, table_name: str) -> Optional[str]:
        """Fallback to HiveServer2 DESCRIBE FORMATTED parsing using pyhive."""
        try:
            from pyhive import hive

            params = {
                "host": cluster.hive_host,
                "port": cluster.hive_port,
                "database": database_name
                or getattr(cluster, "hive_database", "default")
                or "default",
            }
            if (getattr(cluster, "auth_type", "") or "").upper() == "LDAP" and getattr(
                cluster, "hive_username", None
            ):
                params["username"] = cluster.hive_username
                if getattr(cluster, "hive_password", None):
                    params["password"] = cluster.hive_password
                params["auth"] = "LDAP"

            conn = hive.Connection(**params)
            cur = conn.cursor()
            cur.execute(f"DESCRIBE FORMATTED {table_name}")
            rows = cur.fetchall()
            cur.close()
            conn.close()

            # Parse Location from DESCRIBE output
            for row in rows:
                if (
                    len(row) >= 2
                    and row[0]
                    and (
                        "Location:" in str(row[0])
                        or str(row[0]).strip().lower() == "location"
                    )
                ):
                    return str(row[1]).strip()
        except Exception as e:
            logger.warning(f"PathResolver HS2 fallback failed: {e}")
        return None

    @staticmethod
    def get_table_location(cluster, database_name: str, table_name: str) -> str:
        # 1) Try MetaStore
        loc = PathResolver._resolve_via_metastore(
            cluster.hive_metastore_url, database_name, table_name
        )
        if loc:
            return loc
        # 2) Try HiveServer2 DESCRIBE
        loc = PathResolver._resolve_via_hs2(cluster, database_name, table_name)
        if loc:
            return loc
        # 3) Default warehouse path
        return f"/warehouse/tablespace/managed/hive/{database_name}.db/{table_name}"

    @staticmethod
    def get_partition_locations(
        cluster, database_name: str, table_name: str
    ) -> List[str]:
        """Best-effort partition paths via MetaStore; fallback empty list."""
        paths: List[str] = []
        try:
            locs = None
            scheme = (urlparse(cluster.hive_metastore_url).scheme or "").lower()
            if scheme.startswith("mysql"):
                connector = MySQLHiveMetastoreConnector(cluster.hive_metastore_url)
            else:
                connector = HiveMetastoreConnector(cluster.hive_metastore_url)
            with connector as conn:
                parts = conn.get_table_partitions(database_name, table_name)
                locs = [
                    p.get("partition_path") for p in parts if p.get("partition_path")
                ]
            if locs:
                paths.extend(locs)
        except Exception as e:
            logger.warning(f"PathResolver partition metastore fetch failed: {e}")
        return paths
