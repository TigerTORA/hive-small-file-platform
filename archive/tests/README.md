# Archived manual tests

The files under `archive/tests/` capture one-off HTML/JS/Python probes that were
formerly checked into the repository root for manual verification:

- `manual/` contains ad-hoc dashboards (`test_frontend_logs.html`, `test_logs_debug.html`),
  API pokers (`test_frontend_api.js`), and quick-load scripts (`test_load_function.*`)
  that rely on demo data only.
- `sample_smallfiles/` mirrors the tiny text fixtures that previously lived in
  `.tmp_smallfiles/` so we still have reference payloads without keeping them at repo root.

These helpers are **not** part of CI or automated demo flows. Keep them here for
reference, or copy them into a sandbox when debugging. Please avoid adding new
root-level `test_*.py`/`.js` files—prefer `backend/tests/` or `frontend/src/test/`.
