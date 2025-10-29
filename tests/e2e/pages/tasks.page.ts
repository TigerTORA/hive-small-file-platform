import { Page, Locator } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * 任务状态类型
 */
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'success' | 'error'

/**
 * 任务信息接口
 */
export interface TaskInfo {
  id: string
  name?: string
  type?: string
  status: TaskStatus
  progress?: number
  startTime?: string
  endTime?: string
  duration?: string
  errorMessage?: string
}

/**
 * 任务中心页面对象
 */
export class TasksPage extends BasePage {
  // 页面元素定位器
  readonly pageTitle: Locator
  readonly taskTable: Locator
  readonly refreshBtn: Locator
  readonly filterSelect: Locator
  readonly searchInput: Locator
  readonly taskDetailDialog: Locator
  readonly clearBtn: Locator

  constructor(page: Page) {
    super(page)

    // 初始化定位器
    this.pageTitle = page.locator('h1, .page-title')
    this.taskTable = page.locator('.el-table')
    this.refreshBtn = page.locator('button:has-text("刷新")')
    this.filterSelect = page.locator('.el-select:has-text("状态"), select[placeholder*="状态"]')
    this.searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="任务"]')
    this.taskDetailDialog = page.locator('.el-dialog')
    this.clearBtn = page.locator('button:has-text("清空"), button:has-text("清理")')
  }

  /**
   * 访问任务中心页面
   */
  async navigate() {
    await this.goto('/#/tasks')
    await this.waitForLoading()
  }

  /**
   * 验证页面已加载
   */
  async verifyPageLoaded(): Promise<boolean> {
    try {
      await this.waitForPageLoad()

      // 验证页面标题或任务表格存在
      const hasTitle = await this.isVisible(this.pageTitle)
      const hasTable = await this.isVisible(this.taskTable)

      return hasTitle || hasTable
    } catch (error) {
      console.error('任务中心页面加载验证失败:', error)
      return false
    }
  }

  /**
   * 获取任务数量
   */
  async getTaskCount(): Promise<number> {
    if (await this.isVisible(this.taskTable)) {
      return await this.getTableRowCount()
    }
    return 0
  }

  /**
   * 获取所有任务列表
   */
  async getAllTasks(): Promise<TaskInfo[]> {
    const tasks: TaskInfo[] = []

    if (!(await this.isVisible(this.taskTable))) {
      return tasks
    }

    const rows = this.taskTable.locator('tbody tr')
    const count = await rows.count()

    for (let i = 0; i < count; i++) {
      const cells = await rows.nth(i).locator('td').allTextContents()

      if (cells.length >= 3 && !cells[0].includes('暂无数据')) {
        tasks.push({
          id: cells[0]?.trim() || `task-${i}`,
          name: cells[1]?.trim(),
          status: this.parseTaskStatus(cells[2]?.trim()),
          startTime: cells[3]?.trim(),
          endTime: cells[4]?.trim(),
          duration: cells[5]?.trim(),
        })
      }
    }

    return tasks
  }

  /**
   * 解析任务状态
   */
  private parseTaskStatus(statusText?: string): TaskStatus {
    if (!statusText) return 'pending'

    const text = statusText.toLowerCase()

    if (text.includes('成功') || text.includes('完成') || text.includes('completed') || text.includes('success')) {
      return 'completed'
    }
    if (text.includes('失败') || text.includes('错误') || text.includes('failed') || text.includes('error')) {
      return 'failed'
    }
    if (text.includes('运行') || text.includes('执行') || text.includes('running')) {
      return 'running'
    }
    if (text.includes('等待') || text.includes('pending')) {
      return 'pending'
    }

    return 'pending'
  }

  /**
   * 按状态过滤任务
   */
  async filterByStatus(status: 'all' | 'completed' | 'running' | 'failed' | 'pending') {
    if (await this.isVisible(this.filterSelect)) {
      await this.clickElement(this.filterSelect)

      // 选择对应的状态选项
      const statusMap: { [key: string]: string } = {
        all: '全部',
        completed: '已完成',
        running: '运行中',
        failed: '失败',
        pending: '等待中',
      }

      const option = this.page.locator(`.el-select-dropdown__item:has-text("${statusMap[status]}")`)
      await this.clickElement(option)

      await this.wait(500)
    }
  }

  /**
   * 搜索任务
   */
  async searchTask(keyword: string) {
    if (await this.isVisible(this.searchInput)) {
      await this.fillInput(this.searchInput, keyword)
      await this.wait(500)
    }
  }

  /**
   * 刷新任务列表
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
   * 查看任务详情
   */
  async viewTaskDetail(taskId: string) {
    const row = this.taskTable.locator(`tbody tr:has-text("${taskId}")`).first()
    const detailBtn = row.locator('button:has-text("详情"), a:has-text("详情")').first()

    await this.clickElement(detailBtn)
    await this.waitForElement(this.taskDetailDialog)
  }

  /**
   * 获取任务详情（从对话框）
   */
  async getTaskDetailFromDialog(): Promise<any> {
    if (!(await this.isVisible(this.taskDetailDialog))) {
      return null
    }

    const content = await this.getText(this.taskDetailDialog)

    return {
      rawContent: content,
      // 可以根据实际对话框结构解析更多字段
    }
  }

  /**
   * 关闭任务详情对话框
   */
  async closeTaskDetail() {
    if (await this.isVisible(this.taskDetailDialog)) {
      const closeBtn = this.taskDetailDialog.locator('.el-dialog__close, button:has-text("关闭")')
      await this.clickElement(closeBtn)
      await this.waitForElementHidden(this.taskDetailDialog)
    }
  }

  /**
   * 取消任务
   */
  async cancelTask(taskId: string) {
    const row = this.taskTable.locator(`tbody tr:has-text("${taskId}")`).first()
    const cancelBtn = row.locator('button:has-text("取消"), button:has-text("停止")').first()

    if (await this.isVisible(cancelBtn)) {
      await this.clickElement(cancelBtn)

      // 确认取消
      await this.confirmDialog()
      await this.waitForLoading()

      return true
    }

    return false
  }

  /**
   * 删除任务
   */
  async deleteTask(taskId: string) {
    const row = this.taskTable.locator(`tbody tr:has-text("${taskId}")`).first()
    const deleteBtn = row.locator('button:has-text("删除")').first()

    if (await this.isVisible(deleteBtn)) {
      await this.clickElement(deleteBtn)

      // 确认删除
      await this.confirmDialog()
      await this.waitForLoading()

      return true
    }

    return false
  }

  /**
   * 获取指定状态的任务数量
   */
  async getTaskCountByStatus(status: TaskStatus): Promise<number> {
    const tasks = await this.getAllTasks()
    return tasks.filter(task => task.status === status).length
  }

  /**
   * 等待任务完成
   */
  async waitForTaskCompletion(
    taskId: string,
    timeout: number = 300000,
    pollInterval: number = 2000
  ): Promise<boolean> {
    const startTime = Date.now()

    while (Date.now() - startTime < timeout) {
      await this.refresh()

      const tasks = await this.getAllTasks()
      const task = tasks.find(t => t.id === taskId)

      if (!task) {
        console.warn(`任务未找到: ${taskId}`)
        return false
      }

      if (task.status === 'completed' || task.status === 'success') {
        console.log(`任务已完成: ${taskId}`)
        return true
      }

      if (task.status === 'failed' || task.status === 'error') {
        console.error(`任务失败: ${taskId}`)
        return false
      }

      console.log(`等待任务完成: ${taskId}, 当前状态: ${task.status}`)
      await this.wait(pollInterval)
    }

    console.error(`任务超时: ${taskId}`)
    return false
  }

  /**
   * 获取最新的任务
   */
  async getLatestTask(): Promise<TaskInfo | null> {
    const tasks = await this.getAllTasks()
    return tasks.length > 0 ? tasks[0] : null
  }

  /**
   * 获取运行中的任务
   */
  async getRunningTasks(): Promise<TaskInfo[]> {
    const tasks = await this.getAllTasks()
    return tasks.filter(task => task.status === 'running')
  }

  /**
   * 获取失败的任务
   */
  async getFailedTasks(): Promise<TaskInfo[]> {
    const tasks = await this.getAllTasks()
    return tasks.filter(task => task.status === 'failed' || task.status === 'error')
  }

  /**
   * 获取已完成的任务
   */
  async getCompletedTasks(): Promise<TaskInfo[]> {
    const tasks = await this.getAllTasks()
    return tasks.filter(task => task.status === 'completed' || task.status === 'success')
  }

  /**
   * 清空已完成的任务
   */
  async clearCompletedTasks() {
    if (await this.isVisible(this.clearBtn)) {
      await this.clickElement(this.clearBtn)
      await this.confirmDialog()
      await this.waitForLoading()
      return true
    }
    return false
  }

  /**
   * 检查是否有失败的任务
   */
  async hasFailedTasks(): Promise<boolean> {
    const failedTasks = await this.getFailedTasks()
    return failedTasks.length > 0
  }

  /**
   * 验证任务列表数据完整性
   */
  async verifyTaskListIntegrity(): Promise<{
    isValid: boolean
    issues: string[]
  }> {
    const issues: string[] = []

    const tasks = await this.getAllTasks()

    // 检查是否有重复的任务ID
    const taskIds = tasks.map(t => t.id)
    const uniqueIds = new Set(taskIds)
    if (taskIds.length !== uniqueIds.size) {
      issues.push('存在重复的任务ID')
    }

    // 检查任务状态是否有效
    const invalidTasks = tasks.filter(
      t => !['pending', 'running', 'completed', 'failed', 'success', 'error'].includes(t.status)
    )
    if (invalidTasks.length > 0) {
      issues.push(`存在无效的任务状态: ${invalidTasks.length}个`)
    }

    return {
      isValid: issues.length === 0,
      issues,
    }
  }

  /**
   * 导出任务列表
   */
  async exportTaskList() {
    const exportBtn = this.page.locator('button:has-text("导出"), button:has-text("下载")')

    if (await this.isVisible(exportBtn)) {
      await this.clickElement(exportBtn)
      await this.wait(1000)
      return true
    }

    return false
  }

  /**
   * 获取任务统计信息
   */
  async getTaskStatistics(): Promise<{
    total: number
    running: number
    completed: number
    failed: number
    pending: number
  }> {
    const tasks = await this.getAllTasks()

    return {
      total: tasks.length,
      running: tasks.filter(t => t.status === 'running').length,
      completed: tasks.filter(t => t.status === 'completed' || t.status === 'success').length,
      failed: tasks.filter(t => t.status === 'failed' || t.status === 'error').length,
      pending: tasks.filter(t => t.status === 'pending').length,
    }
  }
}
