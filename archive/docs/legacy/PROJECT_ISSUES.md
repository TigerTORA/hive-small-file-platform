#+ 项目问题清单与修复建议

记录时间：2025-09-08

本文汇总当前代码库中发现的问题、不一致与建议修复路径，供排期与跟进。

## 1) 依赖不一致（HDFS 客户端）
- 问题：`HDFSScanner` 使用 `from hdfs3 import HDFileSystem`，但 `backend/requirements.txt` 仅包含 `hdfs==2.7.0`，未包含 `hdfs3`。
- 影响：真实 HDFS 扫描将发生 ImportError 或运行时异常；仅能依赖 Mock 扫描器演示。
- 修复建议：
  - 方案 A：在 `requirements.txt` 增加 `hdfs3`，并确认镜像系统依赖（libhdfs/native 相关）可用；
  - 方案 B（推荐稳妥）：改造 `HDFSScanner` 使用 `hdfs`(WebHDFS) 客户端，避免 `hdfs3` 的原生依赖问题；通过配置切换 mock/real。

## 2) API 与前端契约不匹配
- 问题：
  - 前端调用 `PUT /api/v1/clusters/{id}`、`DELETE /api/v1/clusters/{id}`，但 `backend/app/api/clusters.py` 未实现更新/删除；
  - 前端调用 `GET /api/v1/tasks/{id}/logs`，但 `backend/app/api/tasks.py` 未提供日志查询路由（虽有 `TaskLog` 模型）。
- 影响：相关前端操作将 404/失败。
- 修复建议：
  - 在 `clusters.py` 实现更新与删除路由，遵循既有 Pydantic 模型；
  - 在 `tasks.py` 增加 `GET /{task_id}/logs`，支持分页/排序（按 `timestamp` 降序）。

## 3) 文档与代码不一致（Alembic 迁移缺失）
- 问题：README/CLAUDE.md 引导执行 `alembic upgrade head`，但仓库未包含 `alembic.ini` 与 `migrations/`。
- 影响：新环境会因缺少迁移而困惑；当前仅依赖 `Base.metadata.create_all` 自动建表，缺少版本化能力。
- 修复建议：
  - 方案 A：补齐 Alembic 初始化与首次迁移；
  - 方案 B：若短期不使用迁移，更新文档移除相关命令，明确采用自动建表策略。

## 4) Docker Compose 前端端口映射错误
- 问题：`frontend` 镜像以 Nginx 方式提供静态站点（容器监听 80），`docker-compose.yml` 却配置端口映射 `"3000:3000"`。
- 影响：宿主机 3000 端口无服务监听，无法访问前端。
- 修复建议：将端口映射改为 `"3000:80"`。

## 5) 安全与认证未落地
- 问题：前后端留有 TODO（请求拦截器未注入 token、后端无鉴权中间件）。
- 影响：生产环境缺少基本访问控制与审计能力。
- 修复建议：
  - 后端增加 JWT 认证（登录/刷新/权限），对敏感路由加依赖；
  - 前端在 Axios 拦截器注入 token，处理 401 重定向登录；
  - 收敛 CORS 与秘钥管理（从环境变量读取）。

## 6) 测试脚本包含硬编码敏感信息
- 问题：`backend/test_mysql_connection.py` 硬编码了 MySQL 地址与密码。
- 影响：泄漏风险；不利于多环境复用。
- 修复建议：改为从环境变量读取连接串，并将示例迁移为 `.env.example`；必要时将该脚本移出主仓库或标注为示例脚本。

## 7) 生产/开发扫描器混用
- 问题：API 多处使用 `MockTableScanner`（演示），生产应使用 `TableScanner`（真实连接 Hive MetaStore 与 HDFS）。
- 影响：演示数据与真实环境不一致，易引发误判。
- 修复建议：
  - 增加配置开关（如 `USE_MOCK_SCANNER`），开发默认使用 mock，生产强制使用真实扫描器；
  - 在路由中按配置注入对应 Scanner 实现。

## 8) 启动脚本/流程的统一性
- 问题：`start.sh` 同时使用 `docker run` 与 `docker-compose` 的混合方式，且端口占用检测依赖 `lsof`（部分环境缺少）。
- 影响：使用路径不统一，提升上手复杂度。
- 修复建议：统一用 `docker-compose up -d` 启动全部服务；端口检测作为可选步骤或使用 cross-platform 方案。

---

## 变更建议一览（可直接排期）
1. 修复 `docker-compose.yml` 前端端口映射（3000:80）。
2. 在后端补齐 `clusters` 更新/删除与 `tasks` 日志查询路由。
3. 决策 HDFS 客户端路线（`hdfs3` vs WebHDFS），并完成依赖/实现对齐。
4. 文档与 Alembic 迁移策略一致化（补迁移或更新说明）。
5. 最小可用认证改造（JWT + 前端拦截器）。
6. 清理硬编码凭据，改为环境变量方案。
7. 增加 mock/real 扫描器切换配置，并在生产默认 real。

> 以上条目按影响面与修复成本综合排序，1–3 建议优先处理。

