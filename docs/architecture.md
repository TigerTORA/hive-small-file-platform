# Hive小文件治理平台 - 架构设计文档

**版本**: v1.0
**创建日期**: 2025-10-12
**架构类型**: Brownfield Evolution
**BMAD版本**: v4

---

## 1. 架构概览

### 1.1 整体架构

```mermaid
graph TB
    subgraph "前端层"
        A[Vue 3 SPA]
        A1[Element Plus UI]
        A2[ECharts可视化]
        A3[Pinia状态管理]
    end

    subgraph "API网关层"
        B[FastAPI]
        B1[CORS中间件]
        B2[异常处理]
        B3[日志中间件]
    end

    subgraph "业务逻辑层"
        C[集群管理]
        D[扫描引擎]
        E[合并引擎]
        F[任务调度]
    end

    subgraph "数据访问层"
        G[SQLAlchemy ORM]
        H[Redis缓存]
        I[MetaStore连接器]
        J[HDFS扫描器]
    end

    subgraph "基础设施层"
        K[(PostgreSQL/MySQL)]
        L[(Redis)]
        M[Celery Worker]
        N[Celery Beat]
    end

    subgraph "外部系统"
        O[Hive/Impala集群]
        P[HDFS]
        Q[MetaStore DB]
    end

    A --> B
    B --> C
    B --> D
    B --> E
    B --> F
    C --> G
    D --> I
    D --> J
    E --> I
    E --> J
    F --> M
    G --> K
    D --> H
    E --> H
    M --> L
    N --> L
    I --> Q
    J --> P
    E --> O

    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#e8f5e9
    style D fill:#e8f5e9
    style E fill:#e8f5e9
    style F fill:#e8f5e9
    style K fill:#fce4ec
    style O fill:#f3e5f5
```

### 1.2 技术栈架构

#### 后端技术栈
```
FastAPI 0.104+ (Web框架)
├── SQLAlchemy 2.0+ (ORM)
├── Pydantic 2.x (数据验证)
├── Celery 5.x (分布式任务队列)
├── Alembic (数据库迁移)
├── Redis 4.x (缓存/消息队列)
├── impyla (Hive连接)
├── PyMySQL/psycopg2 (MetaStore连接)
└── Sentry SDK (错误监控)
```

#### 前端技术栈
```
Vue 3.3+ (前端框架)
├── TypeScript 5.x (类型系统)
├── Element Plus 2.x (UI组件库)
├── Vue Router 4.x (路由管理)
├── Pinia 2.x (状态管理)
├── ECharts 5.x (图表库)
├── Axios 1.x (HTTP客户端)
└── Vite 5.x (构建工具)
```

---

## 2. 核心模块设计

### 2.1 集群管理模块

**职责**: 多集群配置管理、连接测试、健康监控

#### 2.1.1 组件架构

```python
# backend/app/api/clusters.py
router = APIRouter(prefix="/clusters", tags=["clusters"])

@router.post("/")                    # 创建集群
@router.get("/")                     # 列出集群
@router.get("/{id}")                 # 获取集群详情
@router.put("/{id}")                 # 更新集群配置
@router.delete("/{id}")              # 删除集群
@router.post("/{id}/test")           # 测试连接
```

#### 2.1.2 数据模型

```python
# backend/app/models/cluster.py
class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Hive连接配置
    hive_host: Mapped[str] = mapped_column(String(255))
    hive_port: Mapped[int] = mapped_column(default=10000)

    # MetaStore配置
    hive_metastore_url: Mapped[str] = mapped_column(String(500))

    # HDFS配置
    hdfs_namenode_url: Mapped[str] = mapped_column(String(500))
    hdfs_user: Mapped[str] = mapped_column(String(100), default="hdfs")
    hdfs_password: Mapped[Optional[str]] = mapped_column(String(255))

    # 业务配置
    small_file_threshold: Mapped[int] = mapped_column(default=134217728)  # 128MB
    scan_enabled: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

    # 关系
    table_metrics: Mapped[List["TableMetric"]] = relationship(back_populates="cluster")
    merge_tasks: Mapped[List["MergeTask"]] = relationship(back_populates="cluster")
```

#### 2.1.3 连接测试策略

```python
# backend/app/services/cluster_status_service.py
class ClusterStatusService:
    async def test_cluster_connection(self, cluster_id: int) -> dict:
        """测试集群连接状态"""
        results = {
            "hive_server": await self._test_hive_server(),
            "metastore": await self._test_metastore(),
            "hdfs": await self._test_hdfs(),
            "overall": "success"
        }
        # 任一失败则overall=failed
        if any(v["status"] == "failed" for v in results.values() if isinstance(v, dict)):
            results["overall"] = "failed"
        return results
```

---

### 2.2 智能扫描引擎

**职责**: 混合扫描策略、分区深度扫描、进度追踪

#### 2.2.1 混合扫描架构

```mermaid
graph TD
    A[扫描请求] --> B{strict_real模式?}
    B -->|true| C[强制实连模式]
    B -->|false| D[智能降级模式]

    C --> C1{MetaStore可用?}
    C1 -->|yes| C2[MetaStore扫描]
    C1 -->|no| C3[抛出错误]

    D --> D1{MetaStore可用?}
    D1 -->|yes| D2[MetaStore扫描]
    D1 -->|no| D3{HDFS可用?}
    D3 -->|yes| D4[HDFS扫描]
    D3 -->|no| D5[Mock降级]

    C2 --> E[返回结果]
    D2 --> E
    D4 --> E
    D5 --> E

    style C fill:#ff6b6b
    style D fill:#51cf66
```

#### 2.2.2 扫描器组件

```python
# backend/app/monitor/table_scanner.py
class IntelligentHybridScanner:
    """智能混合扫描器"""

    def __init__(self, cluster: Cluster, strict_real: bool = True):
        self.cluster = cluster
        self.strict_real = strict_real
        self.connector = None  # MetaStore连接器
        self.hdfs_scanner = None  # HDFS扫描器

    async def scan_table(
        self,
        database: str,
        table: str
    ) -> TableMetric:
        """扫描单表"""
        # 1. 尝试MetaStore扫描
        try:
            if connector := self._get_metastore_connector():
                return await self._scan_via_metastore(database, table)
        except Exception as e:
            if self.strict_real:
                raise ScanError("Strict mode: MetaStore failed") from e
            logger.warning(f"MetaStore failed, trying HDFS: {e}")

        # 2. 降级HDFS扫描
        try:
            if hdfs := self._get_hdfs_scanner():
                return await self._scan_via_hdfs(database, table)
        except Exception as e:
            if self.strict_real:
                raise ScanError("Strict mode: HDFS failed") from e
            logger.warning(f"HDFS failed, using mock: {e}")

        # 3. 兜底Mock数据
        return self._generate_mock_metric(database, table)
```

#### 2.2.3 MetaStore连接器设计

**设计模式**: 上下文管理器 + 连接池

```python
# backend/app/engines/connection_manager.py
class MetaStoreConnectionManager:
    """MetaStore连接管理器(上下文管理器)"""

    def __init__(self, metastore_url: str):
        self.url = metastore_url
        self.engine = create_engine(metastore_url, pool_size=5, max_overflow=10)
        self.connection = None

    def __enter__(self):
        self.connection = self.engine.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()
        if exc_type:
            logger.error(f"MetaStore error: {exc_val}")
        return False

    def get_table_location(self, db: str, table: str) -> str:
        """查询表存储位置"""
        sql = """
        SELECT sd.LOCATION
        FROM TBLS t
        JOIN DBS d ON t.DB_ID = d.DB_ID
        JOIN SDS sd ON t.SD_ID = sd.SD_ID
        WHERE d.NAME = :db AND t.TBL_NAME = :table
        """
        result = self.connection.execute(text(sql), {"db": db, "table": table})
        row = result.fetchone()
        return row[0] if row else None
```

#### 2.2.4 HDFS扫描器设计

**核心功能**: WebHDFS REST API + 并发扫描

```python
# backend/app/monitor/webhdfs_scanner.py
class EnhancedWebHDFSScanner:
    """增强型WebHDFS扫描器(支持并发)"""

    def __init__(self, namenode_url: str, user: str, concurrency: int = 5):
        self.namenode_url = namenode_url
        self.user = user
        self.concurrency = min(max(concurrency, 1), 20)  # 限制1-20
        self.client = WebHDFSClient(namenode_url, user)

    async def scan_partitions(
        self,
        table_location: str,
        partitions: List[str]
    ) -> List[PartitionMetric]:
        """并发扫描分区"""
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = [
                executor.submit(self._scan_single_partition, table_location, part)
                for part in partitions
            ]
            results = [f.result() for f in as_completed(futures)]
        return results

    def _scan_single_partition(self, base_location: str, partition: str) -> PartitionMetric:
        """扫描单个分区"""
        partition_path = f"{base_location}/{partition}"
        files = self.client.list_status(partition_path, recursive=True)

        total_files = len(files)
        small_files = [f for f in files if f['length'] < self.threshold]

        return PartitionMetric(
            partition_value=partition,
            total_files=total_files,
            small_files=len(small_files),
            total_size=sum(f['length'] for f in files),
            small_files_size=sum(f['length'] for f in small_files)
        )
```

---

### 2.3 文件合并引擎

**职责**: 多策略合并、原子交换、数据校验

#### 2.3.1 引擎工厂模式

```python
# backend/app/engines/engine_factory.py
class MergeEngineFactory:
    """合并引擎工厂"""

    _engines = {
        "safe_hive": SafeHiveEngine,
        "real_hive": RealHiveEngine,
        "demo_merge": DemoMergeEngine
    }

    @classmethod
    def create_engine(cls, strategy: str, cluster: Cluster) -> BaseMergeEngine:
        engine_class = cls._engines.get(strategy)
        if not engine_class:
            raise ValueError(f"Unknown strategy: {strategy}")
        return engine_class(cluster)
```

#### 2.3.2 安全合并引擎架构

**核心设计**: 原子交换 + 数据校验 + 分布式锁

```mermaid
sequenceDiagram
    participant C as 客户端
    participant E as SafeHiveEngine
    participant L as TableLockManager
    participant H as Hive
    participant V as ValidationService

    C->>E: merge_table(db, table)
    E->>L: acquire_lock(table)
    L-->>E: lock_acquired

    E->>V: validate_before_merge()
    V->>H: check_file_format
    V->>H: check_space
    V-->>E: validation_passed

    E->>H: create_temp_table()
    H-->>E: temp_table_created

    E->>H: insert_into_temp()
    H-->>E: data_copied

    E->>V: validate_data_consistency()
    V->>H: count(*)原表
    V->>H: count(*)临时表
    V-->>E: counts_match

    E->>H: atomic_swap(temp, original)
    H-->>E: swap_success

    E->>H: drop_temp_table()
    E->>L: release_lock(table)
    E-->>C: merge_success
```

#### 2.3.3 核心模块拆分(重构目标)

**当前问题**: `safe_hive_engine.py` 165KB (4000+行)

**重构方案**: 拆分为5个模块

```python
# 1. backend/app/engines/safe_hive_metadata_manager.py
class MetadataManager:
    """元数据管理器(表信息/分区信息/文件统计)"""
    def get_table_info(self, db: str, table: str) -> TableInfo: pass
    def get_partitions(self, db: str, table: str) -> List[str]: pass
    def get_file_stats(self, location: str) -> FileStats: pass

# 2. backend/app/engines/safe_hive_temp_table.py
class TempTableManager:
    """临时表管理器(创建/删除/数据迁移)"""
    def create_temp_table(self, source_table: str) -> str: pass
    def copy_data(self, source: str, temp: str): pass
    def drop_temp_table(self, temp_table: str): pass

# 3. backend/app/engines/safe_hive_atomic_swap.py
class AtomicSwapHandler:
    """原子交换处理器(表重命名/回滚)"""
    def swap_tables(self, temp: str, original: str): pass
    def rollback(self, backup: str, original: str): pass

# 4. backend/app/engines/safe_hive_file_counter.py
class FileCounter:
    """文件计数器(合并前后对比)"""
    def count_files(self, table_location: str) -> int: pass
    def compare_before_after(self, before: int, after: int) -> CompareResult: pass

# 5. backend/app/engines/validation_service.py
class ValidationService:
    """数据校验服务(行数/大小/格式一致性)"""
    def validate_row_count(self, table1: str, table2: str) -> bool: pass
    def validate_file_format(self, table: str, strategy: str) -> bool: pass
    def validate_space_available(self, required_space: int) -> bool: pass
```

---

### 2.4 任务调度系统

**职责**: Celery分布式任务队列、定时调度、进度追踪

#### 2.4.1 Celery架构

```python
# backend/app/scheduler/celery_app.py
celery_app = Celery(
    "hive_small_file_platform",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/2"
)

# 任务路由
celery_app.conf.task_routes = {
    "app.scheduler.scan_tasks.*": {"queue": "scan"},
    "app.scheduler.merge_tasks.*": {"queue": "merge"},
    "app.scheduler.maintenance_tasks.*": {"queue": "maintenance"}
}

# Beat定时调度
celery_app.conf.beat_schedule = {
    "scan-all-clusters": {
        "task": "app.scheduler.scan_tasks.scan_all_clusters",
        "schedule": crontab(hour=2, minute=0),  # 每天凌晨2点
    },
    "cleanup-old-logs": {
        "task": "app.scheduler.maintenance_tasks.cleanup_old_logs",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # 每周日3点
    }
}
```

#### 2.4.2 任务模块

```python
# backend/app/scheduler/scan_tasks.py
@celery_app.task(bind=True, max_retries=3)
def scan_single_table(self, cluster_id: int, database: str, table: str):
    """扫描单表任务"""
    try:
        scanner = IntelligentHybridScanner(cluster_id)
        metric = scanner.scan_table(database, table)
        # 保存到数据库
        save_table_metric(metric)
        return {"status": "success", "table": f"{database}.{table}"}
    except Exception as exc:
        logger.error(f"Scan failed: {exc}")
        raise self.retry(exc=exc, countdown=60)  # 60秒后重试

# backend/app/scheduler/merge_tasks.py
@celery_app.task(bind=True, max_retries=2)
def execute_merge_task(self, task_id: int):
    """执行合并任务"""
    task = get_merge_task(task_id)
    engine = MergeEngineFactory.create_engine("safe_hive", task.cluster)

    try:
        result = engine.merge_table(
            database=task.database_name,
            table=task.table_name,
            strategy=task.merge_strategy
        )
        update_task_status(task_id, "success", result)
        return result
    except Exception as exc:
        update_task_status(task_id, "failed", {"error": str(exc)})
        raise
```

---

### 2.5 前端架构

#### 2.5.1 组件层次

```
src/
├── views/                  # 页面组件(路由级)
│   ├── Dashboard.vue       # 仪表板
│   ├── ClustersManagement.vue  # 集群管理
│   ├── Tables.vue          # 表监控
│   ├── Tasks.vue           # 任务管理
│   └── Settings.vue        # 系统设置
├── components/             # 业务组件
│   ├── dashboard/
│   │   ├── DashboardSummaryCards.vue
│   │   ├── DashboardPieChart.vue
│   │   └── DashboardRankingTable.vue
│   ├── tasks/
│   │   ├── TasksTable.vue
│   │   ├── TasksFiltersPane.vue
│   │   └── TaskCreateDialog.vue
│   └── TableDetail/
│       └── PartitionSelector.vue
├── composables/            # 组合式函数(业务逻辑)
│   ├── useDashboardData.ts
│   ├── useTableActions.ts
│   ├── useTableDetail.ts
│   └── tasks/
│       ├── useTasksData.ts
│       └── useTaskFilters.ts
├── stores/                 # Pinia状态管理
│   └── dashboard.ts
├── api/                    # API封装
│   ├── dashboard.ts
│   ├── tables.ts
│   └── tasks.ts
└── router/                 # 路由配置
    └── index.ts
```

#### 2.5.2 状态管理设计

```typescript
// frontend/src/stores/dashboard.ts
export const useDashboardStore = defineStore('dashboard', () => {
  // 状态
  const clusterStats = ref<ClusterStats | null>(null)
  const topTables = ref<TableRanking[]>([])
  const loading = ref(false)

  // 计算属性
  const totalSmallFiles = computed(() =>
    clusterStats.value?.total_small_files ?? 0
  )

  // 异步操作
  async function fetchDashboardData(clusterId?: number) {
    loading.value = true
    try {
      const data = await dashboardAPI.getOverview(clusterId)
      clusterStats.value = data.cluster_stats
      topTables.value = data.top_tables
    } catch (error) {
      ElMessage.error('Failed to load dashboard data')
    } finally {
      loading.value = false
    }
  }

  return { clusterStats, topTables, totalSmallFiles, fetchDashboardData }
})
```

---

## 3. 数据库设计

### 3.1 ER关系图

```mermaid
erDiagram
    CLUSTERS ||--o{ TABLE_METRICS : has
    CLUSTERS ||--o{ MERGE_TASKS : has
    TABLE_METRICS ||--o{ PARTITION_METRICS : has
    MERGE_TASKS ||--o{ TASK_LOGS : has
    CLUSTERS ||--o{ SCAN_TASK_LOGS : has

    CLUSTERS {
        int id PK
        string name
        string hive_host
        int hive_port
        string metastore_url
        string hdfs_namenode_url
        int small_file_threshold
        boolean scan_enabled
        string status
        timestamp created_time
    }

    TABLE_METRICS {
        int id PK
        int cluster_id FK
        string database_name
        string table_name
        string table_location
        string file_format
        int total_files
        int small_files
        bigint total_size
        bigint small_files_size
        bigint avg_file_size
        timestamp last_scan_time
    }

    PARTITION_METRICS {
        int id PK
        int table_metric_id FK
        string partition_value
        int total_files
        int small_files
        bigint total_size
        bigint small_files_size
    }

    MERGE_TASKS {
        int id PK
        int cluster_id FK
        string database_name
        string table_name
        string merge_strategy
        string status
        int progress
        int files_before_merge
        int files_after_merge
        bigint space_saved
        timestamp created_time
        timestamp started_time
        timestamp completed_time
    }

    TASK_LOGS {
        int id PK
        int merge_task_id FK
        string log_level
        text message
        timestamp created_time
    }

    SCAN_TASK_LOGS {
        int id PK
        int cluster_id FK
        string database_name
        string table_name
        string status
        int tables_scanned
        text error_message
        timestamp started_time
        timestamp completed_time
    }
```

### 3.2 关键索引

```sql
-- 表指标查询优化
CREATE INDEX idx_table_metrics_cluster_time
ON table_metrics(cluster_id, last_scan_time DESC);

CREATE INDEX idx_table_metrics_small_files
ON table_metrics(small_files DESC) WHERE small_files > 100;

-- 任务查询优化
CREATE INDEX idx_merge_tasks_status_time
ON merge_tasks(status, created_time DESC);

CREATE INDEX idx_merge_tasks_cluster_status
ON merge_tasks(cluster_id, status);

-- 扫描日志查询优化
CREATE INDEX idx_scan_logs_cluster_time
ON scan_task_logs(cluster_id, started_time DESC);

-- 分区指标查询优化
CREATE INDEX idx_partition_metrics_table
ON partition_metrics(table_metric_id, partition_value);
```

---

## 4. API设计

### 4.1 REST API规范

#### 4.1.1 基础规范

| 规范 | 说明 |
|-----|------|
| 基础路径 | `/api/v1/` |
| 认证方式 | Bearer Token (可选,v2.0) |
| 数据格式 | JSON (Content-Type: application/json) |
| 状态码 | 标准HTTP状态码(200/201/400/404/500) |
| 错误格式 | `{"detail": "error message"}` |
| 分页参数 | `?page=1&page_size=50` |
| 排序参数 | `?sort_by=created_time&order=desc` |

#### 4.1.2 核心API列表

**集群管理**
```
GET    /api/v1/clusters/                    # 列出集群
POST   /api/v1/clusters/                    # 创建集群
GET    /api/v1/clusters/{id}                # 获取集群详情
PUT    /api/v1/clusters/{id}                # 更新集群
DELETE /api/v1/clusters/{id}                # 删除集群
POST   /api/v1/clusters/{id}/test           # 测试连接
```

**表监控**
```
GET    /api/v1/tables/metrics               # 查询表指标
       ?cluster_id=1&database=default
POST   /api/v1/tables/scan                  # 统一扫描入口
       body: {cluster_id, database_name?, table_name?}
       params: ?strict_real=true
POST   /api/v1/tables/scan/{cluster_id}     # 集群级批量扫描
       params: ?max_tables_per_db=100&strict_real=true
GET    /api/v1/tables/scan-progress/{task_id}  # 查询扫描进度
GET    /api/v1/tables/partition-metrics     # 查询分区统计
       ?cluster_id=1&database=default&table=user_logs
       &page=1&page_size=50&concurrency=5
```

**任务管理**
```
GET    /api/v1/tasks/                       # 查询任务列表
       ?cluster_id=1&status=running&page=1
POST   /api/v1/tasks/                       # 创建任务
POST   /api/v1/tasks/{id}/execute           # 执行任务
POST   /api/v1/tasks/{id}/cancel            # 取消任务
GET    /api/v1/tasks/{id}/logs              # 查询任务日志
```

**仪表板**
```
GET    /api/v1/dashboard/overview           # 仪表板概览
       ?cluster_id=1
```

---

## 5. 非功能架构设计

### 5.1 性能优化

#### 5.1.1 缓存策略

```python
# 1. Redis缓存(仪表板数据)
@cached(ttl=300, key="dashboard:overview:{cluster_id}")
async def get_dashboard_overview(cluster_id: int):
    """仪表板数据缓存5分钟"""
    pass

# 2. 应用层缓存(文件格式枚举)
@lru_cache(maxsize=128)
def get_file_format_info(format_name: str):
    """文件格式信息缓存"""
    pass

# 3. 数据库连接池
engine = create_engine(
    DATABASE_URL,
    pool_size=10,         # 连接池大小
    max_overflow=20,      # 最大溢出连接
    pool_recycle=3600,    # 连接回收时间
    pool_pre_ping=True    # 连接前检测
)
```

#### 5.1.2 异步处理

```python
# 1. Celery异步任务
@celery_app.task
def bulk_scan_tables(cluster_id, tables):
    """批量扫描(避免阻塞API)"""
    pass

# 2. 并发扫描
async def scan_partitions_concurrently(partitions):
    """线程池并发扫描分区"""
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scan, p) for p in partitions]
        return [f.result() for f in futures]
```

### 5.2 可靠性设计

#### 5.2.1 错误处理

```python
# 1. 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    sentry_sdk.capture_exception(exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# 2. Celery任务重试
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scan_table(self, cluster_id, database, table):
    try:
        # 扫描逻辑
        pass
    except Exception as exc:
        raise self.retry(exc=exc)
```

#### 5.2.2 数据一致性

```python
# 1. 原子交换(事务保证)
@transactional
def atomic_swap_tables(temp_table, original_table):
    """原子交换两个表"""
    # RENAME TABLE操作是原子的
    execute_sql(f"""
        ALTER TABLE {original_table} RENAME TO {original_table}_backup;
        ALTER TABLE {temp_table} RENAME TO {original_table};
        DROP TABLE {original_table}_backup;
    """)

# 2. 分布式锁(防止并发)
from app.utils.table_lock_manager import TableLockManager

with TableLockManager.acquire_lock(f"{database}.{table}"):
    # 合并操作
    pass
```

### 5.3 可扩展性设计

#### 5.3.1 水平扩展

```yaml
# 1. API服务扩展(负载均衡)
nginx:
  upstream backend:
    - server backend-1:8000
    - server backend-2:8000
    - server backend-3:8000

# 2. Celery Worker扩展
celery_workers:
  - worker-1: 4 processes
  - worker-2: 4 processes
  - worker-3: 4 processes

# 3. 数据库扩展(读写分离)
database:
  master: write operations
  replicas:
    - replica-1: read operations
    - replica-2: read operations
```

#### 5.3.2 插件化架构

```python
# 1. 扫描器插件接口
class BaseScannerPlugin(ABC):
    @abstractmethod
    def scan_database(self, config): pass

    @abstractmethod
    def scan_table(self, config): pass

# 2. 合并引擎插件接口
class BaseMergeEngine(ABC):
    @abstractmethod
    def validate_merge(self, params): pass

    @abstractmethod
    def execute_merge(self, params): pass

    @abstractmethod
    def rollback_merge(self, params): pass

# 3. 插件注册机制
MergeEngineFactory.register("spark_merge", SparkMergeEngine)
```

---

## 6. 安全架构

### 6.1 数据安全

```python
# 1. 敏感信息加密
from cryptography.fernet import Fernet

class PasswordEncryptor:
    def __init__(self, key):
        self.cipher = Fernet(key)

    def encrypt(self, password: str) -> str:
        return self.cipher.encrypt(password.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self.cipher.decrypt(encrypted.encode()).decode()

# 2. 数据库连接加密
DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=require"

# 3. HTTPS强制(生产环境)
if ENV == "production":
    @app.middleware("https")
    async def enforce_https(request, call_next):
        if request.url.scheme != "https":
            return RedirectResponse(url=str(request.url).replace("http:", "https:"))
        return await call_next(request)
```

### 6.2 审计日志

```python
# backend/app/models/audit_log.py
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(200))  # CREATE_CLUSTER/DELETE_TABLE
    resource: Mapped[str] = mapped_column(String(200))  # clusters/1
    ip_address: Mapped[str] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)

# 审计中间件
@app.middleware("audit")
async def audit_middleware(request, call_next):
    response = await call_next(request)
    if request.method in ["POST", "PUT", "DELETE"]:
        log_audit(
            action=f"{request.method}_{request.url.path}",
            ip=request.client.host
        )
    return response
```

---

## 7. 部署架构

### 7.1 容器化部署

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  backend:
    image: ghcr.io/project/hive-platform-backend:latest
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G

  frontend:
    image: ghcr.io/project/hive-platform-frontend:latest
    ports:
      - "80:80"
    depends_on:
      - backend

  celery-worker:
    image: ghcr.io/project/hive-platform-backend:latest
    command: celery -A app.scheduler.celery_app worker --loglevel=info -Q scan,merge
    deploy:
      replicas: 5

  celery-beat:
    image: ghcr.io/project/hive-platform-backend:latest
    command: celery -A app.scheduler.celery_app beat --loglevel=info
    deploy:
      replicas: 1

  postgres:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=hive_small_file_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data
```

### 7.2 监控告警

```python
# backend/app/config.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=SENTRY_DSN,
    environment=ENV,
    integrations=[
        FastApiIntegration(),
        CeleryIntegration()
    ],
    traces_sample_rate=0.1,  # 10%性能追踪
    send_default_pii=False   # 不发送敏感信息
)
```

---

## 8. 技术债和重构计划

### 8.1 当前技术债

| 债务项 | 严重程度 | 影响范围 | 计划解决 |
|-------|---------|---------|---------|
| safe_hive_engine.py超大文件 | 严重 | 合并引擎 | EPIC-6 Story 1-5 |
| 测试覆盖率<30% | 严重 | 全局 | EPIC-6 Story 6 |
| 缺少API docstring | 中等 | 文档 | EPIC-6 Story 7 |
| 硬编码配置 | 中等 | 配置管理 | v1.1优化 |

### 8.2 重构里程碑

**Phase 1 (2025-10-14 ~ 10-20)**: 拆分超大文件
- Story 1: 提取MetadataManager (backend/app/engines/safe_hive_metadata_manager.py)
- Story 2: 提取TempTableManager (backend/app/engines/safe_hive_temp_table.py)
- Story 3: 提取AtomicSwapHandler (backend/app/engines/safe_hive_atomic_swap.py)
- Story 4: 提取FileCounter (backend/app/engines/safe_hive_file_counter.py)
- Story 5: 重构ValidationService (backend/app/engines/validation_service.py)

**Phase 2 (2025-10-21 ~ 10-25)**: 补充测试
- Story 6: 补充单元测试(目标80%覆盖率)

**Phase 3 (2025-10-26 ~ 11-01)**: 完善文档
- Story 7: 补充API docstring和架构文档

---

## 附录

### A. 编码规范

见 `docs/architecture/coding-standards.md`(BMAD自动分片)

### B. 项目结构

见 `docs/architecture/source-tree.md`(BMAD自动分片)

### C. 技术栈详解

见 `docs/architecture/tech-stack.md`(BMAD自动分片)

---

## 9. 测试架构

### 9.1 测试金字塔

```
         /\
        /E2\     5%  - E2E测试(关键用户流程)
       /----\
      /集成测\   15% - 集成测试(API接口、数据库)
     /--------\
    /单元测试测\ 80% - 单元测试(核心业务逻辑)
   /----------\
```

### 9.2 测试规范

#### 9.2.1 单元测试
```python
# backend/tests/test_merge_engine.py
import pytest
from app.engines.safe_hive_engine import SafeHiveEngine

class TestSafeHiveEngine:
    @pytest.fixture
    def engine(self):
        return SafeHiveEngine(cluster_config={"id": 1})

    def test_validate_merge_format_compatible(self, engine):
        """测试文件格式兼容性验证"""
        result = engine.validate_file_format("TEXTFILE", "concatenate")
        assert result is True

    def test_validate_merge_format_incompatible(self, engine):
        """测试文件格式不兼容验证"""
        with pytest.raises(ValueError):
            engine.validate_file_format("PARQUET", "concatenate")
```

**规范要求**:
- 所有public方法必须有单元测试
- 测试文件命名: `test_{module_name}.py`
- 使用pytest + pytest-cov
- 禁止硬编码测试数据(使用fixture)
- 每个测试函数只测试一个行为
- 测试函数名描述测试场景:`test_{what}_{when}_{expected}`

#### 9.2.2 集成测试
```python
# backend/tests/integration/test_scan_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_scan_table_returns_metrics():
    """测试扫描API返回正确的指标数据"""
    response = client.post(
        "/api/v1/tables/scan",
        json={"cluster_id": 1, "database_name": "test_db", "table_name": "test_table"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_files" in data
    assert "small_files" in data
```

#### 9.2.3 E2E测试
```bash
# 使用Playwright执行E2E测试
make e2e

# 或直接运行
npm run test:e2e
```

**E2E测试覆盖场景**:
1. **用户登录流程** (待开发认证功能)
2. **扫描表流程**: 选择集群 → 选择数据库 → 扫描 → 查看结果
3. **查看仪表板流程**: 登录 → 查看汇总统计 → 查看TOP10问题表
4. **创建合并任务流程**: 进入表详情 → 创建任务 → 查看任务状态 → 查看日志

### 9.3 测试命令

```bash
# 后端单元测试
cd backend && pytest

# 后端测试覆盖率
cd backend && pytest --cov=app --cov-report=html

# 前端单元测试
cd frontend && npm run test:unit

# E2E测试
make e2e

# 全量测试(单元+集成+E2E)
make test
```

### 9.4 持续集成

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run backend tests
        run: |
          cd backend
          pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run frontend tests
        run: |
          cd frontend
          npm run test:unit
```

---

## 10. 端口和配置约定

### 10.1 服务端口

| 服务 | 开发端口 | 生产端口 | 说明 |
|-----|---------|---------|------|
| 前端(Vite Dev Server) | 3000 | - | 开发环境 |
| 前端(Nginx) | - | 80/443 | 生产环境 |
| 后端(FastAPI) | 8000 | 8000 | API服务 |
| PostgreSQL | 5432 | 5432 | 数据库 |
| Redis | 6379 | 6379 | 缓存/消息队列 |
| Celery Flower | 5555 | 5555 | 任务监控(可选) |

### 10.2 环境变量配置

#### 开发环境(.env.development)
```bash
# 数据库(推荐SQLite开发)
DATABASE_URL=sqlite:///./var/data/hive_small_file_db.db

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# API基础路径
API_BASE_URL=http://localhost:8000/api/v1

# 自动建表(开发环境开启)
AUTO_CREATE_SCHEMA=true

# 日志级别
LOG_LEVEL=DEBUG
```

#### 生产环境(.env.production)
```bash
# 数据库(生产推荐PostgreSQL)
DATABASE_URL=postgresql://user:password@postgres:5432/hive_small_file_db

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# API基础路径(相对路径)
API_BASE_URL=/api/v1

# 自动建表(生产环境关闭,使用Alembic)
AUTO_CREATE_SCHEMA=false

# 日志级别
LOG_LEVEL=INFO

# Sentry错误监控
SENTRY_DSN=https://your-sentry-dsn
SENTRY_ENVIRONMENT=production
```

### 10.3 端口冲突处理

```bash
# 如果端口被占用,杀掉占用进程
lsof -ti:3000 | xargs kill -9  # 前端
lsof -ti:8000 | xargs kill -9  # 后端
```

---

## 11. 数据库迁移

### 11.1 Alembic迁移流程

#### 11.1.1 创建新迁移
```bash
cd backend

# 自动生成迁移(基于models变更)
alembic revision --autogenerate -m "add_new_column_to_clusters"

# 手动创建迁移
alembic revision -m "custom_migration"
```

#### 11.1.2 执行迁移
```bash
# 升级到最新版本
alembic upgrade head

# 升级到指定版本
alembic upgrade 1d273c8f4a90

# 回滚一个版本
alembic downgrade -1

# 回滚到基线
alembic downgrade base
```

#### 11.1.3 查看迁移历史
```bash
# 查看当前版本
alembic current

# 查看迁移历史
alembic history

# 查看待执行的迁移
alembic show head
```

### 11.2 迁移文件结构

```python
# backend/alembic/versions/1d273c8f4a90_add_merge_target_format_fields.py
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '1d273c8f4a90'
down_revision = '2ab3f4c5d6e7'
branch_labels = None
depends_on = None

def upgrade():
    """升级操作"""
    op.add_column('merge_tasks', sa.Column('target_format', sa.String(50)))
    op.add_column('merge_tasks', sa.Column('compression', sa.String(20)))

def downgrade():
    """回滚操作"""
    op.drop_column('merge_tasks', 'compression')
    op.drop_column('merge_tasks', 'target_format')
```

### 11.3 生产环境迁移最佳实践

```bash
# 1. 备份数据库
pg_dump hive_small_file_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 在测试环境验证迁移
alembic upgrade head  # 测试环境

# 3. 生产环境执行(停机时间窗口)
# 停止应用服务
docker-compose stop backend celery-worker

# 执行迁移
docker-compose run backend alembic upgrade head

# 验证迁移
docker-compose run backend alembic current

# 重启服务
docker-compose start backend celery-worker

# 4. 监控应用日志
docker-compose logs -f backend
```

### 11.4 常见迁移问题

#### 问题1: 迁移冲突
```bash
# 多个分支同时修改models导致迁移冲突
# 解决: 合并迁移文件
alembic merge <rev1> <rev2>
```

#### 问题2: 回滚失败
```bash
# 原因: downgrade()函数写得不完整
# 解决: 检查并修复迁移文件的downgrade()
```

#### 问题3: 生产环境迁移超时
```bash
# 原因: 表数据量大,加列/索引耗时
# 解决: 分批迁移或在业务低峰期执行
```

---

**架构维护者**: 项目架构师
**最后更新**: 2025-10-12
**下次评审**: Sprint结束评审会
