import { Page, ConsoleMessage } from '@playwright/test'
import fs from 'fs'
import path from 'path'

/**
 * Console消息类型
 */
export interface CapturedConsoleMessage {
  type: string
  text: string
  timestamp: number
  location?: string
  args?: any[]
}

/**
 * Console监控助手类
 * 用于捕获和分析浏览器Console输出
 */
export class ConsoleMonitor {
  private messages: CapturedConsoleMessage[] = []
  private errorMessages: CapturedConsoleMessage[] = []
  private warningMessages: CapturedConsoleMessage[] = []
  private isMonitoring: boolean = false
  private testName: string

  // 忽略的错误模式（可配置）
  private ignorePatterns: RegExp[] = [
    /Download the Vue Devtools extension/i,
    /Failed to load resource.*favicon.ico/i,
    /ResizeObserver loop limit exceeded/i,
  ]

  constructor(testName: string) {
    this.testName = testName
  }

  /**
   * 开始监控Console
   */
  startMonitoring(page: Page) {
    if (this.isMonitoring) {
      console.warn('⚠️ Console监控已经在运行')
      return
    }

    this.isMonitoring = true
    this.messages = []
    this.errorMessages = []
    this.warningMessages = []

    page.on('console', (msg: ConsoleMessage) => {
      this.handleConsoleMessage(msg)
    })

    page.on('pageerror', (error: Error) => {
      this.handlePageError(error)
    })

    console.log('🎯 Console监控已启动')
  }

  /**
   * 处理Console消息
   */
  private async handleConsoleMessage(msg: ConsoleMessage) {
    const capturedMsg: CapturedConsoleMessage = {
      type: msg.type(),
      text: msg.text(),
      timestamp: Date.now(),
      location: msg.location().url,
    }

    // 尝试获取参数（可能包含更详细的信息）
    try {
      const args = await Promise.all(
        msg.args().map(arg => arg.jsonValue().catch(() => null))
      )
      if (args.length > 0 && args.some(arg => arg !== null)) {
        capturedMsg.args = args.filter(arg => arg !== null)
      }
    } catch (error) {
      // 忽略参数解析错误
    }

    // 存储所有消息
    this.messages.push(capturedMsg)

    // 分类存储错误和警告
    if (msg.type() === 'error') {
      // 检查是否应该忽略
      if (!this.shouldIgnoreError(capturedMsg.text)) {
        this.errorMessages.push(capturedMsg)
        console.error(`❌ [Console Error] ${capturedMsg.text}`)
      }
    } else if (msg.type() === 'warning') {
      if (!this.shouldIgnoreError(capturedMsg.text)) {
        this.warningMessages.push(capturedMsg)
        console.warn(`⚠️ [Console Warning] ${capturedMsg.text}`)
      }
    }
  }

  /**
   * 处理页面错误
   */
  private handlePageError(error: Error) {
    const capturedMsg: CapturedConsoleMessage = {
      type: 'pageerror',
      text: error.message,
      timestamp: Date.now(),
      args: [{ stack: error.stack }],
    }

    this.errorMessages.push(capturedMsg)
    console.error(`💥 [Page Error] ${error.message}`)
  }

  /**
   * 检查是否应该忽略错误
   */
  private shouldIgnoreError(text: string): boolean {
    return this.ignorePatterns.some(pattern => pattern.test(text))
  }

  /**
   * 添加忽略模式
   */
  addIgnorePattern(pattern: RegExp | string) {
    if (typeof pattern === 'string') {
      this.ignorePatterns.push(new RegExp(pattern, 'i'))
    } else {
      this.ignorePatterns.push(pattern)
    }
  }

  /**
   * 停止监控
   */
  stopMonitoring() {
    this.isMonitoring = false
    console.log('🛑 Console监控已停止')
  }

  /**
   * 获取所有错误消息
   */
  getErrors(): CapturedConsoleMessage[] {
    return this.errorMessages
  }

  /**
   * 获取所有警告消息
   */
  getWarnings(): CapturedConsoleMessage[] {
    return this.warningMessages
  }

  /**
   * 获取所有消息
   */
  getAllMessages(): CapturedConsoleMessage[] {
    return this.messages
  }

  /**
   * 检查是否有错误
   */
  hasErrors(): boolean {
    return this.errorMessages.length > 0
  }

  /**
   * 检查是否有警告
   */
  hasWarnings(): boolean {
    return this.warningMessages.length > 0
  }

  /**
   * 生成Console报告
   */
  generateReport(): {
    totalMessages: number
    errors: number
    warnings: number
    errorList: CapturedConsoleMessage[]
    warningList: CapturedConsoleMessage[]
  } {
    return {
      totalMessages: this.messages.length,
      errors: this.errorMessages.length,
      warnings: this.warningMessages.length,
      errorList: this.errorMessages,
      warningList: this.warningMessages,
    }
  }

  /**
   * 保存Console日志到文件
   */
  saveToFile(outputDir: string = 'tests/reports/console-logs') {
    const dir = path.resolve(__dirname, '../../../', outputDir)
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const fileName = `${this.testName}_${timestamp}.json`
    const filePath = path.join(dir, fileName)

    const report = {
      testName: this.testName,
      timestamp: new Date().toISOString(),
      summary: {
        totalMessages: this.messages.length,
        errors: this.errorMessages.length,
        warnings: this.warningMessages.length,
      },
      errors: this.errorMessages,
      warnings: this.warningMessages,
      allMessages: this.messages,
    }

    fs.writeFileSync(filePath, JSON.stringify(report, null, 2))
    console.log(`📝 Console日志已保存: ${filePath}`)

    return filePath
  }

  /**
   * 清空消息记录
   */
  clear() {
    this.messages = []
    this.errorMessages = []
    this.warningMessages = []
  }

  /**
   * 断言无Console错误
   */
  assertNoErrors(allowedPatterns: RegExp[] = []): void {
    const errors = this.errorMessages.filter(error => {
      // 如果有允许的错误模式，则过滤掉这些错误
      return !allowedPatterns.some(pattern => pattern.test(error.text))
    })

    if (errors.length > 0) {
      const errorSummary = errors
        .map((e, i) => `${i + 1}. [${e.type}] ${e.text}`)
        .join('\n')
      throw new Error(`发现 ${errors.length} 个Console错误:\n${errorSummary}`)
    }
  }

  /**
   * 等待特定的Console消息出现
   */
  async waitForMessage(
    page: Page,
    pattern: RegExp | string,
    timeout: number = 5000
  ): Promise<CapturedConsoleMessage | null> {
    const startTime = Date.now()
    const regex = typeof pattern === 'string' ? new RegExp(pattern, 'i') : pattern

    while (Date.now() - startTime < timeout) {
      const message = this.messages.find(msg => regex.test(msg.text))
      if (message) {
        return message
      }
      await new Promise(resolve => setTimeout(resolve, 100))
    }

    return null
  }

  /**
   * 获取按类型分组的消息统计
   */
  getMessageStats(): { [type: string]: number } {
    const stats: { [type: string]: number } = {}

    this.messages.forEach(msg => {
      stats[msg.type] = (stats[msg.type] || 0) + 1
    })

    return stats
  }
}
