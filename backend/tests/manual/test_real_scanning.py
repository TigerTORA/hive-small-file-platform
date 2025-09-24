#!/usr/bin/env python3
"""
真实数据扫描测试
- 使用真实的MySQL Hive MetaStore
- 智能选择HDFS扫描器（真实/Mock）
- 演示完整的表扫描流程
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.database import Base
from app.models.cluster import Cluster
from app.models.partition_metric import PartitionMetric
from app.models.table_metric import TableMetric
from app.monitor.hybrid_table_scanner import HybridTableScanner

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_test_database():
    """设置测试数据库"""
    engine = create_engine("sqlite:///test_real_scan.db", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def create_test_cluster(db_session):
    """创建测试集群配置"""
    cluster = Cluster(
        name="CDP测试集群",
        description="连接到192.168.0.105的真实CDP集群",
        hive_host="192.168.0.105",
        hive_port=10000,
        hive_database="default",
        hive_metastore_url="mysql://root:!qaz2wsx3edC@192.168.0.105:3306/hive",
        hdfs_namenode_url="hdfs://nameservice1",
        hdfs_user="hdfs",
        small_file_threshold=128 * 1024 * 1024,  # 128MB
        status="active",
    )

    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster


def test_real_scanning():
    """执行真实数据扫描测试"""
    logger.info("🚀 开始真实数据扫描测试")

    try:
        # 设置测试环境
        db_session = setup_test_database()
        cluster = create_test_cluster(db_session)
        logger.info(f"创建测试集群: {cluster.name} (ID: {cluster.id})")

        # 创建混合扫描器
        scanner = HybridTableScanner(cluster)

        # 测试连接
        logger.info("\n📡 测试连接状态...")
        connections = scanner.test_connections()

        logger.info("MetaStore连接:")
        metastore = connections.get("metastore", {})
        if metastore.get("status") == "success":
            logger.info(f"  ✅ 连接成功")
            logger.info(f"  📊 总数据库数: {metastore['total_databases']}")
            logger.info(f"  📋 总表数: {metastore['total_tables']}")
            logger.info(f"  📝 示例数据库: {metastore['sample_databases']}")
        else:
            logger.error(f"  ❌ 连接失败: {metastore.get('message')}")
            return False

        logger.info("\nHDFS连接:")
        hdfs = connections.get("hdfs", {})
        if hdfs.get("status") == "success":
            mode = hdfs.get("mode", "unknown")
            logger.info(f"  ✅ 连接成功 (模式: {mode})")
            if mode == "mock":
                logger.info(
                    f"  🔄 注意: 使用Mock模式，真实HDFS连接失败: {hdfs.get('real_hdfs_error')}"
                )
            else:
                logger.info(f"  🎯 WebHDFS URL: {hdfs.get('webhdfs_url')}")
        else:
            logger.error(f"  ❌ 连接失败: {hdfs.get('message')}")
            return False

        # 扫描测试数据库
        test_database = "default"
        logger.info(f"\n🔍 开始扫描数据库: {test_database}")

        scan_result = scanner.scan_database_tables(
            db_session, test_database, max_tables=5  # 限制扫描5个表进行演示
        )

        logger.info("\n📊 扫描结果:")
        logger.info(f"  数据库: {scan_result['database_name']}")
        logger.info(f"  扫描模式: {scan_result['hdfs_mode']}")
        logger.info(f"  已扫描表数: {scan_result['tables_scanned']}")
        logger.info(f"  总文件数: {scan_result['total_files']}")
        logger.info(f"  小文件数: {scan_result['total_small_files']}")
        logger.info(f"  扫描用时: {scan_result['scan_duration']:.2f} 秒")

        if scan_result["errors"]:
            logger.warning(f"  错误信息: {scan_result['errors']}")

        # 查询并展示扫描结果
        logger.info("\n📋 扫描详细结果:")
        table_metrics = (
            db_session.query(TableMetric)
            .filter(TableMetric.cluster_id == cluster.id)
            .all()
        )

        for metric in table_metrics:
            logger.info(f"\n  表: {metric.database_name}.{metric.table_name}")
            logger.info(f"    路径: {metric.table_path}")
            logger.info(f"    总文件: {metric.total_files}")
            logger.info(f"    小文件: {metric.small_files}")
            logger.info(
                f"    小文件比例: {(metric.small_files/metric.total_files*100):.1f}%"
                if metric.total_files > 0
                else "N/A"
            )
            logger.info(f"    总大小: {metric.total_size / (1024**3):.2f} GB")
            logger.info(f"    平均文件大小: {metric.avg_file_size / (1024**2):.2f} MB")
            logger.info(f"    是否分区表: {'是' if metric.is_partitioned else '否'}")

            if metric.is_partitioned:
                logger.info(f"    分区数: {metric.partition_count}")

                # 显示分区详情
                partitions = (
                    db_session.query(PartitionMetric)
                    .filter(PartitionMetric.table_metric_id == metric.id)
                    .all()
                )

                for partition in partitions[:3]:  # 只显示前3个分区
                    logger.info(f"      分区: {partition.partition_name}")
                    logger.info(f"        文件数: {partition.file_count}")
                    logger.info(f"        小文件数: {partition.small_file_count}")
                    logger.info(
                        f"        大小: {partition.total_size / (1024**2):.2f} MB"
                    )

                if len(partitions) > 3:
                    logger.info(f"      ... 还有 {len(partitions) - 3} 个分区")

        # 生成小文件分析报告
        if table_metrics:
            logger.info("\n📈 小文件分析报告:")
            total_tables = len(table_metrics)
            total_files = sum(m.total_files for m in table_metrics)
            total_small_files = sum(m.small_files for m in table_metrics)

            if total_files > 0:
                overall_ratio = (total_small_files / total_files) * 100
                logger.info(f"  总计: {total_tables} 个表，{total_files} 个文件")
                logger.info(f"  小文件: {total_small_files} 个 ({overall_ratio:.1f}%)")

                # 找出小文件问题最严重的表
                problematic_tables = [
                    m
                    for m in table_metrics
                    if m.total_files > 0 and (m.small_files / m.total_files) > 0.5
                ]

                if problematic_tables:
                    logger.info(f"\n  🚨 需要优化的表 (小文件比例>50%):")
                    for table in sorted(
                        problematic_tables,
                        key=lambda x: x.small_files / x.total_files,
                        reverse=True,
                    )[:5]:
                        ratio = (table.small_files / table.total_files) * 100
                        logger.info(
                            f"    {table.database_name}.{table.table_name}: {ratio:.1f}%"
                        )

        logger.info("\n🎉 真实数据扫描测试完成!")
        return True

    except Exception as e:
        logger.error(f"💥 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        if "db_session" in locals():
            db_session.close()


if __name__ == "__main__":
    success = test_real_scanning()
    if success:
        print("\n✅ 真实数据扫描测试成功! 系统可以正常工作。")
        print("\n💡 测试结果已保存到 test_real_scan.db 数据库文件中。")
    else:
        print("\n❌ 真实数据扫描测试失败，请检查配置。")
        sys.exit(1)
