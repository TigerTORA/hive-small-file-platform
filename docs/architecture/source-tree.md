# 项目目录结构

**版本**: v1.0
**基于**: Architecture Document v1.0
**最后更新**: 2025-10-12

---

## 1. 项目根目录结构

```
hive-small-file-platform/
├── README.md                      # 项目说明(GitHub首页)
├── Makefile                       # 开发便捷命令
├── VERSION                        # 版本号文件
├── package.json                   # 前端依赖(根目录)
├── package-lock.json
│
├── docker-compose.yml             # Docker本地开发环境
├── docker-compose.demo.yml        # Docker Demo环境
├── docker-compose.prod.yml        # Docker生产环境
│
├── .git/                          # Git版本控制
├── .github/                       # GitHub CI/CD配置
├── .gitignore                     # Git忽略规则
├── .githooks/                     # Git钩子脚本
├── .bmad-core/                    # BMAD方法论核心文件
├── .claude/                       # Claude AI配置
├── .cursor/                       # Cursor IDE配置
├── .venv/                         # Python虚拟环境
├── .nvmrc                         # Node版本管理
│
├── backend/                       # Python后端(FastAPI)
├── frontend/                      # Vue前端(TypeScript)
├── docs/                          # 项目文档
├── scripts/                       # 工具脚本
├── logs/                          # 日志目录
├── archive/                       # 归档文件
└── node_modules/                  # NPM依赖
```

---

## 2. 后端目录结构 (backend/)

### 2.1 完整目录树

```
backend/
├── main.py                        # FastAPI应用入口
├── requirements.txt               # Python依赖清单
├── pyproject.toml                 # Python项目配置(Black/Ruff等)
├── pytest.ini                     # Pytest配置
├── mypy.ini                       # Mypy类型检查配置
│
├── alembic/                       # 数据库迁移
│   ├── versions/                  # 迁移版本文件
│   │   ├── 1d273c8f4a90_add_merge_target_format_fields.py
│   │   └── 2ab3f4c5d6e7_add_use_ec_flag_to_merge_tasks.py
│   ├── env.py                     # Alembic环境配置
│   └── script.py.mako             # 迁移模板
│
├── app/                           # 应用主目录
│   ├── __init__.py
│   ├── main.py                    # FastAPI应用初始化
│   ├── config.py                  # 配置加载(环境变量)
│   │
│   ├── api/                       # API路由层
│   │   ├── __init__.py
│   │   ├── clusters.py            # 集群管理API
│   │   ├── dashboard.py           # 仪表板API
│   │   ├── tables_core.py         # 表监控API(核心)
│   │   ├── tables_refactored.py   # 表监控API(重构版)
│   │   ├── table_management.py    # 表管理API
│   │   ├── table_scanning.py      # 表扫描API
│   │   ├── partition_archiving.py # 分区归档API
│   │   ├── tasks.py               # 任务管理API
│   │   ├── websocket.py           # WebSocket实时通信
│   │   └── test_tables.py         # 测试表API(开发专用)
│   │
│   ├── models/                    # 数据模型(SQLAlchemy ORM)
│   │   ├── __init__.py
│   │   ├── base.py                # Base类定义
│   │   ├── cluster.py             # 集群模型
│   │   ├── table_metric.py        # 表指标模型
│   │   ├── partition_metric.py    # 分区指标模型
│   │   ├── merge_task.py          # 合并任务模型
│   │   ├── merge_task_log.py      # 合并任务日志模型
│   │   ├── scan_task.py           # 扫描任务模型
│   │   ├── scan_task_log.py       # 扫描任务日志模型
│   │   ├── test_table_task.py     # 测试表任务模型
│   │   └── test_table_task_log.py # 测试表任务日志模型
│   │
│   ├── schemas/                   # Pydantic数据验证
│   │   ├── __init__.py
│   │   ├── cluster.py             # 集群请求/响应Schema
│   │   ├── table.py               # 表相关Schema
│   │   ├── task.py                # 任务相关Schema
│   │   ├── test_table.py          # 测试表Schema
│   │   └── dashboard.py           # 仪表板Schema
│   │
│   ├── engines/                   # 核心引擎模块
│   │   ├── __init__.py
│   │   ├── connection_manager.py  # Hive/MetaStore连接管理
│   │   ├── real_hive_engine.py    # 真实Hive引擎
│   │   ├── demo_merge_engine.py   # Demo合并引擎(Mock数据)
│   │   │
│   │   ├── safe_hive_engine.py    # 安全合并引擎(主引擎,待重构)
│   │   ├── safe_hive_engine_original_backup.py  # 原始备份
│   │   ├── safe_hive_engine_refactored.py       # 重构版本
│   │   │
│   │   ├── safe_hive_metadata_manager.py  # 元数据管理器(重构提取)
│   │   ├── safe_hive_temp_table.py        # 临时表管理器(重构提取)
│   │   ├── safe_hive_atomic_swap.py       # 原子交换处理器(重构提取)
│   │   ├── safe_hive_file_counter.py      # 文件计数器(重构提取)
│   │   ├── safe_hive_utils.py             # 工具函数
│   │   ├── validation_service.py          # 验证服务(重构提取)
│   │   │
│   │   ├── hive_partition_merge_executor.py  # 分区合并执行器
│   │   ├── hive_partition_path_resolver.py   # 分区路径解析器
│   │   ├── merge_executor.py              # 合并执行器基类
│   │   └── merge_progress_tracker.py      # 合并进度追踪器
│   │
│   ├── monitor/                   # 扫描监控模块
│   │   ├── __init__.py
│   │   ├── table_scanner.py       # 混合扫描引擎(主扫描器)
│   │   ├── base_connector.py      # MetaStore连接器基类
│   │   ├── beeline_connector.py   # Beeline连接器(废弃)
│   │   ├── cold_data_scanner.py   # 冷数据扫描器
│   │   ├── native_hdfs_scanner.py # 原生HDFS扫描器
│   │   ├── webhdfs_scanner.py     # WebHDFS扫描器(推荐)
│   │   ├── partition_archive_engine.py  # 分区归档引擎
│   │   └── simple_archive_engine.py     # 简单归档引擎
│   │
│   ├── scheduler/                 # Celery任务调度
│   │   ├── __init__.py
│   │   ├── celery_app.py          # Celery应用初始化
│   │   ├── scan_tasks.py          # 扫描任务(Celery)
│   │   └── merge_tasks.py         # 合并任务(Celery)
│   │
│   ├── services/                  # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── cluster_status_service.py   # 集群状态服务
│   │   ├── scan_service.py             # 扫描服务
│   │   ├── test_table_service.py       # 测试表服务
│   │   └── websocket_service.py        # WebSocket服务
│   │
│   └── utils/                     # 工具模块
│       ├── __init__.py
│       ├── logger.py              # 日志工具
│       ├── table_lock_manager.py  # 表锁管理器(分布式锁)
│       └── webhdfs_client.py      # WebHDFS客户端
│
├── scripts/                       # 脚本工具
│   ├── generate_demo_data.py      # 生成Demo数据
│   ├── seed_demo_archive.py       # 填充归档数据
│   └── __init__.py
│
├── tests/                         # 测试目录
│   ├── __init__.py
│   ├── conftest.py                # Pytest配置
│   ├── engines/                   # 引擎模块测试
│   │   ├── test_safe_hive_engine.py
│   │   ├── test_safe_hive_metadata_manager.py
│   │   └── test_merge_executor.py
│   ├── api/                       # API测试
│   │   ├── test_clusters.py
│   │   ├── test_tables.py
│   │   └── test_tasks.py
│   └── integration/               # 集成测试
│       └── test_scan_workflow.py
│
├── var/                           # 运行时数据
│   └── data/                      # SQLite数据库(开发环境)
│       └── hive_small_file_db.db
│
└── demo-data/                     # Demo数据文件
    └── demo_scan_data.json
```

### 2.2 核心模块说明

#### 2.2.1 API层 (app/api/)
- **职责**: 接收HTTP请求,调用服务层,返回响应
- **命名规范**: `{resource}_core.py` 或 `{resource}_management.py`
- **文件大小**: 每个API文件<500行

#### 2.2.2 模型层 (app/models/)
- **职责**: 数据库表结构定义(SQLAlchemy ORM)
- **命名规范**: `{table_name}.py` (单数形式)
- **关系映射**: 使用`relationship`定义表关联

#### 2.2.3 Schema层 (app/schemas/)
- **职责**: API请求/响应数据验证(Pydantic)
- **命名规范**: `{resource}.py`
- **类命名**: `Create{Resource}Request`, `{Resource}Response`

#### 2.2.4 引擎层 (app/engines/)
- **职责**: 核心业务逻辑(合并/扫描引擎)
- **文件大小限制**: ❌ safe_hive_engine.py(4228行) → ✅ 拆分为5个模块

**重构目标**:
```
safe_hive_engine.py (4228行)
  ↓ 拆分
safe_hive_engine.py (协调器,<500行)
  ├── safe_hive_metadata_manager.py (~900行)
  ├── safe_hive_temp_table.py (~700行)
  ├── safe_hive_atomic_swap.py (~600行)
  ├── safe_hive_file_counter.py (~500行)
  └── validation_service.py (~400行)
```

#### 2.2.5 监控层 (app/monitor/)
- **职责**: 表扫描、分区统计、冷数据扫描
- **核心类**: `IntelligentHybridScanner` (混合扫描引擎)

#### 2.2.6 调度层 (app/scheduler/)
- **职责**: Celery后台任务调度
- **任务类型**: 扫描任务、合并任务、定时任务

---

## 3. 前端目录结构 (frontend/)

### 3.1 完整目录树

```
frontend/
├── index.html                     # HTML入口
├── package.json                   # NPM依赖清单
├── package-lock.json
├── tsconfig.json                  # TypeScript配置
├── vite.config.ts                 # Vite构建配置
├── playwright.config.ts           # Playwright E2E配置
├── .eslintrc.js                   # ESLint配置
├── .prettierrc                    # Prettier配置
│
├── public/                        # 静态资源(不经过Webpack)
│   └── favicon.ico
│
├── src/                           # 源代码主目录
│   ├── main.ts                    # Vue应用入口
│   ├── App.vue                    # 根组件
│   │
│   ├── router/                    # Vue Router路由配置
│   │   └── index.ts               # 路由定义
│   │
│   ├── stores/                    # Pinia状态管理
│   │   └── dashboard.ts           # 仪表板状态
│   │
│   ├── views/                     # 页面组件(路由级)
│   │   ├── Dashboard.vue          # 仪表板页面
│   │   ├── ClustersManagement.vue # 集群管理页面
│   │   ├── Tables.vue             # 表监控页面
│   │   ├── Tasks.vue              # 任务管理页面
│   │   └── Settings.vue           # 系统设置页面
│   │
│   ├── components/                # 业务组件
│   │   ├── dashboard/             # 仪表板相关组件
│   │   │   ├── DashboardSummaryCards.vue  # 汇总卡片
│   │   │   ├── DashboardPieChart.vue      # 饼图
│   │   │   ├── DashboardRankingTable.vue  # 排行榜
│   │   │   └── SavingsDonut.vue           # 节省空间环形图
│   │   ├── tasks/                 # 任务相关组件
│   │   │   ├── TasksTable.vue     # 任务表格
│   │   │   ├── TasksFiltersPane.vue  # 筛选面板
│   │   │   └── TaskCreateDialog.vue  # 创建任务对话框
│   │   └── TableDetail/           # 表详情相关组件
│   │       └── PartitionSelector.vue  # 分区选择器
│   │
│   ├── composables/               # 组合式函数(业务逻辑)
│   │   ├── useDashboardData.ts    # 仪表板数据逻辑
│   │   ├── useTableActions.ts     # 表操作逻辑
│   │   ├── useTableDetail.ts      # 表详情逻辑
│   │   ├── useTableMetrics.ts     # 表指标逻辑
│   │   ├── usePartitionManagement.ts  # 分区管理逻辑
│   │   ├── useGlobalRefresh.ts    # 全局刷新逻辑
│   │   └── tasks/                 # 任务相关逻辑
│   │       ├── useTasksData.ts    # 任务数据逻辑
│   │       └── useTaskFilters.ts  # 任务筛选逻辑
│   │
│   ├── api/                       # API封装
│   │   ├── dashboard.ts           # 仪表板API
│   │   ├── tables.ts              # 表监控API
│   │   ├── tasks.ts               # 任务管理API
│   │   └── system.ts              # 系统API
│   │
│   ├── styles/                    # 样式文件
│   │   ├── cloudera-theme.css     # Cloudera主题
│   │   └── design-system.css      # 设计系统
│   │
│   └── test/                      # 前端测试
│       ├── stores/                # Store单元测试
│       │   └── dashboard.test.ts
│       ├── integration/           # 集成测试
│       │   └── dashboard.integration.test.ts
│       └── performance/           # 性能测试
│           └── performance-baseline.test.ts
│
├── tests/                         # E2E测试(Playwright,已废弃)
│   └── visual/
│       ├── dashboard.spec.ts
│       └── tasks.spec.ts
│
└── dist/                          # 构建产物(生产环境)
```

### 3.2 核心模块说明

#### 3.2.1 Views (src/views/)
- **职责**: 页面级组件,对应路由
- **命名规范**: 大驼峰,如`ClustersManagement.vue`
- **文件大小**: 每个页面<300行

#### 3.2.2 Components (src/components/)
- **职责**: 可复用业务组件
- **组织方式**: 按功能模块分组(dashboard/tasks/TableDetail)
- **命名规范**: 大驼峰,描述性强

#### 3.2.3 Composables (src/composables/)
- **职责**: 提取业务逻辑为组合式函数
- **命名规范**: `use{Feature}.ts`,如`useDashboardData.ts`
- **优点**: 逻辑复用、组件简洁

**示例**:
```typescript
// composables/useDashboardData.ts
export function useDashboardData(clusterId?: Ref<number | undefined>) {
  const store = useDashboardStore()
  const loading = ref(false)

  const refresh = async () => {
    loading.value = true
    try {
      await store.fetchDashboardData(clusterId?.value)
    } finally {
      loading.value = false
    }
  }

  onMounted(() => refresh())

  return {
    clusterStats: computed(() => store.clusterStats),
    loading: readonly(loading),
    refresh
  }
}
```

#### 3.2.4 API层 (src/api/)
- **职责**: 封装后端API调用
- **命名规范**: `{resource}.ts`,如`dashboard.ts`
- **结构**: 导出API对象,包含所有相关方法

**示例**:
```typescript
// api/dashboard.ts
export const dashboardAPI = {
  async getOverview(params: DashboardOverviewParams): Promise<DashboardOverviewResponse> {
    const { data } = await axios.get<DashboardOverviewResponse>('/dashboard/overview', { params })
    return data
  }
}
```

#### 3.2.5 Stores (src/stores/)
- **职责**: Pinia全局状态管理
- **命名规范**: `{feature}.ts`,如`dashboard.ts`
- **组织**: State + Getters + Actions

---

## 4. 文档目录结构 (docs/)

### 4.1 完整目录树

```
docs/
├── README.md                      # 文档导航中心
├── prd.md                         # 产品需求文档(单一事实源)
├── architecture.md                # 架构设计文档(单一事实源)
│
├── epics/                         # Epic级需求文档(BMAD生成)
│   └── epic-006-code-refactoring.md  # Epic-6: 代码重构
│
├── stories/                       # Story级任务文档(BMAD生成)
│   └── epic-006/
│       └── story-001-extract-metadata-manager.md  # Story 6.1
│
├── architecture/                  # 架构详细文档(BMAD拆分)
│   ├── coding-standards.md        # 编码规范
│   ├── tech-stack.md              # 技术栈详解
│   └── source-tree.md             # 项目目录结构(本文档)
│
├── qa/                            # QA评估和质量门禁(BMAD生成)
│   ├── risk-assessment/           # 风险评估
│   ├── test-design/               # 测试设计
│   └── review-reports/            # 评审报告
│
└── adr/                           # 架构决策记录
    ├── README.md                  # ADR索引
    ├── 0000-template.md           # ADR模板
    ├── 0001-hdfs-access-and-scan-approach.md  # HDFS访问方案
    ├── 0002-strict-real-default.md            # strict_real默认值
    └── 0003-unify-celery-scanner-to-hybrid.md # 混合扫描架构
```

### 4.2 文档组织原则

#### 4.2.1 单一事实源(SSOT)
- **核心文档**: `prd.md` + `architecture.md`
- **自动生成**: epics/stories/architecture/qa目录由BMAD生成
- **禁止手工编辑**: 自动生成的文档不手工修改,通过更新prd/architecture并重新生成

#### 4.2.2 文档生成流程

```mermaid
graph LR
    A[编辑 prd.md] --> B[/BMadpo shard-doc]
    B --> C[生成 epics/ + stories/]

    D[编辑 architecture.md] --> E[/BMadpo shard-doc]
    E --> F[生成 architecture/详细文档]

    G[/BMadsm create-story] --> H[生成新Story]
    H --> I[docs/stories/epic-X/story-Y.md]

    J[/BMadqa *risk] --> K[生成风险评估]
    K --> L[docs/qa/risk-assessment/]

    M[/BMadqa *design] --> N[生成测试设计]
    N --> O[docs/qa/test-design/]

    P[/BMadqa *review] --> Q[生成评审报告]
    Q --> R[docs/qa/review-reports/]
```

---

## 5. 脚本工具目录 (scripts/)

### 5.1 完整目录树

```
scripts/
├── README.md                      # 脚本说明文档
│
├── dev/                           # 开发辅助脚本
│   └── seed_demo_archive.py       # 填充Demo归档数据
│
├── ops/                           # 运维脚本(已归档到archive/)
│
└── cleanup_workspace.py           # 工作区清理脚本
```

### 5.2 脚本使用示例

```bash
# 1. 生成Demo数据
cd backend
python scripts/generate_demo_data.py

# 2. 填充归档数据
python scripts/dev/seed_demo_archive.py

# 3. 清理工作区
python scripts/cleanup_workspace.py
```

---

## 6. 归档目录结构 (archive/)

### 6.1 完整目录树

```
archive/
├── docs/                          # 历史文档归档
│   ├── E2E_TEST.md
│   ├── Hbase同步优化1_formatted.docx
│   └── e2e-reports/               # E2E测试报告
│
├── frontend/                      # 前端历史代码
│   └── tests/visual/              # 旧Playwright测试
│
├── screenshots/                   # 历史截图
│   └── playwright-mcp/legacy/
│
├── scripts/                       # 废弃脚本
│   └── ops/                       # 运维脚本(已迁移)
│
└── tests/                         # 历史测试文件
```

### 6.2 归档原则
- **临时报告**: 归档到`archive/reports/`
- **历史文档**: 归档到`archive/docs/legacy/`
- **截图素材**: 归档到`archive/screenshots/`
- **废弃代码**: 归档到`archive/frontend/`或`archive/backend/`

---

## 7. GitHub Actions工作流 (.github/)

### 7.1 完整目录树

```
.github/
├── workflows/                     # CI/CD工作流
│   ├── ci.yml                     # 持续集成(测试+构建)
│   ├── deploy.yml                 # 部署(生产环境)
│   └── cleanup.yml                # 定期清理
│
└── PULL_REQUEST_TEMPLATE.md       # PR模板
```

### 7.2 工作流说明

#### 7.2.1 CI工作流 (ci.yml)
- **触发**: push到main/develop分支,或PR
- **Job**: backend-test → frontend-test → build-and-push
- **产物**: Docker镜像推送到ghcr.io

#### 7.2.2 Deploy工作流 (deploy.yml)
- **触发**: 手动触发或tag推送
- **Job**: 拉取镜像 → 更新docker-compose → 重启服务

---

## 8. 开发环境配置文件

### 8.1 Python配置文件

| 文件 | 用途 | 位置 |
|-----|------|------|
| `requirements.txt` | Python依赖清单 | backend/ |
| `pyproject.toml` | Black/Ruff/项目元信息 | backend/ |
| `pytest.ini` | Pytest配置 | backend/ |
| `mypy.ini` | Mypy类型检查 | backend/ |
| `.venv/` | 虚拟环境 | 根目录 |

### 8.2 TypeScript配置文件

| 文件 | 用途 | 位置 |
|-----|------|------|
| `package.json` | NPM依赖清单 | frontend/ |
| `tsconfig.json` | TypeScript配置 | frontend/ |
| `vite.config.ts` | Vite构建配置 | frontend/ |
| `.eslintrc.js` | ESLint规则 | frontend/ |
| `.prettierrc` | Prettier格式化 | frontend/ |
| `playwright.config.ts` | Playwright E2E配置 | frontend/ |

### 8.3 Docker配置文件

| 文件 | 用途 | 位置 |
|-----|------|------|
| `docker-compose.yml` | 本地开发环境 | 根目录 |
| `docker-compose.demo.yml` | Demo演示环境 | 根目录 |
| `docker-compose.prod.yml` | 生产环境 | 根目录 |
| `Dockerfile` | 后端镜像构建(如有) | backend/ |
| `Dockerfile` | 前端镜像构建(如有) | frontend/ |

---

## 9. 文件命名约定

### 9.1 Python文件命名

```python
# 模块名: 小写+下划线
safe_hive_engine.py
table_metric.py
cluster_status_service.py

# 测试文件: test_前缀
test_safe_hive_engine.py
test_cluster_api.py
```

### 9.2 TypeScript/Vue文件命名

```typescript
// 组件: 大驼峰
DashboardSummaryCards.vue
TaskCreateDialog.vue

// Composables: 小驼峰,use前缀
useDashboardData.ts
useTaskFilters.ts

// API/Store: 小驼峰
dashboard.ts
tasks.ts
```

### 9.3 文档文件命名

```markdown
# Epic文档: epic-{编号}-{功能}.md
epic-006-code-refactoring.md

# Story文档: story-{编号}-{功能}.md
story-001-extract-metadata-manager.md

# ADR文档: {编号}-{决策}.md
0001-hdfs-access-and-scan-approach.md
```

---

## 10. 文件大小限制

### 10.1 代码文件限制

| 语言 | 限制 | 例外 | 检查方式 |
|-----|------|------|---------|
| Python | 500行 | models/可放宽至800行 | Pre-commit Hook |
| TypeScript/Vue | 300行 | views/可放宽至400行 | ESLint规则 |

### 10.2 违反处理

```bash
# Pre-commit Hook自动拒绝超大文件
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-file-size
      name: Check Python file line count
      entry: python scripts/check_file_size.py --max-lines 500
      language: python
      files: \.py$
```

---

## 11. 最佳实践

### 11.1 目录组织
- ✅ 按功能模块分组(dashboard/tasks/tables)
- ✅ 同类文件放同一目录(api/models/schemas)
- ❌ 避免深层嵌套(>4层)

### 11.2 文件拆分
- ✅ 单文件职责单一
- ✅ 相关功能就近放置
- ✅ 及时重构超大文件

### 11.3 命名一致性
- ✅ 统一命名风格(Python小写+下划线,TypeScript小驼峰)
- ✅ 描述性名称(避免缩写)
- ✅ 文件名与类名一致

---

**文档维护者**: 项目架构师
**最后更新**: 2025-10-12
**下次评审**: 每季度架构评审会
