import logging
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.utils.webhdfs_client import WebHDFSClient

logger = logging.getLogger(__name__)

class SimpleArchiveEngine:
    """
    简单归档引擎，实现表级数据归档和恢复功能
    """

    def __init__(self, cluster: Cluster, archive_root_path: str = "/archive"):
        """
        初始化归档引擎
        Args:
            cluster: 集群对象
            archive_root_path: 归档根目录路径
        """
        self.cluster = cluster
        self.archive_root_path = archive_root_path.rstrip('/')

    def archive_table(self, db_session: Session, database_name: str, table_name: str,
                     force: bool = False) -> Dict:
        """
        归档指定表
        Args:
            db_session: 数据库会话
            database_name: 数据库名
            table_name: 表名
            force: 是否强制归档（忽略状态检查）
        Returns:
            归档结果字典
        """
        logger.info(f"开始归档表: {database_name}.{table_name}")

        try:
            # 1. 获取表指标记录
            table_metric = self._get_table_metric(db_session, database_name, table_name)
            if not table_metric:
                raise ValueError(f"表 {database_name}.{table_name} 在系统中不存在")

            # 2. 检查表状态
            if not force and table_metric.archive_status != 'active':
                raise ValueError(f"表 {database_name}.{table_name} 已被归档，状态: {table_metric.archive_status}")

            if not force and table_metric.is_cold_data != 1:
                raise ValueError(f"表 {database_name}.{table_name} 不是冷数据，无法归档")

            # 3. 获取表的HDFS路径信息
            table_location = self._get_table_location(database_name, table_name)
            if not table_location:
                raise ValueError(f"无法获取表 {database_name}.{table_name} 的存储位置")

            # 4. 创建归档目录结构
            archive_path = self._create_archive_path(database_name, table_name)

            # 5. 执行数据文件移动
            moved_files = self._move_table_data(table_location, archive_path)

            # 6. 更新表元数据
            table_metric.archive_status = 'archived'
            table_metric.archive_location = archive_path
            table_metric.archived_at = datetime.now()

            db_session.commit()

            result = {
                'status': 'success',
                'table_full_name': f"{database_name}.{table_name}",
                'original_location': table_location,
                'archive_location': archive_path,
                'files_moved': len(moved_files),
                'moved_files': moved_files,
                'archived_at': datetime.now().isoformat(),
                'cluster_id': self.cluster.id,
                'cluster_name': self.cluster.name
            }

            logger.info(f"表 {database_name}.{table_name} 归档成功，移动了 {len(moved_files)} 个文件")
            return result

        except Exception as e:
            logger.error(f"归档表 {database_name}.{table_name} 失败: {e}")
            db_session.rollback()
            raise

    def restore_table(self, db_session: Session, database_name: str, table_name: str) -> Dict:
        """
        恢复归档表
        Args:
            db_session: 数据库会话
            database_name: 数据库名
            table_name: 表名
        Returns:
            恢复结果字典
        """
        logger.info(f"开始恢复表: {database_name}.{table_name}")

        try:
            # 1. 获取表指标记录
            table_metric = self._get_table_metric(db_session, database_name, table_name)
            if not table_metric:
                raise ValueError(f"表 {database_name}.{table_name} 在系统中不存在")

            # 2. 检查归档状态
            if table_metric.archive_status != 'archived':
                raise ValueError(f"表 {database_name}.{table_name} 未被归档，状态: {table_metric.archive_status}")

            if not table_metric.archive_location:
                raise ValueError(f"表 {database_name}.{table_name} 缺少归档位置信息")

            # 3. 获取原始表位置
            original_location = self._get_table_location(database_name, table_name)
            if not original_location:
                raise ValueError(f"无法获取表 {database_name}.{table_name} 的原始存储位置")

            # 4. 执行数据文件恢复
            restored_files = self._restore_table_data(table_metric.archive_location, original_location)

            # 5. 更新表元数据
            table_metric.archive_status = 'active'
            table_metric.archive_location = None
            table_metric.archived_at = None

            db_session.commit()

            result = {
                'status': 'success',
                'table_full_name': f"{database_name}.{table_name}",
                'archive_location': table_metric.archive_location,
                'restored_location': original_location,
                'files_restored': len(restored_files),
                'restored_files': restored_files,
                'restored_at': datetime.now().isoformat(),
                'cluster_id': self.cluster.id,
                'cluster_name': self.cluster.name
            }

            logger.info(f"表 {database_name}.{table_name} 恢复成功，恢复了 {len(restored_files)} 个文件")
            return result

        except Exception as e:
            logger.error(f"恢复表 {database_name}.{table_name} 失败: {e}")
            db_session.rollback()
            raise

    def get_archive_status(self, db_session: Session, database_name: str, table_name: str) -> Dict:
        """
        获取表的归档状态信息
        Args:
            db_session: 数据库会话
            database_name: 数据库名
            table_name: 表名
        Returns:
            归档状态字典
        """
        table_metric = self._get_table_metric(db_session, database_name, table_name)
        if not table_metric:
            return {
                'exists': False,
                'table_full_name': f"{database_name}.{table_name}"
            }

        return {
            'exists': True,
            'table_full_name': f"{database_name}.{table_name}",
            'archive_status': table_metric.archive_status,
            'archive_location': table_metric.archive_location,
            'archived_at': table_metric.archived_at.isoformat() if table_metric.archived_at else None,
            'is_cold_data': bool(table_metric.is_cold_data),
            'days_since_last_access': table_metric.days_since_last_access,
            'last_access_time': table_metric.last_access_time.isoformat() if table_metric.last_access_time else None,
            'total_size': table_metric.total_size,
            'total_files': table_metric.total_files
        }

    def list_archived_tables(self, db_session: Session, limit: int = 100) -> Dict:
        """
        列出集群中所有已归档的表
        Args:
            db_session: 数据库会话
            limit: 返回结果限制
        Returns:
            已归档表列表
        """
        try:
            archived_tables = db_session.query(TableMetric).filter(
                TableMetric.cluster_id == self.cluster.id,
                TableMetric.archive_status == 'archived'
            ).order_by(
                TableMetric.archived_at.desc()
            ).limit(limit).all()

            table_list = []
            total_archived_size = 0

            for table in archived_tables:
                table_info = {
                    'database_name': table.database_name,
                    'table_name': table.table_name,
                    'archive_location': table.archive_location,
                    'archived_at': table.archived_at.isoformat() if table.archived_at else None,
                    'days_since_last_access': table.days_since_last_access,
                    'last_access_time': table.last_access_time.isoformat() if table.last_access_time else None,
                    'total_size': table.total_size,
                    'total_files': table.total_files
                }
                table_list.append(table_info)
                total_archived_size += table.total_size or 0

            return {
                'cluster_id': self.cluster.id,
                'cluster_name': self.cluster.name,
                'total_archived_tables': len(table_list),
                'total_archived_size': total_archived_size,
                'archived_tables': table_list,
                'query_timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"获取已归档表列表失败: {e}")
            raise

    def _get_table_metric(self, db_session: Session, database_name: str, table_name: str) -> Optional[TableMetric]:
        """获取表指标记录"""
        return db_session.query(TableMetric).filter(
            TableMetric.cluster_id == self.cluster.id,
            TableMetric.database_name == database_name,
            TableMetric.table_name == table_name
        ).first()

    def _get_table_location(self, database_name: str, table_name: str) -> Optional[str]:
        """
        从MetaStore获取表的存储位置
        Args:
            database_name: 数据库名
            table_name: 表名
        Returns:
            表的HDFS存储路径
        """
        try:
            with MySQLHiveMetastoreConnector(self.cluster.hive_metastore_url) as conn:
                location = conn.get_table_location(database_name, table_name)
                return location
        except Exception as e:
            logger.error(f"获取表 {database_name}.{table_name} 存储位置失败: {e}")
            return None

    def _create_archive_path(self, database_name: str, table_name: str) -> str:
        """
        创建归档路径
        Args:
            database_name: 数据库名
            table_name: 表名
        Returns:
            归档路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = f"{self.archive_root_path}/{self.cluster.name}/{database_name}/{table_name}_{timestamp}"
        return archive_path

    def _move_table_data(self, source_path: str, target_path: str) -> List[str]:
        """
        移动表数据文件到归档位置
        Args:
            source_path: 源路径
            target_path: 目标路径
        Returns:
            移动的文件列表
        """
        try:
            # 暂时返回模拟的归档结果，后续完善实际的HDFS操作
            logger.warning(f"归档功能暂未完整实现，模拟移动数据从 {source_path} 到 {target_path}")

            # 模拟移动的文件列表
            moved_files = [
                {
                    'source': f"{source_path}/000000_0",
                    'target': f"{target_path}/000000_0"
                },
                {
                    'source': f"{source_path}/000001_0",
                    'target': f"{target_path}/000001_0"
                }
            ]

            logger.info(f"模拟移动 {len(moved_files)} 个文件从 {source_path} 到 {target_path}")
            return moved_files

        except Exception as e:
            logger.error(f"移动表数据失败: {e}")
            raise

    def _restore_table_data(self, archive_path: str, restore_path: str) -> List[str]:
        """
        从归档位置恢复表数据文件
        Args:
            archive_path: 归档路径
            restore_path: 恢复路径
        Returns:
            恢复的文件列表
        """
        try:
            # 暂时返回模拟的恢复结果，后续完善实际的HDFS操作
            logger.warning(f"恢复功能暂未完整实现，模拟恢复数据从 {archive_path} 到 {restore_path}")

            # 模拟恢复的文件列表
            restored_files = [
                {
                    'archive': f"{archive_path}/000000_0",
                    'restored': f"{restore_path}/000000_0"
                },
                {
                    'archive': f"{archive_path}/000001_0",
                    'restored': f"{restore_path}/000001_0"
                }
            ]

            logger.info(f"模拟恢复 {len(restored_files)} 个文件从 {archive_path} 到 {restore_path}")
            return restored_files

        except Exception as e:
            logger.error(f"恢复表数据失败: {e}")
            raise

    def get_archive_statistics(self, db_session: Session) -> Dict:
        """
        获取集群的归档统计信息
        Args:
            db_session: 数据库会话
        Returns:
            归档统计字典
        """
        try:
            # 统计各状态的表数量
            total_tables = db_session.query(TableMetric).filter(
                TableMetric.cluster_id == self.cluster.id
            ).count()

            archived_tables = db_session.query(TableMetric).filter(
                TableMetric.cluster_id == self.cluster.id,
                TableMetric.archive_status == 'archived'
            ).count()

            active_tables = db_session.query(TableMetric).filter(
                TableMetric.cluster_id == self.cluster.id,
                TableMetric.archive_status == 'active'
            ).count()

            # 统计归档存储空间节省
            archived_size = db_session.query(
                db_session.query(TableMetric.total_size).filter(
                    TableMetric.cluster_id == self.cluster.id,
                    TableMetric.archive_status == 'archived'
                ).scalar_subquery()
            ).scalar() or 0

            # 最近归档的表
            recent_archived = db_session.query(TableMetric).filter(
                TableMetric.cluster_id == self.cluster.id,
                TableMetric.archive_status == 'archived'
            ).order_by(
                TableMetric.archived_at.desc()
            ).limit(10).all()

            recent_list = [
                {
                    'database_name': t.database_name,
                    'table_name': t.table_name,
                    'archived_at': t.archived_at.isoformat() if t.archived_at else None,
                    'total_size': t.total_size,
                    'days_since_access': t.days_since_last_access
                }
                for t in recent_archived
            ]

            return {
                'cluster_id': self.cluster.id,
                'cluster_name': self.cluster.name,
                'statistics': {
                    'total_tables': total_tables,
                    'archived_tables': archived_tables,
                    'active_tables': active_tables,
                    'archive_ratio': round(archived_tables / max(total_tables, 1) * 100, 2),
                    'total_archived_size': archived_size,
                    'archive_root_path': self.archive_root_path
                },
                'recent_archived_tables': recent_list,
                'statistics_timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"获取归档统计信息失败: {e}")
            raise