import { test, expect } from '@playwright/test'

// Helper to ensure route guard passes (selected cluster in localStorage)
async function seedSelectedCluster(page) {
  await page.addInitScript(() => {
    try {
      localStorage.setItem('selectedCluster', '1')
    } catch {}
  })
}

test.describe('Tables UI', () => {
  test('renders header, toolbar and tabs', async ({ page }) => {
    await seedSelectedCluster(page)
    await page.goto('/#/tables')

    // Header title
    await expect(page.getByText('表管理')).toBeVisible({ timeout: 10000 })

    // Toolbar essentials
    await expect(page.getByPlaceholder('搜索表名...')).toBeVisible()
    await expect(page.getByRole('button', { name: '扫描' })).toBeVisible()
    await expect(page.getByRole('button', { name: '刷新' })).toBeVisible()

    // Tabs visible
    await expect(page.getByRole('tab', { name: '小文件/合并' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '归档' })).toBeVisible()

    // Screenshot main area (for quick visual check)
    await page.waitForTimeout(300) // give a moment for layout
    await expect(page).toHaveScreenshot('tables-toolbar.png', { fullPage: false, maxDiffPixels: 200 })
  })
})

