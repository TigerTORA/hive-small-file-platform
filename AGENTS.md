# Repository Guidelines

## Project Structure & Module Organization
- Backend (`backend/app`): FastAPI app, routers under `api/`, engines under `engines/`, jobs under `scheduler/`, ORM in `models/`, settings in `config/`.
- Frontend (`frontend/src`): Vue 3 + TS; components in `components/`, pages in `views/`, API clients in `api/`, tests in `src/test/` (plus some root `test-*.js`).
- Tests: Python tests live in `backend/tests` and `backend/test_*.py` (pytest discovers both).
- Scripts: `scripts/` contains project status and quality helpers.

## Build, Test, and Development Commands
- Bootstrap: `make setup` (sets `.githooks`, installs backend/frontend deps).
- Run backend: `cd backend && uvicorn app.main:app --reload`.
- Run frontend: `cd frontend && npm run dev`.
- Format & Lint: `make format` (Black/isort) and `make check` (Black, isort, Flake8; frontend lint optional).
- Tests (all): `make test` (pytest + vitest). CI mode: `make ci-test`.
- Images: `make build-images` then `docker-compose.prod.yml` or `docker-compose up -d` for local stacks.

## Coding Style & Naming Conventions
- Python: Black 88 cols, isort profile=black, Flake8 ignores `E203,W503,E501`; 4‑space indent; modules/functions `snake_case`, classes `PascalCase`. Type hints required for new public funcs (MyPy enabled).
- Vue/TS: Prefer Composition API + TypeScript. Components `PascalCase.vue`; composables/util fns `camelCase.ts`.
- Keep functions small; avoid unrelated refactors in a single PR.

## Testing Guidelines
- Backend: pytest with markers (`unit`, `integration`, `e2e`, `slow`), coverage threshold 75% (see `backend/pytest.ini`).
  - Run: `cd backend && pytest -m unit -q` or `pytest -v`.
  - Naming: `test_*.py`, test classes `Test*`, test funcs `test_*`.
- Frontend: Vitest for unit (`npm run test:run`, `npm run test:coverage`), Playwright for e2e (`npm run test:e2e`). Add tests near code or under `src/test/`.

## Commit & Pull Request Guidelines
- Conventional Commits: `feat:`, `fix:`, `chore:`, `ci:`, `test:` … Example: `fix(frontend): correct table resize jitter`.
- PRs must include: clear description, rationale, linked issues, test plan, and screenshots/GIFs for UI changes. Ensure `make check` and `make test` pass; update docs when behavior changes.

## Security & Configuration Tips
- Never commit secrets. Copy `.env.example` to `.env` (backend/front). In prod, disable auto schema creation and use Alembic. Sentry DSN optional; set via env.

## Agent-Specific Instructions
- Follow this file’s scope repo‑wide. Prefer Makefile tasks; match existing style; keep patches minimal and focused; update or add tests with new code.
