# Hive小文件治理平台概要设计说明书

**文档版本**：v1.0  
**创建日期**：2025-09-10  
**项目名称**：Hive/Impala小文件治理平台  
**技术架构**：Python FastAPI + Vue 3 + TypeScript

---

## 1. 系统概述

### 1.1 项目背景

在大数据环境中，Hive/Impala集群经常面临小文件过多的问题，这会导致：
- NameNode内存压力增大
- 查询性能下降
- 存储效率降低
- 集群整体性能受影响

本平台旨在提供一套完整的Hive/Impala小文件监控、管理和治理解决方案。

### 1.2 系统目标

- **智能监控**：实时监控多集群小文件状况
- **可视化管理**：提供直观的Web界面进行管理操作
- **自动化治理**：支持自动化的小文件合并和治理
- **任务调度**：基于Celery的分布式任务处理
- **多集群支持**：统一管理多个CDH/CDP集群

### 1.3 核心功能特性

| 功能模块 | 主要特性 |
|---------|---------|
| 集群管理 | 多集群配置、连接测试、状态监控 |
| 智能扫描 | 直连MetaStore、HDFS扫描、增量更新 |
| 可视化监控 | 实时仪表板、趋势分析、统计报表 |
| 自动合并 | 多种合并策略、批量处理、任务调度 |
| 权限控制 | 角色管理、操作审计、安全认证 |
| 日志追踪 | 完整日志链、错误追踪、性能监控 |

## 2. 系统架构设计

### 2.1 整体架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │◄──►│   Vue 3 SPA     │◄──►│   FastAPI       │
│    (用户界面)    │    │   (前端应用)     │    │   (后端API)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       │                                │                                 │
                       ▼                                ▼                                 ▼
              ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
              │   Celery Beat   │              │  Celery Worker  │              │  SQLite/MySQL   │
              │   (任务调度)     │              │  (任务执行)      │              │   (数据存储)     │
              └─────────────────┘              └─────────────────┘              └─────────────────┘
                       │                                │
                       └────────────┬───────────────────┘
                                    │
                            ┌─────────────────┐
                            │      Redis      │
                            │   (消息队列)     │
                            └─────────────────┘
                                    │
                       ┌────────────┼────────────┐
                       │                         │
                       ▼                         ▼
              ┌─────────────────┐       ┌─────────────────┐
              │  Hive MetaStore │       │   HDFS Cluster  │
              │   (元数据库)     │       │   (文件系统)     │
              └─────────────────┘       └─────────────────┘
```

### 2.2 技术栈架构

#### 后端技术栈
```
FastAPI (Web框架)
├── SQLAlchemy (ORM)
├── Pydantic (数据验证)
├── Celery (任务队列)
├── Alembic (数据库迁移)
├── Redis (缓存/消息队列)
└── Sentry (错误监控)
```

#### 前端技术栈
```
Vue 3 (前端框架)
├── TypeScript (类型系统)
├── Element Plus (UI组件库)
├── Vue Router (路由管理)
├── Pinia (状态管理)
├── ECharts (图表库)
├── Axios (HTTP客户端)
└── Vite (构建工具)
```

### 2.3 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                        负载均衡器                            │
│                    (Nginx/HAProxy)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
              ┌───────┴───────┐
              │               │
              ▼               ▼
    ┌─────────────────┐ ┌─────────────────┐
    │   Frontend      │ │   Backend       │
    │   Container     │ │   Container     │
    │   (Vue 3 SPA)   │ │   (FastAPI)     │
    └─────────────────┘ └─────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  Celery Worker  │ │   PostgreSQL    │ │      Redis      │
    │   Container     │ │   Container     │ │   Container     │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 2.4 数据流向设计

```
用户操作 → Vue 3前端 → REST API → FastAPI后端 → 业务逻辑处理
    ↑                                                    ↓
    ┌─── 异步任务结果 ← Redis队列 ← Celery Worker ← 任务分发
    │
    └─── 实时数据更新 ← WebSocket连接 ← 监控数据收集
```

## 3. 功能模块设计

### 3.1 集群管理模块

#### 3.1.1 模块功能
- 集群配置管理（增删改查）
- 连接状态测试和监控
- 集群参数配置和调优
- 集群健康状态检查

#### 3.1.2 核心接口
```python
# 集群管理API
POST /api/v1/clusters/                    # 创建集群
GET /api/v1/clusters/                     # 获取集群列表  
GET /api/v1/clusters/{cluster_id}         # 获取集群详情
PUT /api/v1/clusters/{cluster_id}         # 更新集群配置
DELETE /api/v1/clusters/{cluster_id}      # 删除集群
POST /api/v1/clusters/{cluster_id}/test   # 测试连接
```

#### 3.1.3 数据模型
```python
class Cluster(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    hive_host = Column(String(255), nullable=False)
    hive_port = Column(Integer, default=10000)
    hive_metastore_url = Column(String(500), nullable=False)
    hdfs_namenode_url = Column(String(500), nullable=False)
    status = Column(String(20), default="active")
    small_file_threshold = Column(Integer, default=128*1024*1024)
```

### 3.2 监控扫描模块

#### 3.2.1 架构设计
```
扫描调度器
├── HybridTableScanner (智能混合扫描)
│   ├── MySQLHiveConnector (MySQL MetaStore)
│   ├── HiveConnector (PostgreSQL MetaStore) 
│   └── EnhancedWebHDFSScanner (HDFS文件扫描)
├── 连接器适配模式
│   ├── 连接器工厂 (ConnectorFactory)
│   ├── 上下文管理器 (Context Manager)
│   └── 异常处理机制 (Error Handling)
└── 扫描策略
    ├── 全量扫描 (Full Scan)
    ├── 增量扫描 (Incremental Scan)
    └── 分批扫描 (Batch Scan)
```

#### 3.2.2 核心扫描器
```python
class IntelligentHybridScanner:
    """智能混合扫描器 - 自适应选择最优扫描策略"""
    
    async def scan_database(self, cluster_id: int, database: str):
        """扫描整个数据库"""
        
    async def scan_table(self, cluster_id: int, database: str, table: str):
        """扫描单个表"""
        
    async def get_scan_progress(self, scan_id: str):
        """获取扫描进度"""
```

#### 3.2.3 连接器设计模式
```python
class MySQLHiveMetastoreConnector:
    """MySQL MetaStore连接器 - 适用于CDP集群"""
    
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        
    def get_tables(self, database: str):
        """获取数据库表列表"""
        
    def get_table_locations(self, database: str, table: str):
        """获取表存储位置"""
```

### 3.3 合并引擎模块

#### 3.3.1 引擎架构
```
合并引擎工厂 (EngineFactory)
├── BaseMergeEngine (抽象基类)
│   ├── validate_merge() (合并前验证)
│   ├── execute_merge() (执行合并)
│   └── rollback_merge() (回滚操作)
├── HiveConcatenateEngine (CONCATENATE策略)
│   ├── 适用格式: TEXTFILE, SEQUENCEFILE, RCFILE
│   ├── 直接HDFS层面合并
│   └── 高性能、低资源消耗
└── HiveInsertOverwriteEngine (INSERT OVERWRITE策略)
    ├── 适用所有文件格式
    ├── 重写数据布局
    └── 支持压缩优化
```

#### 3.3.2 工厂模式实现
```python
class MergeEngineFactory:
    @staticmethod
    def create_engine(strategy: str, cluster_config: dict) -> BaseMergeEngine:
        if strategy == "concatenate":
            return HiveConcatenateEngine(cluster_config)
        elif strategy == "insert_overwrite":
            return HiveInsertOverwriteEngine(cluster_config)
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")
```

### 3.4 任务调度模块

#### 3.4.1 Celery架构设计
```
Celery应用架构
├── celery_app.py (Celery应用配置)
├── 任务模块
│   ├── scan_tasks.py (扫描任务)
│   ├── merge_tasks.py (合并任务)  
│   └── maintenance_tasks.py (维护任务)
├── 调度配置
│   ├── Celery Beat (定时调度)
│   ├── 任务路由规则
│   └── 任务优先级设置
└── 监控告警
    ├── 任务状态监控
    ├── 失败任务重试
    └── 性能指标收集
```

#### 3.4.2 核心任务定义
```python
@celery_app.task(bind=True, max_retries=3)
def scan_cluster_tables(self, cluster_id: int, database: str = None):
    """扫描集群表任务"""
    
@celery_app.task(bind=True, max_retries=2)  
def merge_small_files(self, merge_task_id: int):
    """小文件合并任务"""
    
@celery_app.task
def cleanup_old_metrics():
    """清理历史指标数据"""
```

### 3.5 Web界面模块

#### 3.5.1 Vue 3组件架构
```
Vue 3应用架构
├── 布局组件 (Layout Components)
│   ├── DraggableGrid.vue (可拖拽网格布局)
│   └── 响应式布局适配
├── 页面组件 (Page Components)  
│   ├── Dashboard.vue (仪表板)
│   ├── Clusters.vue (集群管理)
│   ├── Tables.vue (表监控)
│   ├── Tasks.vue (任务管理)
│   └── TableDetail.vue (表详情)
├── 业务组件 (Business Components)
│   ├── cards/ (卡片组件)
│   │   ├── ClusterCard.vue
│   │   ├── TableCard.vue  
│   │   └── SmallFileCard.vue
│   └── charts/ (图表组件)
│       ├── TrendChart.vue
│       ├── DistributionChart.vue
│       └── TableFileCountChart.vue
└── 基础组件 (Base Components)
    └── ConnectionTestDialog.vue
```

#### 3.5.2 状态管理设计
```typescript
// Pinia Store设计
interface DashboardStore {
  // 状态数据
  clusters: Cluster[]
  metrics: TableMetric[]
  realTimeData: RealtimeData
  
  // 计算属性
  totalSmallFiles: ComputedRef<number>
  averageFileSize: ComputedRef<number>
  
  // 异步操作
  fetchDashboardData(): Promise<void>
  updateRealTimeData(): Promise<void>
}
```

## 4. 数据库设计

### 4.1 核心数据模型

#### 4.1.1 ER关系图
```
Cluster (集群)
    │ 1:N
    ├── TableMetric (表指标)
    │       │ 1:N
    │       └── PartitionMetric (分区指标)
    │
    └── MergeTask (合并任务)
            │ 1:N  
            └── TaskLog (任务日志)
```

#### 4.1.2 核心表结构

**clusters 表（集群配置）**
```sql
CREATE TABLE clusters (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    hive_host VARCHAR(255) NOT NULL,
    hive_port INTEGER DEFAULT 10000,
    hive_metastore_url VARCHAR(500) NOT NULL,
    hdfs_namenode_url VARCHAR(500) NOT NULL,
    hdfs_user VARCHAR(100) DEFAULT 'hdfs',
    hdfs_password VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active',
    small_file_threshold INTEGER DEFAULT 134217728,
    scan_enabled BOOLEAN DEFAULT true,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**table_metrics 表（表指标）**
```sql
CREATE TABLE table_metrics (
    id INTEGER PRIMARY KEY,
    cluster_id INTEGER REFERENCES clusters(id),
    database_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(200) NOT NULL,
    table_location VARCHAR(1000),
    file_format VARCHAR(50),
    total_files INTEGER DEFAULT 0,
    small_files INTEGER DEFAULT 0,
    total_size BIGINT DEFAULT 0,
    small_files_size BIGINT DEFAULT 0,
    avg_file_size BIGINT DEFAULT 0,
    last_scan_time TIMESTAMP,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**merge_tasks 表（合并任务）**
```sql
CREATE TABLE merge_tasks (
    id INTEGER PRIMARY KEY,
    cluster_id INTEGER REFERENCES clusters(id),
    database_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(200) NOT NULL,
    merge_strategy VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    files_before_merge INTEGER DEFAULT 0,
    files_after_merge INTEGER DEFAULT 0,
    space_saved BIGINT DEFAULT 0,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_time TIMESTAMP,
    completed_time TIMESTAMP
);
```

### 4.2 数据关系设计

#### 4.2.1 SQLAlchemy关系映射
```python
class Cluster(Base):
    # 一对多关系 - 集群包含多个表指标
    table_metrics = relationship("TableMetric", back_populates="cluster")
    # 一对多关系 - 集群包含多个合并任务  
    merge_tasks = relationship("MergeTask", back_populates="cluster")

class TableMetric(Base):
    # 多对一关系 - 表指标属于某个集群
    cluster = relationship("Cluster", back_populates="table_metrics")
    # 一对多关系 - 表包含多个分区指标
    partition_metrics = relationship("PartitionMetric", back_populates="table_metric")
```

## 5. 接口设计

### 5.1 REST API设计规范

#### 5.1.1 API版本和路径规范
```
基础路径: http://localhost:8000/api/v1/
认证方式: Bearer Token (可选)
数据格式: JSON
状态码: 标准HTTP状态码
```

#### 5.1.2 统一响应格式
```json
{
  "success": true,
  "data": {...},
  "message": "操作成功",
  "timestamp": "2025-09-10T08:00:00Z"
}
```

### 5.2 核心API接口

#### 5.2.1 集群管理接口
```yaml
# 集群列表
GET /api/v1/clusters/
Response: {
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "生产集群",
      "status": "active",
      "hive_host": "hive-prod.company.com",
      "small_file_threshold": 134217728,
      "created_time": "2025-09-10T08:00:00Z"
    }
  ]
}

# 连接测试  
POST /api/v1/clusters/{cluster_id}/test
Response: {
  "success": true,
  "data": {
    "hive_connection": "success",
    "hdfs_connection": "success", 
    "metastore_connection": "success"
  }
}
```

#### 5.2.2 表监控接口
```yaml
# 获取表指标
GET /api/v1/tables/metrics?cluster_id=1&database=default
Response: {
  "success": true,
  "data": [
    {
      "id": 1,
      "database_name": "default",
      "table_name": "user_logs", 
      "total_files": 1500,
      "small_files": 800,
      "total_size": 1073741824,
      "small_files_ratio": 0.533
    }
  ]
}

# 扫描表
POST /api/v1/tables/scan-table/{cluster_id}/{database}/{table}
Response: {
  "success": true,
  "data": {
    "scan_id": "scan_20250910_001",
    "status": "running"
  }
}
```

#### 5.2.3 任务管理接口
```yaml
# 创建合并任务
POST /api/v1/tasks/
Request: {
  "cluster_id": 1,
  "database_name": "default",
  "table_name": "user_logs",
  "merge_strategy": "concatenate"
}

# 执行任务
POST /api/v1/tasks/{task_id}/execute
Response: {
  "success": true,
  "data": {
    "task_id": 123,
    "status": "running",
    "celery_task_id": "task_uuid_12345"
  }
}
```

#### 5.2.4 仪表板接口
```yaml
# 获取仪表板数据
GET /api/v1/dashboard/overview
Response: {
  "success": true,
  "data": {
    "total_clusters": 3,
    "total_tables": 256,  
    "total_small_files": 12584,
    "total_space_wasted": 5368709120,
    "recent_tasks": [...],
    "top_problem_tables": [...]
  }
}
```

## 6. 安全设计

### 6.1 认证授权机制

#### 6.1.1 JWT Token认证 (可选扩展)
```python
# 认证装饰器
@jwt_required
async def protected_endpoint():
    current_user = get_jwt_identity()
    return {"user": current_user}
```

#### 6.1.2 操作权限控制
```python
class Permission(Enum):
    READ_CLUSTER = "cluster:read"
    WRITE_CLUSTER = "cluster:write" 
    EXECUTE_TASK = "task:execute"
    DELETE_DATA = "data:delete"
```

### 6.2 数据安全保护

#### 6.2.1 敏感信息加密
- 集群连接密码使用AES加密存储
- API传输使用HTTPS协议
- 数据库连接启用SSL

#### 6.2.2 审计日志
```python
class AuditLog(Base):
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))
    action = Column(String(200))  # 操作类型
    resource = Column(String(200))  # 操作资源
    ip_address = Column(String(45))
    timestamp = Column(DateTime)
```

## 7. 部署与运维

### 7.1 环境依赖

#### 7.1.1 运行环境要求
```yaml
系统环境:
  - Linux/Unix系统 (推荐CentOS 7+/Ubuntu 18+)
  - Python 3.9+
  - Node.js 16+

数据库:
  - PostgreSQL 12+ (推荐生产环境)
  - MySQL 8+ (支持)
  - SQLite 3+ (开发环境)

中间件:
  - Redis 6+ (消息队列和缓存)
  - Nginx (反向代理和负载均衡)
```

#### 7.1.2 集群连接要求
```yaml
Hive/Impala集群:
  - Hive Server2 可访问
  - Hive MetaStore 数据库可连接
  - HDFS NameNode WebHDFS API可访问
  - 网络连通性和防火墙配置

权限要求:
  - Hive数据库查询权限
  - HDFS文件系统读写权限
  - Kerberos认证支持 (如果启用)
```

### 7.2 Docker容器化部署

#### 7.2.1 Docker Compose配置
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
      
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
      
  celery-worker:
    build: ./backend
    command: celery -A app.scheduler.celery_app worker --loglevel=info
    depends_on:
      - postgres
      - redis
      
  celery-beat:
    build: ./backend  
    command: celery -A app.scheduler.celery_app beat --loglevel=info
    depends_on:
      - postgres
      - redis
      
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=hive_small_file_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  redis:
    image: redis:6-alpine
    
volumes:
  postgres_data:
```

### 7.3 监控告警系统

#### 7.3.1 监控指标
```yaml
系统指标:
  - API响应时间和成功率
  - 数据库连接池状态
  - Redis队列长度
  - Celery任务执行情况

业务指标:  
  - 集群连接状态
  - 扫描任务执行频率
  - 小文件数量变化趋势
  - 合并任务成功率
  
资源指标:
  - CPU使用率
  - 内存占用  
  - 磁盘空间
  - 网络IO
```

#### 7.3.2 告警规则
```yaml
告警级别:
  Critical: 系统不可用、数据丢失风险
  Warning: 性能下降、功能异常
  Info: 状态变更、操作记录

告警通道:
  - 邮件通知
  - 钉钉/企微机器人
  - 短信通知 (Critical级别)
```

## 8. 性能与扩展性

### 8.1 性能优化策略

#### 8.1.1 数据库优化
```sql
-- 核心表索引优化
CREATE INDEX idx_table_metrics_cluster_time ON table_metrics(cluster_id, last_scan_time);
CREATE INDEX idx_merge_tasks_status_time ON merge_tasks(status, created_time);
CREATE INDEX idx_clusters_status ON clusters(status);

-- 分区表设计 (大数据量场景)
CREATE TABLE table_metrics_2025_09 PARTITION OF table_metrics
FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
```

#### 8.1.2 缓存策略  
```python
# Redis缓存配置
@cached(ttl=300)  # 5分钟缓存
async def get_cluster_summary(cluster_id: int):
    """集群摘要信息缓存"""
    
# 应用层缓存
@lru_cache(maxsize=128)
def get_file_format_info(format_name: str):
    """文件格式信息缓存"""
```

#### 8.1.3 异步处理优化
```python
# 异步扫描任务
@celery_app.task
def bulk_scan_tables(cluster_id: int, tables: List[str]):
    """批量扫描表 - 减少任务调度开销"""
    
# 并发控制
CELERY_WORKER_CONCURRENCY = 4  # Worker并发数
CELERY_TASK_RATE_LIMIT = "10/m"  # 任务限流
```

### 8.2 扩展性设计

#### 8.2.1 水平扩展支持
```yaml
前端扩展:
  - 静态资源CDN分发
  - 多实例负载均衡
  - 客户端缓存策略

后端扩展:  
  - API服务多实例部署
  - 数据库读写分离
  - 微服务架构演进

任务处理扩展:
  - Celery Worker集群
  - 队列路由和分片  
  - 任务优先级调度
```

#### 8.2.2 插件化架构
```python
# 扫描器插件接口
class BaseScannerPlugin:
    def scan_database(self, config): pass
    def scan_table(self, config): pass
    
# 合并引擎插件
class BaseEnginePlugin:  
    def validate_merge(self, params): pass
    def execute_merge(self, params): pass
```

### 8.3 容量规划

#### 8.3.1 存储容量评估
```yaml
数据存储预估 (每集群):
  - 表指标数据: ~100KB/表/月
  - 任务日志数据: ~50KB/任务
  - 审计日志: ~10KB/操作
  
中等规模环境 (10集群, 10K表):
  - 数据库存储: ~50GB/年
  - Redis内存: ~4GB
  - 应用日志: ~20GB/年
```

#### 8.3.2 性能基准
```yaml
性能目标:
  - API响应时间: P95 < 1000ms
  - 页面加载时间: < 3s
  - 表扫描速度: > 100表/分钟
  - 合并任务并发: > 10任务同时执行

硬件建议:
  - CPU: 8核+ (推荐16核)
  - 内存: 16GB+ (推荐32GB)
  - 存储: SSD 500GB+
  - 网络: 千兆以太网
```

---

## 附录

### A. 配置文件模板

#### A.1 后端环境配置 (.env)
```env
# 数据库配置
DATABASE_URL=postgresql://username:password@localhost/hive_small_file_db

# Redis配置  
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 安全配置
SECRET_KEY=your-secret-key-here-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Hive/HDFS默认配置
DEFAULT_HIVE_HOST=localhost
DEFAULT_HIVE_PORT=10000
DEFAULT_HDFS_URL=hdfs://localhost:9000

# 业务配置
SMALL_FILE_THRESHOLD=134217728  # 128MB

# Sentry监控 (可选)
SENTRY_DSN=https://your-sentry-dsn
SENTRY_ENVIRONMENT=production
```

### B. 部署脚本

#### B.1 快速部署脚本
```bash
#!/bin/bash
# 快速部署脚本

echo "开始部署Hive小文件治理平台..."

# 创建目录
mkdir -p /opt/hive-platform
cd /opt/hive-platform

# 下载代码
git clone <repository-url> .

# 构建并启动服务
docker-compose up -d --build

# 等待服务启动
sleep 30

# 初始化数据库
docker-compose exec backend alembic upgrade head

echo "部署完成!"
echo "Web界面: http://localhost:3000"
echo "API文档: http://localhost:8000/docs"
```

### C. 常见问题解答

#### C.1 连接问题
**Q: 无法连接到Hive MetaStore数据库？**
A: 检查防火墙设置、数据库权限配置、网络连通性

**Q: HDFS连接超时？**  
A: 确认NameNode WebHDFS服务状态，检查端口(通常50070/9870)是否开放

#### C.2 性能问题
**Q: 扫描大表很慢？**
A: 调整扫描批量大小，考虑分批扫描或增量扫描策略

**Q: 合并任务排队很长？**
A: 增加Celery Worker实例，调整任务并发数配置

---

**文档版权**：© 2025 Hive小文件治理平台项目组  
**技术支持**：通过项目Issue系统获取技术支持  
**更新频率**：本文档将随项目迭代持续更新