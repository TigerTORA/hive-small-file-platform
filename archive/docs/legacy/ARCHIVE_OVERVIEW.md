# Archive directory layout

The `archive/` tree stores historical artifacts that we still want available but
do not want cluttering the active workspace. Nothing here is required for the
default demo profile or CI workflows.

## Top-level areas

- `archive/docs/` – legacy design docs, E2E walkthroughs, and historical reports
  (moved from `docs/`). Consult `archive/docs/E2E_TEST.md` for the full live
  cluster E2E guide.
- `archive/frontend/` – deprecated Vue components, storyboards, and prototyping
  assets that do not belong in the production build.
- `archive/internal/` – scratch data, spike notebooks, or operational exports.
- `archive/reports/` – generated HTML dashboards and data exports kept for audit.
- `archive/screenshots/` – UI screenshots and Playwright captures. Includes the
  legacy `screenshot_dashboard.js` harness and historical Playwright exports
  under `archive/screenshots/playwright-mcp/legacy/`.
- `archive/scripts/` – demo/ops scripts no longer wired into the public CLI.
- `archive/tests/` – manual/debugging-only test harnesses (`manual/` subfolder).

## Usage guidelines

1. Treat `archive/` as **read-only** for day-to-day development. Copy assets out
   if you need to run them.
2. When retiring a doc or helper, move it into the relevant archive subfolder
   instead of deleting it outright. Add a short pointer from the active doc (if
   any consumers remain).
3. Avoid committing temporary data (logs, JSON dumps). Prefer `make clean`
   or `scripts/cleanup_workspace.py` to purge them locally.
