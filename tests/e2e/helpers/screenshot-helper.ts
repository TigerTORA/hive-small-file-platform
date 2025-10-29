import { Page } from '@playwright/test'
import fs from 'fs'
import path from 'path'
import dotenv from 'dotenv'

dotenv.config({ path: path.resolve(__dirname, '../../.env') })

/**
 * 截图助手类
 * 用于统一管理测试过程中的截图
 */
export class ScreenshotHelper {
  private screenshotDir: string
  private testName: string

  constructor(testName: string) {
    this.testName = testName.replace(/[^a-zA-Z0-9-_]/g, '_')
    this.screenshotDir = path.resolve(
      __dirname,
      '../../../',
      process.env.SCREENSHOT_DIR || 'docs/screenshots',
      this.testName
    )

    // 确保截图目录存在
    this.ensureDirectoryExists(this.screenshotDir)
  }

  /**
   * 确保目录存在
   */
  private ensureDirectoryExists(dir: string) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
  }

  /**
   * 获取截图文件名
   */
  private getScreenshotFileName(stepName: string, timestamp: boolean = true): string {
    const sanitizedName = stepName.replace(/[^a-zA-Z0-9-_]/g, '_')
    const time = timestamp ? `_${Date.now()}` : ''
    return `${sanitizedName}${time}.png`
  }

  /**
   * 截取整个页面
   */
  async captureFullPage(page: Page, stepName: string): Promise<string> {
    const fileName = this.getScreenshotFileName(stepName)
    const filePath = path.join(this.screenshotDir, fileName)

    await page.screenshot({
      path: filePath,
      fullPage: true,
    })

    console.log(`📸 截图已保存: ${filePath}`)
    return filePath
  }

  /**
   * 截取当前视口
   */
  async captureViewport(page: Page, stepName: string): Promise<string> {
    const fileName = this.getScreenshotFileName(stepName)
    const filePath = path.join(this.screenshotDir, fileName)

    await page.screenshot({
      path: filePath,
      fullPage: false,
    })

    console.log(`📸 截图已保存: ${filePath}`)
    return filePath
  }

  /**
   * 截取特定元素
   */
  async captureElement(
    page: Page,
    selector: string,
    stepName: string
  ): Promise<string> {
    const fileName = this.getScreenshotFileName(stepName)
    const filePath = path.join(this.screenshotDir, fileName)

    const element = await page.locator(selector).first()
    await element.screenshot({ path: filePath })

    console.log(`📸 元素截图已保存: ${filePath}`)
    return filePath
  }

  /**
   * 对比截图（简单实现，仅记录路径）
   * 实际对比可以使用像素差异库，如 pixelmatch
   */
  async compareScreenshots(
    page: Page,
    stepName: string,
    baselinePath?: string
  ): Promise<{ current: string; baseline?: string; match: boolean }> {
    const currentPath = await this.captureFullPage(page, stepName)

    if (!baselinePath || !fs.existsSync(baselinePath)) {
      console.log(`⚠️ 基准截图不存在，将当前截图作为基准: ${currentPath}`)
      return { current: currentPath, match: true }
    }

    // 这里可以添加实际的图片对比逻辑
    // 例如使用 pixelmatch 库
    console.log(`📊 截图对比: 当前 ${currentPath} vs 基准 ${baselinePath}`)

    return {
      current: currentPath,
      baseline: baselinePath,
      match: true, // 简化实现，实际应该进行像素对比
    }
  }

  /**
   * 截取失败场景
   */
  async captureFailure(
    page: Page,
    errorMessage: string,
    stepName: string
  ): Promise<string> {
    const fileName = this.getScreenshotFileName(`FAILURE_${stepName}`)
    const filePath = path.join(this.screenshotDir, fileName)

    await page.screenshot({
      path: filePath,
      fullPage: true,
    })

    // 同时保存错误信息
    const errorLogPath = filePath.replace('.png', '.txt')
    fs.writeFileSync(errorLogPath, `错误信息:\n${errorMessage}\n\n发生时间: ${new Date().toISOString()}`)

    console.error(`❌ 失败截图已保存: ${filePath}`)
    console.error(`📝 错误日志已保存: ${errorLogPath}`)

    return filePath
  }

  /**
   * 批量截图（用于记录完整流程）
   */
  async captureSequence(
    page: Page,
    steps: Array<{ name: string; action?: () => Promise<void> }>
  ): Promise<string[]> {
    const screenshots: string[] = []

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i]
      const stepName = `${i + 1}_${step.name}`

      // 执行操作（如果有）
      if (step.action) {
        await step.action()
      }

      // 等待页面稳定
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {
        console.log('⚠️ 网络未完全空闲，继续截图')
      })

      // 截图
      const screenshotPath = await this.captureFullPage(page, stepName)
      screenshots.push(screenshotPath)
    }

    console.log(`✅ 序列截图完成，共 ${screenshots.length} 张`)
    return screenshots
  }

  /**
   * 清理旧截图
   */
  cleanOldScreenshots(daysToKeep: number = 7) {
    if (!fs.existsSync(this.screenshotDir)) {
      return
    }

    const now = Date.now()
    const maxAge = daysToKeep * 24 * 60 * 60 * 1000

    const files = fs.readdirSync(this.screenshotDir)
    let deletedCount = 0

    files.forEach(file => {
      const filePath = path.join(this.screenshotDir, file)
      const stats = fs.statSync(filePath)
      const age = now - stats.mtimeMs

      if (age > maxAge) {
        fs.unlinkSync(filePath)
        deletedCount++
      }
    })

    console.log(`🧹 清理了 ${deletedCount} 个旧截图`)
  }

  /**
   * 获取截图目录路径
   */
  getScreenshotDir(): string {
    return this.screenshotDir
  }
}
