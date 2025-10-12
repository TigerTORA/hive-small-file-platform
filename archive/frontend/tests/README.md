## Tests Directory Overview

- End-to-end Playwright specs live in `src/test/e2e/`. Run them via `npm run test:e2e` or `make e2e`.
- Visual regression specs remain under `tests/visual/` and are exercised through `npm run test:visual` commands.
- Legacy Node scripts in the project root (`frontend/test-*.js`, `frontend/manual-*.js`) are retained for historical/manual workflows; they are **not** part of the automated E2E pipeline and can be archived/removed once equivalent Playwright coverage exists.
