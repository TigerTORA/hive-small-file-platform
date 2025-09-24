#!/usr/bin/env python3
"""
Seed a minimal demo cluster and one table metric for archive E2E.

It creates:
- Cluster: name='demo-archive', hive_metastore_url='mysql://root:pass@127.0.0.1:3306/hive'
  (no real connection is made; SimpleArchiveEngine will fall back to TableMetric.table_path)
- TableMetric: cluster_id -> the demo cluster, database 'default', table 't1',
  table_path set to a plausible HDFS path, is_cold_data=1, archive_status='active'.

After seeding, you can start the backend and frontend and trigger archive from UI
or call the API: POST /api/v1/table-archiving/archive-with-progress/{cluster}/{db}/{table}
"""
from __future__ import annotations

import sys
import os
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_ROOT = os.path.join(REPO_ROOT, 'backend')
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.config.settings import settings  # type: ignore
from app.config.database import Base  # type: ignore
from app.models.cluster import Cluster  # type: ignore
from app.models.table_metric import TableMetric  # type: ignore


def main() -> None:
    engine = create_engine(settings.DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        # Create or get demo cluster
        cluster = db.query(Cluster).filter(Cluster.name == 'demo-archive').first()
        if not cluster:
            cluster = Cluster(
                name='demo-archive',
                description='Local demo cluster for archive E2E',
                hive_host='127.0.0.1',
                hive_port=10000,
                hive_database='default',
                # No real MySQL needed; engine now falls back to TableMetric.table_path
                hive_metastore_url='mysql://root:pass@127.0.0.1:3306/hive',
                # HDFS URL format is validated only by prefix; real connection will simulate
                hdfs_namenode_url='http://127.0.0.1:9870',
                hdfs_user='hdfs',
                small_file_threshold=128 * 1024 * 1024,
                status='active',
                scan_enabled=True,
                archive_enabled=True,
                archive_root_path='/archive'
            )
            db.add(cluster)
            db.commit()
            db.refresh(cluster)
            print(f"Created cluster id={cluster.id} name={cluster.name}")
        else:
            print(f"Using existing cluster id={cluster.id} name={cluster.name}")

        # Upsert one table metric for default.t1
        tm = (
            db.query(TableMetric)
            .filter(
                TableMetric.cluster_id == cluster.id,
                TableMetric.database_name == 'default',
                TableMetric.table_name == 't1',
            )
            .order_by(TableMetric.id.desc())
            .first()
        )
        if not tm:
            tm = TableMetric(
                cluster_id=cluster.id,
                database_name='default',
                table_name='t1',
                # plausible HDFS path (no real NN needed for demo)
                table_path='hdfs://nameservice1/user/hive/warehouse/default.db/t1',
                table_type='MANAGED_TABLE',
                storage_format='PARQUET',
                input_format='org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
                output_format='org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
                serde_lib='org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe',
                table_owner='hive',
                total_files=12,
                small_files=9,
                total_size=1024 * 1024 * 256,
                avg_file_size=int((1024 * 1024 * 256) / max(12, 1)),
                is_partitioned=0,
                partition_count=0,
                scan_time=datetime.utcnow(),
                is_cold_data=1,
                archive_status='active',
            )
            db.add(tm)
            db.commit()
            print("Seeded table metric default.t1 (cold, active)")
        else:
            # ensure cold + active
            tm.is_cold_data = 1
            tm.archive_status = 'active'
            if not tm.table_path:
                tm.table_path = 'hdfs://nameservice1/user/hive/warehouse/default.db/t1'
            db.commit()
            print("Updated existing table metric to cold+active")

        print("Done. You can now run:")
        print("  cd backend && uvicorn app.main:app --reload --port 8000")
        print("  curl -X POST 'http://localhost:8000/api/v1/table-archiving/archive-with-progress/%d/default/t1'" % cluster.id)
        print("Then watch logs at: GET /api/v1/scan-tasks/{task_id}/logs")
    finally:
        db.close()


if __name__ == '__main__':
    main()
