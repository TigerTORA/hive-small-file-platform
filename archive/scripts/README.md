# Archived & Legacy Scripts

Scripts stored here depend on Hive clusters, Docker Compose stacks, or bespoke
ops tooling that we no longer ship as part of the default demo. They are kept
for reference only.

Current layout:
- `demo_small_files.sh`: demo-era helper that orchestrated Hive small-file scans.
- `legacy/`: Hive/ops automation helpers (docker bootstrap, CDP setup, etc.).
  - `legacy/create_test_external_table.sh` + `test-table-config.conf`: Hive test-table generator.
  - `legacy/verify_test_table.sh`: verification helper for Hive tables.
  - `legacy/calculate_monthly_data.sh`, `legacy/monthly_data_commands.md`: ad-hoc reporting helpers.
  - `legacy/install_runner_docker.sh`: GitHub runner helper.

If you need these flows, copy them back to `scripts/` and re-enable the live Hive
infrastructure manually. Demo mode and CI do not invoke anything under `archive/scripts/`.
