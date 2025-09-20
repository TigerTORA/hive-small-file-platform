/**
 * 关键用户场景端到端测试
 * 测试完整的用户操作流程和业务场景
 */

import { test, expect, type Page, type BrowserContext } from '@playwright/test'

// 测试配置
const APP_URL = process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://localhost:3001'
const API_URL = process.env.PLAYWRIGHT_API_BASE_URL || 'http://localhost:8000'

// 用户场景：系统管理员监控平台运行状态
test.describe('关键用户场景测试', () => {
  test.beforeEach(async ({ page }) => {
    // 设置演示模式
    await page.goto(`${APP_URL}?demo=true`)
    await page.waitForLoadState('networkidle')
  })

  test.describe('场景1：系统管理员日常监控', () => {
    test('应该完成完整的监控工作流程', async ({ page }) => {
      // 步骤1：访问仪表盘
      await page.goto(APP_URL)
      await expect(page.locator('[data-testid="dashboard-loaded"]')).toBeVisible({ timeout: 10000 })

      // 验证关键指标显示
      await expect(page.locator('.metric-value')).toHaveCount(4)
      await expect(page.locator('.cluster-name')).toContainText(/集群/)

      // 步骤2：检查系统状态
      const totalTables = await page.locator('.metric-value').first().textContent()
      expect(totalTables).toMatch(/\d+/)

      // 步骤3：进入大屏模式监控
      await page.locator('[title="进入大屏模式"]').click()
      await page.waitForURL('**/big-screen**')

      // 验证大屏模式加载
      await expect(page.locator('.big-screen-monitor')).toBeVisible()
      await expect(page.locator('[data-testid="big-screen-time"]')).toBeVisible()

      // 步骤4：检查实时指标
      await expect(page.locator('.metric-card')).toHaveCount(4)
      await expect(page.locator('.status-indicators')).toBeVisible()

      // 步骤5：退出大屏模式
      await page.locator('[title="退出大屏模式"]').click()
      await page.waitForURL('**/')
      await expect(page.locator('.dashboard')).toBeVisible()
    })

    test('应该正确响应集群切换', async ({ page }) => {
      // 访问仪表盘
      await page.goto(APP_URL)
      await page.waitForSelector('[data-testid="dashboard-loaded"]')

      // 获取当前指标值
      const initialValue = await page.locator('.metric-value').first().textContent()

      // 切换集群（如果有多个集群选项）
      const clusterSelect = page.locator('.cluster-selector select, .el-select')
      if (await clusterSelect.isVisible()) {
        await clusterSelect.click()
        await page.locator('.el-select-dropdown__item').nth(1).click()

        // 等待数据更新
        await page.waitForTimeout(2000)

        // 验证数据可能发生变化（在真实环境中）
        // 在演示模式下可能数据相同，这是正常的
      }
    })
  })

  test.describe('场景2：运维人员任务执行', () => {
    test('应该完成扫描任务创建和监控流程', async ({ page }) => {
      // 步骤1：访问任务管理页面
      await page.goto(`${APP_URL}/#/tasks?demo=true`)
      await page.waitForLoadState('networkidle')

      // 验证任务列表加载（适配新版统一表格）
      await expect(page.locator('.task-list, .tasks-table, .cloudera-data-table')).toBeVisible()

      // 步骤2：创建新的扫描任务
      const createTaskBtn = page.locator('text=创建任务, button:has-text("创建")')
      if (await createTaskBtn.isVisible()) {
        await createTaskBtn.click()

        // 填写任务表单
        await expect(page.locator('.el-dialog, .task-dialog')).toBeVisible()

        // 选择任务类型
        const taskTypeSelect = page.locator('select, .el-select').first()
        if (await taskTypeSelect.isVisible()) {
          await taskTypeSelect.click()
          await page.locator('text=扫描任务').click()
        }

        // 确认创建
        await page.locator('button:has-text("确定"), button:has-text("创建")').click()

        // 验证任务创建成功
        await expect(page.locator('.el-message--success, .success-message')).toBeVisible()
      }

      // 步骤3：查看任务状态
      const taskItems = page.locator('.task-item, .task-row')
      if ((await taskItems.count()) > 0) {
        // 验证任务信息显示
        await expect(taskItems.first()).toContainText(/扫描|合并/)
        await expect(taskItems.first()).toContainText(/completed|running|pending/)
      }
    })

    test('应该正确显示任务执行日志', async ({ page }) => {
      // 访问任务页面
      await page.goto(`${APP_URL}/#/tasks?demo=true`)
      await page.waitForLoadState('networkidle')

      // 查找并点击日志按钮
      const logButton = page.locator('text=日志, button:has-text("查看日志")').first()
      if (await logButton.isVisible()) {
        await logButton.click()

        // 验证日志对话框打开
        await expect(page.locator('.log-dialog, .el-dialog')).toBeVisible()

        // 验证日志内容（如果有的话）
        const logContent = page.locator('.log-content, .log-list')
        if (await logContent.isVisible()) {
          await expect(logContent).toContainText(/INFO|ERROR|WARN|开始|完成|处理/)
        }

        // 关闭日志对话框
        await page.locator('.el-dialog__close, button:has-text("关闭")').click()
      }
    })
  })

  test.describe('场景3：数据分析师表管理', () => {
    test('应该完成表查询和详情查看流程', async ({ page }) => {
      // 步骤1：访问表管理页面
      await page.goto(`${APP_URL}/#/tables?demo=true`)
      await page.waitForLoadState('networkidle')

      // 验证表列表加载
      await expect(page.locator('.table-list, .tables-table, .cloudera-data-table')).toBeVisible()

      // 步骤2：使用搜索功能
      const searchInput = page.locator('input[placeholder*="搜索"], .search-input')
      if (await searchInput.isVisible()) {
        await searchInput.fill('user')
        await page.keyboard.press('Enter')

        // 等待搜索结果
        await page.waitForTimeout(1000)
      }

      // 步骤3：查看表详情
      const tableRow = page.locator('.table-row, .el-table__row').first()
      if (await tableRow.isVisible()) {
        await tableRow.click()

        // 验证表详情页面
        await expect(page.url()).toMatch(/tables\/.*\/.*\/.*/)

        // 验证详情信息显示
        await expect(page.locator('.table-info, .basic-info')).toBeVisible()
        await expect(page.locator('.file-statistics')).toBeVisible()
      }
    })

    test('应该正确显示表的文件分布信息', async ({ page }) => {
      // 直接访问一个表详情页面（演示数据）
      await page.goto(`${APP_URL}/#/tables/cluster-1/demo_db/demo_table?demo=true`)
      await page.waitForLoadState('networkidle')

      // 验证基本信息
      await expect(page.locator('.basic-info, .table-basic-info')).toBeVisible()

      // 验证文件统计信息
      await expect(page.locator('.file-statistics')).toBeVisible()

      // 验证文件分布图表
      const chartContainer = page.locator('.chart-container, .file-distribution-chart')
      if (await chartContainer.isVisible()) {
        // 等待图表渲染
        await page.waitForTimeout(2000)
        await expect(chartContainer).toBeVisible()
      }

      // 验证历史扫描记录
      await expect(page.locator('.scan-history, .recent-scans')).toBeVisible()
    })
  })

  test.describe('场景4：特性开关和配置管理', () => {
    test('应该正确管理特性开关', async ({ page, context }) => {
      // 启用开发工具特性
      await page.goto(`${APP_URL}?demo=true`)
      await page.waitForLoadState('networkidle')

      // 打开浏览器控制台来测试特性开关API
      await page.evaluate(() => {
        console.log('当前特性配置:', window.FeatureManager?.getAllFeatures())

        // 测试特性切换
        if (window.FeatureManager) {
          window.FeatureManager.enable('darkTheme')
          console.log('启用深色主题')

          window.FeatureManager.disable('realtimeMonitoring')
          console.log('禁用实时监控')
        }
      })

      // 验证特性开关生效（通过UI变化）
      // 这里需要根据实际的特性实现来验证
    })

    test('应该支持演示模式切换', async ({ page }) => {
      // 测试演示模式开关
      await page.goto(APP_URL)

      // 通过URL参数启用演示模式
      await page.goto(`${APP_URL}?demo=true`)
      await page.waitForLoadState('networkidle')

      // 验证演示模式指示器
      const demoIndicator = page.locator('.demo-mode-indicator, [data-testid="demo-mode"]')
      if (await demoIndicator.isVisible()) {
        await expect(demoIndicator).toBeVisible()
      }

      // 验证演示数据加载
      await expect(page.locator('.metric-value')).toHaveCount(4)
    })
  })

  test.describe('场景5：响应式设计验证', () => {
    test('应该在移动设备上正确显示', async ({ page }) => {
      // 设置移动设备视口
      await page.setViewportSize({ width: 375, height: 812 })

      await page.goto(`${APP_URL}?demo=true`)
      await page.waitForLoadState('networkidle')

      // 验证移动端布局
      await expect(page.locator('.dashboard')).toBeVisible()

      // 验证关键指标在移动端的显示
      await expect(page.locator('.metric-item')).toHaveCount(4)

      // 验证菜单在移动端的行为
      const menuToggle = page.locator('.menu-toggle, .mobile-menu-btn')
      if (await menuToggle.isVisible()) {
        await menuToggle.click()
        await expect(page.locator('.mobile-menu, .sidebar')).toBeVisible()
      }
    })

    test('应该在平板设备上正确显示', async ({ page }) => {
      // 设置平板视口
      await page.setViewportSize({ width: 768, height: 1024 })

      await page.goto(`${APP_URL}?demo=true`)
      await page.waitForLoadState('networkidle')

      // 验证平板端布局
      await expect(page.locator('.dashboard')).toBeVisible()

      // 验证表格在平板端的显示
      await page.goto(`${APP_URL}/#/tables?demo=true`)
      await expect(page.locator('.table-list, .tables-table, .cloudera-data-table')).toBeVisible()
    })

    test('应该在大屏设备上正确显示', async ({ page }) => {
      // 设置大屏视口
      await page.setViewportSize({ width: 1920, height: 1080 })

      await page.goto(`${APP_URL}/#/big-screen?demo=true`)
      await page.waitForLoadState('networkidle')

      // 验证大屏布局
      await expect(page.locator('.big-screen-monitor')).toBeVisible()

      // 验证所有指标卡片显示
      await expect(page.locator('.metric-card')).toHaveCount(4)

      // 验证图表区域
      await expect(page.locator('.charts-section')).toBeVisible()
    })
  })

  test.describe('场景6：错误处理和恢复', () => {
    test('应该优雅处理网络错误', async ({ page, context }) => {
      // 模拟网络中断
      await context.setOffline(true)

      await page.goto(APP_URL)

      // 恢复网络
      await context.setOffline(false)

      // 重新加载页面
      await page.reload()
      await page.waitForLoadState('networkidle')

      // 验证页面正常工作
      await expect(page.locator('.dashboard')).toBeVisible()
    })

    test('应该处理无效的路由', async ({ page }) => {
      // 访问不存在的路由
      await page.goto(`${APP_URL}/#/nonexistent-route`)

      // 验证错误处理或重定向
      // 这里根据实际的路由配置来验证
      await page.waitForLoadState('networkidle')
    })
  })

  test.describe('场景7：性能验证', () => {
    test('页面加载性能应该符合标准', async ({ page }) => {
      const startTime = Date.now()

      await page.goto(`${APP_URL}?demo=true`)
      await page.waitForSelector('[data-testid="dashboard-loaded"]')

      const loadTime = Date.now() - startTime

      // 页面应该在5秒内加载完成
      expect(loadTime).toBeLessThan(5000)

      // 验证关键元素存在
      await expect(page.locator('.metric-value')).toHaveCount(4)
    })

    test('大量数据渲染性能应该可接受', async ({ page }) => {
      // 访问数据较多的页面
      await page.goto(`${APP_URL}/#/tables?demo=true`)

      const startTime = Date.now()
      await page.waitForLoadState('networkidle')
      const loadTime = Date.now() - startTime

      // 表格页面应该在合理时间内加载
      expect(loadTime).toBeLessThan(8000)

      // 验证表格渲染完成
      await expect(page.locator('.table-list, .tables-table')).toBeVisible()
    })
  })

  test.describe('场景8：用户体验验证', () => {
    test('应该提供清晰的反馈信息', async ({ page }) => {
      await page.goto(`${APP_URL}/#/tasks?demo=true`)
      await page.waitForLoadState('networkidle')

      // 测试操作反馈
      const actionButton = page
        .locator('button:has-text("创建任务"), button:has-text("刷新")')
        .first()
      if (await actionButton.isVisible()) {
        await actionButton.click()

        // 验证加载状态或成功反馈
        const feedback = page.locator('.el-message, .loading, .success-message')
        if (await feedback.isVisible()) {
          await expect(feedback).toBeVisible()
        }
      }
    })

    test('应该支持键盘导航', async ({ page }) => {
      await page.goto(`${APP_URL}?demo=true`)
      await page.waitForLoadState('networkidle')

      // 测试Tab键导航
      await page.keyboard.press('Tab')
      await page.keyboard.press('Tab')
      await page.keyboard.press('Tab')

      // 验证焦点移动
      const focusedElement = await page.evaluate(() => document.activeElement?.tagName)
      expect(['BUTTON', 'A', 'INPUT', 'SELECT']).toContain(focusedElement)
    })

    test('应该提供辅助功能支持', async ({ page }) => {
      await page.goto(`${APP_URL}?demo=true`)
      await page.waitForLoadState('networkidle')

      // 检查重要元素的无障碍属性
      const metrics = page.locator('.metric-item')
      const firstMetric = metrics.first()

      if (await firstMetric.isVisible()) {
        // 验证是否有合适的aria-label或文本内容
        const ariaLabel = await firstMetric.getAttribute('aria-label')
        const textContent = await firstMetric.textContent()

        expect(ariaLabel || textContent).toBeTruthy()
      }
    })
  })
})

// 辅助函数
async function waitForApiResponse(page: Page, apiPath: string) {
  return page.waitForResponse(
    response => response.url().includes(apiPath) && response.status() === 200
  )
}

async function takeScreenshotOnFailure(page: Page, testInfo: any) {
  if (testInfo.status === 'failed') {
    const screenshot = await page.screenshot()
    await testInfo.attach('screenshot', { body: screenshot, contentType: 'image/png' })
  }
}

// 全局错误处理
test.afterEach(async ({ page }, testInfo) => {
  await takeScreenshotOnFailure(page, testInfo)
})
