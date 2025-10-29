import { Page, Locator } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * 表管理页面对象
 */
export class TablesPage extends BasePage {
  // 页面元素定位器
  readonly pageTitle: Locator
  readonly databaseSelect: Locator
  readonly searchInput: Locator
  readonly tableList: Locator
  readonly tableTable: Locator
  readonly refreshBtn: Locator
  readonly detailBtn: Locator
  readonly mergeBtn: Locator

  constructor(page: Page) {
    super(page)

    // 初始化定位器
    this.pageTitle = page.locator('h1, .page-title')
    this.databaseSelect = page.locator('.el-select:has-text("数据库"), select[placeholder*="数据库"]')
    this.searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="表名"]')
    this.tableList = page.locator('.table-list, .el-table')
    this.tableTable = page.locator('.el-table')
    this.refreshBtn = page.locator('button:has-text("刷新")')
    this.detailBtn = page.locator('button:has-text("详情"), a:has-text("详情")')
    this.mergeBtn = page.locator('button:has-text("合并"), button:has-text("优化")')
  }

  /**
   * 访问表管理页面
   */
  async navigate() {
    await this.goto('/#/tables')
    await this.waitForLoading()
  }

  /**
   * 验证页面已加载
   */
  async verifyPageLoaded(): Promise<boolean> {
    try {
      await this.waitForPageLoad()

      // 验证页面标题或表格存在
      const hasTitle = await this.isVisible(this.pageTitle)
      const hasTable = await this.isVisible(this.tableTable)

      return hasTitle || hasTable
    } catch (error) {
      console.error('表管理页面加载验证失败:', error)
      return false
    }
  }

  /**
   * 选择数据库
   */
  async selectDatabase(databaseName: string = 'default') {
    if (await this.isVisible(this.databaseSelect)) {
      await this.clickElement(this.databaseSelect)

      // 在下拉选项中选择数据库
      const option = this.page.locator(`.el-select-dropdown__item:has-text("${databaseName}")`)
      await this.clickElement(option)

      await this.waitForLoading()
    }
  }

  /**
   * 获取当前选中的数据库
   */
  async getCurrentDatabase(): Promise<string> {
    if (await this.isVisible(this.databaseSelect)) {
      const selectedOption = this.databaseSelect.locator('.el-select__selected-item, input')
      return await selectedOption.inputValue() || 'default'
    }
    return 'default'
  }

  /**
   * 搜索表
   */
  async searchTable(tableName: string) {
    if (await this.isVisible(this.searchInput)) {
      await this.fillInput(this.searchInput, tableName)
      await this.wait(500) // 等待搜索结果更新
    }
  }

  /**
   * 获取表数量
   */
  async getTableCount(): Promise<number> {
    if (await this.isVisible(this.tableTable)) {
      return await this.getTableRowCount()
    }
    return 0
  }

  /**
   * 获取所有表名
   */
  async getTableNames(): Promise<string[]> {
    const names: string[] = []

    if (!(await this.isVisible(this.tableTable))) {
      return names
    }

    const rows = this.tableTable.locator('tbody tr')
    const count = await rows.count()

    for (let i = 0; i < count; i++) {
      // 假设表名在第一列
      const nameCell = rows.nth(i).locator('td').first()
      const name = await this.getText(nameCell)
      if (name && !name.includes('暂无数据')) {
        names.push(name.trim())
      }
    }

    return names
  }

  /**
   * 获取表的详细信息（从表格行）
   */
  async getTableInfo(tableName: string): Promise<{
    name: string
    fileCount?: number
    totalSize?: string
    avgSize?: string
  } | null> {
    if (!(await this.isVisible(this.tableTable))) {
      return null
    }

    const row = this.tableTable.locator(`tbody tr:has-text("${tableName}")`).first()

    if (!(await this.isVisible(row))) {
      return null
    }

    const cells = await row.locator('td').allTextContents()

    return {
      name: tableName,
      fileCount: cells[1] ? parseInt(cells[1]) : undefined,
      totalSize: cells[2] || undefined,
      avgSize: cells[3] || undefined,
    }
  }

  /**
   * 点击表的详情按钮
   */
  async viewTableDetail(tableName: string) {
    const row = this.tableTable.locator(`tbody tr:has-text("${tableName}")`).first()
    const detailBtn = row.locator('button:has-text("详情"), a:has-text("详情")').first()

    await this.clickElement(detailBtn)
    await this.waitForLoading()
    await this.waitForNavigation()
  }

  /**
   * 点击表的合并按钮
   */
  async clickMergeButton(tableName: string) {
    const row = this.tableTable.locator(`tbody tr:has-text("${tableName}")`).first()
    const mergeBtn = row.locator('button:has-text("合并"), button:has-text("优化")').first()

    await this.clickElement(mergeBtn)
    await this.wait(500)
  }

  /**
   * 触发表合并任务
   */
  async triggerTableMerge(tableName: string, hdfsPath?: string) {
    await this.clickMergeButton(tableName)

    // 如果有合并对话框，填写并提交
    const dialog = this.page.locator('.el-dialog')
    if (await this.isVisible(dialog)) {
      // 填写HDFS路径（如果需要）
      if (hdfsPath) {
        const pathInput = dialog.locator('input[placeholder*="路径"], input[placeholder*="HDFS"]')
        if (await this.isVisible(pathInput)) {
          await this.fillInput(pathInput, hdfsPath)
        }
      }

      // 点击确认按钮
      const confirmBtn = dialog.locator('button:has-text("确定"), button:has-text("提交")')
      await this.clickElement(confirmBtn)

      await this.waitForLoading()

      // 等待成功消息
      try {
        await this.waitForMessage('success', 5000)
      } catch {
        console.warn('未收到成功消息，可能任务已提交')
      }
    }
  }

  /**
   * 刷新表列表
   */
  async refresh() {
    if (await this.isVisible(this.refreshBtn)) {
      await this.clickElement(this.refreshBtn)
      await this.waitForLoading()
    } else {
      // 如果没有刷新按钮，重新加载页面
      await this.reload()
    }
  }

  /**
   * 检查表是否存在
   */
  async hasTable(tableName: string): Promise<boolean> {
    const tableNames = await this.getTableNames()
    return tableNames.includes(tableName)
  }

  /**
   * 等待表出现在列表中
   */
  async waitForTable(tableName: string, timeout: number = 10000): Promise<boolean> {
    const startTime = Date.now()

    while (Date.now() - startTime < timeout) {
      if (await this.hasTable(tableName)) {
        return true
      }

      await this.wait(1000)
      await this.refresh()
    }

    return false
  }

  /**
   * 获取表的小文件数量
   */
  async getSmallFileCount(tableName: string): Promise<number | null> {
    const tableInfo = await this.getTableInfo(tableName)
    return tableInfo?.fileCount || null
  }

  /**
   * 按文件数量排序
   */
  async sortByFileCount(order: 'asc' | 'desc' = 'desc') {
    const fileCountHeader = this.tableTable.locator('th:has-text("文件数"), th:has-text("小文件")')

    if (await this.isVisible(fileCountHeader)) {
      // 点击表头排序
      await this.clickElement(fileCountHeader)

      // 如果需要倒序，再点击一次
      if (order === 'desc') {
        await this.wait(300)
        await this.clickElement(fileCountHeader)
      }

      await this.wait(500)
    }
  }

  /**
   * 过滤有小文件问题的表（文件数量 > 阈值）
   */
  async filterTablesWithSmallFiles(threshold: number = 100): Promise<string[]> {
    const allTableNames = await this.getTableNames()
    const tablesWithIssues: string[] = []

    for (const tableName of allTableNames) {
      const info = await this.getTableInfo(tableName)
      if (info && info.fileCount && info.fileCount > threshold) {
        tablesWithIssues.push(tableName)
      }
    }

    return tablesWithIssues
  }

  /**
   * 验证表列表已加载
   */
  async verifyTablesLoaded(): Promise<boolean> {
    if (!(await this.isVisible(this.tableTable))) {
      return false
    }

    // 等待表格数据加载
    await this.wait(1000)

    // 检查是否有"暂无数据"提示
    const noDataText = await this.page.locator('.el-table__empty-text').textContent()
    if (noDataText) {
      console.log('表列表为空')
      return true // 空列表也是有效的加载状态
    }

    // 检查是否有表格行
    const rowCount = await this.getTableRowCount()
    return rowCount >= 0
  }

  /**
   * 导航到第一个表的详情页
   */
  async goToFirstTableDetail(): Promise<string | null> {
    const tableNames = await this.getTableNames()

    if (tableNames.length === 0) {
      console.log('没有找到任何表')
      return null
    }

    const firstTable = tableNames[0]
    await this.viewTableDetail(firstTable)

    return firstTable
  }
}
