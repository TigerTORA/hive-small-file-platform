import fs from 'fs'
import path from 'path'
import dotenv from 'dotenv'

dotenv.config({ path: path.resolve(__dirname, '../../.env') })

/**
 * 测试结果状态
 */
export enum TestStatus {
  PASSED = '✅ 已通过',
  FAILED = '❌ 未通过',
  PENDING = '⊘ 待测试',
  SKIPPED = '⊗ 已跳过',
}

/**
 * 测试结果接口
 */
export interface TestResult {
  testId: string // 测试ID，如 "9.1"
  status: TestStatus
  timestamp?: string
  duration?: number // 测试耗时（毫秒）
  errorMessage?: string
  screenshotPath?: string
  consoleErrors?: number
  additionalNotes?: string
}

/**
 * 文档更新助手类
 * 用于自动更新 functional-test-checklist.md
 */
export class DocUpdater {
  private docPath: string
  private content: string

  constructor(docPath?: string) {
    this.docPath =
      docPath ||
      path.resolve(
        __dirname,
        '../../../',
        process.env.CHECKLIST_DOC || 'docs/functional-test-checklist.md'
      )

    if (!fs.existsSync(this.docPath)) {
      throw new Error(`文档不存在: ${this.docPath}`)
    }

    this.content = fs.readFileSync(this.docPath, 'utf-8')
  }

  /**
   * 更新测试状态
   */
  updateTestStatus(result: TestResult): void {
    const { testId, status, timestamp, duration, errorMessage, consoleErrors, additionalNotes } = result

    // 查找测试章节标题
    const sectionPattern = new RegExp(
      `(### ${testId} .*?) - (⊘ 待测试|✅ 已通过|❌ 未通过|⊗ 已跳过)`,
      'g'
    )

    // 检查是否找到了对应的章节
    if (!sectionPattern.test(this.content)) {
      console.warn(`⚠️ 未找到测试章节: ${testId}`)
      return
    }

    // 重置正则表达式的lastIndex
    sectionPattern.lastIndex = 0

    // 替换状态
    this.content = this.content.replace(sectionPattern, `$1 - ${status}`)

    // 查找测试结果部分并更新或添加
    const resultSectionPattern = new RegExp(
      `(### ${testId} .*?\\n\\n)((#### 🔒 检查项说明|#### 📊 测试结果))`,
      's'
    )

    let resultContent = this.generateResultSection(result)

    if (resultSectionPattern.test(this.content)) {
      // 如果已有测试结果部分，替换它
      this.content = this.content.replace(
        new RegExp(`(### ${testId} .*?\\n\\n)#### 📊 测试结果.*?(?=\\n####|\\n###|\\n##|\\n$)`, 's'),
        `$1${resultContent}`
      )
    } else {
      // 如果没有测试结果部分，在检查项说明之前插入
      this.content = this.content.replace(
        resultSectionPattern,
        `$1${resultContent}\n$2`
      )
    }

    console.log(`✅ 已更新测试状态: ${testId} -> ${status}`)
  }

  /**
   * 生成测试结果部分
   */
  private generateResultSection(result: TestResult): string {
    const { status, timestamp, duration, errorMessage, screenshotPath, consoleErrors, additionalNotes } = result

    let section = '#### 📊 测试结果\n\n'

    section += `- **状态**: ${status}\n`

    if (timestamp) {
      section += `- **测试时间**: ${timestamp}\n`
    }

    if (duration !== undefined) {
      section += `- **耗时**: ${(duration / 1000).toFixed(2)}秒\n`
    }

    if (consoleErrors !== undefined) {
      section += `- **Console错误**: ${consoleErrors}个\n`
    }

    if (screenshotPath) {
      section += `- **截图**: [查看截图](${this.getRelativePath(screenshotPath)})\n`
    }

    if (errorMessage) {
      section += `- **错误信息**: \n\`\`\`\n${errorMessage}\n\`\`\`\n`
    }

    if (additionalNotes) {
      section += `- **备注**: ${additionalNotes}\n`
    }

    section += '\n'

    return section
  }

  /**
   * 获取相对路径（相对于文档路径）
   */
  private getRelativePath(absolutePath: string): string {
    const docDir = path.dirname(this.docPath)
    return path.relative(docDir, absolutePath).replace(/\\/g, '/')
  }

  /**
   * 批量更新测试结果
   */
  updateMultipleTests(results: TestResult[]): void {
    results.forEach(result => {
      this.updateTestStatus(result)
    })
  }

  /**
   * 更新统计信息
   */
  updateStatistics(): void {
    // 统计各种状态的数量
    const passedCount = (this.content.match(/- ✅ 已通过/g) || []).length
    const failedCount = (this.content.match(/- ❌ 未通过/g) || []).length
    const pendingCount = (this.content.match(/- ⊘ 待测试/g) || []).length
    const skippedCount = (this.content.match(/- ⊗ 已跳过/g) || []).length

    const totalTests = passedCount + failedCount + pendingCount + skippedCount

    // 查找并更新统计信息部分
    const statsPattern = /## 📊 测试统计[\s\S]*?(?=\n##)/

    const newStats = `## 📊 测试统计

**测试执行总览**:
- 总测试项: ${totalTests}
- ✅ 已通过: ${passedCount}
- ❌ 未通过: ${failedCount}
- ⊘ 待测试: ${pendingCount}
- ⊗ 已跳过: ${skippedCount}

**通过率**: ${totalTests > 0 ? ((passedCount / totalTests) * 100).toFixed(1) : 0}%

**最后更新**: ${new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}
`

    if (statsPattern.test(this.content)) {
      this.content = this.content.replace(statsPattern, newStats)
    } else {
      // 如果没有统计部分，在文档开头插入
      const firstSectionPattern = /\n## /
      this.content = this.content.replace(firstSectionPattern, `\n${newStats}\n## `)
    }

    console.log('✅ 已更新测试统计信息')
  }

  /**
   * 添加测试执行记录
   */
  addExecutionRecord(testSuite: string, results: TestResult[]): void {
    const timestamp = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })

    let record = `\n---\n\n### 测试执行记录 - ${timestamp}\n\n`
    record += `**测试套件**: ${testSuite}\n\n`
    record += `| 测试ID | 状态 | 耗时 | Console错误 | 备注 |\n`
    record += `|--------|------|------|-------------|------|\n`

    results.forEach(result => {
      const duration = result.duration ? `${(result.duration / 1000).toFixed(2)}s` : '-'
      const errors = result.consoleErrors !== undefined ? result.consoleErrors.toString() : '-'
      const notes = result.additionalNotes || '-'
      record += `| ${result.testId} | ${result.status} | ${duration} | ${errors} | ${notes} |\n`
    })

    // 在文档末尾添加执行记录
    this.content += `\n${record}`

    console.log('✅ 已添加测试执行记录')
  }

  /**
   * 保存文档
   */
  save(): void {
    // 创建备份
    const backupPath = `${this.docPath}.backup_${Date.now()}`
    fs.copyFileSync(this.docPath, backupPath)
    console.log(`📦 已创建备份: ${backupPath}`)

    // 保存更新后的内容
    fs.writeFileSync(this.docPath, this.content, 'utf-8')
    console.log(`💾 文档已更新: ${this.docPath}`)
  }

  /**
   * 预览更改（不保存）
   */
  preview(): string {
    return this.content
  }

  /**
   * 获取文档路径
   */
  getDocPath(): string {
    return this.docPath
  }

  /**
   * 重新加载文档（撤销未保存的更改）
   */
  reload(): void {
    this.content = fs.readFileSync(this.docPath, 'utf-8')
    console.log('🔄 已重新加载文档')
  }

  /**
   * 标记整个章节为通过（用于批量更新）
   */
  markChapterPassed(chapterId: string): void {
    const chapterPattern = new RegExp(
      `(### ${chapterId}\\.\\d+ .*?) - (⊘ 待测试|❌ 未通过|⊗ 已跳过)`,
      'g'
    )

    this.content = this.content.replace(chapterPattern, `$1 - ${TestStatus.PASSED}`)
    console.log(`✅ 已将章节 ${chapterId} 的所有测试标记为通过`)
  }

  /**
   * 检查特定测试的当前状态
   */
  getTestStatus(testId: string): TestStatus | null {
    const statusPattern = new RegExp(`### ${testId} .*? - (⊘ 待测试|✅ 已通过|❌ 未通过|⊗ 已跳过)`)
    const match = this.content.match(statusPattern)

    if (match && match[1]) {
      return match[1] as TestStatus
    }

    return null
  }
}
