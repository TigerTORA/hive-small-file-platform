# 本次重构计划（v1.0 → v1.1）

记录本轮重构的目标、范围、里程碑、任务清单与验收标准，作为实施与评审依据。

## 目标与成功标准
- 安全基线达标：收敛 CORS、密钥管理合规、移除危险工作流；无明文凭据。
- 路由与代码结构收敛：表相关 API 模块化（management/scanning/archiving），去重大文件与重复端点。
- CI 质量门槛恢复：单测覆盖率阈值逐步回升到 75% 且 PR 阶段不可忽略；关键路径最小 E2E 冒烟。
- 版本与依赖一致：统一 Python 版本、前端依赖收敛到 frontend/、构建与运行脚本一致。
- 部署连通性：本地 docker-compose、生产 compose 端口映射与反代一致，可直接访问。

## 范围
In scope（本轮纳入）：
- 安全与 CI 相关修复；表 API 路由拆分落地；依赖/版本一致化；构建/部署配置修复；仓库卫生。

Out of scope（暂不纳入）：
- 新功能开发；权限系统完整落地（仅预留接口与 TODO）；大规模性能优化。

## 里程碑（建议两周内完成）
1) M1 安全与 CI（D1–D2）[已合并]
2) M2 路由重构落地（D3–D4）[已合并]
3) M3 版本/依赖一致化（D5–D7）[已合并]
4) M4 构建/部署修复（D8–D9）[进行中]
5) M5 仓库卫生与文档（D10）
6) M6 最小 E2E 与收尾（D11–D12）[进行中]

## 任务清单（按优先级）

### P0 安全与 CI
- [ ] CORS 收敛：生产关闭 `*` + credentials，改环境白名单（backend/app/main.py:44）
- [ ] 加密密钥管理：生产强制从环境读取，缺失即启动失败；禁用明文日志（backend/app/utils/encryption.py）
- [ ] CI 门槛恢复：移除 `continue-on-error`，覆盖率阈值逐步回升到 ≥75%（.github/workflows/ci.yml）
- [ ] 危险工作流处理：默认禁用/删除紧急 SSH workflows 或加“受保护环境+审批”（.github/workflows/emergency-ssh-fix.yml, ssh-only-fix.yml）
- [ ] 明文凭据清理：测试脚本改为读 env（backend/test_mysql_connection.py）并迁移示例到 docs/

### P0 API 路由重构与去重
- [ ] 启用拆分后的路由聚合：在应用入口改为挂载 `tables_refactored.router`（backend/app/main.py）
- [ ] 去重与迁移：移除/废弃 `backend/app/api/tables.py` 中与 `table_management.py`、`table_scanning.py`、`table_archiving.py` 重复的端点
- [ ] 统一响应模型与错误处理：抛出 HTTPException + 结构化日志，去除 `print` 调试输出
- [ ] 补齐前端契约缺口：确认 clusters、tasks 日志查询等端点契合前端 API 客户端（frontend/src/api/*.ts）

### P1 版本与依赖一致化
- [ ] 统一 Python 版本（建议 3.11）：
  - Dockerfile 基础镜像（backend/Dockerfile）
  - CI 配置（.github/workflows/ci.yml）
  - mypy/black 配置（backend/pyproject.toml）
- [ ] Node 依赖收敛：移除根目录 Node 配置与依赖，统一在 `frontend/` 管理
- [ ] 前端依赖分层：将 `express/cors/puppeteer` 等仅本地/测试用途的包移至 devDependencies（frontend/package.json）
- [ ] ESLint 依赖补齐：添加 `@rushstack/eslint-patch` 或移除引用；补 `npm run lint/format` 并接入 `make check`

### P1 构建与部署
- [ ] docker-compose（dev）端口映射修复：前端容器为 Nginx 80，应为 `3000:80`（docker-compose.yml）
- [ ] 前后端基址一致：开发态 Vite 代理 `/api` → backend:8000；生产态前端 Nginx 反代 `/api` → backend
- [ ] Release 工作流校验：前端产物全部在 CI 预构建并 COPY（frontend/Dockerfile 与 .github/workflows/release.yml 保持一致）
- [ ] 部署工作流 SSH 凭据：改用 SSH key（appleboy/ssh-action `key:`），开启环境保护

### P2 仓库卫生
- [ ] .gitignore 覆盖日志/生成物（如 frontend/api-server.log、dist、*.db 等）
- [ ] 移除重复目录与无用文件（如 frontend/frontend/…）
- [ ] 清理控制台输出，统一结构化日志（logging/Sentry gated by env）

### P2 测试/E2E
- [ ] PR 阶段最小 E2E 冒烟：Playwright 基本打开与标题断言，限定 1–2 条（frontend/src/test/e2e）
- [ ] Nightly/手动环境运行完整 E2E 与视觉回归（单独工作流，不阻塞 PR）

## 验收标准（文件级）
- CORS：`backend/app/main.py` 使用环境白名单；生产默认不允许 `*` + credentials。
- 加密：`backend/app/utils/encryption.py` 生产缺密钥启动失败，且不打印明文密钥。
- CI：`.github/workflows/ci.yml` 去掉 `continue-on-error`，`--cov-fail-under` 提升；上传 coverage.xml。
- 路由：`backend/app/main.py` 引用 `app.api.tables_refactored:router`；`backend/app/api/tables.py` 删除或仅保留向后兼容转发。
- 依赖与版本：`backend/Dockerfile`、`backend/pyproject.toml`、`ci.yml` 中 Python 版本一致；根 Node 依赖清理；前端 devDependencies 调整。
- Compose：`docker-compose.yml` 前端端口映射修复为 `3000:80` 并可访问首页。
- 危险工作流：SSH 修复工作流禁用或受保护；部署工作流改 key 模式。
- 仓库卫生：误入库的日志/生成物不再被追踪；新增忽略规则。

## 风险与回滚
- 路由拆分导致的兼容性风险：保留兼容转发或 API 版本前缀（/api/v1/…）不变；必要时临时双栈。
- 版本统一的构建风险：先在分支与 CI 验证通过后再合并；保留 tag 回滚点。
- CI 门槛提高引发短期红灯：分阶段提升（如从 40% → 60% → 75%），并给出修复指引。

## 影响与沟通
- 运维：需更新部署流水线凭据方式与 compose 端口映射；Sentry DSN/白名单域配置。
- 前端：API 客户端契约校对；npm 脚本与 ESLint 更新；本地开发依赖更新。
- 后端：统一 Python 版本与工具链；日志与异常规范；Alembic 迁移策略确认（生产禁用自动建表）。

## 附录：参考路径
- CORS：backend/app/main.py:44
- 加密：backend/app/utils/encryption.py
- CI：.github/workflows/ci.yml
- 危险工作流：.github/workflows/emergency-ssh-fix.yml, .github/workflows/ssh-only-fix.yml
- 路由拆分：backend/app/api/tables_refactored.py, backend/app/api/table_management.py, backend/app/api/table_scanning.py, backend/app/api/table_archiving.py
- 端口映射：docker-compose.yml
- 版本配置：backend/Dockerfile, backend/pyproject.toml, .github/workflows/ci.yml
- 前端依赖与脚本：frontend/package.json, frontend/.eslintrc.cjs, frontend/vite.config.ts

—— 负责人：<Owner/Team>｜计划发布日期：<YYYY-MM-DD>｜文档版本：1.0
