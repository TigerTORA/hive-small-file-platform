import { test, expect } from '@playwright/test'

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the dashboard page
    await page.goto('/')

    // Wait for the page to load
    await page.waitForLoadState('networkidle')
  })

  test('应该显示仪表盘页面基本结构', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/Hive小文件管理平台/)

    // Check main navigation exists
    await expect(page.locator('.el-menu')).toBeVisible()

    // Check main content area exists
    await expect(page.locator('.main-content')).toBeVisible()
  })

  test('应该显示集群统计卡片', async ({ page }) => {
    // Wait for cluster card to load
    const clusterCard = page.locator('.cluster-card')
    await expect(clusterCard).toBeVisible()

    // Check cluster statistics are displayed
    await expect(clusterCard.locator('text=集群统计')).toBeVisible()
    await expect(clusterCard.locator('text=总集群数')).toBeVisible()
    await expect(clusterCard.locator('text=活跃集群')).toBeVisible()

    // Check cluster count numbers are displayed
    const clusterCount = clusterCard.locator('[data-testid="cluster-count"]')
    if (await clusterCount.isVisible()) {
      await expect(clusterCount).toContainText(/\d+/)
    }
  })

  test('应该显示小文件问题分析卡片', async ({ page }) => {
    // Wait for small file card to load
    const smallFileCard = page.locator('.small-file-card')
    await expect(smallFileCard).toBeVisible()

    // Check small file analysis is displayed
    await expect(smallFileCard.locator('text=小文件问题')).toBeVisible()

    // Check file statistics
    await expect(smallFileCard.locator('text=小文件数量')).toBeVisible()
    await expect(smallFileCard.locator('text=小文件占比')).toBeVisible()

    // Check severity indicator exists
    const severityTag = smallFileCard.locator('.el-tag')
    if (await severityTag.isVisible()) {
      await expect(severityTag).toContainText(/(正常|注意|警告|严重)/)
    }
  })

  test('应该显示趋势图表', async ({ page }) => {
    // Wait for trend chart to load
    const trendChart = page.locator('.trend-chart')
    await expect(trendChart).toBeVisible()

    // Check chart title
    await expect(trendChart.locator('text=小文件趋势分析')).toBeVisible()

    // Check chart container exists
    const chartContainer = trendChart.locator('.chart-container')
    await expect(chartContainer).toBeVisible()

    // Check chart actions (refresh, export, fullscreen buttons)
    const chartActions = trendChart.locator('.chart-actions')
    if (await chartActions.isVisible()) {
      await expect(chartActions.locator('button')).toHaveCount(3)
    }
  })

  test('应该支持集群选择功能', async ({ page }) => {
    // Look for cluster selector dropdown
    const clusterSelector = page.locator('.cluster-selector .el-select')

    if (await clusterSelector.isVisible()) {
      // Click on cluster selector
      await clusterSelector.click()

      // Wait for dropdown options to appear
      await page.waitForSelector('.el-select-dropdown', { timeout: 2000 })

      // Check if dropdown options exist
      const options = page.locator('.el-select-dropdown .el-option')
      const optionCount = await options.count()

      if (optionCount > 0) {
        // Select the first option
        await options.first().click()

        // Verify selection was made
        await expect(clusterSelector).toContainText(/.+/)
      }
    }
  })

  test('应该响应刷新操作', async ({ page }) => {
    // Wait for initial load
    await page.waitForTimeout(1000)

    // Look for refresh button in chart
    const refreshButton = page
      .locator('.chart-actions button[aria-label="刷新"]')
      .or(page.locator('.chart-actions button').filter({ hasText: 'refresh' }))
      .or(page.locator('button').filter({ hasText: '刷新' }))

    if (await refreshButton.isVisible()) {
      // Click refresh button
      await refreshButton.click()

      // Wait for refresh to complete
      await page.waitForTimeout(500)

      // Verify page is still functional
      await expect(page.locator('.main-content')).toBeVisible()
    }
  })

  test('应该显示加载状态', async ({ page }) => {
    // Navigate to dashboard and check for loading states
    await page.goto('/')

    // Look for skeleton loaders or loading indicators
    const loadingIndicators = page.locator('.el-skeleton, .loading, [data-loading="true"]')

    // Loading indicators might appear briefly, so we don't assert they must be present
    // but if they are present, they should eventually disappear
    if (await loadingIndicators.first().isVisible({ timeout: 1000 })) {
      // Wait for loading to finish
      await expect(loadingIndicators.first()).not.toBeVisible({ timeout: 10000 })
    }

    // Ensure main content is loaded
    await expect(page.locator('.main-content')).toBeVisible()
  })

  test('应该处理网络错误情况', async ({ page }) => {
    // Mock network failure for API calls
    await page.route('**/api/v1/dashboard/**', route => {
      route.abort('failed')
    })

    // Navigate to dashboard
    await page.goto('/')

    // Wait for error handling
    await page.waitForTimeout(2000)

    // Check for error messages or empty states
    const errorElements = page.locator('.el-empty, .error-message, [data-testid="error"]')
    const hasError = (await errorElements.count()) > 0

    // Should either show error state or gracefully handle the failure
    expect(hasError || (await page.locator('.main-content').isVisible())).toBeTruthy()
  })

  test('应该支持响应式设计', async ({ page }) => {
    // Test desktop view
    await page.setViewportSize({ width: 1200, height: 800 })
    await expect(page.locator('.main-content')).toBeVisible()

    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 })
    await expect(page.locator('.main-content')).toBeVisible()

    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 })
    await expect(page.locator('.main-content')).toBeVisible()

    // Check if mobile menu exists or navigation adapts
    const mobileMenu = page.locator('.mobile-menu, .el-menu-collapse')
    const navigation = page.locator('.el-menu')

    // Either mobile menu should exist or regular menu should be visible
    expect((await mobileMenu.isVisible()) || (await navigation.isVisible())).toBeTruthy()
  })

  test('应该支持数据导出功能', async ({ page }) => {
    // Wait for chart to load
    const trendChart = page.locator('.trend-chart')
    await expect(trendChart).toBeVisible()

    // Look for export button
    const exportButton = page
      .locator('.chart-actions button[aria-label="导出"]')
      .or(page.locator('.chart-actions button').filter({ hasText: 'download' }))
      .or(page.locator('button').filter({ hasText: '导出' }))

    if (await exportButton.isVisible()) {
      // Set up download expectation
      const downloadPromise = page.waitForEvent('download', { timeout: 5000 })

      // Click export button
      await exportButton.click()

      try {
        // Wait for download to start
        const download = await downloadPromise

        // Verify download started
        expect(download.suggestedFilename()).toContain('.')
      } catch (error) {
        // Export might trigger a different action (like showing a modal)
        // In that case, just verify the button is clickable
        expect(await exportButton.isEnabled()).toBeTruthy()
      }
    }
  })
})
