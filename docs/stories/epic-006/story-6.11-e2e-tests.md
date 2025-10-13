# Story 6.11: E2E回归测试完成

**Story ID**: 6.11
**Epic**: Epic-6 (代码重构与质量保证)
**优先级**: P0
**工作量**: 2天
**状态**: 待开始
**责任人**: QA Agent + Dev Agent
**创建日期**: 2025-10-12

---

## 1. 用户故事

**作为** 项目QA
**我想要** 完成核心业务流程的E2E回归测试
**以便** 确保Epic-6重构后所有功能正常,无业务回归问题

---

## 2. 验收标准

### 2.1 测试覆盖 ✅
- [ ] 完成4个E2E测试场景 (扫描/合并/Dashboard/任务管理)
- [ ] 每个场景包含完整的用户操作流程
- [ ] 测试用例覆盖正常流程和异常流程
- [ ] 测试数据准备和清理自动化

### 2.2 测试通过 ✅
- [ ] 所有E2E测试用例通过率 100%
- [ ] 关键路径响应时间 < 3秒
- [ ] WebSocket实时推送延迟 < 500ms
- [ ] 前后端API契约测试通过

### 2.3 Bug修复 ✅
- [ ] 测试发现的Bug全部修复
- [ ] 修复后回归测试通过
- [ ] Bug修复记录到Issue追踪

---

## 3. 测试场景

### 场景1: 集群扫描流程 (4小时)

**用户故事**: 用户添加Hive集群,配置扫描策略,触发扫描任务,验证扫描结果准确性

**测试步骤**:
1. **添加Hive集群连接**
   - 导航到 "集群管理" 页面
   - 点击 "添加集群" 按钮
   - 填写集群信息 (名称、MetaStore URL、HDFS NameNode URL、Hive连接信息)
   - 点击 "测试连接" 按钮
   - 验证连接测试成功提示
   - 保存集群配置

2. **配置扫描策略**
   - 导航到 "表管理" 页面
   - 选择刚添加的集群
   - 点击 "扫描配置" 按钮
   - 配置过滤条件:
     - Database filter: `test_db`
     - Table filter: `test_table_*`
     - 最小文件数阈值: 100
   - 保存配置

3. **触发扫描任务**
   - 点击 "立即扫描" 按钮
   - 验证扫描任务创建成功
   - 观察扫描进度条实时更新 (WebSocket)

4. **验证扫描结果**
   - 等待扫描完成 (最多2分钟)
   - 检查扫描结果表格:
     - 小文件数量准确 (与实际HDFS数据对比)
     - 分区统计正确
     - 表大小计算正确
   - 验证Dashboard数据实时刷新:
     - 饼图更新
     - 排行榜更新

**验收标准**:
- [ ] 扫描成功率 100%
- [ ] 扫描准确率 > 99% (与实际HDFS数据对比)
- [ ] 扫描速度 > 100 tables/min
- [ ] WebSocket推送延迟 < 500ms

**测试工具**: Playwright (frontend), pytest (backend API)

**测试数据准备**:
```bash
# 创建测试表 (10个表,每表100个小文件)
python backend/scripts/create_test_tables.py \
  --cluster test-cluster \
  --database test_db \
  --num-tables 10 \
  --files-per-table 100
```

---

### 场景2: 文件合并流程 (6小时)

**用户故事**: 用户选择扫描结果中的表,创建合并任务,监控任务进度,验证合并结果

**测试步骤**:
1. **选择扫描结果中的表**
   - 导航到 "表管理" 页面
   - 在扫描结果列表中选择一个表 (test_db.test_table_001)
   - 点击 "合并" 按钮

2. **创建合并任务**
   - 在合并任务创建对话框中配置:
     - 目标格式: PARQUET
     - 压缩方式: SNAPPY
     - EC策略: 默认
     - 分区过滤: 留空 (全表合并)
   - 点击 "创建任务" 按钮
   - 验证任务创建成功提示

3. **监控任务进度**
   - 导航到 "任务管理" 页面
   - 在任务列表中找到刚创建的任务
   - 点击 "查看详情" 按钮
   - 观察任务状态实时更新 (WebSocket):
     - PENDING → RUNNING → SUCCESS
   - 观察任务日志实时滚动
   - 验证进度条更新

4. **验证合并结果**
   - 等待任务完成 (最多5分钟)
   - 检查任务执行结果:
     - 合并前文件数 (例如: 100)
     - 合并后文件数 (例如: 1-5)
     - 数据大小不变 (容差 < 1%)
   - 验证数据完整性:
     - 行数一致
     - 数据checksum一致
   - 验证元数据更新:
     - Hive MetaStore中的表格式更新为PARQUET
     - 压缩方式更新为SNAPPY

5. **验证回滚机制** (异常场景)
   - 模拟合并失败 (手动删除临时表)
   - 验证自动回滚:
     - 备份表存在
     - 原表未被修改
     - 任务状态标记为FAILED
     - 错误日志清晰记录

**验收标准**:
- [ ] 合并成功率 > 95%
- [ ] 单分区合并时间 < 30秒
- [ ] 数据完整性校验通过 (行数/checksum)
- [ ] WebSocket推送延迟 < 500ms
- [ ] 回滚机制正常工作 (异常场景)

**测试工具**: Playwright (frontend), pytest (backend API + Celery)

---

### 场景3: Dashboard可视化流程 (2小时)

**用户故事**: 用户在Dashboard切换集群,过滤数据,查看图表联动,导出数据

**测试步骤**:
1. **多集群切换**
   - 导航到 "Dashboard" 页面
   - 在集群下拉列表中选择不同集群
   - 验证数据立即刷新

2. **数据过滤**
   - 使用过滤器:
     - Database过滤: 选择 `test_db`
     - Table过滤: 输入 `test_table_*`
     - 分区过滤: 选择日期范围
   - 验证图表数据更新

3. **图表联动**
   - 点击饼图中的某个扇区 (例如: "小文件 100-500")
   - 验证排行榜自动过滤,只显示该范围的表

4. **数据导出**
   - 点击 "导出" 按钮
   - 选择导出格式 (CSV/Excel)
   - 验证文件下载成功
   - 验证导出数据与页面显示一致

**验收标准**:
- [ ] Dashboard首屏加载 < 3秒 (P95)
- [ ] 数据刷新延迟 < 1秒
- [ ] 图表联动响应 < 500ms
- [ ] 数据导出成功率 100%

**测试工具**: Playwright (frontend)

---

### 场景4: 任务管理流程 (2小时)

**用户故事**: 用户在任务管理页面进行分页、排序、搜索、重试、取消、批量操作

**测试步骤**:
1. **任务列表分页**
   - 导航到 "任务管理" 页面
   - 验证分页控件显示
   - 点击 "下一页" 按钮
   - 验证数据刷新

2. **任务排序**
   - 点击 "创建时间" 列标题
   - 验证任务按创建时间降序排列
   - 再次点击,验证升序排列

3. **任务搜索**
   - 在搜索框输入表名 (例如: `test_table_001`)
   - 验证任务列表过滤,只显示相关任务

4. **任务详情查看**
   - 点击某个任务的 "查看详情" 按钮
   - 验证任务详情对话框显示
   - 验证日志实时滚动 (WebSocket)
   - 点击 "下载日志" 按钮,验证日志文件下载

5. **任务重试**
   - 选择一个FAILED状态的任务
   - 点击 "重试" 按钮
   - 验证任务重新进入PENDING状态
   - 验证任务重新执行

6. **任务取消**
   - 选择一个RUNNING状态的任务
   - 点击 "取消" 按钮
   - 验证任务状态变为CANCELLED
   - 验证Celery任务被revoke

7. **批量操作**
   - 勾选多个任务 (3个)
   - 点击 "批量重试" 按钮
   - 验证所有选中任务重新执行

**验收标准**:
- [ ] 分页/排序/搜索响应 < 1秒
- [ ] 任务详情加载 < 500ms
- [ ] 日志实时滚动延迟 < 500ms
- [ ] 重试/取消操作成功率 100%
- [ ] 批量操作成功率 100%

**测试工具**: Playwright (frontend), pytest (backend API)

---

## 4. 技术实现

### 4.1 测试框架

**Frontend E2E测试**:
```typescript
// frontend/tests/e2e/critical-flows.spec.ts
import { test, expect } from '@playwright/test';

test.describe('场景1: 集群扫描流程', () => {
  test('应该成功添加集群并触发扫描', async ({ page }) => {
    // 1. 添加集群
    await page.goto('http://localhost:3000/clusters');
    await page.click('button:has-text("添加集群")');
    await page.fill('input[name="name"]', 'test-cluster');
    await page.fill('input[name="metastoreUrl"]', 'mysql://test:test@localhost:3306/hive');
    await page.click('button:has-text("测试连接")');
    await expect(page.locator('text=连接成功')).toBeVisible({ timeout: 5000 });
    await page.click('button:has-text("保存")');

    // 2. 触发扫描
    await page.goto('http://localhost:3000/tables');
    await page.selectOption('select[name="cluster"]', 'test-cluster');
    await page.click('button:has-text("立即扫描")');
    await expect(page.locator('text=扫描任务已创建')).toBeVisible();

    // 3. 等待扫描完成
    await page.waitForSelector('text=扫描完成', { timeout: 120000 });

    // 4. 验证结果
    const rowCount = await page.locator('table tbody tr').count();
    expect(rowCount).toBeGreaterThan(0);
  });
});
```

**Backend Integration测试**:
```python
# backend/tests/integration/test_e2e_workflows.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_merge_workflow_end_to_end():
    """测试完整的合并工作流"""
    # 1. 创建合并任务
    response = client.post(
        "/api/tasks/merge",
        json={
            "table_id": 1,
            "target_format": "PARQUET",
            "compression": "SNAPPY",
        }
    )
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    # 2. 等待任务完成
    import time
    max_wait = 300  # 5分钟
    start_time = time.time()
    while time.time() - start_time < max_wait:
        response = client.get(f"/api/tasks/{task_id}")
        task = response.json()
        if task["status"] in ["SUCCESS", "FAILED"]:
            break
        time.sleep(5)

    # 3. 验证结果
    assert task["status"] == "SUCCESS"
    assert task["files_before"] > task["files_after"]
    assert abs(task["size_before"] - task["size_after"]) < task["size_before"] * 0.01  # 容差1%
```

### 4.2 测试数据准备

**自动化测试数据生成**:
```python
# backend/scripts/create_test_tables.py
def create_test_table_with_small_files(
    cluster: str,
    database: str,
    table_name: str,
    num_partitions: int = 10,
    files_per_partition: int = 100,
    file_size_kb: int = 10
):
    """创建包含小文件的测试表"""
    # 1. 创建Hive表
    # 2. 创建分区
    # 3. 生成小文件到HDFS
    # 4. 刷新元数据
    pass
```

### 4.3 CI集成

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup test environment
        run: |
          docker-compose -f docker-compose.test.yml up -d
      - name: Run E2E tests
        run: |
          cd frontend
          npm run test:e2e
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

---

## 5. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| E2E测试发现重大Bug | 高 | 留出2天修复窗口,优先修复P0 Bug |
| 测试环境不稳定 | 中 | 使用Docker Compose隔离环境,自动重试失败用例 |
| 测试数据准备耗时 | 中 | 自动化测试数据生成脚本,并行准备 |
| WebSocket测试不稳定 | 中 | 增加等待超时,使用retry机制 |

---

## 6. Definition of Done

- [x] 所有4个E2E测试场景实现并通过
- [x] 测试通过率 100%
- [x] 关键路径响应时间 < 3秒
- [x] WebSocket延迟 < 500ms
- [x] 测试发现的Bug全部修复或记录
- [x] E2E测试集成到CI/CD
- [x] 生成E2E测试报告 (`docs/qa/testing/e2e-test-report.md`)

---

## 7. 交付物

- `frontend/tests/e2e/critical-flows.spec.ts` (4个场景)
- `backend/tests/integration/test_e2e_workflows.py`
- `backend/scripts/create_test_tables.py` (测试数据生成)
- `docs/qa/testing/e2e-test-report.md` (测试报告)
- `.github/workflows/e2e-tests.yml` (CI集成)

---

## 8. 依赖

**前置依赖**:
- Story 6.10 (QA质量门) 完成

**后续依赖**:
- Story 6.12 (性能基线) 依赖本Story完成

---

## 9. 参考文档

- [Playwright文档](https://playwright.dev/docs/intro)
- [FastAPI TestClient文档](https://fastapi.tiangolo.com/tutorial/testing/)
- [Epic-6 v2.0 PRD](../../epics/epic-006-refactoring-v2.md)

---

**Story Owner**: QA Agent
**协作**: Dev Agent (Bug修复)
**创建日期**: 2025-10-12
**最后更新**: 2025-10-12
