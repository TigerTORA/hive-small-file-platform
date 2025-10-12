# “厨房收拾”现状盘点

本文件记录仪表盘 / 表管理 / 任务管理三大核心视图的接口依赖、后端实现位置以及所需的数据源，便于后续逐块治理与降级改造。

## 1. 仪表盘（`Dashboard.vue` + `useDashboardData`）

| 前端调用 | 接口路径 | 后端实现 | 主要数据来源 | 备注 |
| --- | --- | --- | --- | --- |
| `dashboardApi.getSummary` | `GET /api/v1/dashboard/summary` | `backend/app/api/dashboard.py:get_dashboard_summary` | `table_metrics` 去重聚合 | 完全基于本地缓存，无需 Hive |
| `dashboardApi.getFileClassification` | `GET /dashboard/file-classification` | `dashboard.py:get_file_classification` | `table_metrics` 字段推断 | 依赖 `input_format`/`serde_lib`，无 Hive |
| `dashboardApi.getEnhancedColdnessDistribution` | `GET /dashboard/enhanced-coldness-distribution` | `dashboard.py:get_enhanced_coldness_distribution` | `partition_metrics` + `table_metrics` | 仅使用缓存字段，允许无 Hive |
| `dashboardApi.getFormatCompressionDistribution` 等格式类接口 | `/dashboard/(storage-format|compression-format|format-compression)-distribution` | `dashboard.py` 同一节 | `table_metrics` +（部分）`partition_metrics` | `format-compression` 在缓存缺失时会使用分区补齐；仍不触发 Hive |
| `dashboardApi.getTopTables`, `getRecentTasks`, `getTrends`, `getFileDistribution`, `getColdestData` | `GET /dashboard/...` | `dashboard.py` 对应函数 | `table_metrics`, `partition_metrics`, `merge_tasks`, `scan_tasks` 等 ORM 表 | 均基于本地数据库；无需外部连接 |

> 结论：仪表盘所有接口均可在 demo/SQLite 数据下工作，优先保证这些 ORM 表同步即可。

## 2. 表管理（`Tables.vue` 等）

| 前端调用 | 接口路径 | 后端实现 | 主要数据来源 | 备注 |
| --- | --- | --- | --- | --- |
| `tablesApi.getTableMetrics` / `useTableDetail` 初始加载 | `GET /api/v1/tables/metrics` | `table_management.py:get_table_metrics` | `table_metrics`（按表去重） | 缓存友好 |
| `tablesApi.getClusterStats` | `GET /clusters/{id}/stats` | `api/clusters.py:get_cluster_stats` | `table_metrics` | 基于 ORM |
| `tablesApi.getDatabases` | `GET /tables/databases/{cluster_id}` | `table_management.py:get_databases` | `table_metrics` | 仅返回已扫描数据库 |
| `tablesApi.getSmallFileSummary` | `GET /tables/small-files` | `table_management.py:get_small_file_summary` | `table_metrics` 聚合 | 缓存友好 |
| `tablesApi.triggerScan`/`scanTable`/`scanDatabase`/`scanAllDatabases` | `POST /tables/scan*` 系列 | `table_scanning.py`（HybridScanner） | Hive MetaStore + WebHDFS 实连 | **需要真实集群**；在 demo 下应禁用或做 Mock |
| `tablesApi.getPartitionMetrics` / `usePartitionManagement` | `GET /tables/partition-metrics` | `table_scanning.py:get_partition_metrics` | Hive MetaStore + WebHDFS | Demo 模式返回 503 提示，live 模式需连 Hive |
| `tablesApi.archive*` / `restore*` | `/tables/archive-table`, `/table-archiving/...` | `tables_archive.py` 等 | HDFS + ORM | 归档链路同样依赖外部集群 |

### Table Detail 页额外依赖

| 前端调用 | 接口路径 | 后端实现/状态 | 主要数据来源 | 现状 |
| --- | --- | --- | --- | --- |
| `tablesApi.getCachedTableInfo`（新增） | `GET /tables/{cluster}/{db}/{table}/info` | `table_management.py:get_table_info`（缓存模式） | `table_metrics` 最新记录 | ✅ demo 可用 |
| `tasksApi.getTablePartitions` | `GET /tables/{cluster}/{db}/{table}/partitions` | 旧版接口，需 Hive | Hive MetaStore | 需实连，demo 已禁用 |
| `tablesApi.getPartitionMetrics` | `GET /tables/partition-metrics` | `table_scanning.py` | Hive + WebHDFS | 在 demo 下 500（连接被拒），导致分区面板加载失败 |

> 建议：在 `table_management.py` 内新增 `/tables/{cluster}/{db}/{table}/info` 的缓存版本，至少返回 `table_metrics` 中已有字段；分区相关接口可在无法联通 Hive 时返回“未启用严格实连”的提示。

## 3. 任务管理（`Tasks.vue` + `useTasksData`）

| 前端调用 | 接口路径 | 后端实现 | 数据来源 | 备注 |
| --- | --- | --- | --- | --- |
| `tasksApi.list` / `getByCluster` | `GET /api/v1/tasks/` | `api/tasks.py:list_tasks` | `merge_tasks`, `scan_tasks`, `test_table_tasks` ORM | 可离线 |
| `tasksApi.create` / `execute` / `cancel` | `POST /tasks/...` | `api/tasks.py` | 直接操作 `MergeTask` + Celery 触发 | 不需 Hive，但后续 worker 仍仰赖真实环境 |
| `tasksApi.getLogs` | `GET /tasks/{id}/logs` | `tasks.py:get_task_logs` | `task_logs`、`scan_task_logs` | 本地可查 |
| `tasksApi.getScanTasks` | `GET /scan-tasks/` | `api/scan_tasks.py` | `scan_tasks` ORM | 可离线 |
| `tasksApi.getTableInfo`（live）/`tablesApi.getCachedTableInfo`（demo） | `/tables/{cluster}/{db}/{table}/info` | 缓存接口可用；live 接口待重新启用 | `table_metrics` / Hive | Demo 默认使用缓存；旧 live 接口在 archive |
| `tasksApi.createSmart` / 预览等 | `/tasks/smart-create`, `/tables/.../merge-preview` | `smart_merge` 相关模块 | 通常需要 Hive/HDFS | Demo 模式下可选择禁用 |

## 4. 后续收拾计划提示

1. **恢复 `info` 接口的可用性（已完成）**  
   - 缓存接口：`table_management.py:get_table_info`；前端改用 `tablesApi.getCachedTableInfo`。  
   - Live 模式保留在 archive 中，待 Hive 环境可用再启用。

2. **为分区接口提供“未连接 Hive”反馈（已完成）**  
   - Demo 模式直接返回空数据 + 503 指引，前端空态提示。  
   - Live 模式需要 Hive/WebHDFS。

3. **集中管理扫描/归档触发（进行中）**  
   - Demo 模式已禁用扫描/合并按钮，FeatureFlag 控制 live 功能。

4. **建立最小测试网（已完成）**  
   - 后端：`backend/tests/test_cache_api.py` 使用 FastAPI TestClient 覆盖关键缓存接口。  
   - 前端：`frontend/src/test/integration/demo-mode-partition.test.ts` 验证 demo gating；其余 Vitest suite 仍可运行。  
   - Playwright smoke（可选）仅在具备可用端口时触发缓存场景。

### 归档说明

- Hive/容器脚本：`archive/scripts/legacy/`
- E2E 报告与文档：`archive/docs/`

本文会随着治理推进持续更新，新增接口/改动完成后请同步表格。
