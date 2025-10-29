# Hive小文件平台 E2E自动化测试

本目录包含基于Playwright的端到端自动化测试套件，用于验证Hive小文件平台的前端功能。

## 📁 目录结构

```
tests/
├── e2e/                          # E2E测试文件
│   ├── helpers/                  # 工具类
│   │   ├── api-client.ts        # API客户端（数据验证）
│   │   ├── console-monitor.ts   # Console错误监控
│   │   ├── screenshot-helper.ts # 截图管理
│   │   └── doc-updater.ts       # 自动更新功能测试清单
│   ├── pages/                   # Page Object模式页面对象
│   │   ├── base.page.ts         # 基础页面类
│   │   ├── dashboard.page.ts    # 首页仪表盘
│   │   ├── clusters.page.ts     # 集群管理
│   │   ├── tables.page.ts       # 表管理
│   │   ├── table-detail.page.ts # 表详情
│   │   └── tasks.page.ts        # 任务中心
│   ├── 9.1-homepage.spec.ts     # 测试: 首页访问和初始化
│   ├── 9.2-cluster-mgmt.spec.ts # 测试: 集群管理操作
│   ├── 9.3-table-mgmt.spec.ts   # 测试: 表管理和小文件检测
│   ├── 9.4-task-center.spec.ts  # 测试: 任务中心功能
│   └── 9.5-complete-flow.spec.ts # 测试: 完整用户流程
├── reports/                     # 测试报告输出目录
│   ├── html/                    # HTML报告
│   ├── console-logs/            # Console日志
│   └── results.json             # JSON格式测试结果
├── .env.example                 # 环境变量模板
├── .env                         # 环境变量配置（需自行创建）
├── package.json                 # NPM依赖配置
├── playwright.config.ts         # Playwright配置
├── tsconfig.json               # TypeScript配置
└── README.md                   # 本文档
```

## 🚀 快速开始

### 1. 环境准备

#### 系统要求
- Node.js >= 16.x
- npm >= 7.x
- Chrome浏览器（Playwright会自动安装Chromium）

#### 前置条件
- 前端服务运行在 `http://192.168.0.105:3002`
- 后端API服务运行在 `http://192.168.0.105:8000`

### 2. 安装依赖

```bash
cd tests
npm install
```

### 3. 安装浏览器

```bash
npm run install-browsers
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并根据实际环境修改：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下关键参数：

```bash
# 前端访问地址
FRONTEND_URL=http://192.168.0.105:3002

# 后端API地址
BACKEND_API_URL=http://192.168.0.105:8000

# 测试集群ID（需要替换为真实的集群ID）
TEST_CLUSTER_ID=your-test-cluster-id

# 测试表名
TEST_TABLE=test_small_files_table

# 是否启用无头模式
HEADLESS=false

# 是否自动启动前后端服务
AUTO_START_SERVERS=false
```

### 5. 运行测试

#### 运行所有E2E测试
```bash
npm test
```

#### 运行指定测试
```bash
# 运行9.1测试（首页）
npm run test:9.1

# 运行9.2测试（集群管理）
npm run test:9.2

# 运行9.3测试（表管理）
npm run test:9.3

# 运行9.4测试（任务中心）
npm run test:9.4

# 运行9.5测试（完整流程）
npm run test:9.5
```

#### 以UI模式运行（推荐用于调试）
```bash
npm run test:ui
```

#### 有头模式运行（查看浏览器操作）
```bash
npm run test:headed
```

#### 调试模式运行
```bash
npm run test:debug
```

### 6. 查看测试报告

```bash
npm run report
```

这将在浏览器中打开HTML格式的测试报告。

## 📊 测试覆盖范围

### 9.1 前端首页访问和初始化
- ✅ 验证首页正常访问
- ✅ 验证页面布局和视口大小
- ✅ 验证无Console错误
- ✅ 验证导航菜单功能

### 9.2 集群管理操作
- ✅ 验证集群列表显示
- ✅ 验证集群选择功能
- ✅ 验证UI数据与API数据一致性
- ✅ 验证路由守卫功能

### 9.3 表管理和小文件检测
- ✅ 验证表列表显示
- ✅ 验证小文件统计准确性
- ✅ 验证表详情页面正常
- ✅ 验证文件列表数据完整性

### 9.4 任务中心功能
- ✅ 验证任务列表显示
- ✅ 验证任务状态更新
- ✅ 验证任务筛选功能
- ✅ 验证任务数据一致性

### 9.5 完整用户流程
- ✅ 验证从首页到任务完成的完整流程
- ✅ 验证跨页面数据一致性
- ✅ 验证页面导航完整性
- ✅ 验证整个流程无Console错误

## 🔧 核心功能

### 1. Page Object模式
采用Page Object设计模式，提高代码可维护性和可重用性。

### 2. 自动截图
- 每个测试步骤自动截图
- 测试失败时自动保存失败截图
- 截图保存在 `docs/screenshots/` 目录

### 3. Console错误监控
- 自动监控浏览器Console输出
- 检测JavaScript错误和警告
- 生成详细的Console日志报告

### 4. API数据验证
- UI数据与后端API数据对比验证
- 确保前后端数据一致性

### 5. 自动更新功能测试清单
- 测试完成后自动更新 `docs/functional-test-checklist.md`
- 记录测试状态、耗时、错误数等
- 生成测试执行记录

## 📝 编写新测试

### 1. 创建新的测试文件

在 `tests/e2e/` 目录下创建新的 `.spec.ts` 文件：

```typescript
import { test, expect } from '@playwright/test'
import { YourPage } from './pages/your.page'
import { ConsoleMonitor } from './helpers/console-monitor'
import { ScreenshotHelper } from './helpers/screenshot-helper'

let yourPage: YourPage
let consoleMonitor: ConsoleMonitor
let screenshotHelper: ScreenshotHelper

test.describe('Your Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    yourPage = new YourPage(page)
    consoleMonitor = new ConsoleMonitor('your-test')
    screenshotHelper = new ScreenshotHelper('your-test')
    consoleMonitor.startMonitoring(page)
  })

  test('should do something', async ({ page }) => {
    await yourPage.navigate()
    await screenshotHelper.captureFullPage(page, 'test_step')

    // 你的测试逻辑

    expect(true).toBeTruthy()
  })
})
```

### 2. 创建新的Page Object

在 `tests/e2e/pages/` 目录下创建新的页面类：

```typescript
import { Page, Locator } from '@playwright/test'
import { BasePage } from './base.page'

export class YourPage extends BasePage {
  readonly someElement: Locator

  constructor(page: Page) {
    super(page)
    this.someElement = page.locator('.some-selector')
  }

  async navigate() {
    await this.goto('/#/your-route')
    await this.waitForLoading()
  }

  async doSomething() {
    await this.clickElement(this.someElement)
  }
}
```

## 🐛 调试技巧

### 1. 使用UI模式
```bash
npm run test:ui
```
这将打开Playwright的交互式UI，可以逐步执行测试、查看截图、检查元素等。

### 2. 使用有头模式
```bash
npm run test:headed
```
可以看到浏览器实际执行测试的过程。

### 3. 使用调试模式
```bash
npm run test:debug
```
会在测试代码中暂停，可以使用Chrome DevTools调试。

### 4. 查看截图
所有测试截图保存在 `docs/screenshots/` 目录下，按测试名称分类。

### 5. 查看Console日志
Console日志保存在 `tests/reports/console-logs/` 目录下，JSON格式。

## ⚙️ 配置选项

### Playwright配置 (`playwright.config.ts`)

```typescript
{
  testDir: './e2e',              // 测试目录
  fullyParallel: false,          // 顺序执行（避免并发问题）
  workers: 1,                    // 单线程执行
  timeout: 30000,                // 测试超时（30秒）
  expect: { timeout: 10000 },    // 断言超时（10秒）
  use: {
    baseURL: 'http://192.168.0.105:3002',
    headless: false,             // 是否无头模式
    viewport: { width: 1920, height: 1080 },
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  }
}
```

### 环境变量 (`.env`)

参考 `.env.example` 文件，所有可配置项都有详细注释。

## 📦 依赖说明

- `@playwright/test`: Playwright测试框架
- `typescript`: TypeScript支持
- `dotenv`: 环境变量管理
- `axios`: HTTP客户端（API调用）

## 🔗 相关文档

- [Playwright官方文档](https://playwright.dev/)
- [功能测试清单](../docs/functional-test-checklist.md)
- [项目主README](../README.md)

## 📞 问题反馈

如果遇到问题，请：

1. 检查环境变量配置是否正确
2. 确认前后端服务正常运行
3. 查看测试报告和Console日志
4. 查看截图定位问题

## 🎯 最佳实践

1. **保持测试独立**: 每个测试应该独立运行，不依赖其他测试的状态
2. **使用Page Object**: 页面元素定位统一在Page Object中管理
3. **添加适当等待**: 使用 `waitForLoading()` 等待页面加载完成
4. **验证关键数据**: 使用API客户端验证UI数据与后端数据一致性
5. **捕获失败场景**: 测试失败时自动截图和记录错误信息
6. **定期更新文档**: 测试完成后自动更新功能测试清单

## 🚀 CI/CD集成

未来可以集成到CI/CD流程：

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: cd tests && npm install
      - run: npm run install-browsers
      - run: npm test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: tests/reports/
```

## 📄 许可证

MIT
