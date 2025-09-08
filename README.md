# Hive/Impala 小文件治理平台

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