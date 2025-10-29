import { Page, Locator } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * 集群管理页面对象
 */
export class ClustersPage extends BasePage {
  // 页面元素定位器
  readonly pageTitle: Locator
  readonly addClusterBtn: Locator
  readonly clusterCards: Locator
  readonly searchInput: Locator
  readonly clusterDialog: Locator
  readonly clusterTable: Locator

  constructor(page: Page) {
    super(page)

    // 初始化定位器
    this.pageTitle = page.locator('h1, .page-title')
    this.addClusterBtn = page.locator('button:has-text("添加集群"), button:has-text("新增集群")')
    this.clusterCards = page.locator('.cluster-card')
    this.searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="查找"]')
    this.clusterDialog = page.locator('.el-dialog')
    this.clusterTable = page.locator('.el-table')
  }

  /**
   * 访问集群管理页面
   */
  async navigate() {
    await this.goto('/#/clusters')
    await this.waitForLoading()
  }

  /**
   * 验证页面已加载
   */
  async verifyPageLoaded(): Promise<boolean> {
    try {
      await this.waitForPageLoad()

      // 验证页面标题或集群列表存在
      const hasTitle = await this.isVisible(this.pageTitle)
      const hasCards = await this.clusterCards.count() > 0
      const hasTable = await this.isVisible(this.clusterTable)

      return hasTitle || hasCards || hasTable
    } catch (error) {
      console.error('集群管理页面加载验证失败:', error)
      return false
    }
  }

  /**
   * 获取集群数量
   */
  async getClusterCount(): Promise<number> {
    // 等待集群卡片或表格加载
    await this.wait(1000)

    // 尝试通过卡片计数
    const cardCount = await this.clusterCards.count()
    if (cardCount > 0) {
      return cardCount
    }

    // 尝试通过表格计数
    if (await this.isVisible(this.clusterTable)) {
      return await this.getTableRowCount()
    }

    return 0
  }

  /**
   * 获取所有集群名称
   */
  async getClusterNames(): Promise<string[]> {
    const names: string[] = []

    // 尝试从卡片获取
    const cardCount = await this.clusterCards.count()
    if (cardCount > 0) {
      for (let i = 0; i < cardCount; i++) {
        const nameElement = this.clusterCards.nth(i).locator('.cluster-name, .name, h3, .title')
        const name = await this.getText(nameElement)
        if (name) {
          names.push(name.trim())
        }
      }
      return names
    }

    // 尝试从表格获取
    if (await this.isVisible(this.clusterTable)) {
      const rows = this.clusterTable.locator('tbody tr')
      const count = await rows.count()

      for (let i = 0; i < count; i++) {
        const nameCell = rows.nth(i).locator('td').first()
        const name = await this.getText(nameCell)
        if (name) {
          names.push(name.trim())
        }
      }
    }

    return names
  }

  /**
   * 选择集群（点击集群卡片）
   */
  async selectCluster(clusterName: string) {
    const clusterCard = this.clusterCards.filter({ hasText: clusterName }).first()
    await this.clickElement(clusterCard)
    await this.waitForLoading()

    // 等待选择状态更新
    await this.wait(500)
  }

  /**
   * 选择第一个集群
   */
  async selectFirstCluster(): Promise<string> {
    const firstCard = this.clusterCards.first()
    await this.waitForElement(firstCard)

    const clusterName = await this.getText(firstCard.locator('.cluster-name, .name, h3'))
    await this.clickElement(firstCard)
    await this.waitForLoading()

    return clusterName.trim()
  }

  /**
   * 点击添加集群按钮
   */
  async clickAddCluster() {
    await this.clickElement(this.addClusterBtn)
    await this.waitForElement(this.clusterDialog)
  }

  /**
   * 填写集群表单
   */
  async fillClusterForm(data: {
    name: string
    host: string
    port: string | number
    metastoreUrl: string
    hdfsUrl: string
    hdfsUser?: string
  }) {
    await this.waitForElement(this.clusterDialog)

    // 填写集群名称
    const nameInput = this.clusterDialog.locator('input[placeholder*="名称"]')
    await this.fillInput(nameInput, data.name)

    // 填写Hive主机地址
    const hostInput = this.clusterDialog.locator('input[placeholder*="Hive"]')
    await this.fillInput(hostInput, data.host)

    // 填写Hive端口（el-input-number组件）
    const portInput = this.clusterDialog.locator('.el-form-item:has-text("Hive 端口") .el-input-number input')
    await this.fillInput(portInput, data.port.toString())

    // 填写MetaStore URL
    const metastoreInput = this.clusterDialog.locator('input[placeholder*="postgresql"], input[placeholder*="mysql"]')
    await this.fillInput(metastoreInput, data.metastoreUrl)

    // 填写HDFS/HttpFS地址
    const hdfsInput = this.clusterDialog.locator('input[placeholder*="httpfs"], input[placeholder*="webhdfs"]')
    await this.fillInput(hdfsInput, data.hdfsUrl)

    // 填写HDFS用户（如果提供）
    if (data.hdfsUser) {
      const hdfsUserInput = this.clusterDialog.locator('.el-form-item:has-text("HDFS 用户") input')
      await this.fillInput(hdfsUserInput, data.hdfsUser)
    }
  }

  /**
   * 提交集群表单
   */
  async submitClusterForm() {
    // 滚动对话框到底部，确保提交按钮可见
    await this.clusterDialog.evaluate((el) => {
      const content = el.querySelector('.el-dialog__body')
      if (content) {
        content.scrollTop = content.scrollHeight
      }
    })

    await this.wait(500) // 等待滚动完成

    // 直接通过footer定位提交按钮
    const submitBtn = this.clusterDialog.locator('.el-dialog__footer button.el-button--primary')
    await this.clickElement(submitBtn)
    await this.waitForLoading()

    // 等待对话框关闭
    await this.waitForElementHidden(this.clusterDialog, 5000)
  }

  /**
   * 添加新集群（完整流程）
   */
  async addCluster(data: {
    name: string
    host: string
    port: string | number
    metastoreUrl: string
    hdfsUrl: string
    hdfsUser?: string
  }) {
    await this.clickAddCluster()
    await this.fillClusterForm(data)
    await this.submitClusterForm()

    // 等待成功消息
    await this.waitForMessage('success')
  }

  /**
   * 编辑集群
   */
  async editCluster(clusterName: string, newData: Partial<{
    name: string
    host: string
    port: string | number
  }>) {
    // 找到集群卡片
    const clusterCard = this.clusterCards.filter({ hasText: clusterName }).first()

    // 点击编辑按钮
    const editBtn = clusterCard.locator('button:has-text("编辑"), .edit-btn, [class*="edit"]')
    await this.clickElement(editBtn)

    // 等待对话框出现
    await this.waitForElement(this.clusterDialog)
    await this.wait(500) // 等待表单加载

    // 更新表单数据
    if (newData.name) {
      const nameInput = this.clusterDialog.locator('input[placeholder*="名称"]')
      await this.fillInput(nameInput, newData.name)
    }

    if (newData.host) {
      const hostInput = this.clusterDialog.locator('input[placeholder*="Hive"]')
      await this.fillInput(hostInput, newData.host)
    }

    if (newData.port) {
      // 使用和fillClusterForm相同的选择器
      const portInput = this.clusterDialog.locator('.el-form-item:has-text("Hive 端口") .el-input-number input')
      await this.fillInput(portInput, newData.port.toString())
    }

    // 提交表单
    await this.submitClusterForm()
  }

  /**
   * 删除集群
   */
  async deleteCluster(clusterName: string) {
    const clusterCard = this.clusterCards.filter({ hasText: clusterName }).first()

    // 点击删除按钮
    const deleteBtn = clusterCard.locator('button:has-text("删除"), .delete-btn, [class*="delete"]')
    await this.clickElement(deleteBtn)

    // 确认删除
    await this.confirmDialog()
    await this.waitForLoading()

    // 等待成功消息
    await this.waitForMessage('success')
  }

  /**
   * 搜索集群
   */
  async searchCluster(keyword: string) {
    if (await this.isVisible(this.searchInput)) {
      await this.fillInput(this.searchInput, keyword)
      await this.wait(500) // 等待搜索结果更新
    }
  }

  /**
   * 测试集群连接
   */
  async testConnection(clusterName: string): Promise<boolean> {
    const clusterCard = this.clusterCards.filter({ hasText: clusterName }).first()

    // 点击测试连接按钮
    const testBtn = clusterCard.locator('button:has-text("测试"), .test-btn')

    if (await this.isVisible(testBtn)) {
      await this.clickElement(testBtn)
      await this.waitForLoading()

      // 检查是否有成功消息
      try {
        await this.waitForMessage('success', 5000)
        return true
      } catch {
        return false
      }
    }

    return false
  }

  /**
   * 获取集群详细信息
   */
  async getClusterInfo(clusterName: string): Promise<{
    name: string
    host?: string
    port?: string
    status?: string
  } | null> {
    const clusterCard = this.clusterCards.filter({ hasText: clusterName }).first()

    if (!(await this.isVisible(clusterCard))) {
      return null
    }

    const info: any = { name: clusterName }

    // 尝试获取主机地址
    const hostElement = clusterCard.locator('.host, .address, [class*="host"]')
    if (await this.isVisible(hostElement)) {
      info.host = await this.getText(hostElement)
    }

    // 尝试获取端口
    const portElement = clusterCard.locator('.port, [class*="port"]')
    if (await this.isVisible(portElement)) {
      info.port = await this.getText(portElement)
    }

    // 尝试获取状态
    const statusElement = clusterCard.locator('.status, [class*="status"]')
    if (await this.isVisible(statusElement)) {
      info.status = await this.getText(statusElement)
    }

    return info
  }

  /**
   * 验证集群是否被选中
   */
  async isClusterSelected(clusterName: string): Promise<boolean> {
    const clusterCard = this.clusterCards.filter({ hasText: clusterName }).first()

    if (!(await this.isVisible(clusterCard))) {
      return false
    }

    // 检查是否有选中状态的class
    const classList = await clusterCard.getAttribute('class')
    return classList?.includes('selected') || classList?.includes('active') || false
  }

  /**
   * 获取当前选中的集群
   */
  async getSelectedCluster(): Promise<string | null> {
    const selectedCard = this.clusterCards.locator('.selected, .active').first()

    if (await this.isVisible(selectedCard)) {
      const nameElement = selectedCard.locator('.cluster-name, .name, h3')
      return await this.getText(nameElement)
    }

    return null
  }
}
