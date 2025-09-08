# 用户查询端到端流程追踪文档

## 概述
本文档详细追踪用户查询从前端发起到后端处理，再到数据库查询的完整流程。

## 1. 前端架构 (frontend/)

### 1.1 路由结构
**文件**: `/frontend/src/router/index.ts`

主要路由映射:
- `/` → 重定向到 `/dashboard`
- `/dashboard` → `Dashboard.vue` (监控仪表板)
- `/clusters` → `Clusters.vue` (集群管理)
- `/tables` → `Tables.vue` (表管理)
- `/tasks` → `Tasks.vue` (任务管理)
- `/settings` → `Settings.vue` (系统设置)

每个路由都设置了 `meta.title` 用于页面标题显示。

### 1.2 API客户端封装
**文件**: `/frontend/src/api/index.ts`

- 基础URL: `/api/v1`
- 超时时间: 30秒
- 自动错误提示 (通过 Element Plus)
- 响应拦截器自动提取 `response.data`

### 1.3 集群相关API
**文件**: `/frontend/src/api/clusters.ts`

提供的API方法:
- `clustersApi.list()` → `GET /api/v1/clusters/`
- `clustersApi.create()` → `POST /api/v1/clusters/`
- `clustersApi.get(id)` → `GET /api/v1/clusters/${id}`
- `clustersApi.update(id)` → `PUT /api/v1/clusters/${id}`
- `clustersApi.delete(id)` → `DELETE /api/v1/clusters/${id}`
- `clustersApi.testConnection(id)` → `POST /api/v1/clusters/${id}/test`

### 1.4 Dashboard组件示例
**文件**: `/frontend/src/views/Dashboard.vue`

- 显示统计卡片：集群数、监控表数、文件总数、小文件数量
- ECharts图表：小文件趋势图、文件大小分布饼图  
- 最近任务列表、小文件数量TOP10表格
- 当前使用模拟数据 (TODO: 调用实际API)

## 2. 后端架构 (backend/)

### 2.1 FastAPI应用入口
**文件**: `/backend/app/main.py`

- 基础路径：`/api/v1/`
- 路由注册：
  - `/api/v1/clusters` → `clusters.router`
  - `/api/v1/tables` → `tables.router`
  - `/api/v1/tasks` → `tasks.router`
  - `/api/v1/errors` → `errors.router`
- CORS中间件：允许所有来源
- 健康检查：`GET /health`

### 2.2 集群管理API
**文件**: `/backend/app/api/clusters.py`

核心端点:
- `GET /` → 获取所有集群列表
- `POST /` → 创建新集群
- `GET /{cluster_id}` → 获取集群详情
- `POST /{cluster_id}/test` → 测试集群连接
- `GET /health-check` → 检查所有集群健康状态

### 2.3 表管理API
**文件**: `/backend/app/api/tables.py`

核心端点:
- `GET /metrics?cluster_id=X` → 获取表指标数据
- `GET /small-files?cluster_id=X` → 获取小文件汇总
- `GET /databases/{cluster_id}` → 获取数据库列表
- `GET /tables/{cluster_id}/{database_name}` → 获取表列表
- `POST /scan` → 统一扫描端点(表或数据库)
- `POST /scan/{cluster_id}/{database_name}` → 扫描数据库所有表
- `POST /scan-table/{cluster_id}/{database_name}/{table_name}` → 扫描单表

## 3. 数据层架构

### 3.1 连接器模式
**文件**: `/backend/app/monitor/mysql_hive_connector.py`

`MySQLHiveMetastoreConnector` 类:
- 连接 CDP 集群的 MySQL MetaStore
- 使用 PyMySQL 驱动，支持上下文管理器
- 核心方法：
  - `get_databases()` → 查询 `DBS` 表获取数据库列表  
  - `get_tables(database_name)` → 联接 `TBLS`, `SDS`, `DBS` 表获取表信息
  - `get_table_partitions()` → 联接 `PARTITIONS` 表获取分区信息
  - `test_connection()` → 连接测试并返回基本统计

### 3.2 表扫描器
**文件**: `/backend/app/monitor/mock_table_scanner.py`

`MockTableScanner` 类 (演示版本):
- 整合 `MySQLHiveMetastoreConnector` 和 `MockHDFSScanner`
- 核心方法：
  - `scan_table()` → 扫描单表，保存 `TableMetric` 和 `PartitionMetric`
  - `scan_database_tables()` → 批量扫描数据库所有表
  - `test_connections()` → 测试 MetaStore 和 HDFS 连接

### 3.3 数据模型
**文件**: `/backend/app/models/table_metric.py`

`TableMetric` 模型字段:
- 表标识：`cluster_id`, `database_name`, `table_name`, `table_path`
- 文件指标：`total_files`, `small_files`, `total_size`, `avg_file_size`
- 分区信息：`is_partitioned`, `partition_count`
- 扫描元数据：`scan_time`, `scan_duration`
- 关系：与 `Cluster` 和 `PartitionMetric` 的外键关联

## 4. 典型查询流程示例

### 场景：Dashboard页面加载集群统计

1. **前端发起**:
   ```typescript
   // Dashboard.vue 组件挂载时
   onMounted(() => {
     loadDashboardData()
   })
   ```

2. **API调用** (当前为模拟数据):
   ```typescript
   // 未来应调用：
   const clusters = await clustersApi.list()
   const metrics = await tablesApi.getMetrics(clusterId)
   ```

3. **后端处理**:
   ```python
   # /api/v1/clusters/ → clusters.py:list_clusters()
   clusters = db.query(Cluster).all()
   return clusters
   ```

4. **数据库查询**:
   ```sql
   SELECT * FROM clusters;
   ```

### 场景：扫描单表小文件

1. **前端发起**:
   ```typescript
   await tablesApi.scanTable(clusterId, databaseName, tableName)
   ```

2. **后端路由** (`/api/v1/tables/scan-table/{cluster_id}/{database_name}/{table_name}`):
   ```python
   # tables.py:scan_single_table()
   cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
   scanner = MockTableScanner(cluster)
   ```

3. **MetaStore查询**:
   ```python
   # MySQLHiveMetastoreConnector.get_tables()
   query = """
   SELECT t.TBL_NAME, s.LOCATION, t.TBL_TYPE, COUNT(p.PART_ID)
   FROM TBLS t JOIN SDS s ON t.SD_ID = s.SD_ID 
   JOIN DBS d ON t.DB_ID = d.DB_ID
   LEFT JOIN PARTITIONS p ON p.TBL_ID = t.TBL_ID
   WHERE d.NAME = %s
   """
   ```

4. **HDFS扫描** (模拟):
   ```python
   # MockHDFSScanner.scan_table_partitions()
   # 模拟生成文件统计数据
   ```

5. **结果保存**:
   ```python
   # 保存到 table_metrics 表
   table_metric = TableMetric(...)
   db_session.add(table_metric)
   db_session.commit()
   ```

## 5. 数据流向总结

```
用户操作 → Vue组件 → API客户端 → FastAPI路由 → 业务逻辑 → 连接器层 → 外部系统
  ↓         ↓        ↓        ↓         ↓        ↓        ↓
Dashboard → loadData → axios → /clusters → query → SQLAlchemy → PostgreSQL/MySQL
  ↓         ↓        ↓        ↓         ↓        ↓        ↓  
Tables   → scanTable → axios → /tables → scanner → Connector → Hive MetaStore
  ↓         ↓        ↓        ↓         ↓        ↓        ↓
Results  → display ← response ← JSON ← Model ← Query ← MySQL/HDFS
```

## 6. 关键技术组件

- **前端**: Vue 3 + TypeScript + Element Plus + ECharts + Axios
- **后端**: FastAPI + SQLAlchemy + Pydantic + PyMySQL  
- **数据存储**: SQLite/PostgreSQL (应用数据) + MySQL (Hive MetaStore)
- **监控**: Sentry (错误追踪)
- **任务队列**: Celery + Redis (后台扫描任务)

## 7. 开发模式特点

- **连接器模式**: 可插拔的 MetaStore 和 HDFS 连接器
- **工厂模式**: 多种合并引擎的抽象工厂
- **上下文管理**: 自动资源管理 (`__enter__`/`__exit__`)
- **模拟模式**: Mock组件用于开发和演示

---

**证据链接**: 
- 前端路由: `frontend/src/router/index.ts:3-41`
- API客户端: `frontend/src/api/index.ts:4-32` 
- 集群API: `backend/app/api/clusters.py:10-94`
- 表API: `backend/app/api/tables.py:12-309`
- MetaStore连接: `backend/app/monitor/mysql_hive_connector.py:23-184`
- 扫描器: `backend/app/monitor/mock_table_scanner.py:25-162`
- 数据模型: `backend/app/models/table_metric.py:6-33`