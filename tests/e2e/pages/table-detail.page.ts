import { Page, Locator } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * 表详情页面对象
 */
export class TableDetailPage extends BasePage {
  // 页面元素定位器
  readonly pageTitle: Locator
  readonly backBtn: Locator
  readonly tableName: Locator
  readonly tableStats: Locator
  readonly fileListTable: Locator
  readonly mergeBtn: Locator
  readonly refreshBtn: Locator
  readonly filterInput: Locator
  readonly chartContainer: Locator

  constructor(page: Page) {
    super(page)

    // 初始化定位器
    this.pageTitle = page.locator('h1, .page-title')
    this.backBtn = page.locator('button:has-text("返回"), .back-btn, a:has-text("返回")')
    this.tableName = page.locator('.table-name, h2')
    this.tableStats = page.locator('.stats, .statistics, .table-info')
    this.fileListTable = page.locator('.el-table')
    this.mergeBtn = page.locator('button:has-text("合并"), button:has-text("优化")')
    this.refreshBtn = page.locator('button:has-text("刷新")')
    this.filterInput = page.locator('input[placeholder*="过滤"], input[placeholder*="搜索"]')
    this.chartContainer = page.locator('.chart-container, [id*="chart"]')
  }

  /**
   * 访问表详情页面
   */
  async navigate(clusterId: string, database: string, tableName: string) {
    await this.goto(`/#/table-detail?cluster=${clusterId}&database=${database}&table=${tableName}`)
    await this.waitForLoading()
  }

  /**
   * 验证页面已加载
   */
  async verifyPageLoaded(): Promise<boolean> {
    try {
      await this.waitForPageLoad()

      // 验证表名或统计信息存在
      const hasTableName = await this.isVisible(this.tableName)
      const hasStats = await this.isVisible(this.tableStats)
      const hasTable = await this.isVisible(this.fileListTable)

      return hasTableName || hasStats || hasTable
    } catch (error) {
      console.error('表详情页面加载验证失败:', error)
      return false
    }
  }

  /**
   * 获取表名
   */
  async getTableName(): Promise<string> {
    if (await this.isVisible(this.tableName)) {
      return await this.getText(this.tableName)
    }
    return ''
  }

  /**
   * 获取表统计信息
   */
  async getTableStatistics(): Promise<{
    totalFiles?: number
    smallFiles?: number
    totalSize?: string
    avgFileSize?: string
  }> {
    const stats: any = {}

    if (!(await this.isVisible(this.tableStats))) {
      return stats
    }

    // 尝试提取各种统计数据
    const statsText = await this.getText(this.tableStats)

    // 使用正则表达式提取数字
    const totalFilesMatch = statsText.match(/总文件数[：:]\s*(\d+)/)
    if (totalFilesMatch) {
      stats.totalFiles = parseInt(totalFilesMatch[1])
    }

    const smallFilesMatch = statsText.match(/小文件数[：:]\s*(\d+)/)
    if (smallFilesMatch) {
      stats.smallFiles = parseInt(smallFilesMatch[1])
    }

    const totalSizeMatch = statsText.match(/总大小[：:]\s*([\d.]+\s*[KMGT]?B)/)
    if (totalSizeMatch) {
      stats.totalSize = totalSizeMatch[1]
    }

    const avgSizeMatch = statsText.match(/平均大小[：:]\s*([\d.]+\s*[KMGT]?B)/)
    if (avgSizeMatch) {
      stats.avgFileSize = avgSizeMatch[1]
    }

    return stats
  }

  /**
   * 获取文件列表
   */
  async getFileList(): Promise<Array<{
    path: string
    size: string
    modifyTime?: string
  }>> {
    const files: Array<{ path: string; size: string; modifyTime?: string }> = []

    if (!(await this.isVisible(this.fileListTable))) {
      return files
    }

    const rows = this.fileListTable.locator('tbody tr')
    const count = await rows.count()

    for (let i = 0; i < count; i++) {
      const cells = await rows.nth(i).locator('td').allTextContents()

      if (cells.length >= 2 && !cells[0].includes('暂无数据')) {
        files.push({
          path: cells[0]?.trim() || '',
          size: cells[1]?.trim() || '',
          modifyTime: cells[2]?.trim(),
        })
      }
    }

    return files
  }

  /**
   * 获取小文件数量（从文件列表）
   */
  async getSmallFileCount(sizeThreshold: string = '128MB'): Promise<number> {
    const files = await this.getFileList()

    // 简单实现：统计所有文件（实际应该根据阈值过滤）
    return files.length
  }

  /**
   * 过滤文件列表
   */
  async filterFiles(keyword: string) {
    if (await this.isVisible(this.filterInput)) {
      await this.fillInput(this.filterInput, keyword)
      await this.wait(500)
    }
  }

  /**
   * 刷新页面数据
   */
  async refresh() {
    if (await this.isVisible(this.refreshBtn)) {
      await this.clickElement(this.refreshBtn)
      await this.waitForLoading()
    } else {
      await this.reload()
    }
  }

  /**
   * 触发小文件合并
   */
  async triggerMerge(hdfsPath?: string) {
    await this.clickElement(this.mergeBtn)

    // 如果有合并对话框
    const dialog = this.page.locator('.el-dialog')
    if (await this.isVisible(dialog)) {
      // 填写HDFS路径（如果需要）
      if (hdfsPath) {
        const pathInput = dialog.locator('input[placeholder*="路径"]')
        if (await this.isVisible(pathInput)) {
          await this.fillInput(pathInput, hdfsPath)
        }
      }

      // 点击确认
      const confirmBtn = dialog.locator('button:has-text("确定"), button:has-text("提交")')
      await this.clickElement(confirmBtn)

      await this.waitForLoading()

      // 等待成功消息
      try {
        const message = await this.waitForMessage('success', 5000)
        console.log('合并任务已提交:', message)
      } catch {
        console.warn('未收到成功消息')
      }
    }
  }

  /**
   * 返回表管理页面
   */
  async goBack() {
    if (await this.isVisible(this.backBtn)) {
      await this.clickElement(this.backBtn)
      await this.waitForNavigation()
    } else {
      // 如果没有返回按钮，通过导航返回
      await this.goto('/#/tables')
    }
  }

  /**
   * 检查是否有图表展示
   */
  async hasChart(): Promise<boolean> {
    return await this.isVisible(this.chartContainer)
  }

  /**
   * 获取文件大小分布（如果有图表）
   */
  async getFileSizeDistribution(): Promise<any> {
    // 这里需要根据实际的图表实现来解析数据
    // 简化实现：返回是否有图表
    return {
      hasChart: await this.hasChart(),
    }
  }

  /**
   * 验证表详情数据完整性
   */
  async verifyDataIntegrity(): Promise<{
    isValid: boolean
    issues: string[]
  }> {
    const issues: string[] = []

    // 检查表名
    const tableName = await this.getTableName()
    if (!tableName) {
      issues.push('表名未显示')
    }

    // 检查统计信息
    const stats = await this.getTableStatistics()
    if (!stats.totalFiles && stats.totalFiles !== 0) {
      issues.push('统计信息未加载')
    }

    // 检查文件列表
    const files = await this.getFileList()
    if (files.length === 0 && stats.totalFiles && stats.totalFiles > 0) {
      issues.push('文件列表与统计信息不一致')
    }

    return {
      isValid: issues.length === 0,
      issues,
    }
  }

  /**
   * 导出文件列表（如果有导出功能）
   */
  async exportFileList() {
    const exportBtn = this.page.locator('button:has-text("导出"), button:has-text("下载")')

    if (await this.isVisible(exportBtn)) {
      await this.clickElement(exportBtn)
      await this.wait(1000)
      return true
    }

    return false
  }

  /**
   * 获取分区信息（如果是分区表）
   */
  async getPartitionInfo(): Promise<string[]> {
    const partitions: string[] = []

    const partitionSection = this.page.locator('.partition-info, .partitions')
    if (await this.isVisible(partitionSection)) {
      const partitionElements = partitionSection.locator('.partition-item, li')
      const count = await partitionElements.count()

      for (let i = 0; i < count; i++) {
        const text = await partitionElements.nth(i).textContent()
        if (text) {
          partitions.push(text.trim())
        }
      }
    }

    return partitions
  }

  /**
   * 检查表是否有小文件问题
   */
  async hasSmallFileIssue(threshold: number = 100): Promise<boolean> {
    const stats = await this.getTableStatistics()

    if (stats.smallFiles !== undefined) {
      return stats.smallFiles > threshold
    }

    if (stats.totalFiles !== undefined) {
      return stats.totalFiles > threshold
    }

    return false
  }

  /**
   * 等待数据加载完成
   */
  async waitForDataLoaded(timeout: number = 10000) {
    // 等待加载动画消失
    await this.waitForLoading()

    // 等待表格或统计信息可见
    await Promise.race([
      this.waitForElement(this.fileListTable, timeout),
      this.waitForElement(this.tableStats, timeout),
    ])

    // 等待网络空闲
    await this.waitForPageLoad()
  }
}
