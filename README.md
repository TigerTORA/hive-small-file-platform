# Hive/Impala 小文件治理平台

![CI](https://github.com/your-username/hive-small-file-platform/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Status Report](https://img.shields.io/badge/Status-Project%20Report-blue)

一个基于 Python 的 Hive/Impala 小文件监控和治理平台，支持多集群管理、自动扫描、智能合并和任务调度。

## 项目概述

该平台通过直连 Hive MetaStore 数据库和 HDFS API 来扫描集群中的小文件情况，提供 Web 界面进行监控和管理，支持自动化的文件合并任务来优化存储和性能。

## 主要功能

- **多集群管理**：支持管理多个 CDH/CDP 集群
- **智能扫描**：直连 MetaStore 和 HDFS，高效扫描表的文件分布
- **可视化监控**：提供仪表板展示小文件统计和趋势
- **自动合并**：支持 Hive CONCATENATE 和 INSERT OVERWRITE 两种合并策略
- **任务调度**：基于 Celery Beat 的定时任务和手动触发
- **权限控制**：安全的操作权限管理
- **日志追踪**：完整的任务执行日志和错误追踪

## 系统架构

### 技术栈
- **后端**：Python FastAPI + SQLAlchemy + Celery
- **前端**：Vue 3 + TypeScript + Element Plus + ECharts
- **数据库**：PostgreSQL/MySQL
- **消息队列**：Redis
- **任务调度**：Celery Beat
- **监控**：Prometheus + Grafana

### 核心模块
- **监控模块**：Hive MetaStore 连接器 + HDFS 扫描器
- **合并引擎**：可扩展的合并引擎架构
- **任务调度**：Celery 分布式任务队列
- **Web 界面**：Vue 3 响应式管理界面

## 项目结构

```
hive-small-file-platform/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── monitor/           # 监控模块
│   │   │   ├── hive_connector.py      # Hive MetaStore 连接器
│   │   │   ├── hdfs_scanner.py        # HDFS 文件扫描器
│   │   │   └── table_scanner.py       # 表扫描服务
│   │   ├── engines/           # 合并引擎
│   │   │   ├── base_engine.py         # 引擎基类
│   │   │   ├── hive_engine.py         # Hive SQL 引擎
│   │   │   └── engine_factory.py      # 引擎工厂
│   │   ├── scheduler/         # 任务调度
│   │   │   ├── celery_app.py          # Celery 应用配置
│   │   │   ├── scan_tasks.py          # 扫描任务
│   │   │   ├── merge_tasks.py         # 合并任务
│   │   │   └── maintenance_tasks.py   # 维护任务
│   │   ├── api/              # API 接口
│   │   ├── models/           # 数据模型
│   │   ├── schemas/          # Pydantic 模式
│   │   ├── security/         # 权限控制
│   │   └── config/           # 配置管理
│   ├── config/               # 配置文件
│   └── requirements.txt      # Python 依赖
├── frontend/                  # 前端界面
│   ├── src/
│   │   ├── components/       # Vue 组件
│   │   ├── views/           # 页面视图
│   │   ├── api/             # API 调用
│   │   └── router/          # 路由配置
│   ├── package.json         # Node.js 依赖
│   └── vite.config.ts       # Vite 配置
├── docker/                   # Docker 部署
└── docs/                    # 文档
```

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+
- PostgreSQL 12+ 或 MySQL 8+
- Redis 6+
- 可访问的 CDH/CDP 集群

### 1. 克隆项目

```bash
git clone <repository-url>
cd hive-small-file-platform
```

### 2. 后端设置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\\Scripts\\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库连接等配置

# 初始化数据库
alembic upgrade head

# 启动 API 服务
uvicorn app.main:app --reload --port 8000
```

### 3. 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 启动 Celery 服务

```bash
# 在 backend 目录下

# 启动 Celery Worker
celery -A app.scheduler.celery_app worker --loglevel=info

# 启动 Celery Beat（定时任务）
celery -A app.scheduler.celery_app beat --loglevel=info
```

### 5. 访问应用

- Web 界面: http://localhost:3000
- API 文档: http://localhost:8000/docs

## 项目健康报告与持续集成

- 一键生成本地报告：`make status`，输出 `PROJECT_STATUS.md` 与 `project_status.json`
- GitHub Actions CI：
  - 后端：pytest + 覆盖率（上传 coverage.xml）
  - 前端：构建 + Vitest 单元测试
  - 汇总：生成并上传项目健康报告工件（PROJECT_STATUS.md / project_status.json）
- 每周报告：`Weekly Status Report` 工作流会按周生成最新报告工件。

提示：将徽章中的 `your-username/hive-small-file-platform` 替换为实际仓库路径即可显示状态。

## 迁移与配置（升级指南）

- 数据库迁移（新增扫描日志持久化表）
  - 进入 `backend/`，执行：
    - `alembic upgrade head`
  - 说明：本次升级新增 `scan_task_logs` 表用于持久化扫描任务日志。建议生产环境使用 Alembic 管理迁移，不依赖自动建表。

- 前端 API 基址配置（多环境）
  - 复制 `frontend/.env.example` 为 `.env`，并按需修改：
    - `VITE_API_BASE_URL=http://localhost:8000/api/v1`
  - 前端已读取 `VITE_API_BASE_URL`，未设置时将回退到 `http://localhost:8000/api/v1`。

- 生产环境关闭自动建表
  - 后端环境变量：`AUTO_CREATE_SCHEMA=false`
  - 后端默认在开发环境下自动建表。生产请关闭并依赖 Alembic 迁移。

## 配置说明

### 环境变量配置 (.env)

```env
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost/hive_small_file_db

# Redis 配置
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 安全配置
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 默认 Hive/HDFS 设置
DEFAULT_HIVE_HOST=localhost
DEFAULT_HIVE_PORT=10000
DEFAULT_HDFS_URL=hdfs://localhost:9000

# 小文件阈值（字节）
SMALL_FILE_THRESHOLD=134217728
```

### 集群配置

在 Web 界面的集群管理页面添加集群配置：

1. **集群名称**：便于识别的集群名称
2. **Hive 连接**：Hive Server2 的主机和端口
3. **MetaStore URL**：Hive MetaStore 数据库连接字符串
4. **HDFS NameNode**：HDFS NameNode 的连接地址
5. **小文件阈值**：定义小文件的大小阈值（默认 128MB）

## 使用指南

### 1. 集群管理

- 添加集群配置
- 测试连接状态
- 启用/禁用自动扫描

### 2. 表监控

- 查看表的小文件统计
- 筛选和搜索问题表
- 触发手动扫描

### 3. 任务管理

- 创建合并任务
- 监控任务执行状态
- 查看任务日志
- 手动执行或取消任务

### 4. 监控仪表板

- 集群整体小文件统计
- 小文件趋势图表
- 文件大小分布
- 最近任务和问题表排行

## 合并策略说明

### CONCATENATE 策略
- 适用于 TEXTFILE、SEQUENCEFILE、RCFILE 格式
- 直接在 HDFS 层面合并文件
- 速度快，资源消耗少
- 不改变数据内容

### INSERT OVERWRITE 策略
- 适用于所有文件格式
- 通过重新写入数据进行合并
- 可以重新组织数据布局
- 支持数据压缩和优化

## API 接口

### 集群管理
- `GET /api/v1/clusters/` - 获取集群列表
- `POST /api/v1/clusters/` - 创建集群
- `GET /api/v1/clusters/{id}` - 获取集群详情
- `POST /api/v1/clusters/{id}/test` - 测试集群连接

### 表监控
- `GET /api/v1/tables/metrics` - 获取表指标
- `GET /api/v1/tables/small-files` - 获取小文件摘要
- `POST /api/v1/tables/scan` - 触发表扫描

### 任务管理
- `GET /api/v1/tasks/` - 获取任务列表
- `POST /api/v1/tasks/` - 创建任务
- `POST /api/v1/tasks/{id}/execute` - 执行任务
- `GET /api/v1/tasks/{id}/logs` - 获取任务日志

### 扫描接口（严格模式默认启用）
- `POST /api/v1/tables/scan`
  - 用途：统一扫描入口（支持单库或单表）
  - 请求体：`{ cluster_id, database_name?, table_name? }`
  - 查询参数：
    - `strict_real`（默认 `true`）：严格实连模式，MetaStore 或 HDFS 任一实连失败即终止，不降级 Mock。
  - 行为：当提供 `database_name` 且不提供 `table_name` 时扫描该库；同时提供两者时扫描单表。

- `POST /api/v1/tables/scan/{cluster_id}`
  - 用途：发起集群级批量扫描（带进度追踪）
  - 查询参数：
    - `max_tables_per_db`（默认空）：每库最大扫描表数；为空表示不限制。
    - `strict_real`（默认 `true`）：严格实连模式。
  - 进度查询：
    - `GET /api/v1/tables/scan-progress/{task_id}`（实时）
    - `GET /api/v1/tables/scan-progress/cluster/{cluster_id}`（概览）

- `POST /api/v1/tables/scan-real/{cluster_id}/{database_name}`
  - 用途：对指定数据库执行严格实连扫描
  - 查询参数：
    - `max_tables`（默认 `0`）：`0` 或负值表示不限制；>0 则限制数量。
    - `strict_real`（默认 `true`）

- `GET /api/v1/tables/partition-metrics`
  - 用途：查询分区表的分区级小文件统计
  - 查询参数：
    - `cluster_id`、`database_name`、`table_name`
    - `page`（默认 `1`），`page_size`（默认 `50`，最大 `200`）
    - `concurrency`（默认 `5`，1–20）：并发扫描分区数
  - 说明：为提升性能，服务端对分区目录扫描采用线程池并发；返回按请求页排序。

## 监控告警

### 系统监控指标

- 集群连接状态
- 扫描任务执行情况
- 合并任务成功率
- 小文件数量趋势
- 存储空间节省情况

### 告警规则

- 小文件数量超过阈值
- 小文件占比过高
- 任务执行失败
- 集群连接异常

## 部署方案

### Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d
```

### Kubernetes 部署

```bash
# 应用 Kubernetes 配置
kubectl apply -f k8s/
```

### 生产环境建议

1. **高可用**：部署多个 API 实例和 Worker 实例
2. **监控**：集成 Prometheus 和 Grafana
3. **日志**：配置日志收集和分析
4. **备份**：定期备份数据库和配置
5. **安全**：使用 HTTPS 和身份认证

## 开发指南

### 扩展合并引擎

1. 继承 `BaseMergeEngine` 类
2. 实现必要的抽象方法
3. 在 `engine_factory.py` 中注册新引擎

### 添加新的调度任务

1. 在 `scheduler` 目录下创建任务模块
2. 使用 `@celery_app.task` 装饰器定义任务
3. 在 `celery_app.py` 中配置任务调度

### 前端组件开发

1. 在 `components` 目录下创建 Vue 组件
2. 使用 TypeScript 和 Element Plus
3. 遵循现有的代码风格和命名规范

## 常见问题

### Q: 如何处理大规模集群的性能问题？
A: 
- 调整扫描并发数和超时时间
- 使用数据库索引优化查询
- 考虑对大表分批处理

### Q: 合并任务失败怎么办？
A: 
- 查看任务日志了解具体错误
- 检查集群连接和权限
- 验证表格式和合并策略兼容性

### Q: 如何监控系统运行状态？
A: 
- 查看系统设置页面的系统信息
- 监控 Celery 队列状态
- 检查数据库和 Redis 连接

## 许可证

MIT License

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

## 联系方式

如有问题，请通过 Issue 联系我们。

---

CI 演示占位：本行用于触发 CI 并演示 PR 工作流（可在合并前移除）。

## 工程化护栏（轻量）

- 最小 CI：`.github/workflows/ci.yml` 会在 PR 和 push 时自动运行后端/前端测试并上传状态报告。
- PR 模板：`.github/pull_request_template.md` 引导描述动机、风险、验证与回滚步骤。
- ADR（架构决策记录）：`docs/adr/` 存放重要技术决策；模板见 `0000-template.md`，示例见 `0001-hdfs-access-and-scan-approach.md`。

建议工作流（不拖慢你速度）：
1. 先写 3–5 行目标/验收（PR 描述里即可）。
2. 涉及技术取舍时，新建一条 ADR（模板复制后 5 分钟内可完成）。
3. 提交 PR，CI 通过后合并；如有问题，按模板的回滚步骤执行。
