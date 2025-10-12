import logging
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector

logger = logging.getLogger(__name__)


class SimpleColdDataScanner:
    """
    简单冷数据扫描器，基于MetaStore LAST_ACCESS_TIME字段识别冷数据表
    """

    def __init__(self, cluster: Cluster, cold_days_threshold: int = 90):
        """
        初始化冷数据扫描器
        Args:
            cluster: 集群对象
            cold_days_threshold: 冷数据天数阈值，默认90天
        """
        self.cluster = cluster
        self.cold_days_threshold = cold_days_threshold

    def scan_cold_tables(
        self, db_session: Session, database_name: Optional[str] = None
    ) -> Dict:
        """
        扫描并标记冷数据表
        Args:
            db_session: 数据库会话
            database_name: 指定数据库名，为空则扫描所有数据库
        Returns:
            扫描结果字典
        """
        logger.info(
            f"开始扫描集群 {self.cluster.name} 的冷数据，阈值: {self.cold_days_threshold}天"
        )

        try:
            # 1. 从MetaStore获取访问时间信息
            with MySQLHiveMetastoreConnector(self.cluster.hive_metastore_url) as conn:
                access_info = conn.get_table_access_info(database_name)

            if not access_info:
                logger.warning(f"未获取到数据库 {database_name or 'ALL'} 的表访问信息")
                return {
                    "total_tables_scanned": 0,
                    "cold_tables_found": 0,
                    "cold_tables": [],
                    "threshold_days": self.cold_days_threshold,
                    "scan_timestamp": datetime.now().isoformat(),
                }

            cold_tables = []
            current_time = datetime.now()
            tables_updated = 0

            # 2. 计算每个表的冷热程度并更新数据库
            for info in access_info:
                try:
                    days_since_access = self._calculate_days_since_access(
                        info, current_time
                    )
                    is_cold = days_since_access > self.cold_days_threshold

                    # 3. 获取或创建表指标记录
                    table_metric = self._get_or_create_table_metric(
                        db_session, info["database_name"], info["table_name"]
                    )

                    # 4. 更新冷数据相关字段
                    table_metric.last_access_time = info["last_access_time"]
                    table_metric.days_since_last_access = days_since_access
                    table_metric.is_cold_data = 1 if is_cold else 0

                    tables_updated += 1

                    if is_cold:
                        cold_table_info = {
                            "database_name": info["database_name"],
                            "table_name": info["table_name"],
                            "days_since_access": days_since_access,
                            "last_access_time": (
                                info["last_access_time"].isoformat()
                                if info["last_access_time"]
                                else None
                            ),
                            "create_time": (
                                info["create_time"].isoformat()
                                if info["create_time"]
                                else None
                            ),
                            "table_metric_id": table_metric.id,
                        }
                        cold_tables.append(cold_table_info)

                        logger.debug(
                            f"标记冷数据表: {info['database_name']}.{info['table_name']} "
                            f"(距离上次访问: {days_since_access}天)"
                        )

                except Exception as e:
                    logger.error(
                        f"处理表 {info.get('database_name')}.{info.get('table_name')} 时出错: {e}"
                    )
                    continue

            # 提交数据库更改
            db_session.commit()

            result = {
                "total_tables_scanned": len(access_info),
                "cold_tables_found": len(cold_tables),
                "tables_updated": tables_updated,
                "cold_tables": cold_tables,
                "threshold_days": self.cold_days_threshold,
                "scan_timestamp": datetime.now().isoformat(),
                "cluster_id": self.cluster.id,
                "cluster_name": self.cluster.name,
            }

            logger.info(
                f"冷数据扫描完成: 扫描{len(access_info)}个表，发现{len(cold_tables)}个冷数据表"
            )

            return result

        except Exception as e:
            logger.error(f"冷数据扫描失败: {e}")
            db_session.rollback()
            raise

    def _calculate_days_since_access(self, info: Dict, current_time: datetime) -> int:
        """
        计算距离最后访问的天数
        Args:
            info: 表访问信息字典
            current_time: 当前时间
        Returns:
            距离最后访问的天数
        """
        last_access = info["last_access_time"]

        if not last_access:
            # 如果没有访问时间，用创建时间作为fallback
            create_time = info["create_time"]
            if create_time:
                return (current_time - create_time).days
            else:
                logger.warning(
                    f"表 {info['database_name']}.{info['table_name']} 缺少访问时间和创建时间"
                )
                return 999  # 无任何时间信息，标记为很久

        return (current_time - last_access).days

    def _get_or_create_table_metric(
        self, db_session: Session, database_name: str, table_name: str
    ) -> TableMetric:
        """
        获取或创建表指标记录
        Args:
            db_session: 数据库会话
            database_name: 数据库名
            table_name: 表名
        Returns:
            表指标对象
        """
        # 查找现有记录
        metric = (
            db_session.query(TableMetric)
            .filter(
                TableMetric.cluster_id == self.cluster.id,
                TableMetric.database_name == database_name,
                TableMetric.table_name == table_name,
            )
            .first()
        )

        if not metric:
            # 创建新记录
            metric = TableMetric(
                cluster_id=self.cluster.id,
                database_name=database_name,
                table_name=table_name,
                total_files=0,  # 这些值会在后续的表扫描中更新
                small_files=0,
                total_size=0,
                avg_file_size=0.0,
            )
            db_session.add(metric)
            db_session.flush()  # 获取ID

        return metric

    def get_cold_data_summary(self, db_session: Session) -> Dict:
        """
        获取集群的冷数据统计摘要
        Args:
            db_session: 数据库会话
        Returns:
            冷数据统计摘要
        """
        try:
            # 统计冷数据表
            cold_count = (
                db_session.query(TableMetric)
                .filter(
                    TableMetric.cluster_id == self.cluster.id,
                    TableMetric.is_cold_data == 1,
                )
                .count()
            )

            total_count = (
                db_session.query(TableMetric)
                .filter(TableMetric.cluster_id == self.cluster.id)
                .count()
            )

            # 统计不同冷度区间的表数量
            very_cold = (
                db_session.query(TableMetric)
                .filter(
                    TableMetric.cluster_id == self.cluster.id,
                    TableMetric.days_since_last_access > 180,  # 6个月以上
                )
                .count()
            )

            cold = (
                db_session.query(TableMetric)
                .filter(
                    TableMetric.cluster_id == self.cluster.id,
                    TableMetric.days_since_last_access.between(90, 180),  # 3-6个月
                )
                .count()
            )

            # 获取冷数据表列表（前20个）
            cold_tables = (
                db_session.query(TableMetric)
                .filter(
                    TableMetric.cluster_id == self.cluster.id,
                    TableMetric.is_cold_data == 1,
                )
                .order_by(TableMetric.days_since_last_access.desc())
                .limit(20)
                .all()
            )

            cold_table_list = [
                {
                    "database_name": t.database_name,
                    "table_name": t.table_name,
                    "days_since_access": t.days_since_last_access,
                    "last_access_time": (
                        t.last_access_time.isoformat() if t.last_access_time else None
                    ),
                    "total_size": t.total_size,
                    "total_files": t.total_files,
                }
                for t in cold_tables
            ]

            return {
                "cluster_id": self.cluster.id,
                "cluster_name": self.cluster.name,
                "total_tables": total_count,
                "cold_tables": cold_count,
                "cold_ratio": round(cold_count / max(total_count, 1) * 100, 2),
                "threshold_days": self.cold_days_threshold,
                "distribution": {
                    "very_cold_6m_plus": very_cold,
                    "cold_3_6m": cold,
                    "warm_under_3m": total_count - cold_count,
                },
                "sample_cold_tables": cold_table_list,
                "summary_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"获取冷数据摘要失败: {e}")
            return {
                "cluster_id": self.cluster.id,
                "cluster_name": self.cluster.name,
                "error": str(e),
                "summary_timestamp": datetime.now().isoformat(),
            }
