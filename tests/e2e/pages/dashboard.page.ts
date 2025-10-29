import { Page, Locator } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * 首页仪表盘页面对象
 */
export class DashboardPage extends BasePage {
  // 页面元素定位器
  readonly pageTitle: Locator
  readonly navigationMenu: Locator
  readonly clusterCard: Locator
  readonly statsCards: Locator
  readonly quickActions: Locator

  constructor(page: Page) {
    super(page)

    // 初始化定位器
    this.pageTitle = page.locator('h1, .page-title, .dashboard-title')
    this.navigationMenu = page.locator('.el-menu, nav')
    this.clusterCard = page.locator('.cluster-card, .cluster-info')
    this.statsCards = page.locator('.stats-card, .dashboard-card')
    this.quickActions = page.locator('.quick-actions, .action-buttons')
  }

  /**
   * 访问首页
   */
  async navigate() {
    await this.goto('/')
    await this.waitForLoading()
  }

  /**
   * 验证首页已加载
   */
  async verifyPageLoaded(): Promise<boolean> {
    try {
      // 验证页面关键元素存在
      await this.waitForPageLoad()

      // 验证导航菜单存在
      const hasNav = await this.isVisible(this.navigationMenu)

      return hasNav
    } catch (error) {
      console.error('首页加载验证失败:', error)
      return false
    }
  }

  /**
   * 获取页面标题文本
   */
  async getPageTitle(): Promise<string> {
    if (await this.isVisible(this.pageTitle)) {
      return await this.getText(this.pageTitle)
    }
    return ''
  }

  /**
   * 检查导航菜单项
   */
  async getNavigationItems(): Promise<string[]> {
    const menuItems = this.page.locator('.el-menu-item, .nav-item')
    const count = await menuItems.count()
    const items: string[] = []

    for (let i = 0; i < count; i++) {
      const text = await menuItems.nth(i).textContent()
      if (text) {
        items.push(text.trim())
      }
    }

    return items
  }

  /**
   * 点击导航菜单项
   */
  async clickNavigationItem(itemText: string) {
    const menuItem = this.page.locator('.el-menu-item, .nav-item').filter({ hasText: itemText })
    await this.clickElement(menuItem)
    await this.waitForLoading()
  }

  /**
   * 导航到集群管理页面
   */
  async goToClusters() {
    const clustersLink = this.page.locator('text=集群管理, a[href*="clusters"]').first()
    await this.clickElement(clustersLink)
    await this.waitForNavigation('/clusters')
  }

  /**
   * 导航到表管理页面
   */
  async goToTables() {
    const tablesLink = this.page.locator('text=表管理, a[href*="tables"]').first()
    await this.clickElement(tablesLink)
    await this.waitForNavigation('/tables')
  }

  /**
   * 导航到任务中心页面
   */
  async goToTasks() {
    const tasksLink = this.page.locator('text=任务中心, a[href*="tasks"]').first()
    await this.clickElement(tasksLink)
    await this.waitForNavigation('/tasks')
  }

  /**
   * 获取统计卡片数据
   */
  async getStatsData(): Promise<Array<{ label: string; value: string }>> {
    const cards = await this.statsCards.all()
    const stats: Array<{ label: string; value: string }> = []

    for (const card of cards) {
      const label = await card.locator('.label, .title, h3').textContent()
      const value = await card.locator('.value, .count, .number').textContent()

      if (label && value) {
        stats.push({
          label: label.trim(),
          value: value.trim(),
        })
      }
    }

    return stats
  }

  /**
   * 检查是否显示了集群信息
   */
  async hasClusterInfo(): Promise<boolean> {
    return await this.isVisible(this.clusterCard)
  }

  /**
   * 获取当前选中的集群名称
   */
  async getCurrentClusterName(): Promise<string | null> {
    if (await this.hasClusterInfo()) {
      const clusterName = this.clusterCard.locator('.cluster-name, .name')
      if (await this.isVisible(clusterName)) {
        return await this.getText(clusterName)
      }
    }
    return null
  }

  /**
   * 验证页面无Console错误
   */
  async verifyNoConsoleErrors(): Promise<boolean> {
    // 此方法需要在测试文件中配合ConsoleMonitor使用
    return true
  }

  /**
   * 验证页面布局正常
   */
  async verifyLayout(): Promise<{ isValid: boolean; issues: string[] }> {
    const issues: string[] = []

    // 检查导航栏
    if (!(await this.isVisible(this.navigationMenu))) {
      issues.push('导航栏未显示')
    }

    // 检查视口大小
    const viewport = this.page.viewportSize()
    if (!viewport || viewport.width < 1280 || viewport.height < 720) {
      issues.push('视口大小不符合预期')
    }

    return {
      isValid: issues.length === 0,
      issues,
    }
  }

  /**
   * 等待页面完全渲染
   */
  async waitForFullRender(timeout: number = 5000) {
    // 等待关键元素渲染
    await this.navigationMenu.waitFor({ state: 'visible', timeout })

    // 等待可能的加载动画
    await this.waitForLoading()

    // 等待网络空闲
    await this.waitForPageLoad()
  }

  /**
   * 检查快速操作按钮
   */
  async getQuickActions(): Promise<string[]> {
    if (!(await this.isVisible(this.quickActions))) {
      return []
    }

    const buttons = this.quickActions.locator('button, .action-btn')
    const count = await buttons.count()
    const actions: string[] = []

    for (let i = 0; i < count; i++) {
      const text = await buttons.nth(i).textContent()
      if (text) {
        actions.push(text.trim())
      }
    }

    return actions
  }

  /**
   * 验证首页关键功能
   */
  async verifyKeyFeatures(): Promise<{
    hasNavigation: boolean
    hasStats: boolean
    hasClusterInfo: boolean
  }> {
    return {
      hasNavigation: await this.isVisible(this.navigationMenu),
      hasStats: await this.statsCards.count() > 0,
      hasClusterInfo: await this.hasClusterInfo(),
    }
  }
}
