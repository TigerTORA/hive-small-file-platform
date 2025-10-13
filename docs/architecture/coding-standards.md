# 编码规范

**版本**: v1.0
**基于**: Architecture Document v1.0
**适用范围**: 全栈开发(Python后端 + TypeScript前端)

---

## 1. Python后端编码规范

### 1.1 代码风格

#### 1.1.1 PEP 8基础规范
- 遵循[PEP 8](https://www.python.org/dev/peps/pep-0008/)标准
- 使用4空格缩进(不使用Tab)
- 行宽限制:80字符(代码),100字符(docstring)
- 文件编码:UTF-8

#### 1.1.2 命名约定
```python
# 模块名: 小写+下划线
safe_hive_engine.py

# 类名: 大驼峰(CapWords)
class SafeHiveMetadataManager:
    pass

# 函数名: 小写+下划线
def get_table_location(database: str, table: str) -> Optional[str]:
    pass

# 私有方法: 单下划线前缀
class MyClass:
    def _internal_method(self):
        pass

# 常量: 大写+下划线
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30

# 类型变量: 大驼峰
T = TypeVar('T')
TableMetricT = TypeVar('TableMetricT', bound='TableMetric')
```

#### 1.1.3 类型注解(强制)
```python
# 所有公共函数必须有类型注解
def merge_table(
    database: str,
    table: str,
    strategy: Literal["concatenate", "insert_overwrite"]
) -> Dict[str, Any]:
    """合并表文件"""
    pass

# 使用Optional表示可空
def get_partition_path(partition: str) -> Optional[str]:
    if not partition:
        return None
    return f"/path/to/{partition}"

# 使用Union表示多类型
def process_result(result: Union[dict, list, None]) -> str:
    pass

# Mapped用于SQLAlchemy 2.0+
class Cluster(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
```

### 1.2 文件大小限制(强制)

#### 1.2.1 单文件代码行限制
- **硬性规则**: 单文件不超过500行
- **警告阈值**: 单文件超过300行需评审
- **例外情况**: 数据模型文件(models/)可放宽至800行

#### 1.2.2 违反处理
```bash
# Pre-commit Hook自动检查
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-file-size
      name: Check file line count
      entry: python scripts/check_file_size.py
      language: python
      pass_filenames: true
      files: \.py$
```

#### 1.2.3 拆分策略
```python
# ❌ 错误: 超大文件
# backend/app/engines/safe_hive_engine.py (4228行)

# ✅ 正确: 拆分为模块
backend/app/engines/
├── safe_hive_engine.py              # 主引擎(协调器,<500行)
├── safe_hive_metadata_manager.py    # 元数据管理
├── safe_hive_temp_table.py          # 临时表管理
├── safe_hive_atomic_swap.py         # 原子交换
├── safe_hive_file_counter.py        # 文件计数
└── validation_service.py            # 验证服务
```

### 1.3 导入规范

```python
# 导入顺序: 标准库 → 第三方库 → 项目内部模块
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from pydantic import BaseModel

from app.models.cluster import Cluster
from app.utils.logger import get_logger

# 避免通配符导入(禁止)
# ❌ from app.models import *

# 推荐显式导入
# ✅ from app.models import Cluster, TableMetric

# 相对导入仅在同包内使用
# ✅ from .utils import helper_function
```

### 1.4 函数设计

#### 1.4.1 函数长度
- 单函数不超过50行
- 复杂逻辑拆分为子函数

```python
# ❌ 错误: 单函数过长
def execute_merge(task):
    # ... 100+ lines of code ...
    pass

# ✅ 正确: 拆分为子函数
def execute_merge(task: MergeTask) -> Dict[str, Any]:
    """执行合并(协调器)"""
    _validate_task(task)
    temp_table = _create_temp_table(task)
    _copy_data(task, temp_table)
    _validate_data(task, temp_table)
    _atomic_swap(task, temp_table)
    return _build_result(task)

def _validate_task(task: MergeTask) -> None:
    """验证任务参数"""
    pass

def _create_temp_table(task: MergeTask) -> str:
    """创建临时表"""
    pass
```

#### 1.4.2 参数设计
- 参数数量: ≤5个(超过则使用数据类)
- 关键字参数: 明确默认值

```python
# ❌ 错误: 参数过多
def merge_table(db, table, strategy, format, compression, use_ec, partition_filter, timeout):
    pass

# ✅ 正确: 使用数据类
@dataclass
class MergeConfig:
    strategy: str
    target_format: Optional[str] = None
    compression: Optional[str] = None
    use_ec: bool = False
    partition_filter: Optional[str] = None
    timeout: int = 3600

def merge_table(database: str, table: str, config: MergeConfig) -> Dict:
    pass
```

### 1.5 异常处理

```python
# 1. 具体异常类
class TableNotFoundError(Exception):
    """表不存在错误"""
    pass

class MergeValidationError(Exception):
    """合并验证失败"""
    pass

# 2. 异常传播
def get_table_info(db: str, table: str) -> TableInfo:
    """获取表信息,不存在则抛出异常"""
    if not self._table_exists(db, table):
        raise TableNotFoundError(f"Table {db}.{table} not found")
    return self._fetch_table_info(db, table)

# 3. 错误日志+重抛
@celery_app.task(bind=True, max_retries=3)
def scan_table(self, cluster_id, database, table):
    try:
        scanner = get_scanner(cluster_id)
        return scanner.scan_table(database, table)
    except ConnectionError as exc:
        logger.error(f"Scanner connection failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)  # 60s后重试
```

### 1.6 日志规范

```python
# 1. 使用结构化日志
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 2. 日志级别
logger.debug("Scanning partition: dt=2025-10-11")  # 调试信息
logger.info("Merge task completed: 3000 → 30 files")  # 关键信息
logger.warning("MetaStore connection slow: 5s")  # 警告
logger.error("Merge failed: Table not found", exc_info=True)  # 错误+堆栈

# 3. 日志格式
# ✅ 正确: 包含上下文
logger.info(
    "Merge completed",
    extra={
        "cluster_id": task.cluster_id,
        "database": task.database_name,
        "table": task.table_name,
        "files_before": 3000,
        "files_after": 30,
        "duration_sec": 120
    }
)

# ❌ 错误: 缺少上下文
logger.info("Merge completed")
```

### 1.7 文档字符串(Docstring)

```python
# 所有公共函数/类必须有docstring
def execute_merge(task: MergeTask, db_session: Session) -> Dict[str, Any]:
    """执行安全文件合并。

    Args:
        task: 合并任务对象,包含database_name/table_name/merge_strategy等字段
        db_session: SQLAlchemy数据库会话,用于记录日志

    Returns:
        包含合并结果的字典:
        {
            "success": bool,
            "files_before": int,
            "files_after": int,
            "size_saved": int,
            "duration": float,
            "message": str
        }

    Raises:
        TableNotFoundError: 表不存在时
        MergeValidationError: 数据校验失败时
        ConnectionError: Hive连接失败时

    Example:
        >>> task = MergeTask(database_name="test_db", table_name="user_logs")
        >>> result = execute_merge(task, db_session)
        >>> print(result["files_after"])
        30
    """
    pass
```

---

## 2. TypeScript前端编码规范

### 2.1 代码风格

#### 2.1.1 基础规范
- 遵循[Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- 使用2空格缩进
- 行宽限制:100字符
- 使用单引号(字符串)

#### 2.1.2 命名约定
```typescript
// 组件名: 大驼峰
const DashboardSummaryCards = defineComponent({ ... })

// 变量名: 小驼峰
const totalSmallFiles = ref(0)
const clusterStats = ref<ClusterStats | null>(null)

// 常量: 大写+下划线
const MAX_TABLES_PER_PAGE = 50
const API_BASE_URL = '/api/v1'

// 类型/接口: 大驼峰
interface TableMetric {
  databaseName: string
  tableName: string
  totalFiles: number
}

type MergeStatus = 'pending' | 'running' | 'success' | 'failed'
```

### 2.2 组件设计

#### 2.2.1 单文件组件(SFC)结构
```vue
<!-- 推荐顺序: template → script → style -->
<template>
  <div class="dashboard-summary-cards">
    <el-card v-for="card in cards" :key="card.id">
      {{ card.title }}: {{ card.value }}
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'

// 1. Props定义
interface Props {
  clusterId?: number
}
const props = withDefaults(defineProps<Props>(), {
  clusterId: undefined
})

// 2. Emits定义
const emit = defineEmits<{
  refresh: []
  error: [message: string]
}>()

// 3. Composables
const dashboardStore = useDashboardStore()

// 4. 响应式状态
const loading = ref(false)

// 5. 计算属性
const cards = computed(() => [
  { id: 1, title: '小文件总数', value: dashboardStore.totalSmallFiles },
  // ...
])

// 6. 生命周期
onMounted(async () => {
  await fetchData()
})

// 7. 方法
async function fetchData() {
  loading.value = true
  try {
    await dashboardStore.fetchDashboardData(props.clusterId)
  } catch (error) {
    emit('error', '加载失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.dashboard-summary-cards {
  display: flex;
  gap: 16px;
}
</style>
```

#### 2.2.2 组件拆分原则
- 单组件不超过300行
- 业务逻辑提取到composables/

```typescript
// ✅ 正确: 业务逻辑分离
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

  onMounted(() => {
    refresh()
  })

  return {
    clusterStats: computed(() => store.clusterStats),
    topTables: computed(() => store.topTables),
    loading: readonly(loading),
    refresh
  }
}

// Dashboard.vue (简洁)
<script setup lang="ts">
const clusterId = ref<number | undefined>()
const { clusterStats, topTables, loading, refresh } = useDashboardData(clusterId)
</script>
```

### 2.3 类型定义

```typescript
// 1. 接口定义(推荐使用interface)
export interface ClusterStats {
  totalFiles: number
  smallFiles: number
  smallFileRatio: number
  wastedSpace: number
}

// 2. 类型别名(用于联合类型)
export type MergeStatus = 'pending' | 'running' | 'success' | 'failed' | 'cancelled'

// 3. 泛型
export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  pageSize: number
}

// 4. 联合类型+字面量类型
export interface MergeTask {
  id: number
  databaseName: string
  tableName: string
  status: MergeStatus
  strategy: 'concatenate' | 'insert_overwrite'
}
```

### 2.4 API封装

```typescript
// api/dashboard.ts
import axios from '@/utils/axios'

export interface DashboardOverviewParams {
  clusterId?: number
}

export interface DashboardOverviewResponse {
  clusterStats: ClusterStats
  topTables: TableRanking[]
}

export const dashboardAPI = {
  async getOverview(params: DashboardOverviewParams): Promise<DashboardOverviewResponse> {
    const { data } = await axios.get<DashboardOverviewResponse>('/dashboard/overview', { params })
    return data
  }
}

// 使用
import { dashboardAPI } from '@/api/dashboard'

const data = await dashboardAPI.getOverview({ clusterId: 1 })
console.log(data.clusterStats.totalFiles)
```

### 2.5 状态管理(Pinia)

```typescript
// stores/dashboard.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useDashboardStore = defineStore('dashboard', () => {
  // State
  const clusterStats = ref<ClusterStats | null>(null)
  const topTables = ref<TableRanking[]>([])

  // Getters
  const totalSmallFiles = computed(() => clusterStats.value?.smallFiles ?? 0)

  // Actions
  async function fetchDashboardData(clusterId?: number) {
    const data = await dashboardAPI.getOverview({ clusterId })
    clusterStats.value = data.clusterStats
    topTables.value = data.topTables
  }

  function resetState() {
    clusterStats.value = null
    topTables.value = []
  }

  return {
    // State
    clusterStats,
    topTables,

    // Getters
    totalSmallFiles,

    // Actions
    fetchDashboardData,
    resetState
  }
})
```

---

## 3. 通用规范

### 3.1 Git提交规范

#### 3.1.1 Commit Message格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type类型**:
- `feat`: 新功能
- `fix`: Bug修复
- `refactor`: 重构(不改变外部行为)
- `docs`: 文档更新
- `style`: 代码格式(不影响逻辑)
- `test`: 测试相关
- `chore`: 构建/工具配置

**示例**:
```bash
feat(backend): add partition-level merge support

- Implement _execute_partition_native_merge method
- Add partition_filter validation
- Update merge task model to support partition_filter

Closes #123
```

#### 3.1.2 分支命名
```
<type>/<ticket-id>-<short-description>

# 示例
feature/EPIC-6-extract-metadata-manager
fix/merge-engine-partition-filter-bug
refactor/split-safe-hive-engine
```

### 3.2 代码审查清单

#### 3.2.1 后端审查
- [ ] 文件大小<500行?
- [ ] 所有公共函数有类型注解?
- [ ] 所有公共函数有docstring?
- [ ] 异常处理完整?
- [ ] 日志记录充分?
- [ ] 单元测试覆盖率>80%?
- [ ] 没有硬编码配置?

#### 3.2.2 前端审查
- [ ] 组件大小<300行?
- [ ] 业务逻辑提取到composables?
- [ ] 所有接口有类型定义?
- [ ] 错误处理完整(ElMessage)?
- [ ] 加载状态处理(loading)?
- [ ] 响应式数据正确使用(ref/computed)?

### 3.3 测试规范

#### 3.3.1 测试覆盖要求
- 单元测试: >80%(核心模块100%)
- 集成测试: 覆盖所有API端点
- E2E测试: 覆盖关键用户流程

#### 3.3.2 测试文件组织
```
backend/
├── app/
│   └── engines/
│       └── safe_hive_engine.py
└── tests/
    └── engines/
        └── test_safe_hive_engine.py  # 对应测试文件

frontend/
├── src/
│   └── composables/
│       └── useDashboardData.ts
└── src/test/
    └── composables/
        └── useDashboardData.test.ts  # 对应测试文件
```

---

## 4. 工具配置

### 4.1 后端工具链

#### 4.1.1 Black (代码格式化)
```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
```

#### 4.1.2 Mypy (静态类型检查)
```ini
# mypy.ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

#### 4.1.3 Ruff (Linter)
```toml
# pyproject.toml
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # 行长度由Black控制
```

### 4.2 前端工具链

#### 4.2.1 ESLint
```javascript
// .eslintrc.js
module.exports = {
  extends: [
    'plugin:vue/vue3-recommended',
    '@vue/eslint-config-typescript/recommended',
    '@vue/eslint-config-prettier'
  ],
  rules: {
    'vue/multi-word-component-names': 'off',
    '@typescript-eslint/no-explicit-any': 'warn'
  }
}
```

#### 4.2.2 Prettier
```json
// .prettierrc
{
  "semi": false,
  "singleQuote": true,
  "printWidth": 100,
  "trailingComma": "none",
  "arrowParens": "always"
}
```

---

## 5. 性能优化规范

### 5.1 后端性能

```python
# 1. 数据库查询优化
# ❌ 错误: N+1查询
for task in tasks:
    cluster = db.query(Cluster).filter_by(id=task.cluster_id).first()

# ✅ 正确: 使用join
tasks = db.query(MergeTask).options(joinedload(MergeTask.cluster)).all()

# 2. 缓存
from functools import lru_cache

@lru_cache(maxsize=128)
def get_table_format(format_name: str) -> Dict:
    """缓存表格式信息"""
    pass

# 3. 批量操作
# ❌ 错误: 逐条插入
for metric in metrics:
    db.add(metric)
    db.commit()

# ✅ 正确: 批量插入
db.bulk_insert_mappings(TableMetric, metrics)
db.commit()
```

### 5.2 前端性能

```vue
<script setup lang="ts">
// 1. 计算属性缓存
const expensiveComputation = computed(() => {
  // 仅在依赖变化时重新计算
  return heavyCalculation(props.data)
})

// 2. v-if vs v-show
<!-- 频繁切换用v-show -->
<div v-show="visible">内容</div>

<!-- 条件很少改变用v-if -->
<div v-if="isAdmin">管理功能</div>

// 3. 虚拟滚动(大列表)
import { ElTableV2 } from 'element-plus'

<el-table-v2
  :columns="columns"
  :data="largeDataset"
  :width="700"
  :height="400"
  fixed
/>
</script>
```

---

## 6. 安全规范

### 6.1 后端安全

```python
# 1. SQL注入防护(使用参数化查询)
# ❌ 错误: 字符串拼接
db.execute(f"SELECT * FROM tables WHERE name = '{table_name}'")

# ✅ 正确: 参数化查询
db.execute(text("SELECT * FROM tables WHERE name = :name"), {"name": table_name})

# 2. 敏感信息加密
from cryptography.fernet import Fernet

class PasswordEncryptor:
    def encrypt(self, password: str) -> str:
        cipher = Fernet(SECRET_KEY)
        return cipher.encrypt(password.encode()).decode()

# 3. 输入验证
from pydantic import BaseModel, Field, validator

class CreateClusterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    hive_host: str = Field(..., regex=r'^[\w\-\.]+$')
    hive_port: int = Field(..., ge=1, le=65535)
```

### 6.2 前端安全

```typescript
// 1. XSS防护(Vue自动转义,避免v-html)
// ❌ 错误
<div v-html="userInput"></div>

// ✅ 正确
<div>{{ userInput }}</div>

// 2. CSRF防护(API携带Token)
axios.defaults.headers.common['X-CSRF-Token'] = csrfToken

// 3. 敏感数据不存localStorage
// ❌ 错误
localStorage.setItem('password', password)

// ✅ 正确: 使用sessionStorage或内存
const userStore = useUserStore()
userStore.setToken(token)  // Pinia内存存储
```

---

**文档维护者**: 项目架构师
**最后更新**: 2025-10-12
**下次评审**: 每月技术评审会
