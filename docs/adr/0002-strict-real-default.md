# ADR 0002: Default strict_real for Scanning Endpoints

Date: 2025-09-14
Status: Proposed
Owners: @ops-owner

## Context
- Scanning relies on connecting both Hive MetaStore and HDFS to produce trustworthy metrics.
- In operations, we prefer correctness over silent fallbacks, especially for production decisions.
- Mock/HDFS-degraded mode is useful for demos and empty CI environments but should not mask real issues.

## Decision
- Default `strict_real = true` for critical scanning endpoints (cluster/db/table scans).
- Behavior when `strict_real = true`:
  - If HDFS/WebHDFS fails to connect, the API returns an error and does not fall back to mock.
  - MetaStore failures are also treated as fatal for the scan request.
- Keep API parameter `strict_real` so that callers can explicitly set `false` to allow mock fallback for demos.
- Frontend adds a visible toggle for "严格实连模式" with explanatory tooltip; default ON in production builds.

## Consequences
Positive
- Prevents misleading metrics and reduces risk of wrong optimization decisions.
- Fail-fast behavior shortens troubleshooting loops for connectivity and auth issues.

Negative / Trade-offs
- Environments that are not fully configured will see more failed scans.
- Requires clearer troubleshooting docs and a quick connection test flow (already available via cluster test endpoints).

## Alternatives Considered
- Default `strict_real = false`: fewer failures but higher risk of inaccurate data.
- Global env toggle only: simpler but less flexible per-request; API parameter provides better control.
- Separate endpoints for mock vs real: increases surface area without strong benefits.

## Rollout Plan
1) Ensure endpoints accept and default `strict_real = true` (already implemented for most routes).
2) Frontend exposes a toggle (default ON) under scan actions.
3) Update README and user docs to clarify behavior and fallback usage.
4) Add a short runbook section for connectivity troubleshooting (MetaStore/HDFS/Kerberos/LDAP).

## References
- Implementation points: `app/api/tables.py`, `HybridTableScanner.scan_database_tables` and `scan_table`.
- Connection testing: `clusters/{id}/test?mode=real` and `test-connection` endpoints.

