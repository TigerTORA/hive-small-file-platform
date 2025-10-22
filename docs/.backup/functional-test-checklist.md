# 功能测试清单

> **文档说明**: 本文档用于迭代式功能验证与发布前验收
> **版本**: v1.1
> **最后更新**: 2025-10-21

## 📚 文档使用说明

### 内容分类标记

| 标记 | 说明 | 操作规则 |
|------|------|----------|
| 📋 **TEMPLATE** | 固定模板内容（测试项、检查点） | ⚠️ 需经团队同意才可修改 |
| ✏️ **FILL** | 每次测试时填写的信息 | ✅ 每次测试时更新 |
| ⚠️ **ISSUE** | 测试中发现的问题 | 🔄 问题解决后删除 |
| ✅ **RESULT** | 本次测试的结果记录 | 📝 记录后保留，下次测试前清空 |

### 使用流程

1. **开始新测试**：清空所有 `✏️ FILL` 和 `✅ RESULT` 内容
2. **执行测试**：按顺序完成检查项，勾选 `[ ]` → `[x]`
3. **记录问题**：在对应位置添加 `⚠️ ISSUE` 标记的问题描述
4. **总结归档**：测试完成后保存结果，问题解决后删除 ISSUE 标记

---

## 📋 一、范围与前置条件（TEMPLATE）

### 1.1 环境确认（每次测试填写）

**✏️ FILL - 本次测试环境信息**：

- [ ] **测试环境类型**：
  - [ ] Demo 模式（无 Hive/HDFS）
  - [ ] 预生产环境
  - [ ] 生产环境

- [ ] **测试集群信息**：
  - 集群名称：`_________________`
  - 集群地址：`_________________`
  - 认证方式：`_________________`
  - 测试模式：`_________________`

**✅ RESULT - 本次测试记录**：

<!-- 示例：
- [x] 测试环境类型：预生产环境
- 测试集群：CDP-14 (192.168.0.105)
- 测试模式：Real Mode（真实连接）
- 认证方式：LDAP (Hive: hive/*, HDFS: hdfs)
- 集群状态：active (健康状态: degraded, 最后检查: 2025-10-10)
-->

### 1.2 环境检查（固定检查项）

**📋 TEMPLATE - 必需检查项**：

- [ ] **运行环境**：
  - [ ] Python 版本：3.10+ ✓
  - [ ] Node 版本：20.x ✓
  - [ ] Docker（可选）

- [ ] **配置文件**：
  - [ ] `backend/.env` 已配置（基于 `.env.example`）
  - [ ] `frontend/.env` 已配置（基于 `.env.example`）
  - [ ] ⚠️ 确认未提交密钥信息

- [ ] **依赖安装**：
  - [ ] 后端依赖：`pip install -r requirements.txt`
  - [ ] 前端依赖：`npm install`（如需要）

- [ ] **服务启动**：
  - [ ] 后端服务：`http://localhost:8000`
  - [ ] 前端服务：`http://localhost:5173`（或其他端口）

**✅ RESULT - 实际环境记录**：

<!-- 示例：
- [x] Python 3.10.18（conda 虚拟环境 `hive-backend`）
- [x] Node 20.17.0
- [x] Docker 26.1.4
- [x] backend/.env ✓ 已存在
- [x] frontend/.env ✓ 已存在
- [x] 后端服务运行于 :8000
- [x] 前端服务运行于 :5173
-->

**⚠️ ISSUE - 环境问题记录**：

<!-- 问题解决后删除此部分
示例：
- 问题：Python 3.6 不兼容依赖
- 解决：使用 conda 创建 Python 3.10 环境
- 状态：✅ 已解决
-->

### 1.3 服务验证命令（参考模板）

**📋 TEMPLATE - 验证命令清单**：

```bash
# 1. 后端健康检查
curl -s http://localhost:8000/health

# 2. 后端根路径
curl -s http://localhost:8000/

# 3. 集群列表 API
curl -s http://localhost:8000/api/v1/clusters/

# 4. API 文档（浏览器访问）
# http://localhost:8000/docs

# 5. 前端页面（浏览器访问）
# http://localhost:5173
```

**✅ RESULT - 验证结果**：

<!-- 记录实际执行结果
示例：
✓ 后端健康检查：status=healthy
✓ API 根路径：返回平台标识
✓ 集群列表：返回 3 个集群
✓ Swagger UI：可访问
✓ 前端页面：正常加载
-->

---

## 📋 二、后端 API 基础验证（TEMPLATE）

**测试目标**：验证基础 API 端点可用性、健康检查、CORS 配置

- [ ] **GET `/`**：返回平台标识信息
  - 预期响应：`{"message": "Hive Small File Management Platform API"}`

- [ ] **GET `/health`**：返回健康状态
  - 预期响应：`status=healthy` 且包含 `server_config`

- [ ] **CORS 验证**：
  - [ ] 前端地址在允许列表内
  - [ ] 可正常调用 API（无跨域错误）

**✅ RESULT - 测试结果**：

<!-- 记录测试结果 -->

**⚠️ ISSUE - 问题记录**：

<!-- 记录发现的问题，解决后删除 -->

---

## 📋 三、集群管理 API（/api/v1/clusters）（TEMPLATE）

**测试目标**：验证集群 CRUD 操作、连接测试、健康检查

- [ ] **列表查询**：
  - [ ] `GET /api/v1/clusters/` 返回集群数组
  - [ ] 无 500 错误

- [ ] **创建集群**：
  - [ ] `POST /api/v1/clusters?validate_connection=false` 成功创建
  - [ ] 非法 URL 被拒绝（400 错误）

- [ ] **创建并验证连接**：
  - [ ] `validate_connection=true` 时，MetaStore 失败返回 400
  - [ ] HDFS 失败为警告但仍创建集群

- [ ] **查询单个集群**：
  - [ ] `GET /{id}` 存在时返回 200
  - [ ] 不存在时返回 404

- [ ] **更新集群**：
  - [ ] `PUT /{id}` 部分字段更新成功
  - [ ] 返回最新值

- [ ] **集群统计**：
  - [ ] `GET /{id}/stats` 返回完整字段
  - [ ] 包含 database/table/small files 统计

- [ ] **健康指标**：
  - [ ] `GET /health-metrics?days=7` 正常返回
  - [ ] 有效范围：1–90 天

- [ ] **批量健康检查**：
  - [ ] `POST /batch-health-check` 返回成功/失败计数

- [ ] **连接测试**：
  - [ ] `POST /{id}/test?mode=mock` 模拟测试通过
  - [ ] `POST /{id}/test?mode=real` 真实连接测试
  - [ ] `force_refresh=true/false` 行为符合预期

**✅ RESULT - 测试结果**：

<!-- 记录每个测试项的结果 -->

**⚠️ ISSUE - 问题记录**：

<!-- 记录问题 -->

---

## 📋 四、表与扫描功能（TEMPLATE）

### 4.1 表指标与小文件

- [ ] `GET /api/v1/tables/metrics` 返回结构正确
- [ ] `GET /api/v1/tables/small-files` 返回结构正确
- [ ] `GET /api/v1/tables/databases/{cluster_id}` 可用
- [ ] `GET /api/v1/tables/tables/{cluster_id}/{database}` 可用

### 4.2 扫描任务

- [ ] **触发扫描**：
  - [ ] `POST /api/v1/table-scanning/scan` 全量扫描
  - [ ] `POST /api/v1/table-scanning/scan/{cluster}` 集群扫描
  - [ ] `POST /api/v1/table-scanning/scan/{cluster}/{db}` 数据库扫描
  - [ ] `POST /api/v1/table-scanning/scan-table/{cluster}/{db}/{table}` 表扫描

- [ ] **进度查询**：
  - [ ] `GET /api/v1/scan-tasks/scan-progress/{task_id}` 进度更新正常
  - [ ] `GET /api/v1/scan-tasks/scan-logs/{task_id}` 日志可见

**✅ RESULT - 测试结果**：

**⚠️ ISSUE - 问题记录**：

---

## 📋 五、冷数据与表归档（TEMPLATE）

### 5.1 冷数据扫描

- [ ] `POST /api/v1/table-archiving/scan-cold-data/{cluster}` 扫描成功
- [ ] `GET /api/v1/table-archiving/cold-data-summary/{cluster}` 摘要正确

### 5.2 表归档/恢复

- [ ] `POST /api/v1/table-archiving/archive-with-progress/{cluster}/{db}/{table}` 归档成功
- [ ] `POST /api/v1/table-archiving/restore-with-progress/{cluster}/{db}/{table}` 恢复成功
- [ ] 状态、列表与统计接口可用

### 5.3 分区归档

- [ ] 分区扫描接口正常
- [ ] 批量归档接口正常
- [ ] 统计与分布接口返回合理数据

**✅ RESULT - 测试结果**：

**⚠️ ISSUE - 问题记录**：

---

## 📋 六、存储管理（/api/v1）（TEMPLATE）

- [ ] **纠删码策略**：
  - [ ] `POST /api/v1/ec/set-policy/{cluster_id}` 参数校验正确
  - [ ] 任务提交成功
  - [ ] 结果反馈正确

- [ ] **HDFS 搬迁**：
  - [ ] `POST /api/v1/storage/mover/{cluster_id}` 触发成功
  - [ ] 日志可见

- [ ] **副本数设置**：
  - [ ] `POST /api/v1/storage/set-replication/{cluster_id}` 生效
  - [ ] 越界值被校验拒绝

**✅ RESULT - 测试结果**：

**⚠️ ISSUE - 问题记录**：

---

## 📋 七、任务中心（TEMPLATE）

- [ ] **任务列表**：
  - [ ] `GET /api/v1/tasks` 正常返回
  - [ ] `GET /api/v1/tasks/{task_id}` 详情正确
  - [ ] `GET /api/v1/tasks/stats` 统计数据合理

- [ ] **任务操作**：
  - [ ] `POST /api/v1/tasks/{task_id}/execute` 执行成功
  - [ ] `POST /api/v1/tasks/{task_id}/retry` 重试成功
  - [ ] `POST /api/v1/tasks/{task_id}/cancel` 取消成功
  - [ ] 状态流转正确

- [ ] **任务预览**：
  - [ ] `GET /api/v1/tasks/{task_id}/preview` 数据格式正确

**✅ RESULT - 测试结果**：

**⚠️ ISSUE - 问题记录**：

---

## 📋 八、WebSocket 实时推送（TEMPLATE）

- [ ] **连接建立**：
  - [ ] `ws://{host}/api/v1/ws?user_id=u1&topics=task_updates,scan_progress` 成功握手

- [ ] **心跳机制**：
  - [ ] 发送 `{type:"ping", data:{timestamp:...}}` 收到 `pong`

- [ ] **订阅管理**：
  - [ ] `subscribe` 消息返回确认
  - [ ] `unsubscribe` 消息返回确认

- [ ] **状态查询**：
  - [ ] `{type:"get_status"}` 返回连接统计
  - [ ] `GET /api/v1/ws/stats` 统计一致

- [ ] **消息广播**：
  - [ ] `POST /api/v1/ws/broadcast` 推送成功
  - [ ] 客户端收到消息

**✅ RESULT - 测试结果**：

**⚠️ ISSUE - 问题记录**：

---

## 📋 九、前端关键路径（手工回归）（TEMPLATE）

- [ ] **Dashboard（概览页）**：
  - [ ] 概览指标加载正常
  - [ ] 趋势图表显示正常
  - [ ] 近期任务列表可见
  - [ ] 刷新无报错

- [ ] **集群管理页**：
  - [ ] 集群列表显示正常
  - [ ] 创建集群（含校验）功能可用
  - [ ] 健康检查按钮可用
  - [ ] 连接测试操作可见且可用

- [ ] **表管理页**：
  - [ ] 数据库/表切换正常
  - [ ] 筛选小文件功能正常
  - [ ] 批量创建任务按钮行为正确

- [ ] **任务管理页**：
  - [ ] 任务列表刷新正常
  - [ ] 状态变化显示正确
  - [ ] 日志查看功能正常
  - [ ] WebSocket 推送生效

- [ ] **归档相关页**：
  - [ ] 扫描操作可执行
  - [ ] 归档/恢复流程可操作
  - [ ] 进度显示可见

**✅ RESULT - 测试结果**：

<!-- 建议附截图 -->

**⚠️ ISSUE - 问题记录**：

---

## 📋 十、通过标准与记录（TEMPLATE）

### 10.1 代码质量

- [ ] `make check` 通过
- [ ] `make test` 通过
- [ ] 后端测试覆盖率 ≥ 75%

### 10.2 功能验收

- [ ] 关键用例（本清单第二至九部分）100% 通过
- [ ] 失败项已记录：接口、入参、响应、修复建议

### 10.3 文档记录

- [ ] UI 变更已附截图/录屏
- [ ] WebSocket 用例已附事件摘录
- [ ] 问题已记录在对应的 `⚠️ ISSUE` 部分

**✅ RESULT - 最终总结**：

**⚠️ ISSUE - 遗留问题**：

---

## 📖 附录：常用命令参考

### 环境管理

```bash
# 激活 Python 环境（如使用 conda）
conda activate hive-backend

# 启动后端服务
cd backend && uvicorn app.main:app --host localhost --port 8000

# 启动前端服务
cd frontend && npm run dev
```

### API 测试命令

```bash
# 健康检查
curl -s http://localhost:8000/health

# 创建集群（mock 验证）
curl -X POST 'http://localhost:8000/api/v1/clusters/?validate_connection=true' \
  -H 'Content-Type: application/json' \
  -d '{"name":"demo","hive_metastore_url":"sqlite:///test.db","hdfs_namenode_url":"http://nn"}'

# WebSocket 广播测试
curl -X POST 'http://localhost:8000/api/v1/ws/broadcast?topic=task_updates&message_type=info' \
  -H 'Content-Type: application/json' \
  -d '{"data":{"msg":"hello"}}'

# 集群列表
curl -s http://localhost:8000/api/v1/clusters/
```

### 浏览器访问

- API 文档（Swagger UI）: http://localhost:8000/docs
- 前端应用: http://localhost:5173

---

**文档版本历史**：

- v1.1 (2025-10-21): 添加文档分类标记，明确模板与填写内容
- v1.0 (2025-10-21): 初始版本
