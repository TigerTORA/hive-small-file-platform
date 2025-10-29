import { Page, Locator, expect } from '@playwright/test'

/**
 * 基础页面类
 * 所有Page Object都继承此类
 */
export class BasePage {
  protected page: Page
  protected baseURL: string

  constructor(page: Page) {
    this.page = page
    this.baseURL = process.env.FRONTEND_URL || 'http://localhost:3000'
  }

  /**
   * 导航到指定路径
   */
  async goto(path: string = '/') {
    const url = path.startsWith('http') ? path : `${this.baseURL}${path}`
    await this.page.goto(url, { waitUntil: 'networkidle' })
    await this.waitForPageLoad()
  }

  /**
   * 等待页面加载完成
   */
  async waitForPageLoad() {
    await this.page.waitForLoadState('domcontentloaded')
    await this.page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {
      console.log('⚠️ 网络未完全空闲，继续执行')
    })
  }

  /**
   * 获取页面标题
   */
  async getTitle(): Promise<string> {
    return await this.page.title()
  }

  /**
   * 获取当前URL
   */
  getCurrentURL(): string {
    return this.page.url()
  }

  /**
   * 获取当前路由路径（Hash模式）
   */
  getCurrentRoute(): string {
    const url = this.getCurrentURL()
    const hashIndex = url.indexOf('#')
    return hashIndex >= 0 ? url.substring(hashIndex + 1) : '/'
  }

  /**
   * 等待元素可见
   */
  async waitForElement(locator: Locator, timeout: number = 10000) {
    await locator.waitFor({ state: 'visible', timeout })
  }

  /**
   * 等待元素消失
   */
  async waitForElementHidden(locator: Locator, timeout: number = 10000) {
    await locator.waitFor({ state: 'hidden', timeout })
  }

  /**
   * 点击元素（带重试机制）
   */
  async clickElement(locator: Locator, options?: { timeout?: number; force?: boolean }) {
    const timeout = options?.timeout || 10000
    await locator.waitFor({ state: 'visible', timeout })
    await locator.click({ timeout, force: options?.force })
  }

  /**
   * 填写输入框
   */
  async fillInput(locator: Locator, value: string) {
    await locator.waitFor({ state: 'visible' })
    await locator.clear()
    await locator.fill(value)
  }

  /**
   * 获取文本内容
   */
  async getText(locator: Locator): Promise<string> {
    await locator.waitFor({ state: 'visible' })
    return await locator.textContent() || ''
  }

  /**
   * 检查元素是否可见
   */
  async isVisible(locator: Locator): Promise<boolean> {
    try {
      await locator.waitFor({ state: 'visible', timeout: 3000 })
      return true
    } catch {
      return false
    }
  }

  /**
   * 等待导航完成
   */
  async waitForNavigation(expectedRoute?: string) {
    await this.page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {
      console.log('⚠️ 导航后网络未完全空闲')
    })

    if (expectedRoute) {
      await expect(async () => {
        const currentRoute = this.getCurrentRoute()
        expect(currentRoute).toBe(expectedRoute)
      }).toPass({ timeout: 5000 })
    }
  }

  /**
   * 等待Element-Plus加载动画消失
   */
  async waitForLoading() {
    const loadingMask = this.page.locator('.el-loading-mask')
    if (await loadingMask.isVisible().catch(() => false)) {
      await loadingMask.waitFor({ state: 'hidden', timeout: 30000 })
    }
  }

  /**
   * 等待Element-Plus消息提示出现
   */
  async waitForMessage(type: 'success' | 'error' | 'warning' | 'info' = 'success', timeout: number = 5000) {
    const messageLocator = this.page.locator(`.el-message--${type}`)
    await messageLocator.waitFor({ state: 'visible', timeout })
    return await messageLocator.textContent()
  }

  /**
   * 检查是否有Element-Plus错误消息
   */
  async hasErrorMessage(): Promise<boolean> {
    const errorMessage = this.page.locator('.el-message--error')
    return await errorMessage.isVisible().catch(() => false)
  }

  /**
   * 获取Element-Plus表格数据
   */
  async getTableData(tableSelector: string = '.el-table'): Promise<any[]> {
    const table = this.page.locator(tableSelector)
    await table.waitFor({ state: 'visible' })

    const rows = await table.locator('.el-table__body tr').all()
    const data: any[] = []

    for (const row of rows) {
      const cells = await row.locator('td').allTextContents()
      data.push(cells)
    }

    return data
  }

  /**
   * 获取Element-Plus表格行数
   */
  async getTableRowCount(tableSelector: string = '.el-table'): Promise<number> {
    const table = this.page.locator(tableSelector)
    await table.waitFor({ state: 'visible' })

    const rows = await table.locator('.el-table__body tr').count()
    return rows
  }

  /**
   * 点击Element-Plus对话框确认按钮
   */
  async confirmDialog() {
    const confirmBtn = this.page.locator('.el-message-box__btns .el-button--primary')
    await this.clickElement(confirmBtn)
  }

  /**
   * 点击Element-Plus对话框取消按钮
   */
  async cancelDialog() {
    const cancelBtn = this.page.locator('.el-message-box__btns .el-button--default')
    await this.clickElement(cancelBtn)
  }

  /**
   * 滚动到页面底部
   */
  async scrollToBottom() {
    await this.page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight)
    })
  }

  /**
   * 滚动到页面顶部
   */
  async scrollToTop() {
    await this.page.evaluate(() => {
      window.scrollTo(0, 0)
    })
  }

  /**
   * 等待指定时间
   */
  async wait(milliseconds: number) {
    await this.page.waitForTimeout(milliseconds)
  }

  /**
   * 刷新页面
   */
  async reload() {
    await this.page.reload({ waitUntil: 'networkidle' })
  }

  /**
   * 截图
   */
  async screenshot(options?: { path?: string; fullPage?: boolean }) {
    return await this.page.screenshot({
      fullPage: options?.fullPage ?? true,
      path: options?.path,
    })
  }

  /**
   * 获取页面Console错误
   */
  getConsoleErrors(): string[] {
    // 这个方法需要配合ConsoleMonitor使用
    // 在实际测试中，ConsoleMonitor会在test fixture中初始化
    return []
  }

  /**
   * 验证页面无Console错误（占位方法）
   */
  async assertNoConsoleErrors() {
    // 实际实现在测试文件中通过ConsoleMonitor完成
    console.log('验证Console错误需要通过ConsoleMonitor实现')
  }

  /**
   * 关闭页面
   */
  async close() {
    await this.page.close()
  }
}
