#!/usr/bin/env python3
"""
演示数据生成器
生成用于演示的模拟 Hive 集群数据、表信息和任务记录
"""

import argparse
import json
import random
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.models.scan_task import ScanTask
from app.models.merge_task import MergeTask

# 演示数据预设
DEMO_PRESETS = {
    'comprehensive': {
        'clusters': 3,
        'databases_per_cluster': 8,
        'tables_per_database': 25,
        'scan_tasks': 50,
        'merge_tasks': 30,
        'description': '综合演示 - 多集群、多数据库、丰富的表和任务数据'
    },
    'performance': {
        'clusters': 2,
        'databases_per_cluster': 12,
        'tables_per_database': 40,
        'scan_tasks': 80,
        'merge_tasks': 50,
        'description': '性能演示 - 大量数据展示系统处理能力'
    },
    'small_scale': {
        'clusters': 1,
        'databases_per_cluster': 4,
        'tables_per_database': 15,
        'scan_tasks': 20,
        'merge_tasks': 10,
        'description': '小规模演示 - 适合快速展示和测试'
    },
    'large_scale': {
        'clusters': 5,
        'databases_per_cluster': 15,
        'tables_per_database': 60,
        'scan_tasks': 150,
        'merge_tasks': 100,
        'description': '大规模演示 - 展示企业级规模的数据治理'
    }
}

class DemoDataGenerator:
    def __init__(self, database_url: str, preset: str = 'comprehensive'):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.preset_config = DEMO_PRESETS[preset]
        self.preset_name = preset

        print(f"🎯 使用预设: {preset}")
        print(f"📝 描述: {self.preset_config['description']}")

    def create_tables(self):
        """创建数据库表"""
        print("📊 创建数据库表...")
        Base.metadata.create_all(bind=self.engine)

    def generate_clusters(self, session) -> List[Cluster]:
        """生成集群数据"""
        clusters = []
        cluster_names = [
            'production-cluster', 'staging-cluster', 'development-cluster',
            'analytics-cluster', 'ml-cluster'
        ]

        environments = ['production', 'staging', 'development', 'testing', 'analytics']

        for i in range(self.preset_config['clusters']):
            cluster = Cluster(
                name=cluster_names[i % len(cluster_names)],
                description=f"演示集群 {i+1} - {environments[i % len(environments)]}环境",
                hive_metastore_url=f"mysql://hive:hive@metastore-{i+1}:3306/hive_metastore",
                hdfs_namenode_url=f"http://namenode-{i+1}:9870/webhdfs/v1",
                hdfs_user="hdfs",
                status="active",
                environment=environments[i % len(environments)],
                created_time=datetime.utcnow() - timedelta(days=random.randint(30, 365))
            )
            session.add(cluster)
            clusters.append(cluster)

        session.commit()
        print(f"✅ 生成了 {len(clusters)} 个集群")
        return clusters

    def generate_table_metrics(self, session, clusters: List[Cluster]):
        """生成表指标数据"""
        print("📈 生成表指标数据...")

        # 数据库名称模板
        database_templates = [
            'user_data', 'product_catalog', 'order_management', 'analytics',
            'log_data', 'sensor_data', 'financial_data', 'marketing_data',
            'inventory', 'customer_service', 'recommendation', 'fraud_detection'
        ]

        # 表名称模板
        table_templates = [
            'user_profile', 'user_behavior', 'user_sessions',
            'product_info', 'product_reviews', 'product_sales',
            'order_details', 'order_items', 'order_status',
            'click_stream', 'page_views', 'events',
            'transaction_log', 'error_log', 'access_log',
            'daily_summary', 'hourly_stats', 'real_time_metrics'
        ]

        total_tables = 0

        for cluster in clusters:
            for db_idx in range(self.preset_config['databases_per_cluster']):
                database_name = f"{database_templates[db_idx % len(database_templates)]}_{db_idx+1}"

                for table_idx in range(self.preset_config['tables_per_database']):
                    table_name = f"{table_templates[table_idx % len(table_templates)]}_{table_idx+1}"

                    # 生成真实的小文件分布数据
                    total_files = random.randint(10, 10000)
                    small_file_ratio = random.uniform(0.1, 0.9)
                    small_files = int(total_files * small_file_ratio)

                    # 计算文件大小
                    avg_file_size = random.randint(1024, 256*1024*1024)  # 1KB - 256MB
                    total_size = total_files * avg_file_size

                    # 分区信息
                    is_partitioned = random.choice([True, False])
                    partition_count = random.randint(1, 100) if is_partitioned else 1

                    table_metric = TableMetric(
                        cluster_id=cluster.id,
                        database_name=database_name,
                        table_name=table_name,
                        table_type=random.choice(['MANAGED_TABLE', 'EXTERNAL_TABLE']),
                        file_count=total_files,
                        small_file_count=small_files,
                        total_size=total_size,
                        small_file_ratio=small_file_ratio * 100,
                        avg_file_size=avg_file_size,
                        is_partitioned=is_partitioned,
                        partition_count=partition_count,
                        last_scan_time=datetime.utcnow() - timedelta(
                            hours=random.randint(1, 72)
                        ),
                        created_time=datetime.utcnow() - timedelta(
                            days=random.randint(1, 30)
                        )
                    )

                    session.add(table_metric)
                    total_tables += 1

        session.commit()
        print(f"✅ 生成了 {total_tables} 个表的指标数据")

    def generate_scan_tasks(self, session, clusters: List[Cluster]):
        """生成扫描任务数据"""
        print("🔍 生成扫描任务数据...")

        task_types = ['cluster', 'database', 'table']
        statuses = ['completed', 'failed', 'running', 'pending']
        status_weights = [0.7, 0.1, 0.1, 0.1]  # 大部分任务是完成的

        for i in range(self.preset_config['scan_tasks']):
            cluster = random.choice(clusters)
            task_type = random.choice(task_types)
            status = random.choices(statuses, weights=status_weights)[0]

            start_time = datetime.utcnow() - timedelta(
                hours=random.randint(1, 720)  # 最近30天
            )

            # 根据状态设置结束时间和持续时间
            if status == 'completed':
                duration = random.randint(30, 3600)  # 30秒到1小时
                end_time = start_time + timedelta(seconds=duration)
            elif status == 'failed':
                duration = random.randint(10, 1800)  # 10秒到30分钟
                end_time = start_time + timedelta(seconds=duration)
            else:
                duration = None
                end_time = None

            # 生成任务结果数据
            if status == 'completed':
                total_tables = random.randint(10, 1000)
                total_files = random.randint(total_tables * 5, total_tables * 50)
                small_files = int(total_files * random.uniform(0.3, 0.8))
            else:
                total_tables = random.randint(0, 100) if status == 'failed' else 0
                total_files = random.randint(0, total_tables * 10) if total_tables > 0 else 0
                small_files = int(total_files * random.uniform(0.3, 0.8)) if total_files > 0 else 0

            scan_task = ScanTask(
                cluster_id=cluster.id,
                task_type=task_type,
                task_name=f"{task_type.title()} 扫描任务 #{i+1}",
                status=status,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                total_tables_scanned=total_tables,
                total_files_found=total_files,
                total_small_files=small_files,
                error_message="模拟扫描错误：连接超时" if status == 'failed' else None
            )

            session.add(scan_task)

        session.commit()
        print(f"✅ 生成了 {self.preset_config['scan_tasks']} 个扫描任务")

    def generate_merge_tasks(self, session, clusters: List[Cluster]):
        """生成合并任务数据"""
        print("🔧 生成合并任务数据...")

        merge_strategies = ['safe_merge', 'concatenate', 'insert_overwrite']
        statuses = ['completed', 'failed', 'running', 'pending']
        status_weights = [0.6, 0.15, 0.15, 0.1]

        # 获取一些表名用于任务
        table_names = [
            'user_behavior_logs', 'product_sales_daily', 'click_stream_raw',
            'sensor_data_hourly', 'transaction_details', 'order_items_fact',
            'customer_interactions', 'inventory_snapshots', 'financial_records'
        ]

        database_names = [
            'analytics_db', 'sales_db', 'user_db', 'product_db', 'log_db'
        ]

        for i in range(self.preset_config['merge_tasks']):
            cluster = random.choice(clusters)
            strategy = random.choice(merge_strategies)
            status = random.choices(statuses, weights=status_weights)[0]

            database_name = random.choice(database_names)
            table_name = random.choice(table_names)

            created_time = datetime.utcnow() - timedelta(
                hours=random.randint(1, 720)
            )

            # 生成合并前后的文件数据
            files_before = random.randint(100, 5000)
            if status == 'completed':
                reduction_ratio = random.uniform(0.6, 0.9)  # 60%-90%的文件减少
                files_after = int(files_before * (1 - reduction_ratio))
            else:
                files_after = files_before if status in ['failed', 'pending'] else None

            merge_task = MergeTask(
                cluster_id=cluster.id,
                task_name=f"{table_name} 小文件合并 #{i+1}",
                database_name=database_name,
                table_name=table_name,
                merge_strategy=strategy,
                status=status,
                files_before=files_before,
                files_after=files_after,
                target_file_size=random.choice([64, 128, 256, 512]) * 1024 * 1024,  # MB
                partition_filter=f"dt>='{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')}'" if random.choice([True, False]) else None,
                created_time=created_time
            )

            session.add(merge_task)

        session.commit()
        print(f"✅ 生成了 {self.preset_config['merge_tasks']} 个合并任务")

    def generate_summary_data(self, session):
        """生成汇总统计数据"""
        print("📊 生成汇总统计数据...")

        # 计算实际统计数据
        total_clusters = session.query(Cluster).count()
        total_tables = session.query(TableMetric).count()
        total_small_files = session.query(TableMetric).with_entities(
            session.query(TableMetric.small_file_count).label('sum')
        ).scalar() or 0

        # 计算问题表数量（小文件比例 > 50% 的表）
        problem_tables = session.query(TableMetric).filter(
            TableMetric.small_file_ratio > 50
        ).count()

        summary_data = {
            'generated_at': datetime.utcnow().isoformat(),
            'preset': self.preset_name,
            'preset_description': self.preset_config['description'],
            'statistics': {
                'total_clusters': total_clusters,
                'total_tables': total_tables,
                'total_small_files': int(total_small_files),
                'problem_tables': problem_tables,
                'scan_tasks': self.preset_config['scan_tasks'],
                'merge_tasks': self.preset_config['merge_tasks']
            },
            'features_enabled': {
                'demo_mode': True,
                'advanced_charts': True,
                'smart_recommendations': True,
                'performance_monitoring': True,
                'fullscreen_mode': True
            }
        }

        # 保存汇总数据到文件
        os.makedirs('demo-data', exist_ok=True)
        with open('demo-data/summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

        print(f"📈 汇总数据:")
        print(f"   • 集群数量: {total_clusters}")
        print(f"   • 表总数: {total_tables}")
        print(f"   • 小文件总数: {total_small_files:,}")
        print(f"   • 问题表数量: {problem_tables}")

    def generate_all(self):
        """生成所有演示数据"""
        print(f"🚀 开始生成演示数据...")
        print(f"📋 预设配置: {self.preset_config}")

        session = self.SessionLocal()

        try:
            # 清理现有数据（可选）
            if os.getenv('CLEAR_EXISTING_DATA', 'false').lower() == 'true':
                print("🧹 清理现有数据...")
                session.query(MergeTask).delete()
                session.query(ScanTask).delete()
                session.query(TableMetric).delete()
                session.query(Cluster).delete()
                session.commit()

            # 创建表
            self.create_tables()

            # 生成数据
            clusters = self.generate_clusters(session)
            self.generate_table_metrics(session, clusters)
            self.generate_scan_tasks(session, clusters)
            self.generate_merge_tasks(session, clusters)
            self.generate_summary_data(session)

            print("🎉 演示数据生成完成!")

        except Exception as e:
            session.rollback()
            print(f"❌ 生成数据时出错: {e}")
            raise
        finally:
            session.close()

def main():
    parser = argparse.ArgumentParser(description='生成 Hive 小文件治理平台演示数据')
    parser.add_argument(
        '--preset',
        choices=list(DEMO_PRESETS.keys()),
        default='comprehensive',
        help='演示数据预设'
    )
    parser.add_argument(
        '--database-url',
        default=os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/hive_demo_db'),
        help='数据库连接URL'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='清理现有数据'
    )

    args = parser.parse_args()

    if args.clear:
        os.environ['CLEAR_EXISTING_DATA'] = 'true'

    print("🎯 Hive 小文件治理平台 - 演示数据生成器")
    print("=" * 50)

    # 显示可用预设
    print("📋 可用的数据预设:")
    for name, config in DEMO_PRESETS.items():
        marker = "👉" if name == args.preset else "  "
        print(f"{marker} {name}: {config['description']}")
    print()

    generator = DemoDataGenerator(args.database_url, args.preset)
    generator.generate_all()

if __name__ == '__main__':
    main()