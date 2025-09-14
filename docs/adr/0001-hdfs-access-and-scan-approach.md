# ADR 0001: HDFS Access and Scan Approach

Date: 2025-09-14
Status: Accepted
Owners: @ops-owner

## Context
We need reliable file statistics (file count, small files, total size) for Hive tables
without installing heavy native dependencies on the app side. Environments vary (CDH/CDP),
and ops prefers simple HTTP connectivity. Kerberos may exist but is not always required.

## Decision
- Use WebHDFS/HttpFS over HTTP as the primary access method.
- Prefer GETCONTENTSUMMARY for fast stats; if insufficient, do shallow sampling to estimate small-file counts.
- Implement intelligent fallback (multi-port attempts 9870/50070, httpfs:14000) and mock mode for demos.
- Keep strict_real flag (default true in critical endpoints) to fail fast when real HDFS is unavailable.

## Consequences
Positive
- Works across clusters with only HTTP access; easy to operate.
- Faster for common cases (content summary) and acceptable estimates when needed.

Negative / Trade-offs
- Sampling can under/over-estimate small-file counts; document the behavior.
- HttpFS configurations vary; need clear troubleshooting docs.
- Kerberos is optional; when required, additional setup is needed (requests-gssapi).

## Alternatives Considered
- Native HDFS clients (hdfs3/pyarrow): better performance but heavier deps and ops cost.
- Shelling out to hdfs CLI: operationally brittle and harder to containerize.

## References
- Implementation: `app/utils/webhdfs_client.py`, `app/monitor/webhdfs_scanner.py`.
- Related: `HybridTableScanner` (strict_real, mock fallback).

