#!/usr/bin/env python3
"""
Seed a minimal demo cluster and table metric to exercise the archive flow.

This script is colocated under backend/scripts so it can be executed from within
Docker containers (volume mounts expose /app).  It mirrors the legacy
scripts/dev/seed_demo_archive.py helper but keeps the implementation in a
single canonical place.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.config.database import Base  # type: ignore

# Local imports must succeed when running inside the api container.
from app.config.settings import settings  # type: ignore
from app.models.cluster import Cluster  # type: ignore
from app.models.table_metric import TableMetric  # type: ignore


def ensure_demo_cluster(
    session: sessionmaker,
    name: str = "demo-archive",
    metastore_url: str = "mysql://root:pass@127.0.0.1:3306/hive",
    hdfs_url: str = "http://127.0.0.1:9870",
) -> Cluster:
    cluster = session.query(Cluster).filter(Cluster.name == name).first()
    if cluster:
        return cluster

    cluster = Cluster(
        name=name,
        description="Local demo cluster for archive E2E",
        hive_host="127.0.0.1",
        hive_port=10000,
        hive_database="default",
        hive_metastore_url=metastore_url,
        hdfs_namenode_url=hdfs_url,
        hdfs_user="hdfs",
        small_file_threshold=128 * 1024 * 1024,
        status="active",
        scan_enabled=True,
        archive_enabled=True,
        archive_root_path="/archive",
    )
    session.add(cluster)
    session.commit()
    session.refresh(cluster)
    return cluster


def ensure_demo_table_metric(
    session: sessionmaker,
    cluster_id: int,
    database: str = "default",
    table: str = "t1",
    table_path: Optional[str] = None,
) -> None:
    if table_path is None:
        table_path = "hdfs://nameservice1/user/hive/warehouse/default.db/t1"

    metric = (
        session.query(TableMetric)
        .filter(
            TableMetric.cluster_id == cluster_id,
            TableMetric.database_name == database,
            TableMetric.table_name == table,
        )
        .order_by(TableMetric.id.desc())
        .first()
    )

    if metric is None:
        metric = TableMetric(
            cluster_id=cluster_id,
            database_name=database,
            table_name=table,
            table_path=table_path,
            table_type="MANAGED_TABLE",
            storage_format="PARQUET",
            input_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
            output_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
            serde_lib="org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
            table_owner="hive",
            total_files=12,
            small_files=9,
            total_size=1024 * 1024 * 256,
            avg_file_size=int((1024 * 1024 * 256) / max(12, 1)),
            is_partitioned=0,
            partition_count=0,
            scan_time=datetime.utcnow(),
            is_cold_data=1,
            archive_status="active",
        )
        session.add(metric)
        session.commit()
        return

    # Update existing row to make sure archive UI has a ready record.
    metric.is_cold_data = 1
    metric.archive_status = "active"
    if not metric.table_path:
        metric.table_path = table_path
    session.commit()


def seed_demo_archive(database_url: str) -> None:
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        cluster = ensure_demo_cluster(db)
        ensure_demo_table_metric(db, cluster_id=cluster.id)
        print(
            f"Seeded archive demo data: cluster_id={cluster.id} "
            f"database=default table=t1"
        )
    finally:
        db.close()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed archive demo data for local/stage environments."
    )
    parser.add_argument(
        "--database-url",
        default=settings.DATABASE_URL,
        help="Override database url; defaults to settings.DATABASE_URL",
    )
    args = parser.parse_args(argv)

    seed_demo_archive(args.database_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
