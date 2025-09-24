import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.cluster import Cluster
from app.models.partition_metric import PartitionMetric
from app.models.table_metric import TableMetric
from app.monitor.hdfs_scanner import HDFSScanner
from app.monitor.hive_connector import HiveMetastoreConnector

logger = logging.getLogger(__name__)


class TableScanner:
    """
    表扫描服务，整合 Hive MetaStore 和 HDFS 扫描功能
    """

    def __init__(self, cluster: Cluster):
        """
        初始化表扫描器
        Args:
            cluster: 集群配置对象
        """
        self.cluster = cluster
        self.hive_connector = HiveMetastoreConnector(cluster.hive_metastore_url)
        self.hdfs_scanner = HDFSScanner(cluster.hdfs_namenode_url, cluster.hdfs_user)

    def scan_cluster(
        self,
        db_session: Session,
        database_filter: Optional[str] = None,
        table_filter: Optional[str] = None,
    ) -> Dict:
        """
        扫描整个集群的小文件情况
        Args:
            db_session: 数据库会话
            database_filter: 数据库过滤器（可选）
            table_filter: 表过滤器（可选）
        Returns:
            扫描结果摘要
        """
        start_time = time.time()
        result = {
            "cluster_id": self.cluster.id,
            "cluster_name": self.cluster.name,
            "scan_start_time": datetime.utcnow(),
            "databases_scanned": 0,
            "tables_scanned": 0,
            "total_files": 0,
            "total_small_files": 0,
            "scan_duration": 0.0,
            "errors": [],
        }

        try:
            # 连接 Hive MetaStore 和 HDFS
            if not self.hive_connector.connect():
                raise Exception("Failed to connect to Hive MetaStore")

            if not self.hdfs_scanner.connect():
                raise Exception("Failed to connect to HDFS")

            # 获取数据库列表
            databases = self.hive_connector.get_databases()
            if database_filter:
                databases = [db for db in databases if database_filter in db]

            logger.info(f"Found {len(databases)} databases to scan")

            # 扫描每个数据库
            for database_name in databases:
                try:
                    db_result = self.scan_database(
                        db_session, database_name, table_filter
                    )
                    result["databases_scanned"] += 1
                    result["tables_scanned"] += db_result.get("tables_scanned", 0)
                    result["total_files"] += db_result.get("total_files", 0)
                    result["total_small_files"] += db_result.get("total_small_files", 0)

                except Exception as e:
                    error_msg = f"Failed to scan database {database_name}: {e}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)

            result["scan_duration"] = time.time() - start_time
            logger.info(
                f"Cluster scan completed: {result['tables_scanned']} tables, "
                f"{result['total_files']} files, {result['total_small_files']} small files"
            )

        except Exception as e:
            error_msg = f"Cluster scan failed: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)

        finally:
            self.hive_connector.disconnect()
            self.hdfs_scanner.disconnect()

        return result

    def scan_database(
        self,
        db_session: Session,
        database_name: str,
        table_filter: Optional[str] = None,
    ) -> Dict:
        """
        扫描指定数据库的所有表
        Args:
            db_session: 数据库会话
            database_name: 数据库名称
            table_filter: 表名过滤器（可选）
        Returns:
            数据库扫描结果
        """
        start_time = time.time()
        result = {
            "database_name": database_name,
            "tables_scanned": 0,
            "total_files": 0,
            "total_small_files": 0,
            "scan_duration": 0.0,
            "errors": [],
        }

        try:
            # 获取表列表
            tables = self.hive_connector.get_tables(database_name)
            if table_filter:
                tables = [t for t in tables if table_filter in t["table_name"]]

            logger.info(f"Found {len(tables)} tables in database {database_name}")

            # 扫描每个表
            for table_info in tables:
                try:
                    table_result = self.scan_table(
                        db_session, database_name, table_info
                    )
                    result["tables_scanned"] += 1
                    result["total_files"] += table_result.get("total_files", 0)
                    result["total_small_files"] += table_result.get("small_files", 0)

                except Exception as e:
                    error_msg = f"Failed to scan table {table_info['table_name']}: {e}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)

            result["scan_duration"] = time.time() - start_time

        except Exception as e:
            error_msg = f"Database {database_name} scan failed: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)

        return result

    def scan_table(
        self, db_session: Session, database_name: str, table_info: Dict
    ) -> Dict:
        """
        扫描单个表的文件分布
        Args:
            db_session: 数据库会话
            database_name: 数据库名称
            table_info: 表信息字典
        Returns:
            表扫描结果
        """
        table_name = table_info["table_name"]
        table_path = table_info["table_path"]

        logger.info(f"Scanning table {database_name}.{table_name} at {table_path}")

        try:
            # 获取分区信息（如果是分区表）
            partitions = []
            if table_info["is_partitioned"]:
                partitions = self.hive_connector.get_table_partitions(
                    database_name, table_name
                )

            # 扫描 HDFS 文件
            table_stats, partition_stats = self.hdfs_scanner.scan_table_partitions(
                table_path, partitions, self.cluster.small_file_threshold
            )

            # 保存表级统计到数据库
            table_metric = TableMetric(
                cluster_id=self.cluster.id,
                database_name=database_name,
                table_name=table_name,
                table_path=table_path,
                total_files=table_stats["total_files"],
                small_files=table_stats["small_files"],
                total_size=table_stats["total_size"],
                avg_file_size=table_stats["avg_file_size"],
                is_partitioned=table_info["is_partitioned"],
                partition_count=table_info["partition_count"],
                scan_duration=table_stats["scan_duration"],
            )

            db_session.add(table_metric)
            db_session.flush()  # 获取 table_metric.id

            # 保存分区级统计
            for partition_stat in partition_stats:
                partition_metric = PartitionMetric(
                    table_metric_id=table_metric.id,
                    partition_name=partition_stat["partition_name"],
                    partition_path=partition_stat["partition_path"],
                    file_count=partition_stat["file_count"],
                    small_file_count=partition_stat["small_file_count"],
                    total_size=partition_stat["total_size"],
                    avg_file_size=partition_stat["avg_file_size"],
                )
                db_session.add(partition_metric)

            db_session.commit()

            logger.info(
                f"Saved metrics for table {database_name}.{table_name}: "
                f"{table_stats['total_files']} files, {table_stats['small_files']} small files"
            )

            return table_stats

        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to scan table {database_name}.{table_name}: {e}")
            raise

    def scan_single_table(
        self, db_session: Session, database_name: str, table_name: str
    ) -> Optional[Dict]:
        """
        扫描单个指定的表
        Args:
            db_session: 数据库会话
            database_name: 数据库名称
            table_name: 表名称
        Returns:
            扫描结果或 None（如果失败）
        """
        try:
            # 连接服务
            if not self.hive_connector.connect():
                raise Exception("Failed to connect to Hive MetaStore")

            if not self.hdfs_scanner.connect():
                raise Exception("Failed to connect to HDFS")

            # 获取表信息
            tables = self.hive_connector.get_tables(database_name)
            table_info = None
            for table in tables:
                if table["table_name"] == table_name:
                    table_info = table
                    break

            if not table_info:
                raise Exception(f"Table {database_name}.{table_name} not found")

            # 扫描表
            return self.scan_table(db_session, database_name, table_info)

        except Exception as e:
            logger.error(
                f"Failed to scan single table {database_name}.{table_name}: {e}"
            )
            return None

        finally:
            self.hive_connector.disconnect()
            self.hdfs_scanner.disconnect()
