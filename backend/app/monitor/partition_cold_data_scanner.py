import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.models.partition_metric import PartitionMetric
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector

logger = logging.getLogger(__name__)

class PartitionColdDataScanner:
    """
    分区级冷数据扫描器，基于MetaStore和HDFS信息识别冷分区
    提供比表级别更精细的冷数据识别和归档控制
    """

    def __init__(self, cluster: Cluster, cold_days_threshold: int = 90):
        """
        初始化分区冷数据扫描器
        Args:
            cluster: 集群对象
            cold_days_threshold: 冷数据天数阈值，默认90天
        """
        self.cluster = cluster
        self.cold_days_threshold = cold_days_threshold

    def scan_cold_partitions(self, db_session: Session,
                           database_name: Optional[str] = None,
                           table_name: Optional[str] = None,
                           min_partition_size: int = 0) -> Dict:
        """
        扫描并标记冷数据分区
        Args:
            db_session: 数据库会话
            database_name: 指定数据库名，为空则扫描所有数据库
            table_name: 指定表名，为空则扫描指定数据库的所有表
            min_partition_size: 最小分区大小阈值（字节），用于过滤小分区
        Returns:
            扫描结果字典
        """
        logger.info(f"开始扫描集群 {self.cluster.name} 的分区级冷数据，阈值: {self.cold_days_threshold}天")

        try:
            # 1. 从MetaStore获取分区访问时间信息
            with MySQLHiveMetastoreConnector(self.cluster.hive_metastore_url) as conn:
                partition_access_info = conn.get_partition_access_info(database_name, table_name)

            if not partition_access_info:
                logger.warning(f"未获取到数据库 {database_name or 'ALL'} 的分区访问信息")
                return {
                    'total_partitions_scanned': 0,
                    'cold_partitions_found': 0,
                    'cold_partitions': [],
                    'threshold_days': self.cold_days_threshold,
                    'scan_timestamp': datetime.now().isoformat()
                }

            cold_partitions = []
            current_time = datetime.now()
            partitions_updated = 0

            # 2. 计算每个分区的冷热程度并更新数据库
            for info in partition_access_info:
                try:
                    days_since_access = self._calculate_days_since_access(info, current_time)
                    is_cold = days_since_access > self.cold_days_threshold

                    # 根据大小阈值过滤
                    partition_size = info.get('partition_size', 0)
                    if min_partition_size > 0 and partition_size < min_partition_size:
                        continue

                    # 3. 获取或创建分区指标记录
                    partition_metric = self._get_or_create_partition_metric(
                        db_session,
                        info['database_name'],
                        info['table_name'],
                        info['partition_name'],
                        info['partition_path']
                    )

                    # 4. 更新冷数据相关字段
                    partition_metric.last_access_time = info['last_access_time']
                    partition_metric.days_since_last_access = days_since_access
                    partition_metric.is_cold_data = 1 if is_cold else 0
                    partition_metric.total_size = partition_size
                    partition_metric.scan_time = current_time

                    partitions_updated += 1

                    if is_cold:
                        cold_partition_info = {
                            'database_name': info['database_name'],
                            'table_name': info['table_name'],
                            'partition_name': info['partition_name'],
                            'partition_path': info['partition_path'],
                            'days_since_access': days_since_access,
                            'last_access_time': info['last_access_time'].isoformat() if info['last_access_time'] else None,
                            'partition_size': partition_size,
                            'partition_metric_id': partition_metric.id
                        }
                        cold_partitions.append(cold_partition_info)

                        logger.debug(f"标记冷数据分区: {info['database_name']}.{info['table_name']}.{info['partition_name']} "
                                   f"(距离上次访问: {days_since_access}天，大小: {partition_size}字节)")

                except Exception as e:
                    logger.error(f"处理分区 {info.get('database_name')}.{info.get('table_name')}.{info.get('partition_name')} 时出错: {e}")
                    continue

            # 提交数据库更改
            db_session.commit()

            result = {
                'total_partitions_scanned': len(partition_access_info),
                'cold_partitions_found': len(cold_partitions),
                'partitions_updated': partitions_updated,
                'cold_partitions': cold_partitions,
                'threshold_days': self.cold_days_threshold,
                'min_partition_size': min_partition_size,
                'scan_timestamp': datetime.now().isoformat(),
                'cluster_id': self.cluster.id,
                'cluster_name': self.cluster.name
            }

            logger.info(f"分区冷数据扫描完成: 扫描{len(partition_access_info)}个分区，发现{len(cold_partitions)}个冷数据分区")

            return result

        except Exception as e:
            logger.error(f"分区冷数据扫描失败: {e}")
            db_session.rollback()
            raise

    def _calculate_days_since_access(self, info: Dict, current_time: datetime) -> int:
        """
        计算距离最后访问的天数
        Args:
            info: 分区访问信息字典
            current_time: 当前时间
        Returns:
            距离最后访问的天数
        """
        last_access = info['last_access_time']

        if not last_access:
            # 如果没有访问时间，用分区创建时间作为fallback
            create_time = info.get('create_time')
            if create_time:
                return (current_time - create_time).days
            else:
                logger.warning(f"分区 {info['database_name']}.{info['table_name']}.{info['partition_name']} 缺少访问时间和创建时间")
                return 999  # 无任何时间信息，标记为很久

        return (current_time - last_access).days

    def _get_or_create_partition_metric(self, db_session: Session,
                                      database_name: str, table_name: str,
                                      partition_name: str, partition_path: str) -> PartitionMetric:
        """
        获取或创建分区指标记录
        Args:
            db_session: 数据库会话
            database_name: 数据库名
            table_name: 表名
            partition_name: 分区名
            partition_path: 分区路径
        Returns:
            分区指标对象
        """
        # 先获取对应的表指标记录
        table_metric = db_session.query(TableMetric).filter(
            TableMetric.cluster_id == self.cluster.id,
            TableMetric.database_name == database_name,
            TableMetric.table_name == table_name
        ).first()

        if not table_metric:
            # 如果表指标不存在，创建一个基础记录
            table_metric = TableMetric(
                cluster_id=self.cluster.id,
                database_name=database_name,
                table_name=table_name,
                total_files=0,
                small_files=0,
                total_size=0,
                avg_file_size=0.0,
                is_partitioned=1  # 标记为分区表
            )
            db_session.add(table_metric)
            db_session.flush()

        # 查找现有的分区记录
        partition_metric = db_session.query(PartitionMetric).filter(
            PartitionMetric.table_metric_id == table_metric.id,
            PartitionMetric.partition_name == partition_name
        ).first()

        if not partition_metric:
            # 创建新的分区记录
            partition_metric = PartitionMetric(
                table_metric_id=table_metric.id,
                partition_name=partition_name,
                partition_path=partition_path,
                file_count=0,
                small_file_count=0,
                total_size=0,
                avg_file_size=0.0
            )
            db_session.add(partition_metric)
            db_session.flush()

        return partition_metric

    def get_cold_partitions_summary(self, db_session: Session,
                                  database_name: Optional[str] = None,
                                  table_name: Optional[str] = None) -> Dict:
        """
        获取集群的冷分区统计摘要
        Args:
            db_session: 数据库会话
            database_name: 可选的数据库名过滤
            table_name: 可选的表名过滤
        Returns:
            冷分区统计摘要
        """
        try:
            # 构建基础查询
            base_query = db_session.query(PartitionMetric).join(TableMetric).filter(
                TableMetric.cluster_id == self.cluster.id
            )

            if database_name:
                base_query = base_query.filter(TableMetric.database_name == database_name)

            if table_name:
                base_query = base_query.filter(TableMetric.table_name == table_name)

            # 统计冷分区
            cold_partition_count = base_query.filter(PartitionMetric.is_cold_data == 1).count()
            total_partition_count = base_query.count()

            # 统计不同冷度区间的分区数量
            very_cold = base_query.filter(PartitionMetric.days_since_last_access > 180).count()  # 6个月以上
            cold = base_query.filter(PartitionMetric.days_since_last_access.between(90, 180)).count()  # 3-6个月

            # 获取冷分区总大小
            cold_partitions_size = base_query.filter(PartitionMetric.is_cold_data == 1).with_entities(
                db_session.query(func.sum(PartitionMetric.total_size)).scalar_subquery()
            ).scalar() or 0

            # 获取样本冷分区列表（前20个）
            cold_partitions = base_query.filter(PartitionMetric.is_cold_data == 1).order_by(
                PartitionMetric.days_since_last_access.desc()
            ).limit(20).all()

            cold_partition_list = []
            for p in cold_partitions:
                table_metric = p.table_metric
                cold_partition_list.append({
                    'database_name': table_metric.database_name,
                    'table_name': table_metric.table_name,
                    'partition_name': p.partition_name,
                    'days_since_access': p.days_since_last_access,
                    'last_access_time': p.last_access_time.isoformat() if p.last_access_time else None,
                    'total_size': p.total_size,
                    'file_count': p.file_count,
                    'archive_status': p.archive_status
                })

            return {
                'cluster_id': self.cluster.id,
                'cluster_name': self.cluster.name,
                'total_partitions': total_partition_count,
                'cold_partitions': cold_partition_count,
                'cold_ratio': round(cold_partition_count / max(total_partition_count, 1) * 100, 2),
                'threshold_days': self.cold_days_threshold,
                'distribution': {
                    'very_cold_6m_plus': very_cold,
                    'cold_3_6m': cold,
                    'warm_under_3m': total_partition_count - cold_partition_count
                },
                'cold_partitions_total_size': cold_partitions_size,
                'sample_cold_partitions': cold_partition_list,
                'summary_timestamp': datetime.now().isoformat(),
                'filters': {
                    'database_name': database_name,
                    'table_name': table_name
                }
            }

        except Exception as e:
            logger.error(f"获取冷分区摘要失败: {e}")
            return {
                'cluster_id': self.cluster.id,
                'cluster_name': self.cluster.name,
                'error': str(e),
                'summary_timestamp': datetime.now().isoformat()
            }

    def get_partitions_by_coldness(self, db_session: Session,
                                 coldness_level: str = 'cold',
                                 database_name: Optional[str] = None,
                                 table_name: Optional[str] = None,
                                 limit: int = 100) -> List[Dict]:
        """
        根据冷热程度获取分区列表
        Args:
            db_session: 数据库会话
            coldness_level: 冷热程度 ('very_cold', 'cold', 'warm')
            database_name: 可选的数据库名过滤
            table_name: 可选的表名过滤
            limit: 返回结果限制
        Returns:
            分区列表
        """
        base_query = db_session.query(PartitionMetric).join(TableMetric).filter(
            TableMetric.cluster_id == self.cluster.id
        )

        if database_name:
            base_query = base_query.filter(TableMetric.database_name == database_name)

        if table_name:
            base_query = base_query.filter(TableMetric.table_name == table_name)

        # 根据冷热程度过滤
        if coldness_level == 'very_cold':
            base_query = base_query.filter(PartitionMetric.days_since_last_access > 180)
        elif coldness_level == 'cold':
            base_query = base_query.filter(PartitionMetric.days_since_last_access.between(90, 180))
        elif coldness_level == 'warm':
            base_query = base_query.filter(PartitionMetric.days_since_last_access < 90)

        partitions = base_query.order_by(PartitionMetric.days_since_last_access.desc()).limit(limit).all()

        partition_list = []
        for p in partitions:
            table_metric = p.table_metric
            partition_list.append({
                'database_name': table_metric.database_name,
                'table_name': table_metric.table_name,
                'partition_name': p.partition_name,
                'partition_path': p.partition_path,
                'days_since_access': p.days_since_last_access,
                'last_access_time': p.last_access_time.isoformat() if p.last_access_time else None,
                'total_size': p.total_size,
                'file_count': p.file_count,
                'is_cold_data': bool(p.is_cold_data),
                'archive_status': p.archive_status,
                'archive_location': p.archive_location,
                'archived_at': p.archived_at.isoformat() if p.archived_at else None
            })

        return partition_list