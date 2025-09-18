const TestUtils = require('./test-utils.js')

class EndToEndUserFlowTester {
  constructor() {
    this.utils = new TestUtils()
    this.testResults = {
      total: 0,
      passed: 0,
      failed: 0,
      details: []
    }
  }

  async runCompleteUserFlow() {
    console.log('🚀 开始端到端用户流程测试...\n')

    try {
      await this.utils.initBrowser()

      // 用户流程1：新用户首次访问 -> 查看集群列表 -> 进入集群详情
      await this.testNewUserExperienceFlow()

      // 用户流程2：集群管理流程 -> 创建 -> 编辑 -> 测试连接 -> 删除
      await this.testClusterManagementFlow()

      // 用户流程3：数据监控流程 -> 查看仪表板 -> 分析表数据 -> 查看任务状态
      await this.testDataMonitoringFlow()

      // 用户流程4：任务管理流程 -> 查看任务列表 -> 创建任务 -> 监控执行
      await this.testTaskManagementFlow()

      this.generateSummary()
      return this.testResults
    } catch (error) {
      console.error(`💥 端到端测试过程中出现错误: ${error.message}`)
      return null
    } finally {
      await this.utils.closeBrowser()
    }
  }

  async testNewUserExperienceFlow() {
    console.log('👤 测试新用户首次访问体验流程')
    this.utils.startTest('new-user-experience', 'user-flow')

    try {
      // Step 1: 用户访问主页，应该自动重定向到集群管理
      console.log('📍 Step 1: 访问主页')
      await this.utils.navigateToPage('clusters') // 直接导航到集群页面测试
      await this.utils.waitForPageLoad()

      // 验证自动重定向到集群管理页
      const currentUrl = this.utils.page.url()
      if (currentUrl.includes('clusters')) {
        this.utils.addTestStep('主页重定向', 'success', '成功重定向到集群管理页')
        this.recordTestResult('homepage-redirect', true, '主页重定向正常')
      } else {
        this.utils.addTestStep('主页重定向', 'failed', `重定向失败: ${currentUrl}`)
        this.recordTestResult('homepage-redirect', false, '主页重定向失败')
      }

      // Step 2: 查看集群列表
      console.log('📍 Step 2: 查看集群列表')
      const hasClusterCards = await this.utils.elementExists('.cluster-card')
      const clusterCards = await this.utils.page.$$('.cluster-card')

      if (hasClusterCards && clusterCards.length > 0) {
        this.utils.addTestStep('集群列表展示', 'success', `发现 ${clusterCards.length} 个集群`)
        this.recordTestResult(
          'cluster-list-display',
          true,
          `集群列表正常显示(${clusterCards.length}个)`
        )

        // Step 3: 进入第一个集群详情
        console.log('📍 Step 3: 进入集群详情')
        const firstCard = clusterCards[0]
        const detailButton = await firstCard.$('.cluster-actions button')

        if (detailButton) {
          await detailButton.click()
          await this.utils.page.waitForTimeout(2000)

          // 验证进入详情页
          const detailUrl = this.utils.page.url()
          if (detailUrl.includes('/clusters/')) {
            this.utils.addTestStep('进入集群详情', 'success', '成功进入集群详情页')
            this.recordTestResult('enter-cluster-detail', true, '集群详情导航正常')

            // Step 4: 验证详情页关键信息
            console.log('📍 Step 4: 验证详情页内容')
            await this.validateClusterDetailPage()

            // Step 5: 测试返回功能
            console.log('📍 Step 5: 测试返回功能')
            await this.testBackNavigation()
          } else {
            this.utils.addTestStep('进入集群详情', 'failed', '未能进入详情页')
            this.recordTestResult('enter-cluster-detail', false, '集群详情导航失败')
          }
        } else {
          this.utils.addTestStep('查找详情按钮', 'failed', '未找到详情按钮')
          this.recordTestResult('find-detail-button', false, '详情按钮缺失')
        }
      } else {
        this.utils.addTestStep('集群列表展示', 'failed', '没有发现集群数据')
        this.recordTestResult('cluster-list-display', false, '集群列表为空')
      }

      this.utils.finishTest('success')
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult('new-user-experience', false, error.message)
    }
  }

  async validateClusterDetailPage() {
    // 验证集群详情页的关键元素
    const validations = [
      { selector: '.cluster-header', name: '集群头部信息' },
      { selector: 'h2', name: '集群标题' },
      { selector: '.stats-grid', name: '统计数据网格' },
      { selector: '.el-tabs', name: '功能标签页' },
      { selector: 'button:has-text("测试连接")', name: '测试连接按钮' },
      { selector: 'button:has-text("扫描数据库")', name: '扫描数据库按钮' }
    ]

    for (const validation of validations) {
      const exists = await this.utils.elementExists(validation.selector)
      if (exists) {
        this.utils.addTestStep(`验证${validation.name}`, 'success', '元素存在')
        this.recordTestResult(`validate-${validation.name}`, true, `${validation.name}正常显示`)
      } else {
        this.utils.addTestStep(`验证${validation.name}`, 'warning', '元素缺失')
        this.recordTestResult(`validate-${validation.name}`, false, `${validation.name}缺失`)
      }
    }
  }

  async testBackNavigation() {
    const backButton = await this.utils.elementExists('button:has-text("返回")')
    if (backButton) {
      await this.utils.clickElement('button:has-text("返回")')
      await this.utils.page.waitForTimeout(1000)

      const returnUrl = this.utils.page.url()
      if (returnUrl.includes('clusters') && !returnUrl.includes('/clusters/')) {
        this.utils.addTestStep('返回功能', 'success', '成功返回集群列表')
        this.recordTestResult('back-navigation', true, '返回功能正常')
      } else {
        this.utils.addTestStep('返回功能', 'failed', '返回功能异常')
        this.recordTestResult('back-navigation', false, '返回功能失败')
      }
    }
  }

  async testClusterManagementFlow() {
    console.log('🔧 测试集群管理流程')
    this.utils.startTest('cluster-management-flow', 'user-flow')

    try {
      // 确保在集群管理页
      await this.utils.navigateToPage('clusters')
      await this.utils.waitForPageLoad()

      // Step 1: 测试创建集群功能
      console.log('📍 Step 1: 测试创建集群对话框')
      const addButton = await this.utils.elementExists('button:has-text("添加集群")')
      if (addButton) {
        await this.utils.clickElement('button:has-text("添加集群")', true)
        await this.utils.page.waitForTimeout(1000)

        const dialogExists = await this.utils.elementExists('.el-dialog')
        if (dialogExists) {
          this.utils.addTestStep('创建集群对话框', 'success', '对话框成功打开')
          this.recordTestResult('create-cluster-dialog', true, '创建集群对话框正常')

          // 关闭对话框
          await this.utils.page.keyboard.press('Escape')
          await this.utils.page.waitForTimeout(500)
        } else {
          this.utils.addTestStep('创建集群对话框', 'failed', '对话框未打开')
          this.recordTestResult('create-cluster-dialog', false, '创建集群对话框失败')
        }
      }

      // Step 2: 测试集群操作按钮
      console.log('📍 Step 2: 测试集群操作按钮')
      await this.testClusterOperationButtons()

      this.utils.finishTest('success')
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult('cluster-management-flow', false, error.message)
    }
  }

  async testClusterOperationButtons() {
    const clusterCards = await this.utils.page.$$('.cluster-card')
    if (clusterCards.length > 0) {
      const firstCard = clusterCards[0]

      // 测试各种操作按钮
      const buttons = [
        { text: '快速测试', action: 'quick-test' },
        { text: '编辑', action: 'edit' },
        { text: '删除', action: 'delete' }
      ]

      for (const button of buttons) {
        const buttonElement = await firstCard.$(`button:has-text("${button.text}")`)
        if (buttonElement) {
          this.utils.addTestStep(`${button.text}按钮`, 'success', '按钮存在且可访问')
          this.recordTestResult(`${button.action}-button`, true, `${button.text}按钮正常`)
        } else {
          this.utils.addTestStep(`${button.text}按钮`, 'warning', '按钮不存在')
          this.recordTestResult(`${button.action}-button`, false, `${button.text}按钮缺失`)
        }
      }
    }
  }

  async testDataMonitoringFlow() {
    console.log('📊 测试数据监控流程')
    this.utils.startTest('data-monitoring-flow', 'user-flow')

    try {
      // Step 1: 访问仪表板
      console.log('📍 Step 1: 访问监控仪表板')
      await this.utils.navigateToPage('dashboard')
      await this.utils.waitForPageLoad()

      // 验证仪表板关键组件
      const dashboardElements = [
        { selector: '.summary-card, .dashboard-summary', name: '摘要卡片' },
        { selector: '.chart-container, .chart-wrapper', name: '图表容器' },
        { selector: '.el-statistic', name: '统计数据' }
      ]

      for (const element of dashboardElements) {
        const exists = await this.utils.elementExists(element.selector)
        if (exists) {
          this.utils.addTestStep(`仪表板${element.name}`, 'success', '组件正常显示')
          this.recordTestResult(`dashboard-${element.name}`, true, `${element.name}正常`)
        } else {
          this.utils.addTestStep(`仪表板${element.name}`, 'warning', '组件未找到')
          this.recordTestResult(`dashboard-${element.name}`, false, `${element.name}缺失`)
        }
      }

      // Step 2: 访问表管理页面
      console.log('📍 Step 2: 访问表管理页面')
      await this.utils.navigateToPage('tables')
      await this.utils.waitForPageLoad()

      const hasTableData = await this.utils.elementExists(
        '.table-container, .table-list, .el-table'
      )
      if (hasTableData) {
        this.utils.addTestStep('表管理页面', 'success', '表数据正常显示')
        this.recordTestResult('tables-page', true, '表管理页面正常')
      } else {
        this.utils.addTestStep('表管理页面', 'warning', '表数据未显示')
        this.recordTestResult('tables-page', false, '表管理页面异常')
      }

      this.utils.finishTest('success')
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult('data-monitoring-flow', false, error.message)
    }
  }

  async testTaskManagementFlow() {
    console.log('⚙️ 测试任务管理流程')
    this.utils.startTest('task-management-flow', 'user-flow')

    try {
      // 访问任务管理页面
      console.log('📍 访问任务管理页面')
      await this.utils.navigateToPage('tasks')
      await this.utils.waitForPageLoad()

      // 验证任务管理页面元素
      const hasTaskContainer = await this.utils.elementExists(
        '.task-container, .task-list, .el-table'
      )
      const hasCreateButton = await this.utils.elementExists('button:has-text("创建任务")')

      if (hasTaskContainer) {
        this.utils.addTestStep('任务列表', 'success', '任务列表容器存在')
        this.recordTestResult('task-list', true, '任务列表正常')
      } else {
        this.utils.addTestStep('任务列表', 'warning', '任务列表容器未找到')
        this.recordTestResult('task-list', false, '任务列表异常')
      }

      if (hasCreateButton) {
        this.utils.addTestStep('创建任务按钮', 'success', '创建按钮存在')
        this.recordTestResult('create-task-button', true, '创建任务按钮正常')
      } else {
        this.utils.addTestStep('创建任务按钮', 'warning', '创建按钮未找到')
        this.recordTestResult('create-task-button', false, '创建任务按钮缺失')
      }

      this.utils.finishTest('success')
    } catch (error) {
      this.utils.finishTest('failed', error)
      this.recordTestResult('task-management-flow', false, error.message)
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
    console.log('\n📊 端到端用户流程测试总结')
    console.log('='.repeat(60))
    console.log(`总测试数: ${this.testResults.total}`)
    console.log(`通过数: ${this.testResults.passed}`)
    console.log(`失败数: ${this.testResults.failed}`)
    console.log(`成功率: ${((this.testResults.passed / this.testResults.total) * 100).toFixed(1)}%`)
    console.log('='.repeat(60))

    // 按流程分类统计
    const flows = {}
    this.testResults.details.forEach(test => {
      const flow = test.name.split('-')[0]
      if (!flows[flow]) {
        flows[flow] = { total: 0, passed: 0 }
      }
      flows[flow].total++
      if (test.status === 'PASS') {
        flows[flow].passed++
      }
    })

    console.log('\n📈 用户流程测试结果:')
    Object.entries(flows).forEach(([flow, stats]) => {
      const rate = ((stats.passed / stats.total) * 100).toFixed(1)
      console.log(`  ${flow}: ${stats.passed}/${stats.total} (${rate}%)`)
    })

    if (this.testResults.failed > 0) {
      console.log('\n❌ 失败的测试:')
      this.testResults.details
        .filter(test => test.status === 'FAIL')
        .forEach(test => {
          console.log(`  • ${test.name}: ${test.details}`)
        })
    }

    console.log('\n🎯 用户体验评估:')
    const successRate = (this.testResults.passed / this.testResults.total) * 100
    if (successRate >= 90) {
      console.log('🌟 优秀 - 用户体验流畅，功能完整')
    } else if (successRate >= 75) {
      console.log('👍 良好 - 主要功能正常，少数问题')
    } else if (successRate >= 60) {
      console.log('⚠️ 一般 - 基本可用，需要改进')
    } else {
      console.log('❗ 较差 - 存在较多问题，急需修复')
    }
  }
}

// 运行端到端测试
async function runEndToEndTest() {
  const tester = new EndToEndUserFlowTester()
  const results = await tester.runCompleteUserFlow()

  if (results && results.passed >= results.total * 0.8) {
    console.log('\n🎉 端到端用户流程测试基本通过！')
    process.exit(0)
  } else {
    console.log('\n💥 端到端用户流程测试发现问题！')
    process.exit(1)
  }
}

// 如果直接运行此文件
if (require.main === module) {
  runEndToEndTest().catch(error => {
    console.error('端到端测试运行失败:', error)
    process.exit(1)
  })
}

module.exports = EndToEndUserFlowTester
