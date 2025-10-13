"""
Create test tables on a CDP Hive cluster defined in the app models.

Reads cluster connection info from the application's database (models.Cluster),
connects to Hive via PyHive, creates 10 compression-test tables and 10 archive-test tables,
adds one demo partition for each, and optionally materializes many tiny files under
the partition directory through WebHDFS so the platform can detect small files.

Usage examples:
  PYTHONPATH=backend python3 backend/scripts/create_cdp_test_tables.py \
    --cluster-name "CDP-14" --db cdp14_lab --prefix cdp14 --files-compress 20 --files-archive 8

  PYTHONPATH=backend python3 backend/scripts/create_cdp_test_tables.py \
    --cluster-id 1 --prefix cdp14

Notes:
  - Requires network access to HiveServer2 and WebHDFS of the target cluster.
  - If cluster.auth_type == LDAP and hive_password is not configured, the script
    attempts to connect with username only (depending on cluster config this may fail).
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.engines.connection_manager import HiveConnectionManager
from app.models.cluster import Cluster
from app.utils.webhdfs_client import WebHDFSClient


def _find_cluster(
    db: Session, cluster_id: Optional[int], cluster_name: Optional[str]
) -> Cluster:
    q = db.query(Cluster)
    if cluster_id is not None:
        c = q.filter(Cluster.id == cluster_id).first()
        if not c:
            raise SystemExit(f"Cluster id={cluster_id} not found")
        return c
    if cluster_name:
        c = q.filter(Cluster.name == cluster_name).first()
        if not c:
            raise SystemExit(f"Cluster name='{cluster_name}' not found")
        return c
    # Default: try the first cluster
    c = q.order_by(Cluster.id.asc()).first()
    if not c:
        raise SystemExit("No clusters found in database")
    return c


def _exec(cursor, sql: str):
    print(f"SQL> {sql}")
    cursor.execute(sql)


def _ensure_db(cursor, db_name: str):
    _exec(cursor, f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    _exec(cursor, f"USE `{db_name}`")


def _create_table(cursor, db_name: str, table_name: str):
    ddl = f"""
    CREATE EXTERNAL TABLE IF NOT EXISTS `{db_name}`.`{table_name}` (
      id BIGINT,
      name STRING,
      payload STRING,
      ts TIMESTAMP
    ) PARTITIONED BY (dt STRING)
    STORED AS TEXTFILE
    TBLPROPERTIES (
      'transactional'='false',
      'external.table.purge'='true'
    )
    """
    _exec(cursor, ddl)


def _add_partition(cursor, db_name: str, table_name: str, dt: str):
    _exec(
        cursor,
        f"ALTER TABLE `{db_name}`.`{table_name}` ADD IF NOT EXISTS PARTITION (dt='{dt}')",
    )


def _describe_location(cursor, db_name: str, table_name: str) -> Optional[str]:
    # Parse DESCRIBE FORMATTED to get table Location
    _exec(cursor, f"DESCRIBE FORMATTED `{db_name}`.`{table_name}`")
    rows = cursor.fetchall()
    for row in rows:
        # PyHive returns tuples; Location appears in first/second column depending on version
        try:
            col = (row[0] or "").strip().lower()
            if col == "location" or "location:" in col:
                # Value might be in row[1]
                loc = (row[1] or "").strip()
                return loc
        except Exception:
            continue
    return None


def _write_tiny_files(hdfs: WebHDFSClient, partition_path: str, count: int):
    ok, msg = hdfs.create_directory(partition_path)
    if not ok and "已存在" not in msg and "already exists" not in msg.lower():
        print(f"[WARN] create_directory failed for {partition_path}: {msg}")
    payload = b"demo-small-file\n"
    for i in range(1, count + 1):
        p = f"{partition_path.rstrip('/')}" + f"/part-{i:05d}.txt"
        ok, wmsg = hdfs.write_file(p, payload, overwrite=True)
        if not ok:
            print(f"[WARN] write_file failed: {p}: {wmsg}")


def create_test_tables(
    cluster: Cluster,
    db_name: Optional[str] = None,
    prefix: Optional[str] = None,
    compress_count: int = 10,
    archive_count: int = 10,
    dt: str = "2025-09-18",
    files_per_compress_table: int = 0,
    files_per_archive_table: int = 0,
) -> dict:
    """Create 10 compress and 10 archive test tables for the cluster.

    If files_per_* > 0, writes that many tiny files under each table's demo partition via WebHDFS.
    """
    db = db_name or (cluster.hive_database or "default")
    pref = prefix or (cluster.name or "cdp").lower().replace(" ", "")

    manager = HiveConnectionManager(cluster)
    with manager.get_hive_connection(db) as conn:
        cursor = conn.cursor()
        _ensure_db(cursor, db)

        created = []
        # Compression test tables
        for i in range(1, compress_count + 1):
            t = f"{pref}_compress_{i:02d}"
            _create_table(cursor, db, t)
            _add_partition(cursor, db, t, dt)
            created.append((t, "compress"))

        # Archive test tables
        for i in range(1, archive_count + 1):
            t = f"{pref}_archive_{i:02d}"
            _create_table(cursor, db, t)
            _add_partition(cursor, db, t, dt)
            created.append((t, "archive"))

        # Materialize tiny files if requested
        if files_per_compress_table > 0 or files_per_archive_table > 0:
            hdfs = WebHDFSClient(
                cluster.hdfs_namenode_url, user=cluster.hdfs_user or "hdfs"
            )
            try:
                for t, kind in created:
                    loc = _describe_location(cursor, db, t)
                    if not loc:
                        print(
                            f"[WARN] Cannot resolve location for {db}.{t}, skip files"
                        )
                        continue
                    part_path = f"{loc.rstrip('/')}/dt={dt}"
                    n = (
                        files_per_compress_table
                        if kind == "compress"
                        else files_per_archive_table
                    )
                    if n > 0:
                        print(f"Materializing {n} tiny files under {part_path} ...")
                        _write_tiny_files(hdfs, part_path, n)
            finally:
                try:
                    hdfs.close()
                except Exception:
                    pass

        return {
            "cluster_id": cluster.id,
            "cluster_name": cluster.name,
            "database": db,
            "prefix": pref,
            "tables_created": [f"{db}.{name}" for name, _ in created],
            "partition_dt": dt,
            "files_per_compress_table": files_per_compress_table,
            "files_per_archive_table": files_per_archive_table,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Create CDP test tables using cluster model"
    )
    parser.add_argument(
        "--cluster-id", type=int, default=None, help="Cluster id (optional)"
    )
    parser.add_argument(
        "--cluster-name", type=str, default=None, help="Cluster name, e.g., CDP-14"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Target database (default: cluster.hive_database)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=None,
        help="Table name prefix (default: normalized cluster name)",
    )
    parser.add_argument("--compress-count", type=int, default=10)
    parser.add_argument("--archive-count", type=int, default=10)
    parser.add_argument(
        "--dt", type=str, default="2025-09-18", help="Partition value for dt"
    )
    parser.add_argument(
        "--files-compress",
        type=int,
        default=0,
        help="Create N tiny files per compress table",
    )
    parser.add_argument(
        "--files-archive",
        type=int,
        default=0,
        help="Create N tiny files per archive table",
    )

    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        cluster = _find_cluster(db, args.cluster_id, args.cluster_name)
        print(f"Using cluster: {cluster.id} - {cluster.name}")
        print(
            f"HiveServer2: {cluster.hive_host}:{cluster.hive_port}, DB: {args.db or cluster.hive_database or 'default'}"
        )
        print(f"MetaStore: {cluster.hive_metastore_url}")
        print(f"WebHDFS: {cluster.hdfs_namenode_url} (user={cluster.hdfs_user})")

        t0 = time.time()
        result = create_test_tables(
            cluster,
            db_name=args.db,
            prefix=args.prefix,
            compress_count=args.compress_count,
            archive_count=args.archive_count,
            dt=args.dt,
            files_per_compress_table=args.files_compress,
            files_per_archive_table=args.files_archive,
        )
        dt_ms = int((time.time() - t0) * 1000)
        print("---")
        print("Completed in", dt_ms, "ms")
        print("Database:", result["database"])
        print("Created tables:")
        for t in result["tables_created"]:
            print(" -", t)
        print("Partition dt:", result["partition_dt"])
        print(
            "Tiny files per table (compress/archive):",
            result["files_per_compress_table"],
            "/",
            result["files_per_archive_table"],
        )

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
