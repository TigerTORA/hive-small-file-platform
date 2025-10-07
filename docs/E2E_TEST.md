# 端到端测试文档

> **用途**: 重大变更后的完整回归测试 | 视频录制前的准备验证
> **集群**: CDP-14 (已配置)
> **预计时间**: 30-40分钟

---

## 🚀 快速开始

### 触发测试的3种方式

#### 方式1: 手动逐步测试 (推荐)
按照下方9个场景依次执行,勾选验证清单

#### 方式2: 快速环境检查
```bash
# 检查后端
curl -s http://localhost:8000/docs > /dev/null && echo "✅ 后端正常" || echo "❌ 后端未启动"

# 检查前端
curl -s http://localhost:3000/ > /dev/null && echo "✅ 前端正常" || echo "❌ 前端未启动"

# 检查CDP-14集群
curl -s http://localhost:8000/api/v1/clusters/ | grep -q "CDP-14" && echo "✅ CDP-14已配置" || echo "❌ CDP-14未找到"
```

#### 方式3: 使用检查清单
跳到文档末尾的"测试检查清单",逐项打勾

---

## 📋 测试场景

### 场景0: 环境检查 (2分钟)

**前置条件**:
```bash
# 1. 启动后端 (如未运行)
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# 2. 启动前端 (如未运行)
cd frontend
npm run dev
```

**验证点**:
- [ ] 后端API文档可访问: http://localhost:8000/docs
- [ ] 前端页面可访问: http://localhost:3000
- [ ] CDP-14集群已配置且启用

---

### 场景1: 生成测试数据 (10分钟)

**目标**: 在CDP-14集群创建包含100个小文件的测试表

**操作步骤**:
1. 访问: http://localhost:3000/test-table-generator
2. 选择"轻量测试"场景:
   - 分区数: 5
   - 每分区文件数: 20
   - 单文件大小: 30KB
3. 配置参数:
   - 集群: **CDP-14**
   - 表名: **video_demo_table**
   - 数据库: **demo_db**
   - HDFS路径: **/user/demo/video_test**
4. 点击"开始生成"
5. 观察WebSocket实时进度
6. 等待完成(约2分钟)

**API测试**:
```bash
# 创建测试表任务
curl -X POST http://localhost:8000/api/v1/test-tables/create-task \
  -H "Content-Type: application/json" \
  -d '{
    "cluster_id": 1,
    "table_name": "video_demo_table",
    "database_name": "demo_db",
    "hdfs_base_path": "/user/demo/video_test",
    "num_partitions": 5,
    "files_per_partition": 20,
    "file_size_kb": 30
  }'
```

**验证点**:
- [ ] 进度条从0%到100%
- [ ] WebSocket日志实时输出
- [ ] 显示"任务成功完成"
- [ ] 生成100个文件(5分区 × 20文件)

---

### 场景2: 表扫描 (5分钟)

**目标**: 扫描CDP-14集群,发现新创建的测试表

**操作步骤**:
1. 访问: http://localhost:3000/tables
2. 点击"扫描"按钮
3. 配置:
   - 集群: **CDP-14**
   - 数据库: **demo_db**
   - 严格实连: **✅ 开启**
4. 点击"开始扫描"
5. 观察进度和日志
6. 等待完成

**API测试**:
```bash
# 触发扫描
curl -X POST http://localhost:8000/api/v1/tables/scan \
  -H "Content-Type: application/json" \
  -d '{
    "cluster_id": 1,
    "database_name": "demo_db",
    "strict_real": true
  }'
```

**验证点**:
- [ ] 进度条正常更新
- [ ] 日志显示"正在扫描 demo_db.video_demo_table"
- [ ] 扫描完成后表列表刷新
- [ ] video_demo_table显示100个小文件

---

### 场景3: 仪表板验证 (3分钟)

**目标**: 验证仪表板统计数据

**操作步骤**:
1. 访问: http://localhost:3000/
2. 选择集群: **CDP-14**
3. 查看数据:
   - 小文件摘要卡片
   - 文件分类饼图
   - 冷数据分布
   - 问题表排行榜

**API测试**:
```bash
# 获取仪表板数据
curl http://localhost:8000/api/v1/dashboard/summary?cluster_id=1
curl http://localhost:8000/api/v1/dashboard/file-classification?cluster_id=1
curl http://localhost:8000/api/v1/dashboard/top-tables?cluster_id=1&limit=10
```

**验证点**:
- [ ] 小文件总数 ≥ 100
- [ ] 饼图包含TEXTFILE格式
- [ ] 问题表排行榜包含video_demo_table
- [ ] 所有图表正常渲染

---

### 场景4: 表详情诊断 (5分钟)

**目标**: 查看video_demo_table详细信息

**操作步骤**:
1. 从仪表板点击 **video_demo_table**
2. 查看表详情页:
   - 表摘要: 100文件, 30KB平均大小
   - 分区表格: 5个分区
   - 优化建议: "建议合并小文件"
   - 文件列表: 展开查看

**API测试**:
```bash
# 获取表详情
curl http://localhost:8000/api/v1/tables/1/demo_db/video_demo_table

# 获取分区指标
curl "http://localhost:8000/api/v1/tables/partition-metrics?cluster_id=1&database_name=demo_db&table_name=video_demo_table"
```

**验证点**:
- [ ] 摘要显示100文件
- [ ] 分区表格显示5行
- [ ] 每个分区20个文件
- [ ] 优化建议包含合并建议

---

### 场景5: 创建治理任务 (5分钟)

**目标**: 为video_demo_table创建合并任务

**操作步骤**:
1. 在表详情页点击"治理"
2. 配置合并任务:
   - 合并策略: **CONCATENATE**
   - 选择分区: **前3个** (20250101, 20250102, 20250103)
   - 预估效果: 60文件 → 3文件
3. 点击"确认创建任务"
4. 自动跳转到任务页面

**API测试**:
```bash
# 创建合并任务
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "cluster_id": 1,
    "database_name": "demo_db",
    "table_name": "video_demo_table",
    "merge_strategy": "CONCATENATE",
    "partition_filter": "dt in (20250101,20250102,20250103)"
  }'
```

**验证点**:
- [ ] 治理对话框正常打开
- [ ] 分区选择器显示5个分区
- [ ] 预估: 60→3 (减少95%)
- [ ] 任务创建成功
- [ ] 跳转到Tasks页面

---

### 场景6: 执行任务监控 (10分钟)

**目标**: 执行合并任务并监控进度

**操作步骤**:
1. 在任务列表找到刚创建的任务
2. 点击"执行"
3. 观察:
   - 状态: 待执行 → 执行中
   - 进度条: 0% → 100%
   - 点击"查看日志"
4. 等待任务完成
5. 查看结果: 60文件 → 3文件

**API测试**:
```bash
# 执行任务
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/execute

# 查询任务状态
curl http://localhost:8000/api/v1/tasks/{task_id}

# 查询任务日志
curl http://localhost:8000/api/v1/tasks/{task_id}/logs
```

**验证点**:
- [ ] 任务状态正确变化
- [ ] 进度条流畅更新
- [ ] 日志实时输出(WebSocket)
- [ ] 任务成功完成
- [ ] 显示60→3文件

---

### 场景7: 验证合并效果 (3分钟)

**目标**: 确认合并结果

**操作步骤**:
1. 返回 video_demo_table 表详情
2. 刷新或重新扫描
3. 查看分区指标:
   - dt=20250101: 1文件 ✅
   - dt=20250102: 1文件 ✅
   - dt=20250103: 1文件 ✅
   - dt=20250104: 20文件
   - dt=20250105: 20文件
4. 总文件数: 100 → 43

**验证点**:
- [ ] 前3个分区文件数=1
- [ ] 后2个分区文件数=20
- [ ] 表总文件数从100→43
- [ ] 减少57%

---

### 场景8: 分区归档 (可选, 8分钟)

**目标**: 演示冷数据归档

**操作步骤**:
1. 访问: http://localhost:3000/partition-archive
2. 选择集群: **CDP-14**
3. 点击"扫描冷数据"
4. 设置阈值: 90天
5. 查看冷分区列表
6. 选择1-2个分区
7. 点击"归档"

**验证点**:
- [ ] 冷数据扫描成功
- [ ] 冷分区列表显示
- [ ] 归档任务创建成功
- [ ] 归档进度实时更新

---

### 场景9: 治理流程可视化 (可选, 2分钟)

**目标**: 展示端到端流程

**操作步骤**:
1. 访问: http://localhost:3000/governance-flow
2. 查看流程图
3. 验证各阶段说明

**验证点**:
- [ ] 流程图正常显示
- [ ] 各阶段说明清晰
- [ ] 与实际流程一致

---

## ✅ 测试检查清单

### 环境准备
- [ ] 后端服务运行 (http://localhost:8000) ✅
- [ ] 前端服务运行 (http://localhost:3000) ✅
- [ ] CDP-14集群已配置并启用 ✅

### 核心场景
- [ ] 场景1: 生成测试表 (100文件) ✅
- [ ] 场景2: 表扫描 (实时进度) ✅
- [ ] 场景3: 仪表板验证 ✅
- [ ] 场景4: 表详情诊断 ✅
- [ ] 场景5: 创建治理任务 ✅
- [ ] 场景6: 执行任务监控 ✅
- [ ] 场景7: 验证合并效果 (60→3) ✅
- [ ] 场景8: 分区归档 (可选) ✅
- [ ] 场景9: 治理流程 (可选) ✅

### 测试结果记录
- 测试日期: __________
- 测试人: __________
- 通过场景: ___ / 9
- 失败场景: __________
- 问题记录: __________

---

## 🧹 测试后清理 (可选)

```bash
# 删除测试表 (在Hive中执行)
DROP TABLE demo_db.video_demo_table;

# 删除HDFS数据
hdfs dfs -rm -r /user/demo/video_test

# 或通过API删除
curl -X DELETE http://localhost:8000/api/v1/test-tables/1/demo_db/video_demo_table
```

---

## 📊 预期测试数据

完成测试后的数据状态:
- ✅ CDP-14集群已配置
- ✅ demo_db.video_demo_table (5分区, 43文件)
- ✅ 完整的仪表板统计数据
- ✅ 1个成功的合并任务
- ✅ 完整的执行日志

**此状态可直接用于视频录制!**

---

*最后更新: 2025-10-07*
