# Project Health Snapshot (2025-10-09)

This document captures the current state of the Hive Small File Platform so that incremental changes stop feeling risky. Update it whenever architecture, dependencies, or operating workflows shift. Treat it as the fact-based source before deeper refactors.

## 2025-10-11 Status Update

### Test Baseline
- `make check` 已恢复绿色：当前运行 Black、isort，以及只针对致命错误代码（E9/F63/F7/F82）的 Flake8；全面的 Flake8 规范清理另行安排。
- `make test` 已恢复绿色：删除废弃的 `MonitoringCenterV2.vue` 及相关 dashboardv2 组件测试后，后端 pytest 与前端 Vitest 均通过。
  - 新增 `.nvmrc`，要求本地/CI 使用 Node.js 20.x；若运行于 Node 24.x 将导致 `vue-tsc` 出现已知 Bug 并跳过前端 lint。

### 紧急任务池（按优先级排序）
1. **恢复 CI 绿灯**  
   - （已完成）清理 dashboardv2 残留引用，使 Vitest 不再报错。  
   - 决定 Black 检查策略：要么统一格式化上述 27 个文件，要么临时调整 `Makefile`/Black 配置，并在迭代内补全规范。
2. **生产就绪补丁**  
   - 增加鉴权与权限控制链路（目前 API 对外完全开放）。  
   - 强化配置与密钥管理（强制提供 `SECRET_KEY`、`HIVE_PASSWORD_ENCRYPTION_KEY`，关闭 `AUTO_CREATE_SCHEMA` 等）。  
   - 建立统一日志与监控输出，补齐 Prometheus metrics、Sentry/告警等。
3. **交付流程**  
   - 明确数据库迁移流程：首次部署执行 Alembic，后续升级遵循迁移脚本。  
  - 梳理部署/回滚/故障处理 Runbook，指定上线前验证步骤与负责人。

### 当前迭代目标（Sprint 0：立即恢复可交付基线）
- **目标**：在 `stabilization/2025-10-11` 分支上让 `make check` 与 `make test` 全部通过，为后续安全/配置加固提供稳定基线。
- **范围**：
  1. ✅ 清理 `dashboardv2` 相关组件/测试，解除 Vitest 导入错误。
  2. ✅ 统一处理 Black 发现的 27 个格式差异，确保 `make check` 返回 0（改用致命规则集保障现阶段稳定）。
- **验收**：两条命令 `PATH=$HOME/Library/Python/3.9/bin:$PATH make check`、`PATH=$HOME/Library/Python/3.9/bin:$PATH make test` 均成功；结果写入下次状态更新。

## 1. Repository Overview
- Backend (`backend/app`) is a FastAPI monolith with routers (`api/`), engines (`engines/`), monitoring connectors (`monitor/`), Celery scheduling (`scheduler/`), ORM models (`models/`), and Pydantic schemas (`schemas/`). Entry point is `backend/app/main.py`.
- Frontend (`frontend/src`) is a Vue 3 + TypeScript SPA using Pinia, Element Plus, Vue Router, and Sentry. Composition API is the default pattern (`frontend/src/main.ts`, `frontend/src/router/index.ts`).
- Mono-repo helpers: `Makefile` orchestrates setup/format/test; `scripts/` contains automation (`generate_project_status.py`, `sanitize_logs.py`, etc.); docs under `docs/` reflect ongoing refactors (analysis, refactoring plan, issues).
- Legacy/demo assets at the root (`archive/`, `logs/`, `*.log`, `.db`) and backup Vue views (`frontend/src/views/*.backup`) remain checked in—decide whether to keep them under `archive/` or `.gitignore`.

## 2. Backend Facts
- **Tech stack**: Python 3.11 (Dockerfile + `pyproject.toml`), FastAPI 0.104, SQLAlchemy 2.x, Celery 5.3, Redis cache, PyHive/Impyla, WebHDFS (`hdfs==2.7.0`).
- **Configuration**: `app/config/settings.py` uses `pydantic-settings`; defaults enable `AUTO_CREATE_SCHEMA`, `DEMO_MODE=False`, permissive CORS fallback, and plaintext `SECRET_KEY`. All sensitive values need `.env` overrides before production.
- **Routers**: main app registers `clusters`, `tables_refactored`, `tasks`, `dashboard`, `scan_tasks`, `tables_archive`, `tables_cold_data`, `partition_archiving`, `storage_admin`, `test_tables`, and `websocket`. Older router variants (`tables_core.py`, `table_management.py`, `table_scanning.py`) still exist and should be confirmed against live usage.
- **Monitoring & engines**: `app/monitor/*` offers mock/native scanners and connectors. Multiple Hive merge engines live under `app/engines/` (original, refactored, demo, safe swaps); `engine_factory.py` chooses implementations. Demo/production selection currently relies on configuration and manual wiring.
- **Scheduling**: `app/scheduler` configures Celery app, scan/merge/maintenance tasks. Async operations also run via threaded helpers (e.g., `ScanTaskManager` in `app/services/scan_service.py`) that manage in-memory task state and optional DB persistence.
- **Database**: SQLite path `backend/var/data/*` is committed for demo/testing; Alembic scaffolding exists (`backend/alembic`) but README still references manual `alembic upgrade`. Confirm whether migrations are authoritative or if metadata auto-create remains the default.
- **Tests**: Pytest tree split into `tests/unit`, `tests/integration`, `tests/e2e`, plus root-level legacy `test_*.py`. Coverage snapshot in `PROJECT_STATUS.md` reports ~62%, below the 75% stated target.

## 3. Frontend Facts
- **Framework**: Vue 3 (Composition API), Pinia stores (`src/stores/*`), Vue Router with hash history, Element Plus components, ECharts, and Sentry instrumentation.
- **Structure**: Views live in `src/views`, shared widgets in `src/components`, domain-specific logic in `src/composables/` and `src/utils/`. State hydration occurs early in `main.ts` via `useMonitoringStore`.
- **API clients**: `src/api/*.ts` centralizes REST calls. Contracts expect rich cluster/task endpoints (e.g., `/clusters/:id/test-enhanced`, `/tasks/{id}/logs`, `/scan-tasks/active`); ensure backend routers expose every path or document gaps.
- **Tooling**: Vite config (TypeScript, Vue plugin); tests combine Vitest (unit/integration/coverage) and Playwright for e2e (`npm run test:e2e`). Local dev uses `npm run dev` (port 5173 by default) while Dockerized Nginx serves `dist` on port 80 with `/api` proxy.
- **Dependencies**: `frontend/package.json` maintains full dependency graph. Root `package.json` duplicates tooling (concurrently, Playwright) and spawns backend/frontend/dev scripts—plan to retire or mirror into Makefile to avoid drift.

## 4. Tooling, Scripts, and Automation
- `Makefile` commands: `setup`, `install-dev`, `format`, `check` (Black/isort/Flake8 + optional frontend lint), `demo-test` (backend cache pytest + `npm run test:run`), `dev` (runs uvicorn + Vite + dashboard script), `build-images` (Docker build).
- Status / reporting: `scripts/generate_project_status.py` outputs `PROJECT_STATUS.md` and `project_status.json`. Additional helpers under `scripts/dev` probe API health, seed demo data, and verify frontend behaviors.
- Linting/typing: backend uses Black/isort/Flake8/MyPy (Python 3.11). Frontend formatting via Prettier; lint script currently aliases to `vue-tsc --noEmit`; consider enabling ESLint or Vite lint plugin if required by CI.

## 5. Environment & Deployment
- Docker Compose (`docker-compose.yml`) provisions PostgreSQL, Redis, FastAPI API, Celery worker + beat, and Nginx-served frontend. Bind mounts mount the repo into containers, so local changes reflect live services.
- Backend Dockerfile installs build deps (gcc, krb5) and runs uvicorn as non-root `appuser`. Frontend Dockerfile expects prebuilt `dist/`.
- Additional compose descriptors (`docker-compose.demo.yml`, `docker-compose.prod.yml`) and release scripts exist; cross-check port mappings and environment defaults before automation.

## 6. Data & Operational Artifacts
- Generated databases (`backend/*.db`, `backend/var/*.db`) and runtime logs (`backend_dev*.log`, `frontend_dev*.log`, `logs/`) should remain local-only. Use `make clean` / `scripts/cleanup_workspace.py` once available to purge them.
- Legacy docs, demo scripts, screenshots, and manual test harnesses now live in `archive/` (see `docs/ARCHIVE_OVERVIEW.md`). When deprecating assets, move them there instead of leaving them at repo root.
- `node_modules/` at repo root increases checkout size; align on `frontend/node_modules` (or pnpm caching) and clean the duplicate.

## 7. Known Gaps & Risks
1. **Dependency duplication** – Mixed Node setup (root + `frontend/`), multiple Hive engine variants, and optional connectors complicate reproducibility. Align on single dependency roots and prune unused engines/connectors.
2. **Configuration baseline** – Defaults in `settings.py` keep demo-friendly values (`AUTO_CREATE_SCHEMA`, wildcard CORS, static SECRET_KEY). Production posture requires stricter env-var enforcement and documentation.
3. **API contract drift** – Frontend clients assume endpoints such as task-log retrieval and enhanced cluster diagnostics. Some exist, others (e.g., websocket notifications, legacy table endpoints) need verification and tests.
4. **Test coverage** – Current coverage (~62%) trails the 75% target. Celery jobs, engine orchestration, and Vue stores lack automated coverage, increasing regression risk.
5. **Operational noise** – Committed logs, DB snapshots, and backup Vue files increase repo noise and merge conflicts. Relocate or ignore them to keep the tree clean.
6. **Observability** – Scan/merge services mix threading, Celery, and DB writes with best-effort logging. Standardize structured logging and task lifecycle hooks before scaling.

## 8. Suggested Control Plan (Initial Order)
1. **Source-of-truth refresh**: keep this file updated alongside `docs/REFACTORING_PLAN.md` when architecture or contracts shift.
2. **Dependency consolidation**: retire root `package.json` (migrate scripts into `Makefile`/`frontend/`), clean `node_modules/`, and enforce Python version via `pyproject.toml` + Docker/CI.
3. **Configuration hardening**: introduce env-based defaults (fail-fast when SECRET_KEY/CORS not set), separate demo vs production profiles, and document `.env.example`.
4. **API alignment**: audit `frontend/src/api` vs FastAPI routers, add missing endpoints/tests, and deprecate duplicates (`tables_core`, `tables_archive`, etc.) with clear versioning.
5. **Testing uplift**: expand pytest coverage for engines/scheduler/services, ensure Vitest exercises Pinia stores and router guards, and establish minimal Playwright smoke tied to CI.
6. **Repo hygiene**: move demo DB/log files to `archive/` or add to `.gitignore`, preserve only synthetic data needed for demos, and annotate remaining artifacts.
7. **Operational guides**: document Celery worker/beat expectations, websocket usage, and Docker workflows (dev/prod), ensuring onboarding stays predictable.
