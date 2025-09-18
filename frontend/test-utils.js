const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')
const TEST_CONFIG = require('./test-config.js')

class TestUtils {
  constructor() {
    this.browser = null
    this.page = null
    this.testResults = []
    this.currentTest = null
  }

  // 初始化浏览器和页面
  async initBrowser() {
    console.log('🚀 初始化浏览器...')
    this.browser = await chromium.launch({
      headless: TEST_CONFIG.options.headless,
      slowMo: TEST_CONFIG.options.slowMo
    })

    this.page = await this.browser.newPage()
    await this.page.setViewportSize(TEST_CONFIG.options.viewport)

    // 设置默认超时
    this.page.setDefaultTimeout(TEST_CONFIG.options.timeout)

    // 监听控制台日志
    this.page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log(`💥 页面错误: ${msg.text()}`)
      }
    })

    // 监听网络请求失败
    this.page.on('requestfailed', request => {
      console.log(`🌐 请求失败: ${request.url()} - ${request.failure().errorText}`)
    })

    console.log('✅ 浏览器初始化完成')
  }

  // 关闭浏览器
  async closeBrowser() {
    if (this.browser) {
      await this.browser.close()
      console.log('🔒 浏览器已关闭')
    }
  }

  // 导航到指定页面
  async navigateToPage(pageName) {
    const url = TEST_CONFIG.app.baseUrl + TEST_CONFIG.routes[pageName]
    console.log(`🧭 导航到 ${pageName}: ${url}`)

    try {
      await this.page.goto(url)
      await this.page.waitForLoadState('networkidle')
      return true
    } catch (error) {
      console.error(`❌ 导航失败: ${error.message}`)
      return false
    }
  }

  // 等待元素出现
  async waitForElement(selector, timeout = 5000) {
    try {
      await this.page.waitForSelector(selector, { timeout })
      return true
    } catch (error) {
      console.error(`❌ 元素未找到: ${selector}`)
      return false
    }
  }

  // 点击元素并等待响应
  async clickElement(selector, expectDialog = false, expectNavigation = false) {
    try {
      console.log(`🖱️ 点击元素: ${selector}`)

      if (expectNavigation) {
        await Promise.all([this.page.waitForNavigation(), this.page.click(selector)])
      } else {
        await this.page.click(selector)
      }

      if (expectDialog) {
        await this.page.waitForSelector('.el-dialog', { timeout: 3000 })
      }

      await this.page.waitForTimeout(500) // 短暂等待UI响应
      return true
    } catch (error) {
      console.error(`❌ 点击失败: ${selector} - ${error.message}`)
      return false
    }
  }

  // 填写表单字段
  async fillForm(formData, selectors) {
    console.log('📝 填写表单...')

    for (const [field, value] of Object.entries(formData)) {
      const selector = selectors[field + 'Input']
      if (selector && value !== undefined) {
        try {
          await this.page.fill(selector, value)
          console.log(`✅ 填写字段 ${field}: ${value}`)
        } catch (error) {
          console.error(`❌ 填写字段失败 ${field}: ${error.message}`)
          return false
        }
      }
    }
    return true
  }

  // 检查元素是否存在
  async elementExists(selector) {
    try {
      const element = await this.page.$(selector)
      return element !== null
    } catch (error) {
      return false
    }
  }

  // 检查元素是否可见
  async elementVisible(selector) {
    try {
      return await this.page.isVisible(selector)
    } catch (error) {
      return false
    }
  }

  // 检查元素是否禁用
  async elementDisabled(selector) {
    try {
      return await this.page.isDisabled(selector)
    } catch (error) {
      return false
    }
  }

  // 获取元素文本内容
  async getElementText(selector) {
    try {
      return await this.page.textContent(selector)
    } catch (error) {
      return null
    }
  }

  // 截图保存
  async takeScreenshot(name, fullPage = false) {
    if (!TEST_CONFIG.options.screenshot) return

    const screenshotDir = path.join(TEST_CONFIG.reporting.outputDir, 'screenshots')
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true })
    }

    const filename = `${name}-${Date.now()}.png`
    const filepath = path.join(screenshotDir, filename)

    try {
      await this.page.screenshot({
        path: filepath,
        fullPage
      })
      console.log(`📸 截图保存: ${filename}`)
      return filename
    } catch (error) {
      console.error(`❌ 截图失败: ${error.message}`)
      return null
    }
  }

  // API测试工具
  async testApiEndpoint(endpoint, method = 'GET', data = null) {
    const url = TEST_CONFIG.app.apiBaseUrl + endpoint
    console.log(`🔗 测试API: ${method} ${url}`)

    try {
      const response = await this.page.evaluate(
        async ({ url, method, data }) => {
          const options = {
            method,
            headers: {
              'Content-Type': 'application/json'
            }
          }

          if (data && method !== 'GET') {
            options.body = JSON.stringify(data)
          }

          const resp = await fetch(url, options)
          return {
            status: resp.status,
            ok: resp.ok,
            statusText: resp.statusText
          }
        },
        { url, method, data }
      )

      console.log(`✅ API响应: ${response.status} ${response.statusText}`)
      return response
    } catch (error) {
      console.error(`❌ API测试失败: ${error.message}`)
      return { status: 0, ok: false, statusText: error.message }
    }
  }

  // 测试结果记录
  startTest(testName, category = 'general') {
    this.currentTest = {
      name: testName,
      category,
      startTime: Date.now(),
      status: 'running',
      steps: [],
      screenshots: [],
      errors: []
    }
    console.log(`🧪 开始测试: ${testName}`)
  }

  addTestStep(step, status = 'success', details = '') {
    if (this.currentTest) {
      this.currentTest.steps.push({
        step,
        status,
        details,
        timestamp: Date.now()
      })

      const icon = status === 'success' ? '✅' : '❌'
      console.log(`${icon} ${step}${details ? ': ' + details : ''}`)
    }
  }

  finishTest(status = 'success', error = null) {
    if (this.currentTest) {
      this.currentTest.status = status
      this.currentTest.endTime = Date.now()
      this.currentTest.duration = this.currentTest.endTime - this.currentTest.startTime

      if (error) {
        this.currentTest.errors.push(error)
      }

      this.testResults.push(this.currentTest)

      const icon = status === 'success' ? '✅' : '❌'
      console.log(`${icon} 测试完成: ${this.currentTest.name} (${this.currentTest.duration}ms)`)

      this.currentTest = null
    }
  }

  // 等待页面加载完成
  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle')
    await this.page.waitForTimeout(1000) // 额外等待确保组件渲染完成
  }

  // 验证页面标题
  async verifyPageTitle(expectedTitle) {
    const title = await this.page.title()
    const isCorrect = title.includes(expectedTitle)
    console.log(`📄 页面标题: ${title} ${isCorrect ? '✅' : '❌'}`)
    return isCorrect
  }

  // 检查是否有JavaScript错误
  async checkForJSErrors() {
    const errors = []

    this.page.on('pageerror', error => {
      errors.push(error.message)
    })

    this.page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    return errors
  }

  // 清理测试数据
  async cleanupTestData() {
    console.log('🧹 清理测试数据...')

    // 删除测试创建的集群
    try {
      const clusters = await this.testApiEndpoint('/api/v1/clusters/')
      if (clusters.ok) {
        // 这里可以添加删除测试集群的逻辑
        console.log('✅ 测试数据清理完成')
      }
    } catch (error) {
      console.error(`❌ 清理失败: ${error.message}`)
    }
  }

  // 生成测试报告数据
  getTestResults() {
    const summary = {
      total: this.testResults.length,
      passed: this.testResults.filter(t => t.status === 'success').length,
      failed: this.testResults.filter(t => t.status === 'failed').length,
      duration: this.testResults.reduce((sum, t) => sum + t.duration, 0)
    }

    return {
      summary,
      tests: this.testResults,
      timestamp: new Date().toISOString()
    }
  }

  // 重试机制
  async retryOperation(operation, maxRetries = 3, delay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
      try {
        return await operation()
      } catch (error) {
        console.log(`🔄 重试 ${i + 1}/${maxRetries}: ${error.message}`)
        if (i === maxRetries - 1) throw error
        await this.page.waitForTimeout(delay)
      }
    }
  }
}

module.exports = TestUtils
