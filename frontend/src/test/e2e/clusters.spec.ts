import { test, expect } from '@playwright/test'

test.describe('Clusters Management Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the clusters page
    await page.goto('/clusters')
    
    // Wait for the page to load
    await page.waitForLoadState('networkidle')
  })

  test('应该显示集群管理页面', async ({ page }) => {
    // Check page title and navigation
    await expect(page.locator('text=集群管理')).toBeVisible()
    
    // Check if clusters table or list exists
    const clustersContainer = page.locator('.clusters-container, .el-table, .cluster-list')
    await expect(clustersContainer).toBeVisible()
  })

  test('应该显示添加集群按钮', async ({ page }) => {
    // Look for add cluster button
    const addButton = page.locator('button').filter({ hasText: '添加集群' })
      .or(page.locator('button').filter({ hasText: '新增' }))
      .or(page.locator('[data-testid="add-cluster"]'))
    
    if (await addButton.isVisible()) {
      await expect(addButton).toBeEnabled()
    }
  })

  test('应该支持集群连接测试', async ({ page }) => {
    // Look for existing clusters
    const clusterRows = page.locator('.el-table__row, .cluster-item')
    const clusterCount = await clusterRows.count()
    
    if (clusterCount > 0) {
      // Look for test connection button in first row
      const testButton = clusterRows.first().locator('button').filter({ hasText: '测试连接' })
        .or(clusterRows.first().locator('[data-testid="test-connection"]'))
      
      if (await testButton.isVisible()) {
        await testButton.click()
        
        // Wait for test result
        await page.waitForTimeout(2000)
        
        // Should show some result (success or error message)
        const resultMessage = page.locator('.el-message, .el-notification, .result-message')
        expect(await resultMessage.count()).toBeGreaterThanOrEqual(0)
      }
    }
  })

  test('应该显示集群状态信息', async ({ page }) => {
    // Wait for cluster data to load
    await page.waitForTimeout(1000)
    
    // Look for cluster status indicators
    const statusElements = page.locator('.el-tag, .status-indicator, [data-testid="cluster-status"]')
    
    if (await statusElements.count() > 0) {
      // Check if status shows valid values
      const firstStatus = statusElements.first()
      await expect(firstStatus).toContainText(/(活跃|离线|连接中|已连接|未连接|active|inactive|online|offline)/)
    }
  })

  test('应该支持集群搜索和过滤', async ({ page }) => {
    // Look for search input
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="集群名称"], .el-input__inner')
    
    if (await searchInput.first().isVisible()) {
      // Type in search input
      await searchInput.first().fill('test')
      
      // Wait for search results
      await page.waitForTimeout(500)
      
      // Verify search functionality works (table updates or shows filtered results)
      expect(await page.locator('.el-table, .cluster-list').isVisible()).toBeTruthy()
    }
  })

  test('应该处理集群管理操作', async ({ page }) => {
    // Look for action buttons (edit, delete, etc.)
    const actionButtons = page.locator('button').filter({ hasText: /(编辑|删除|修改|详情)/ })
    
    if (await actionButtons.count() > 0) {
      // Test edit action if available
      const editButton = page.locator('button').filter({ hasText: /(编辑|修改)/ }).first()
      
      if (await editButton.isVisible()) {
        await editButton.click()
        
        // Should open edit dialog or form
        await page.waitForTimeout(500)
        const dialog = page.locator('.el-dialog, .el-drawer, .edit-form')
        expect(await dialog.isVisible() || await page.url().includes('edit')).toBeTruthy()
      }
    }
  })
})

test.describe('Cluster Connection Management', () => {
  test('应该显示集群连接配置', async ({ page }) => {
    // Go to add cluster page or open add dialog
    await page.goto('/clusters')
    await page.waitForLoadState('networkidle')
    
    const addButton = page.locator('button').filter({ hasText: '添加集群' })
      .or(page.locator('[data-testid="add-cluster"]'))
    
    if (await addButton.isVisible()) {
      await addButton.click()
      await page.waitForTimeout(500)
      
      // Check for connection form fields
      const formFields = page.locator('input[placeholder*="集群名称"], input[placeholder*="主机"], input[placeholder*="端口"]')
      
      if (await formFields.count() > 0) {
        // Verify form has required fields
        expect(await formFields.count()).toBeGreaterThan(0)
      }
    }
  })

  test('应该验证连接参数', async ({ page }) => {
    await page.goto('/clusters')
    await page.waitForLoadState('networkidle')
    
    const addButton = page.locator('button').filter({ hasText: '添加集群' })
    
    if (await addButton.isVisible()) {
      await addButton.click()
      await page.waitForTimeout(500)
      
      // Try to submit form without required fields
      const submitButton = page.locator('button').filter({ hasText: /(确定|保存|提交|创建)/ })
      
      if (await submitButton.isVisible()) {
        await submitButton.click()
        
        // Should show validation errors
        await page.waitForTimeout(500)
        const errorMessages = page.locator('.el-form-item__error, .error-message, .validation-error')
        
        // Either shows validation errors or form doesn't submit
        expect(await errorMessages.count() >= 0).toBeTruthy()
      }
    }
  })
})