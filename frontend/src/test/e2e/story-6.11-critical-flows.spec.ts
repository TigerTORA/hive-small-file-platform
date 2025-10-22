import { test, expect } from '@playwright/test'

const CLUSTER_NAME = 'CDP-14'

async function selectDemoCluster(page: any) {
  await page.goto('/#/clusters')
  const clusterCard = page.locator('.cluster-card', { hasText: CLUSTER_NAME }).first()
  await expect(clusterCard).toBeVisible()
  await clusterCard.click()
  await page.waitForURL('**/#/**', { timeout: 10_000 })
  // 页面会弹出提示消息, 稍等其完成以免影响后续点击
  await page.waitForTimeout(500)
}

test.describe('Story 6.11 E2E Demo Flows', () => {
  test.beforeEach(async ({ page }) => {
    await selectDemoCluster(page)
  })

  test('扫描流程: 已完成的扫描任务可查看日志', async ({ page }) => {
    await page.goto('/#/tasks')
    await page.waitForLoadState('networkidle')

    const scanRow = page
      .locator('.cloudera-data-table .el-table__row')
      .filter({ hasText: 'E2E Demo Scan' })
      .first()

    await expect(scanRow).toBeVisible()
    await expect(scanRow).toContainText('扫描')
    await expect(scanRow).toContainText('已成功')

    await scanRow.locator('button:has-text("查看日志")').click()

    const dialog = page.locator('.task-run')
    await expect(dialog).toBeVisible()
    await expect(dialog.locator('.logs .log').first()).toContainText('E2E Demo')
    await dialog.locator('button:has-text("关闭")').click()
    await expect(dialog).toBeHidden()
  })

  test('合并流程: 成功与失败任务的状态与日志', async ({ page }) => {
    await page.goto('/#/tasks')
    await page.waitForLoadState('networkidle')

    const successRow = page
      .locator('.cloudera-data-table .el-table__row')
      .filter({ hasText: 'E2E Demo Merge Success' })
      .first()
    await expect(successRow).toBeVisible()
    await expect(successRow).toContainText('合并')
    await expect(successRow).toContainText('已成功')
    await expect(successRow).toContainText('180')
    await expect(successRow).toContainText('6')

    await successRow.locator('button:has-text("查看日志")').click()
    const dialog = page.locator('.task-run')
    await expect(dialog).toBeVisible()
    await expect(dialog.locator('.logs .log').last()).toContainText('任务成功完成')
    await dialog.locator('button:has-text("关闭")').click()

    const failedRow = page
      .locator('.cloudera-data-table .el-table__row')
      .filter({ hasText: 'E2E Demo Merge Failed' })
      .first()
    await expect(failedRow).toBeVisible()
    await expect(failedRow).toContainText('失败')

    await failedRow.locator('button:has-text("查看日志")').click()
    await expect(dialog).toBeVisible()
    await expect(dialog.locator('.logs .log').filter({ hasText: '已触发自动回滚' })).toHaveCount(1)
    await dialog.locator('button:has-text("关闭")').click()
  })

  test('Dashboard 展示集群统计与指标', async ({ page }) => {
    await page.goto('/#/dashboard')
    await page.waitForLoadState('networkidle')

    const statsCard = page.locator('.stats-grid .el-card').first()
    await expect(statsCard).toBeVisible()
    await expect(statsCard.locator('.el-statistic__content')).toContainText(/\d+/)

    const trendChart = page.locator('.trend-chart .chart-container')
    await expect(trendChart).toBeVisible()

    const problemCard = page.locator('.small-file-card')
    await expect(problemCard).toBeVisible()
  })

  test('任务管理筛选 "失败" 状态能够定位失败任务', async ({ page }) => {
    await page.goto('/#/tasks')
    await page.waitForLoadState('networkidle')

    const failedFilter = page
      .locator('.filter-section', { hasText: '状态' })
      .locator('.filter-item', { hasText: '失败' })
      .first()
    await expect(failedFilter).toBeVisible()
    await failedFilter.click()

    const firstRow = page.locator('.cloudera-data-table .el-table__row').first()
    await expect(firstRow).toBeVisible()
    await expect(firstRow).toContainText('失败')
    await expect(firstRow).toContainText('E2E Demo')
  })
})
