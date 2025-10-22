# 仓库指南（Repository Guidelines）

## 项目结构与模块组织
- `backend/`：FastAPI 服务。核心在 `app/`（API、models、services），配置在 `app/config/`，执行引擎在 `app/engines/`。测试位于 `tests/` 及根目录的 `test_*.py`。
- `frontend/`：Vue 3 + Vite。代码在 `src/`（components、stores、utils），单测为 `*.test.ts`，E2E 使用 Playwright 配置。
- `scripts/`：状态汇总、覆盖率校验、清理等脚本；`docs/`：文档与报告；`.githooks/`：本地 Git 钩子。

## 构建、测试与本地开发
- `make setup`：安装后端（pip）与前端（npm）依赖并设置钩子。
- `make dev`：同时启动后端（Uvicorn `:8000`）与前端（Vite）。
- `make check`：后端 Black/isort/Flake8，自检；前端 Lint 需 Node 20（`nvm use`）。
- `make test`：后端缓存模式用例 + 前端 Vitest。
- 后端：`cd backend && pytest -m 'unit or integration'`。
- 前端：`cd frontend && npm run test:run`（或 `test:coverage`、`test:e2e`）。
- 容器：`make build-images` 构建镜像，`make release-save` 导出至 `dist/`。

## 代码风格与命名约定
- Python（3.10+，工具目标 3.11）：Black（88 列）、isort（profile=black）、Flake8、MyPy；4 空格缩进；文件 `snake_case.py`；类 `PascalCase`。
- 前端（Node 20）：Prettier 格式化、TypeScript；Vue 组件 `PascalCase.vue`；工具 `camelCase.ts`；测试 `*.test.ts`。

## 测试规范
- 后端：Pytest 标记（`unit`、`integration`、`e2e`、`slow`），覆盖率阈值 75%（`--cov=app`）。示例：`pytest -m unit -q`。
- 前端：Vitest 单元/集成（`npm run test:run`），覆盖率（`test:coverage`），E2E 使用 Playwright（`test:e2e`）。UI 变更请在 PR 附截图/日志。

## 提交与合并请求
- 使用 Conventional Commits：`feat:`、`fix:`、`docs(scope):`、`chore:`（建议写 scope）。
- PR 需包含：变更摘要、关联 Issue、复现与测试步骤、UI 截图（如有）、风险与回滚说明。
- 合并前请确保本地 `make check`、`make test` 通过，CI 绿。

## 安全与配置
- 禁止提交密钥。请基于 `backend/.env.example` 与 `frontend/.env.example` 生成本地 `.env`。
- 使用 `nvm use`（见 `.nvmrc`）与 Python 3.10+ 环境（工具目标 3.11）。
- 测试优先使用本地数据库与示例数据，避免改动生产资源。

## Agent 说明
- 先前位于根目录的 BMAD 多代理文档已迁移至 `docs/AGENTS_BMAD.md`，包含角色、命令与流程说明。
