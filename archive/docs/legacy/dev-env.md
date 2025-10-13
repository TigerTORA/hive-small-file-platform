# 开发环境配置（缓存演示模式）

本工程默认提供“缓存演示”模式：所有仪表盘和表详情数据来自本地 SQLite，不需要真实 Hive/HDFS。若需恢复真实集群接入，可参考 `docs/kitchen_cleanup_plan.md` 的接口清单逐项启用。

## 1. 数据库与后端

- 默认数据库：`backend/var/data/hive_small_file_db.db`（SQLite 已随 demo 数据准备）。
- `.env` 建议配置：
  ```ini
  DATABASE_URL=sqlite:///./var/data/hive_small_file_db.db
  AUTO_CREATE_SCHEMA=true
  DEMO_MODE=true
  ```
- 重新灌入演示数据：
  ```bash
  cd backend
  python scripts/seed_demo_archive.py --reset
  ```

## 2. 前端

- Node.js 版本：使用 `nvm use` 对齐仓库根目录 `.nvmrc`（Node 20.x）。Node 24 会导致 `vue-tsc` 抛出已知异常，无法通过 `npm run lint`。
- 推荐的 `.env.local`：
  ```
  VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
  VITE_FEATURE_DEMO_MODE=true
  ```
- 启动：
  ```bash
  cd frontend
  npm install
  npm run dev -- --host 127.0.0.1 --port 3000
  ```

## 3. 测试与验证

- 最小化测试（缓存接口 + 前端 Vitest）：
  ```bash
  make demo-test
  ```
- 单独运行后端缓存测试：
  ```bash
  cd backend
  python -m pytest tests/test_cache_api.py -q
  ```

## 4. 恢复实时 Hive 功能（可选）

若需要重新启用扫描、分区等实时能力：

1. 在 `.env` 中设置 `DEMO_MODE=false`，并配置真实的 `DATABASE_URL`、`HIVE_METASTORE_URL` 等参数。
2. 前端通过 `FeatureManager` 或 `.env` 打开 `VITE_FEATURE_DEMO_MODE=false`。
3. 逐项在 `docs/kitchen_cleanup_plan.md` 中定位所需接口，恢复相应 API（例如分区指标、扫描任务）。

> 建议在恢复实时能力前新增对应的测试与监控，以免再次失控。
