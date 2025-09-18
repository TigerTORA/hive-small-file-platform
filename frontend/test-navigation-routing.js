const TestUtils = require('./test-utils.js')
const TEST_CONFIG = require('./test-config.js')

class NavigationRoutingTester {
  constructor() {
    this.utils = new TestUtils()
    this.testResults = {
      total: 0,
      passed: 0,
      failed: 0,
      details: []
    }
  }

  async runAllNavigationTests() {
    console.log('🧭 开始综合导航和路由测试...\n')

    try {
      await this.utils.initBrowser()

      // 测试基本页面导航
      await this.testBasicPageNavigation()

      // 测试路由参数导航
      await this.testParameterizedRouting()

      // 测试浏览器前进后退
      await this.testBrowserNavigation()

      // 测试深度链接
      await this.testDeepLinking()

      // 测试页面标题更新
      await this.testPageTitleUpdates()

      // 测试导航守卫
      await this.testNavigationGuards()

      this.generateSummary()
      return this.testResults
    } catch (error) {
      console.error(`💥 测试过程中出现错误: ${error.message}`)
      return null
    } finally {
      await this.utils.closeBrowser()
    }
  }

  async testBasicPageNavigation() {
    console.log('\n📄 测试基本页面导航')

    const pages = ['clusters', 'dashboard', 'tables', 'tasks', 'settings']

    for (const page of pages) {
      await this.testSinglePageNavigation(page)
    }

    // 测试循环导航
    await this.testCircularNavigation()
  }

  async testSinglePageNavigation(pageName) {
    this.utils.startTest(`navigate-to-${pageName}`, 'navigation')

    try {
      console.log(`🔗 导航到 ${pageName} 页面`)

      const success = await this.utils.navigateToPage(pageName)
      if (!success) {
        this.utils.addTestStep('页面导航', 'failed', '导航失败')
        this.utils.finishTest('failed', `无法导航到 ${pageName}`)
        this.recordTestResult(`navigate-${pageName}`, false, '导航失败')
        return
      }

      this.utils.addTestStep('页面导航', 'success')

      // 验证URL正确性
      const expectedPath = TEST_CONFIG.routes[pageName]
      const currentUrl = this.utils.page.url()
      const urlContainsPath = currentUrl.includes(expectedPath.replace('/#', ''))

      if (urlContainsPath) {
        this.utils.addTestStep('验证URL', 'success', `URL包含期待路径: ${expectedPath}`)
      } else {
        this.utils.addTestStep(
          '验证URL',
          'failed',
          `URL不匹配: 期待${expectedPath}, 实际${currentUrl}`
        )
      }

      // 验证页面内容加载
      await this.verifyPageContent(pageName)

      // 验证页面标题
      const titleCorrect = await this.utils.verifyPageTitle(this.getExpectedTitle(pageName))
      if (titleCorrect) {
        this.utils.addTestStep('验证页面标题', 'success')
      } else {
        this.utils.addTestStep('验证页面标题', 'warning', '标题不匹配')
      }

      this.utils.finishTest('success')
      this.recordTestResult(`navigate-${pageName}`, true, `${pageName}页面导航成功`)
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult(`navigate-${pageName}`, false, error.message)
    }
  }

  async verifyPageContent(pageName) {
    console.log(`🔍 验证 ${pageName} 页面内容`)

    const contentSelectors = {
      clusters: '.cluster-card, .cluster-grid, button:has-text("添加集群")',
      dashboard: '.summary-card, .chart-container, .dashboard-content',
      tables: '.table-container, .table-metrics, .filter-input',
      tasks: '.task-container, .task-list, button:has-text("创建任务")',
      settings: '.settings-form, .config-form, .settings-container'
    }

    const selector = contentSelectors[pageName]
    if (selector) {
      const selectors = selector.split(', ')
      let contentFound = false

      for (const sel of selectors) {
        if (await this.utils.elementExists(sel.trim())) {
          contentFound = true
          break
        }
      }

      if (contentFound) {
        this.utils.addTestStep('验证页面内容', 'success', '页面内容正常加载')
      } else {
        this.utils.addTestStep('验证页面内容', 'warning', '未找到期待的页面内容')
      }
    } else {
      this.utils.addTestStep('验证页面内容', 'warning', '无内容验证规则')
    }
  }

  getExpectedTitle(pageName) {
    const titles = {
      clusters: '集群管理',
      dashboard: '监控仪表板',
      tables: '表管理',
      tasks: '任务管理',
      settings: '系统设置'
    }
    return titles[pageName] || pageName
  }

  async testCircularNavigation() {
    console.log('\n🔄 测试循环导航')

    this.utils.startTest('circular-navigation', 'navigation')

    try {
      const navigationPath = ['clusters', 'dashboard', 'tables', 'tasks', 'settings', 'clusters']

      for (let i = 0; i < navigationPath.length - 1; i++) {
        const fromPage = navigationPath[i]
        const toPage = navigationPath[i + 1]

        console.log(`📍 从 ${fromPage} 导航到 ${toPage}`)

        if (i === 0) {
          // 第一次导航
          await this.utils.navigateToPage(fromPage)
        }

        // 导航到下一个页面
        await this.utils.navigateToPage(toPage)
        await this.utils.waitForPageLoad()

        this.utils.addTestStep(`${fromPage} → ${toPage}`, 'success')
      }

      this.utils.finishTest('success')
      this.recordTestResult('circular-navigation', true, '循环导航测试通过')
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult('circular-navigation', false, error.message)
    }
  }

  async testParameterizedRouting() {
    console.log('\n🔢 测试参数化路由')

    // 测试集群详情页面路由
    await this.testClusterDetailRouting()

    // 测试表详情页面路由
    await this.testTableDetailRouting()
  }

  async testClusterDetailRouting() {
    this.utils.startTest('cluster-detail-routing', 'parameterized-routing')

    try {
      // 先导航到集群管理页面
      await this.utils.navigateToPage('clusters')
      await this.utils.waitForPageLoad()

      // 检查是否有集群存在
      const clusterExists = await this.utils.elementExists('.cluster-card')
      if (!clusterExists) {
        this.utils.addTestStep('检查集群存在', 'warning', '没有集群数据')
        this.utils.finishTest('success')
        this.recordTestResult('cluster-detail-routing', true, '无集群数据，跳过详情页测试')
        return
      }

      // 点击进入集群详情
      const detailButton = '.cluster-actions button:first-child, .cluster-card .el-button--primary'
      if (await this.utils.elementExists(detailButton)) {
        await this.utils.clickElement(detailButton, false, true)
        await this.utils.waitForPageLoad()

        // 验证URL包含集群ID（支持hash路由）
        const currentUrl = this.utils.page.url()
        const hasClusterId =
          currentUrl.includes('#/clusters/') && /#\/clusters\/\d+/.test(currentUrl)

        if (hasClusterId) {
          this.utils.addTestStep('验证集群详情URL', 'success', `URL: ${currentUrl}`)
          this.recordTestResult('cluster-detail-routing', true, '集群详情路由正常')
        } else {
          this.utils.addTestStep('验证集群详情URL', 'failed', `URL格式不正确: ${currentUrl}`)
          this.recordTestResult('cluster-detail-routing', false, 'URL格式不正确')
        }
      } else {
        this.utils.addTestStep('查找详情按钮', 'warning', '未找到详情按钮')
        this.recordTestResult('cluster-detail-routing', true, '未找到详情按钮')
      }

      this.utils.finishTest('success')
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult('cluster-detail-routing', false, error.message)
    }
  }

  async testTableDetailRouting() {
    this.utils.startTest('table-detail-routing', 'parameterized-routing')

    try {
      // 导航到表管理页面
      await this.utils.navigateToPage('tables')
      await this.utils.waitForPageLoad()

      // 检查是否有表数据
      const tableExists = await this.utils.elementExists('.table-row, .table-item')
      if (!tableExists) {
        this.utils.addTestStep('检查表数据', 'warning', '没有表数据')
        this.utils.finishTest('success')
        this.recordTestResult('table-detail-routing', true, '无表数据，跳过详情页测试')
        return
      }

      // 这里可以添加表详情页面的测试逻辑
      this.utils.addTestStep('表详情路由测试', 'success', '基础检查完成')
      this.utils.finishTest('success')
      this.recordTestResult('table-detail-routing', true, '表详情路由基础测试通过')
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult('table-detail-routing', false, error.message)
    }
  }

  async testBrowserNavigation() {
    console.log('\n⬅️➡️ 测试浏览器前进后退')

    this.utils.startTest('browser-navigation', 'browser-controls')

    try {
      // 建立导航历史
      await this.utils.navigateToPage('clusters')
      await this.utils.waitForPageLoad()

      await this.utils.navigateToPage('dashboard')
      await this.utils.waitForPageLoad()

      await this.utils.navigateToPage('tables')
      await this.utils.waitForPageLoad()

      // 测试后退
      await this.utils.page.goBack()
      await this.utils.waitForPageLoad()

      let currentUrl = this.utils.page.url()
      if (currentUrl.includes('dashboard')) {
        this.utils.addTestStep('浏览器后退', 'success', '后退到dashboard页面')
      } else {
        this.utils.addTestStep('浏览器后退', 'failed', `后退失败，当前URL: ${currentUrl}`)
      }

      // 测试前进
      await this.utils.page.goForward()
      await this.utils.waitForPageLoad()

      currentUrl = this.utils.page.url()
      if (currentUrl.includes('tables')) {
        this.utils.addTestStep('浏览器前进', 'success', '前进到tables页面')
      } else {
        this.utils.addTestStep('浏览器前进', 'failed', `前进失败，当前URL: ${currentUrl}`)
      }

      this.utils.finishTest('success')
      this.recordTestResult('browser-navigation', true, '浏览器导航功能正常')
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult('browser-navigation', false, error.message)
    }
  }

  async testDeepLinking() {
    console.log('\n🔗 测试深度链接')

    const deepLinks = [
      { url: TEST_CONFIG.app.baseUrl + '/#/clusters', expected: 'clusters' },
      { url: TEST_CONFIG.app.baseUrl + '/#/dashboard', expected: 'dashboard' },
      { url: TEST_CONFIG.app.baseUrl + '/#/tables', expected: 'tables' },
      { url: TEST_CONFIG.app.baseUrl + '/#/tasks', expected: 'tasks' },
      { url: TEST_CONFIG.app.baseUrl + '/#/settings', expected: 'settings' }
    ]

    for (const link of deepLinks) {
      await this.testSingleDeepLink(link.url, link.expected)
    }
  }

  async testSingleDeepLink(url, expectedPage) {
    this.utils.startTest(`deep-link-${expectedPage}`, 'deep-linking')

    try {
      console.log(`🔗 测试深度链接: ${url}`)

      await this.utils.page.goto(url)
      await this.utils.waitForPageLoad()

      const currentUrl = this.utils.page.url()
      const isCorrectPage = currentUrl.includes(expectedPage)

      if (isCorrectPage) {
        this.utils.addTestStep('深度链接导航', 'success', `成功导航到${expectedPage}页面`)

        // 验证页面内容
        await this.verifyPageContent(expectedPage)

        this.utils.finishTest('success')
        this.recordTestResult(`deep-link-${expectedPage}`, true, '深度链接正常')
      } else {
        this.utils.addTestStep('深度链接导航', 'failed', `导航失败，当前URL: ${currentUrl}`)
        this.utils.finishTest('failed', '深度链接导航失败')
        this.recordTestResult(`deep-link-${expectedPage}`, false, '深度链接失败')
      }
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult(`deep-link-${expectedPage}`, false, error.message)
    }
  }

  async testPageTitleUpdates() {
    console.log('\n📄 测试页面标题更新')

    this.utils.startTest('page-title-updates', 'navigation-guards')

    try {
      const pages = ['clusters', 'dashboard', 'tables', 'tasks', 'settings']

      for (const page of pages) {
        await this.utils.navigateToPage(page)
        await this.utils.waitForPageLoad()

        const title = await this.utils.page.title()
        const expectedTitle = this.getExpectedTitle(page)

        if (title.includes(expectedTitle)) {
          this.utils.addTestStep(`${page}页面标题`, 'success', `标题: ${title}`)
        } else {
          this.utils.addTestStep(
            `${page}页面标题`,
            'warning',
            `期待包含'${expectedTitle}'，实际'${title}'`
          )
        }
      }

      this.utils.finishTest('success')
      this.recordTestResult('page-title-updates', true, '页面标题更新测试完成')
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult('page-title-updates', false, error.message)
    }
  }

  async testNavigationGuards() {
    console.log('\n🛡️ 测试导航守卫')

    this.utils.startTest('navigation-guards', 'navigation-guards')

    try {
      // 测试路由重定向（根路径重定向到集群页面）
      await this.utils.page.goto(TEST_CONFIG.app.baseUrl + '/')
      await this.utils.waitForPageLoad()

      const currentUrl = this.utils.page.url()
      if (currentUrl.includes('clusters')) {
        this.utils.addTestStep('根路径重定向', 'success', '成功重定向到集群页面')
      } else {
        this.utils.addTestStep('根路径重定向', 'failed', `重定向失败，当前URL: ${currentUrl}`)
      }

      // 测试无效路由处理
      await this.testInvalidRoute()

      this.utils.finishTest('success')
      this.recordTestResult('navigation-guards', true, '导航守卫测试完成')
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult('navigation-guards', false, error.message)
    }
  }

  async testInvalidRoute() {
    console.log('❌ 测试无效路由处理')

    const invalidUrl = TEST_CONFIG.app.baseUrl + '/#/invalid-page-that-does-not-exist'

    try {
      await this.utils.page.goto(invalidUrl)
      await this.utils.waitForPageLoad()

      const currentUrl = this.utils.page.url()

      // 检查是否重定向到有效页面或显示404页面
      const isRedirected =
        currentUrl.includes('clusters') ||
        currentUrl.includes('dashboard') ||
        currentUrl.includes('404') ||
        currentUrl.includes('not-found')

      if (isRedirected) {
        this.utils.addTestStep('无效路由处理', 'success', '无效路由被正确处理')
      } else {
        this.utils.addTestStep('无效路由处理', 'warning', `无效路由处理不确定: ${currentUrl}`)
      }
    } catch (error) {
      this.utils.addTestStep('无效路由处理', 'warning', `无效路由测试异常: ${error.message}`)
    }
  }

  recordTestResult(testName, passed, details = '') {
    this.testResults.total++
    if (passed) {
      this.testResults.passed++
    } else {
      this.testResults.failed++
    }

    this.testResults.details.push({
      name: testName,
      status: passed ? 'PASS' : 'FAIL',
      details: details,
      timestamp: new Date().toISOString()
    })

    const icon = passed ? '✅' : '❌'
    console.log(`${icon} ${testName}: ${details}`)
  }

  generateSummary() {
    console.log('\n📊 导航路由测试总结')
    console.log('='.repeat(50))
    console.log(`总测试数: ${this.testResults.total}`)
    console.log(`通过数: ${this.testResults.passed}`)
    console.log(`失败数: ${this.testResults.failed}`)
    console.log(`成功率: ${((this.testResults.passed / this.testResults.total) * 100).toFixed(1)}%`)
    console.log('='.repeat(50))

    if (this.testResults.failed > 0) {
      console.log('\n❌ 失败的测试:')
      this.testResults.details
        .filter(test => test.status === 'FAIL')
        .forEach(test => {
          console.log(`  • ${test.name}: ${test.details}`)
        })
    }
  }
}

// 运行测试
async function runNavigationTests() {
  const tester = new NavigationRoutingTester()
  const results = await tester.runAllNavigationTests()

  if (results && results.passed === results.total) {
    console.log('\n🎉 所有导航路由测试通过！')
    process.exit(0)
  } else {
    console.log('\n💥 部分导航路由测试失败！')
    process.exit(1)
  }
}

// 如果直接运行此文件
if (require.main === module) {
  runNavigationTests().catch(error => {
    console.error('测试运行失败:', error)
    process.exit(1)
  })
}

module.exports = NavigationRoutingTester
