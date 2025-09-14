# ADR 0003: Unify Celery Scan Tasks to HybridTableScanner

Date: 2025-09-14
Status: Proposed
Owners: @ops-owner

## Context
- Celery tasks used `TableScanner` which depended on a legacy `HDFSScanner` module that is not present in the codebase anymore.
- The REST API has moved to `HybridTableScanner`, which integrates MetaStore (MySQL/Postgres) and WebHDFS/HttpFS with graceful fallback and stricter `strict_real` semantics.
- Maintaining two scanning paths risks drift and inconsistent results.

## Decision
- Replace Celery scan task implementations to use `HybridTableScanner` exclusively.
- Use MetaStore to enumerate databases (via `MySQLHiveMetastoreConnector`) and call `HybridTableScanner.scan_database_tables` per database so that table metrics are persisted uniformly.
- Default to `strict_real=True` in Celery tasks to ensure production correctness; errors are captured and returned per-database.

## Consequences
Positive
- Single source of truth for scanning behavior and persistence logic.
- Less maintenance and fewer hidden dependencies.

Trade-offs
- Slight behavior difference vs legacy `TableScanner` return structure; we normalize the aggregate summary to keep compatibility for callers of the Celery result.

## Rollout Plan
1) Update `app/scheduler/scan_tasks.py` to import and use `HybridTableScanner` and `MySQLHiveMetastoreConnector`.
2) Keep task names unchanged for backward compatibility.
3) Validate on a staging cluster; confirm `table_metrics` are written as before.

## References
- `app/monitor/hybrid_table_scanner.py`
- `app/monitor/mysql_hive_connector.py`

