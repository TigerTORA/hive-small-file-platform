"""
Factory classes for creating test data
"""

from datetime import datetime, timezone

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.models.partition_metric import PartitionMetric
from app.models.table_metric import TableMetric
from app.models.task_log import TaskLog


class ClusterFactory(SQLAlchemyModelFactory):
    """Factory for creating Cluster instances"""

    class Meta:
        model = Cluster
        sqlalchemy_session_persistence = "commit"

    name = factory.Sequence(lambda n: f"cluster-{n}")
    description = factory.Faker("text", max_nb_chars=200)
    hive_host = "localhost"
    hive_port = 10000
    metastore_url = "mysql://user:pass@localhost:3306/hive"
    hdfs_namenode = "hdfs://localhost:9000"
    small_file_threshold = 134217728  # 128MB
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class TableMetricFactory(SQLAlchemyModelFactory):
    """Factory for creating TableMetric instances"""

    class Meta:
        model = TableMetric
        sqlalchemy_session_persistence = "commit"

    cluster_id = factory.SubFactory(ClusterFactory)
    database_name = factory.Sequence(lambda n: f"database_{n}")
    table_name = factory.Sequence(lambda n: f"table_{n}")
    table_type = factory.Faker(
        "random_element", elements=("MANAGED_TABLE", "EXTERNAL_TABLE")
    )
    is_partitioned = factory.Faker("boolean")
    total_files = factory.Faker("random_int", min=10, max=1000)
    small_files = factory.LazyAttribute(lambda obj: int(obj.total_files * 0.7))
    total_size = factory.Faker(
        "random_int", min=1073741824, max=107374182400
    )  # 1GB-100GB
    small_files_size = factory.LazyAttribute(lambda obj: int(obj.total_size * 0.3))
    avg_file_size = factory.LazyAttribute(
        lambda obj: obj.total_size / obj.total_files if obj.total_files > 0 else 0
    )
    compression_ratio = factory.Faker("pyfloat", min_value=0.1, max_value=0.9)
    scan_date = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class PartitionMetricFactory(SQLAlchemyModelFactory):
    """Factory for creating PartitionMetric instances"""

    class Meta:
        model = PartitionMetric
        sqlalchemy_session_persistence = "commit"

    table_metric_id = factory.SubFactory(TableMetricFactory)
    partition_spec = factory.Sequence(lambda n: f"year=2024/month={n % 12 + 1:02d}")
    partition_location = factory.LazyAttribute(
        lambda obj: f"/warehouse/tablespace/managed/hive/{obj.table_metric_id.database_name}.db/{obj.table_metric_id.table_name}/{obj.partition_spec}"
    )
    total_files = factory.Faker("random_int", min=1, max=100)
    small_files = factory.LazyAttribute(lambda obj: int(obj.total_files * 0.8))
    total_size = factory.Faker("random_int", min=1048576, max=1073741824)  # 1MB-1GB
    small_files_size = factory.LazyAttribute(lambda obj: int(obj.total_size * 0.4))
    avg_file_size = factory.LazyAttribute(
        lambda obj: obj.total_size / obj.total_files if obj.total_files > 0 else 0
    )
    scan_date = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class MergeTaskFactory(SQLAlchemyModelFactory):
    """Factory for creating MergeTask instances"""

    class Meta:
        model = MergeTask
        sqlalchemy_session_persistence = "commit"

    cluster_id = factory.SubFactory(ClusterFactory)
    task_name = factory.Sequence(lambda n: f"merge_task_{n}")
    database_name = factory.Sequence(lambda n: f"database_{n}")
    table_name = factory.Sequence(lambda n: f"table_{n}")
    partition_filter = factory.Maybe(
        "has_partition",
        yes_declaration=factory.Sequence(lambda n: f"dt='2024-{n % 12 + 1:02d}-01'"),
        no_declaration=None,
    )
    has_partition = factory.Faker("boolean")
    merge_strategy = factory.Faker(
        "random_element", elements=["concatenate", "insert_overwrite"]
    )
    target_file_size = factory.Faker(
        "random_int", min=134217728, max=1073741824
    )  # 128MB to 1GB
    use_ec = False
    status = "pending"
    celery_task_id = None
    error_message = None
    files_before = factory.Faker("random_int", min=10, max=1000)
    files_after = None
    size_saved = None
    created_time = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    started_time = None
    completed_time = None


class TaskLogFactory(SQLAlchemyModelFactory):
    """Factory for creating TaskLog instances"""

    class Meta:
        model = TaskLog
        sqlalchemy_session_persistence = "commit"

    task_id = factory.SubFactory(MergeTaskFactory)
    level = factory.Faker(
        "random_element", elements=("INFO", "WARNING", "ERROR", "DEBUG")
    )
    message = factory.Faker("sentence")
    details = factory.Maybe(
        "has_details", yes_declaration=factory.Faker("json"), no_declaration=None
    )
    has_details = factory.Faker("boolean")
    timestamp = factory.LazyFunction(lambda: datetime.now(timezone.utc))


# Utility functions for common test scenarios


def create_cluster_with_metrics(session, metrics_count: int = 5):
    """Create a cluster with associated table metrics"""
    cluster = ClusterFactory()
    session.add(cluster)
    session.commit()

    metrics = []
    for _ in range(metrics_count):
        metric = TableMetricFactory(cluster_id=cluster.id)
        session.add(metric)
        metrics.append(metric)

    session.commit()
    return cluster, metrics


def create_table_with_partitions(session, partitions_count: int = 3):
    """Create a table metric with partition metrics"""
    table_metric = TableMetricFactory(is_partitioned=True)
    session.add(table_metric)
    session.commit()

    partitions = []
    for i in range(partitions_count):
        partition = PartitionMetricFactory(
            table_metric_id=table_metric.id, partition_spec=f"year=2024/month={i+1:02d}"
        )
        session.add(partition)
        partitions.append(partition)

    session.commit()
    return table_metric, partitions


def create_task_with_logs(session, logs_count: int = 3):
    """Create a merge task with logs"""
    task = MergeTaskFactory()
    session.add(task)
    session.commit()

    logs = []
    for _ in range(logs_count):
        log = TaskLogFactory(task_id=task.id)
        session.add(log)
        logs.append(log)

    session.commit()
    return task, logs
