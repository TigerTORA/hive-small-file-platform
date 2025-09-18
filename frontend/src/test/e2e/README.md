# E2E 测试说明

## 概述

本项目使用 Playwright 进行端到端测试，覆盖完整的用户交互流程。

## 测试文件结构

```
src/test/e2e/
├── dashboard.spec.ts     # 仪表盘页面测试
├── clusters.spec.ts      # 集群管理测试
├── navigation.spec.ts    # 导航和通用功能测试
└── README.md            # 本说明文档
```

## 测试覆盖范围

### 1. 仪表盘测试 (dashboard.spec.ts)

- ✅ 页面基本结构显示
- ✅ 集群统计卡片功能
- ✅ 小文件问题分析卡片
- ✅ 趋势图表显示和交互
- ✅ 集群选择器功能
- ✅ 数据刷新操作
- ✅ 加载状态处理
- ✅ 网络错误处理
- ✅ 响应式设计测试
- ✅ 数据导出功能

### 2. 集群管理测试 (clusters.spec.ts)

- ✅ 集群管理页面显示
- ✅ 添加集群功能
- ✅ 集群连接测试
- ✅ 集群状态显示
- ✅ 搜索和过滤功能
- ✅ 集群管理操作（编辑、删除）
- ✅ 连接参数验证

### 3. 导航测试 (navigation.spec.ts)

- ✅ 主导航菜单
- ✅ 页面间导航
- ✅ 页面标题和面包屑
- ✅ 侧边栏折叠展开
- ✅ 用户信息和操作
- ✅ 404错误处理
- ✅ 网络连接问题处理
- ✅ 长时间加载处理
- ✅ 键盘导航支持
- ✅ 无障碍访问支持

## 运行测试

### 前置条件

1. 确保前端开发服务器运行在 http://127.0.0.1:5173
2. 确保后端API服务器运行在 http://127.0.0.1:8000
3. 安装Playwright浏览器：`npx playwright install`

### 测试命令

```bash
# 运行所有e2e测试
npm run test:e2e

# 运行测试并查看UI界面
npm run test:e2e:ui

# 调试模式运行测试
npm run test:e2e:debug

# 运行特定测试文件
npx playwright test dashboard.spec.ts

# 只在Chrome中运行测试
npx playwright test --project=chromium

# 运行测试并生成报告
npx playwright test --reporter=html
```

## 测试策略

### 1. 健壮性测试

- 使用可选链式选择器，适应不同的UI实现
- 模拟网络故障和慢响应
- 测试各种屏幕尺寸和设备

### 2. 真实用户场景

- 测试完整的用户工作流程
- 验证数据的端到端流转
- 模拟真实的交互模式

### 3. 错误处理

- 测试各种异常情况
- 验证错误消息显示
- 确保应用程序稳定性

## 测试配置

配置文件：`playwright.config.ts`

- 支持 Chrome、Firefox、Safari 测试
- 自动启动前端和后端服务
- 配置截图和视频录制
- 设置重试和并发策略

## 最佳实践

1. **选择器策略**：优先使用 `data-testid`，其次是语义化选择器
2. **等待策略**：使用 `page.waitForLoadState()` 确保页面完全加载
3. **断言方式**：使用 Playwright 的内置断言，支持自动重试
4. **测试隔离**：每个测试独立运行，不依赖其他测试状态

## 持续集成

测试可以集成到CI/CD流程中：

```yaml
# GitHub Actions 示例
- name: Install dependencies
  run: npm ci

- name: Install Playwright
  run: npx playwright install

- name: Run E2E tests
  run: npm run test:e2e
```

## 故障排除

### 常见问题

1. **页面加载超时**：检查服务器是否正常运行
2. **元素找不到**：验证选择器是否正确，检查页面是否完全加载
3. **测试不稳定**：增加等待时间，使用更可靠的选择器

### 调试技巧

1. 使用 `--debug` 模式逐步执行
2. 使用 `page.pause()` 在关键点暂停
3. 检查生成的截图和视频
4. 查看详细的测试报告

## 扩展测试

添加新的测试用例：

1. 在对应的 `.spec.ts` 文件中添加测试
2. 遵循现有的测试模式和命名约定
3. 确保测试具有良好的描述性
4. 验证测试在不同浏览器中的兼容性
