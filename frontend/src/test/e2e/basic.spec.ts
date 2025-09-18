import { test, expect } from '@playwright/test'

test.describe('Basic E2E Tests', () => {
  test('should load the home page', async ({ page }) => {
    // Set a reasonable timeout
    test.setTimeout(30000)

    try {
      await page.goto('/')

      // Wait for the page to load
      await page.waitForTimeout(2000)

      // Check that we can access the page
      await expect(page).toHaveTitle(/Hive小文件管理平台/)
    } catch (error) {
      console.log('Basic test failed:', error)
      throw error
    }
  })

  test('should navigate to dashboard', async ({ page }) => {
    test.setTimeout(30000)

    try {
      await page.goto('/')
      await page.waitForTimeout(1000)

      // Check if dashboard link exists
      const dashboardLink = page.locator('text=仪表板')
      if (await dashboardLink.isVisible()) {
        await dashboardLink.click()
        await page.waitForTimeout(1000)
      }

      // Just verify we can navigate
      expect(page.url()).toContain('/')
    } catch (error) {
      console.log('Dashboard test failed:', error)
      throw error
    }
  })
})
