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

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_ROOT = os.path.join(REPO_ROOT, 'backend')
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from scripts.seed_demo_archive import seed_demo_archive  # type: ignore
from app.config.settings import settings  # type: ignore


def main() -> None:
    seed_demo_archive(settings.DATABASE_URL)
    print("Done. You can now run:")
    print("  cd backend && uvicorn app.main:app --reload --port 8000")
    print("  curl -X POST 'http://localhost:8000/api/v1/table-archiving/archive-with-progress/<cluster_id>/default/t1'")
    print("Then watch logs at: GET /api/v1/scan-tasks/{task_id}/logs")


if __name__ == '__main__':
    main()
