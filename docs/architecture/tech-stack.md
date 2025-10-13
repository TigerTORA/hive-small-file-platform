# 技术栈详解

**版本**: v1.0
**基于**: Architecture Document v1.0
**最后更新**: 2025-10-12

---

## 1. 后端技术栈

### 1.1 Web框架: FastAPI 0.104+

#### 1.1.1 选型理由
- **高性能**: 基于Starlette和Pydantic,性能接近Golang/Node.js
- **异步支持**: 原生async/await,支持高并发
- **自动文档**: OpenAPI/Swagger自动生成
- **类型安全**: Pydantic自动验证请求/响应

#### 1.1.2 核心特性使用

```python
# 1. 依赖注入
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/tables/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    return db.query(TableMetric).all()

# 2. 后台任务
from fastapi import BackgroundTasks

@app.post("/tables/scan")
async def scan_table(background_tasks: BackgroundTasks):
    background_tasks.add_task(perform_scan, cluster_id, database, table)
    return {"message": "Scan started"}

# 3. WebSocket支持
@app.websocket("/ws/tasks/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: int):
    await websocket.accept()
    while True:
        progress = get_task_progress(task_id)
        await websocket.send_json({"progress": progress})
        await asyncio.sleep(1)
```

#### 1.1.3 中间件使用

```python
# 1. CORS中间件
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 开发环境
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 2. 自定义日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {duration:.2f}s"
    )
    return response
```

---

### 1.2 ORM: SQLAlchemy 2.0+

#### 1.2.1 选型理由
- **成熟稳定**: Python最流行的ORM
- **2.0新特性**: Mapped类型注解,更好的类型支持
- **异步支持**: AsyncSession支持
- **多数据库**: 支持PostgreSQL/MySQL/SQLite

#### 1.2.2 2.0新语法

```python
# 1. Mapped类型注解
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # 关系
    table_metrics: Mapped[List["TableMetric"]] = relationship(back_populates="cluster")

# 2. 新查询API
from sqlalchemy import select

# ❌ 旧语法(1.x)
clusters = session.query(Cluster).filter(Cluster.status == "active").all()

# ✅ 新语法(2.0)
stmt = select(Cluster).where(Cluster.status == "active")
clusters = session.execute(stmt).scalars().all()
```

#### 1.2.3 连接池配置

```python
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=10,              # 连接池大小
    max_overflow=20,           # 最大溢出连接
    pool_recycle=3600,         # 连接回收时间(秒)
    pool_pre_ping=True,        # 连接前检测
    echo=False,                # 不打印SQL(生产环境)
    future=True                # 启用2.0风格
)
```

---

### 1.3 数据验证: Pydantic 2.x

#### 1.3.1 选型理由
- **性能提升**: V2使用Rust重写核心,速度提升17倍
- **类型安全**: 运行时类型验证
- **自动文档**: 与FastAPI集成生成API文档

#### 1.3.2 核心用法

```python
from pydantic import BaseModel, Field, field_validator, model_validator

# 1. 基础模型
class CreateClusterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="集群名称")
    hive_host: str = Field(..., description="Hive Server2地址")
    hive_port: int = Field(10000, ge=1, le=65535, description="Hive端口")
    small_file_threshold: int = Field(134217728, description="小文件阈值(字节)")

# 2. 字段验证器
class MergeTaskRequest(BaseModel):
    database_name: str
    table_name: str
    merge_strategy: Literal["concatenate", "insert_overwrite"]

    @field_validator("merge_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v not in ["concatenate", "insert_overwrite"]:
            raise ValueError("Invalid merge strategy")
        return v

# 3. 模型验证器
class ScanRequest(BaseModel):
    cluster_id: int
    database_name: Optional[str] = None
    table_name: Optional[str] = None

    @model_validator(mode='after')
    def check_table_requires_database(self) -> 'ScanRequest':
        if self.table_name and not self.database_name:
            raise ValueError("table_name requires database_name")
        return self
```

---

### 1.4 任务队列: Celery 5.x

#### 1.4.1 选型理由
- **分布式**: 支持多Worker水平扩展
- **可靠性**: 任务持久化,支持重试
- **定时调度**: Celery Beat支持Cron表达式
- **监控**: Flower提供Web界面监控

#### 1.4.2 核心配置

```python
# backend/app/scheduler/celery_app.py
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "hive_small_file_platform",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/2"
)

# 任务路由
celery_app.conf.task_routes = {
    "app.scheduler.scan_tasks.*": {"queue": "scan"},
    "app.scheduler.merge_tasks.*": {"queue": "merge"},
}

# 任务配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,      # 追踪任务开始
    task_time_limit=3600,          # 任务超时1小时
    task_soft_time_limit=3300,     # 软超时55分钟
)

# Beat定时调度
celery_app.conf.beat_schedule = {
    "scan-all-clusters-daily": {
        "task": "app.scheduler.scan_tasks.scan_all_clusters",
        "schedule": crontab(hour=2, minute=0),  # 每天凌晨2点
    }
}
```

#### 1.4.3 任务设计模式

```python
# 1. 基础任务
@celery_app.task
def simple_task(arg1, arg2):
    return arg1 + arg2

# 2. 重试机制
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scan_table(self, cluster_id, database, table):
    try:
        scanner = get_scanner(cluster_id)
        return scanner.scan_table(database, table)
    except ConnectionError as exc:
        # 60秒后重试,最多3次
        raise self.retry(exc=exc, countdown=60)

# 3. 任务链
from celery import chain

workflow = chain(
    scan_table.s(cluster_id, db, table),    # 先扫描
    create_merge_task.s(),                  # 再创建合并任务
    execute_merge.s()                       # 最后执行合并
)
workflow.apply_async()

# 4. 任务组
from celery import group

job = group(
    scan_table.s(1, "db1", "table1"),
    scan_table.s(1, "db1", "table2"),
    scan_table.s(1, "db1", "table3"),
)
result = job.apply_async()
```

---

### 1.5 缓存: Redis 4.x

#### 1.5.1 选型理由
- **高性能**: 内存存储,ms级响应
- **丰富数据结构**: String/Hash/List/Set/ZSet
- **持久化**: RDB+AOF双重保障
- **发布订阅**: 支持实时消息

#### 1.5.2 使用场景

```python
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# 1. 函数结果缓存
def cached(ttl: int, key_prefix: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 构建缓存key
            cache_key = f"{key_prefix}:{':'.join(map(str, args))}"

            # 尝试从缓存获取
            cached_value = redis_client.get(cache_key)
            if cached_value:
                return json.loads(cached_value)

            # 执行函数
            result = await func(*args, **kwargs)

            # 存入缓存
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

@cached(ttl=300, key_prefix="dashboard:overview")
async def get_dashboard_overview(cluster_id: int):
    # 缓存5分钟
    pass

# 2. 分布式锁
from redis.lock import Lock

def with_lock(lock_name: str, timeout: int = 10):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            lock = redis_client.lock(lock_name, timeout=timeout)
            if lock.acquire(blocking=False):
                try:
                    return func(*args, **kwargs)
                finally:
                    lock.release()
            else:
                raise RuntimeError(f"Failed to acquire lock: {lock_name}")
        return wrapper
    return decorator

@with_lock("merge:db.table", timeout=600)
def execute_merge(task):
    # 同一时间只允许一个合并任务
    pass

# 3. 计数器
def increment_scan_count(cluster_id: int):
    key = f"scan_count:{cluster_id}"
    redis_client.incr(key)
    redis_client.expire(key, 86400)  # 24小时过期
```

---

### 1.6 数据库迁移: Alembic

#### 1.6.1 选型理由
- **SQLAlchemy集成**: 与ORM无缝配合
- **版本控制**: 迁移文件Git管理
- **自动生成**: 检测models变更自动生成迁移
- **回滚支持**: downgrade回滚到任意版本

#### 1.6.2 核心用法

```bash
# 1. 初始化
cd backend
alembic init alembic

# 2. 配置env.py
# backend/alembic/env.py
from app.models.base import Base  # 导入所有models
target_metadata = Base.metadata

# 3. 自动生成迁移
alembic revision --autogenerate -m "add_merge_target_format_fields"

# 4. 执行迁移
alembic upgrade head

# 5. 回滚迁移
alembic downgrade -1
```

---

### 1.7 Hive连接: impyla

#### 1.7.1 选型理由
- **官方推荐**: Cloudera维护
- **Thrift协议**: 直接连接HiveServer2
- **DBAPI 2.0**: 标准Python数据库接口

#### 1.7.2 连接池实现

```python
from impala.dbapi import connect
from contextlib import contextmanager

class HiveConnectionPool:
    def __init__(self, host: str, port: int = 10000, pool_size: int = 5):
        self.host = host
        self.port = port
        self.pool = queue.Queue(maxsize=pool_size)

        # 预创建连接
        for _ in range(pool_size):
            conn = connect(host=host, port=port, auth_mechanism='NOSASL')
            self.pool.put(conn)

    @contextmanager
    def get_connection(self):
        conn = self.pool.get()
        try:
            yield conn
        finally:
            self.pool.put(conn)

# 使用
pool = HiveConnectionPool("hive.example.com", 10000)

with pool.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES")
    databases = cursor.fetchall()
```

---

### 1.8 HDFS访问: WebHDFS Client

#### 1.8.1 选型理由
- **HTTP REST API**: 无需Hadoop依赖
- **跨平台**: Python/JavaScript都可调用
- **防火墙友好**: 只需开放HTTP端口

#### 1.8.2 实现方式

```python
import requests

class WebHDFSClient:
    def __init__(self, namenode_url: str, user: str = "hdfs"):
        self.base_url = namenode_url
        self.user = user

    def list_status(self, path: str, recursive: bool = False) -> List[Dict]:
        """列出目录内容"""
        url = f"{self.base_url}/webhdfs/v1{path}"
        params = {"op": "LISTSTATUS", "user.name": self.user}

        response = requests.get(url, params=params)
        response.raise_for_status()

        files = response.json()["FileStatuses"]["FileStatus"]

        if recursive:
            all_files = []
            for file in files:
                if file["type"] == "DIRECTORY":
                    sub_files = self.list_status(f"{path}/{file['pathSuffix']}", recursive=True)
                    all_files.extend(sub_files)
                else:
                    all_files.append(file)
            return all_files

        return files

    def rename(self, src: str, dst: str) -> bool:
        """重命名文件/目录(用于原子交换)"""
        url = f"{self.base_url}/webhdfs/v1{src}"
        params = {"op": "RENAME", "destination": dst, "user.name": self.user}

        response = requests.put(url, params=params)
        response.raise_for_status()

        return response.json()["boolean"]
```

---

## 2. 前端技术栈

### 2.1 框架: Vue 3.3+

#### 2.1.1 选型理由
- **Composition API**: 逻辑复用更灵活
- **性能提升**: Proxy响应式,性能优于Vue 2
- **TypeScript支持**: 官方完整类型定义
- **生态成熟**: Element Plus/Pinia等配套完善

#### 2.1.2 核心特性

```vue
<script setup lang="ts">
// 1. Composition API
import { ref, computed, onMounted } from 'vue'

const count = ref(0)
const doubleCount = computed(() => count.value * 2)

onMounted(() => {
  console.log('Component mounted')
})

// 2. defineProps + withDefaults
interface Props {
  title?: string
  count?: number
}
const props = withDefaults(defineProps<Props>(), {
  title: 'Default Title',
  count: 0
})

// 3. defineEmits
const emit = defineEmits<{
  update: [value: number]
  delete: []
}>()

function handleClick() {
  emit('update', count.value + 1)
}
</script>
```

---

### 2.2 UI库: Element Plus 2.x

#### 2.2.1 选型理由
- **官方推荐**: Vue 3配套UI库
- **组件丰富**: 70+组件覆盖常见场景
- **TypeScript**: 完整类型定义
- **国际化**: 多语言支持

#### 2.2.2 核心组件使用

```vue
<template>
  <!-- 1. 表格组件 -->
  <el-table :data="tableData" stripe>
    <el-table-column prop="name" label="表名" />
    <el-table-column prop="smallFiles" label="小文件数" sortable />
    <el-table-column label="操作">
      <template #default="{ row }">
        <el-button @click="handleMerge(row)">合并</el-button>
      </template>
    </el-table-column>
  </el-table>

  <!-- 2. 对话框 -->
  <el-dialog v-model="dialogVisible" title="创建任务">
    <el-form :model="form">
      <el-form-item label="合并策略">
        <el-select v-model="form.strategy">
          <el-option label="CONCATENATE" value="concatenate" />
          <el-option label="INSERT OVERWRITE" value="insert_overwrite" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>

  <!-- 3. 消息提示 -->
  <script setup lang="ts">
  import { ElMessage } from 'element-plus'

  function showSuccess() {
    ElMessage.success('操作成功')
  }

  function showError() {
    ElMessage.error('操作失败')
  }
  </script>
</template>
```

---

### 2.3 图表库: ECharts 5.x

#### 2.3.1 选型理由
- **功能强大**: 20+图表类型
- **性能优秀**: Canvas渲染,支持10万+数据点
- **交互丰富**: 缩放/拖拽/高亮等
- **主题定制**: 支持自定义主题

#### 2.3.2 核心用法

```vue
<template>
  <div ref="chartRef" style="width: 100%; height: 400px"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

const props = defineProps<{
  data: Array<{ name: string; value: number }>
}>()

onMounted(() => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value)
    updateChart()
  }
})

watch(() => props.data, () => {
  updateChart()
}, { deep: true })

function updateChart() {
  if (!chartInstance) return

  const option = {
    title: {
      text: '小文件分布',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '文件数',
        type: 'pie',
        radius: '50%',
        data: props.data,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }

  chartInstance.setOption(option)
}
</script>
```

---

### 2.4 状态管理: Pinia 2.x

#### 2.4.1 选型理由
- **TypeScript友好**: 完整类型推断
- **轻量**: 比Vuex小70%
- **模块化**: 自动代码分割
- **DevTools**: Vue DevTools集成

#### 2.4.2 Store设计

```typescript
// stores/dashboard.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { dashboardAPI } from '@/api/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  // State
  const clusterStats = ref<ClusterStats | null>(null)
  const topTables = ref<TableRanking[]>([])
  const loading = ref(false)

  // Getters
  const totalSmallFiles = computed(() => clusterStats.value?.smallFiles ?? 0)
  const smallFileRatio = computed(() => {
    if (!clusterStats.value) return 0
    const { totalFiles, smallFiles } = clusterStats.value
    return totalFiles > 0 ? (smallFiles / totalFiles) * 100 : 0
  })

  // Actions
  async function fetchDashboardData(clusterId?: number) {
    loading.value = true
    try {
      const data = await dashboardAPI.getOverview({ clusterId })
      clusterStats.value = data.clusterStats
      topTables.value = data.topTables
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  function $reset() {
    clusterStats.value = null
    topTables.value = []
    loading.value = false
  }

  return {
    // State
    clusterStats,
    topTables,
    loading,

    // Getters
    totalSmallFiles,
    smallFileRatio,

    // Actions
    fetchDashboardData,
    $reset
  }
})
```

---

### 2.5 构建工具: Vite 5.x

#### 2.5.1 选型理由
- **极速冷启动**: ESM原生支持
- **HMR速度**: 毫秒级热更新
- **按需编译**: 仅编译当前页面
- **生产优化**: Rollup打包

#### 2.5.2 核心配置

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },

  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },

  build: {
    target: 'es2015',
    minify: 'terser',
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          'echarts': ['echarts']
        }
      }
    }
  }
})
```

---

## 3. 基础设施技术栈

### 3.1 数据库: PostgreSQL 13+

#### 3.1.1 选型理由
- **开源免费**: 成熟稳定
- **ACID支持**: 完整事务保证
- **JSON支持**: JSONB高性能存储
- **扩展丰富**: PostGIS/TimescaleDB等

#### 3.1.2 关键配置

```sql
-- 1. 连接池
max_connections = 200

-- 2. 内存配置
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 16MB

-- 3. 查询优化
random_page_cost = 1.1  # SSD优化
effective_io_concurrency = 200

-- 4. WAL配置
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

---

### 3.2 容器化: Docker + Docker Compose

#### 3.2.1 选型理由
- **环境一致**: 开发/生产环境统一
- **快速部署**: 分钟级启动
- **资源隔离**: 容器间互不影响
- **易于扩展**: 水平扩展简单

#### 3.2.2 核心配置

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    image: ghcr.io/project/hive-platform-backend:latest
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/db
      REDIS_URL: redis://redis:6379/0
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

  celery-worker:
    image: ghcr.io/project/hive-platform-backend:latest
    command: celery -A app.scheduler.celery_app worker --loglevel=info
    deploy:
      replicas: 5

  postgres:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

### 3.3 CI/CD: GitHub Actions

#### 3.3.1 选型理由
- **GitHub集成**: 无需第三方平台
- **免费额度**: 开源项目无限制
- **并发构建**: 多Job并行
- **生态丰富**: Marketplace插件多

#### 3.3.2 工作流示例

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Run tests
        run: |
          cd backend
          pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Run tests
        run: |
          cd frontend
          npm run test:unit

  build-and-push:
    needs: [backend-test, frontend-test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker images
        run: |
          docker build -t backend:latest ./backend
          docker build -t frontend:latest ./frontend

      - name: Push to registry
        run: |
          echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker push ghcr.io/project/backend:latest
```

---

## 4. 监控和日志

### 4.1 错误监控: Sentry

#### 4.1.1 选型理由
- **实时错误追踪**: 毫秒级上报
- **堆栈分析**: 完整上下文
- **告警通知**: 邮件/Slack/钉钉
- **性能监控**: APM支持

#### 4.1.2 集成方式

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
    traces_sample_rate=0.1,      # 10%性能追踪
    send_default_pii=False,      # 不发送敏感信息
    before_send=filter_errors,   # 过滤特定错误
)

def filter_errors(event, hint):
    # 过滤404错误
    if event.get('exception'):
        exc = hint.get('exc_info')[1]
        if isinstance(exc, HTTPException) and exc.status_code == 404:
            return None
    return event
```

---

### 4.2 日志聚合: Python logging

#### 4.2.1 配置

```python
# backend/app/utils/logger.py
import logging
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # JSON格式输出
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

# 使用
logger = get_logger(__name__)
logger.info(
    "Merge completed",
    extra={
        "cluster_id": 1,
        "database": "test_db",
        "table": "user_logs",
        "files_before": 3000,
        "files_after": 30
    }
)
```

---

## 5. 开发工具

### 5.1 代码质量

| 工具 | 用途 | 配置文件 |
|-----|------|---------|
| Black | Python代码格式化 | pyproject.toml |
| Mypy | Python静态类型检查 | mypy.ini |
| Ruff | Python Linter | pyproject.toml |
| ESLint | TypeScript Linter | .eslintrc.js |
| Prettier | TypeScript格式化 | .prettierrc |

### 5.2 测试工具

| 工具 | 用途 | 命令 |
|-----|------|------|
| Pytest | Python单元/集成测试 | pytest --cov |
| Vitest | Vue单元测试 | npm run test:unit |
| Playwright | E2E测试 | npm run test:e2e |

---

**文档维护者**: 项目架构师
**最后更新**: 2025-10-12
**下次评审**: 每季度技术栈评审会
