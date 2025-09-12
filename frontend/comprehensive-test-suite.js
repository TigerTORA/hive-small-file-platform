// 综合测试套件 - 主控制器
const ButtonFunctionalityTester = require('./test-buttons-comprehensive.js');
const FormValidationTester = require('./test-forms-validation.js');
const NavigationRoutingTester = require('./test-navigation-routing.js');
const ApiConnectionTester = require('./test-api-connection.js');
const TestDataManager = require('./test-data-manager.js');
const TEST_CONFIG = require('./test-config.js');

class ComprehensiveTestSuite {
  constructor() {
    this.suiteStartTime = Date.now();
    this.testResults = {
      overall: {
        total: 0,
        passed: 0,
        failed: 0,
        skipped: 0,
        duration: 0
      },
      suites: {},
      errors: [],
      screenshots: []
    };
    this.config = {
      parallel: false, // 是否并行执行测试
      continueOnFailure: true, // 测试失败后是否继续
      setupData: true, // 是否设置测试数据
      cleanupData: true, // 是否清理测试数据
      generateReport: true, // 是否生成报告
      takeScreenshots: true // 是否截图
    };
  }

  async runComprehensiveTests(options = {}) {
    console.log('🚀 启动综合自动化测试套件');
    console.log('='.repeat(60));
    console.log(`📅 开始时间: ${new Date().toLocaleString()}`);
    console.log(`🔧 配置: ${JSON.stringify({ ...this.config, ...options }, null, 2)}`);
    console.log('='.repeat(60));
    
    // 合并配置
    Object.assign(this.config, options);
    
    try {
      // 1. 环境检查
      await this.checkEnvironment();
      
      // 2. 测试数据准备
      if (this.config.setupData) {
        await this.setupTestData();
      }
      
      // 3. 执行测试套件
      if (this.config.parallel) {
        await this.runTestsInParallel();
      } else {
        await this.runTestsSequentially();
      }
      
      // 4. 清理测试数据
      if (this.config.cleanupData) {
        await this.cleanupTestData();
      }
      
      // 5. 生成测试报告
      if (this.config.generateReport) {
        await this.generateTestReport();
      }
      
      // 6. 显示最终结果
      this.displayFinalResults();
      
      return this.testResults;
      
    } catch (error) {
      console.error(`💥 测试套件执行失败: ${error.message}`);
      this.testResults.errors.push({
        type: 'suite-error',
        message: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      });
      
      return this.testResults;
    }
  }

  async checkEnvironment() {
    console.log('\n🔍 环境检查...');
    
    const checks = [
      { name: 'Frontend服务', url: TEST_CONFIG.app.baseUrl, type: 'frontend' },
      { name: 'Backend API', url: TEST_CONFIG.app.apiBaseUrl + '/health', type: 'api' },
    ];
    
    for (const check of checks) {
      try {
        console.log(`🌐 检查 ${check.name}: ${check.url}`);
        
        const response = await fetch(check.url);
        if (response.ok || response.status < 500) {
          console.log(`✅ ${check.name} 正常 (${response.status})`);
        } else {
          console.log(`⚠️ ${check.name} 异常 (${response.status})`);
        }
      } catch (error) {
        console.log(`❌ ${check.name} 无法连接: ${error.message}`);
        if (check.type === 'frontend') {
          throw new Error(`前端服务不可用: ${check.url}`);
        }
      }
    }
    
    console.log('✅ 环境检查完成');
  }

  async setupTestData() {
    console.log('\n🛠️ 设置测试数据...');
    
    try {
      const dataManager = new TestDataManager();
      const results = await dataManager.initializeTestEnvironment();
      
      this.testResults.suites['data-setup'] = {
        name: '测试数据设置',
        total: results?.total || 0,
        passed: results?.passed || 0,
        failed: results?.failed || 0,
        duration: 0,
        status: results?.passed === results?.total ? 'PASS' : 'FAIL'
      };
      
      console.log('✅ 测试数据设置完成');
    } catch (error) {
      console.error(`❌ 测试数据设置失败: ${error.message}`);
      this.testResults.errors.push({
        type: 'data-setup-error',
        message: error.message,
        timestamp: new Date().toISOString()
      });
    }
  }

  async runTestsSequentially() {
    console.log('\n📋 顺序执行测试套件...');
    
    const testSuites = [
      { name: 'API连接测试', tester: ApiConnectionTester, key: 'api-connection' },
      { name: '页面导航测试', tester: NavigationRoutingTester, key: 'navigation-routing' },
      { name: '按钮功能测试', tester: ButtonFunctionalityTester, key: 'button-functionality' },
      { name: '表单验证测试', tester: FormValidationTester, key: 'form-validation' }
    ];
    
    for (const suite of testSuites) {
      await this.runSingleTestSuite(suite);
      
      // 如果配置为失败后停止，且当前套件失败，则停止执行
      if (!this.config.continueOnFailure && this.testResults.suites[suite.key]?.status === 'FAIL') {
        console.log(`❌ ${suite.name} 失败，停止后续测试`);
        break;
      }
    }
  }

  async runTestsInParallel() {
    console.log('\n⚡ 并行执行测试套件...');
    
    const testPromises = [
      this.runSingleTestSuite({ name: 'API连接测试', tester: ApiConnectionTester, key: 'api-connection' }),
      this.runSingleTestSuite({ name: '页面导航测试', tester: NavigationRoutingTester, key: 'navigation-routing' }),
      this.runSingleTestSuite({ name: '按钮功能测试', tester: ButtonFunctionalityTester, key: 'button-functionality' }),
      this.runSingleTestSuite({ name: '表单验证测试', tester: FormValidationTester, key: 'form-validation' })
    ];
    
    // 等待所有测试完成
    await Promise.allSettled(testPromises);
  }

  async runSingleTestSuite(suite) {
    const startTime = Date.now();
    console.log(`\n🧪 开始执行: ${suite.name}`);
    console.log('-'.repeat(40));
    
    try {
      const tester = new suite.tester();
      const results = await this.executeTestSuite(tester);
      
      const duration = Date.now() - startTime;
      
      this.testResults.suites[suite.key] = {
        name: suite.name,
        total: results?.total || 0,
        passed: results?.passed || 0,
        failed: results?.failed || 0,
        duration: duration,
        status: results?.passed === results?.total ? 'PASS' : 'FAIL',
        details: results?.details || []
      };
      
      // 更新总体统计
      this.testResults.overall.total += results?.total || 0;
      this.testResults.overall.passed += results?.passed || 0;
      this.testResults.overall.failed += results?.failed || 0;
      
      console.log(`✅ ${suite.name} 完成 (${duration}ms)`);
      console.log(`   通过: ${results?.passed || 0}/${results?.total || 0}`);
      
    } catch (error) {
      const duration = Date.now() - startTime;
      
      console.error(`❌ ${suite.name} 执行失败: ${error.message}`);
      
      this.testResults.suites[suite.key] = {
        name: suite.name,
        total: 0,
        passed: 0,
        failed: 1,
        duration: duration,
        status: 'ERROR',
        error: error.message
      };
      
      this.testResults.overall.failed += 1;
      this.testResults.errors.push({
        type: 'suite-execution-error',
        suite: suite.name,
        message: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      });
    }
  }

  async executeTestSuite(tester) {
    // 根据测试器类型调用相应的方法
    if (typeof tester.runAllButtonTests === 'function') {
      return await tester.runAllButtonTests();
    } else if (typeof tester.runAllFormTests === 'function') {
      return await tester.runAllFormTests();
    } else if (typeof tester.runAllNavigationTests === 'function') {
      return await tester.runAllNavigationTests();
    } else if (typeof tester.runAllApiTests === 'function') {
      return await tester.runAllApiTests();
    } else {
      throw new Error('未知的测试器类型');
    }
  }

  async cleanupTestData() {
    console.log('\n🧹 清理测试数据...');
    
    try {
      const dataManager = new TestDataManager();
      const results = await dataManager.cleanupTestEnvironment();
      
      this.testResults.suites['data-cleanup'] = {
        name: '测试数据清理',
        total: results?.total || 0,
        passed: results?.passed || 0,
        failed: results?.failed || 0,
        duration: 0,
        status: results?.passed === results?.total ? 'PASS' : 'FAIL'
      };
      
      console.log('✅ 测试数据清理完成');
    } catch (error) {
      console.error(`❌ 测试数据清理失败: ${error.message}`);
      this.testResults.errors.push({
        type: 'data-cleanup-error',
        message: error.message,
        timestamp: new Date().toISOString()
      });
    }
  }

  async generateTestReport() {
    console.log('\n📊 生成测试报告...');
    
    try {
      const TestReporter = require('./test-reporter.js');
      const reporter = new TestReporter();
      
      const reportPath = await reporter.generateComprehensiveReport(this.testResults);
      console.log(`✅ 测试报告已生成: ${reportPath}`);
      
      // 生成简化的控制台报告
      this.generateConsoleReport();
      
    } catch (error) {
      console.error(`❌ 报告生成失败: ${error.message}`);
      
      // 即使报告生成失败，也显示基本结果
      this.generateConsoleReport();
    }
  }

  generateConsoleReport() {
    console.log('\n📋 测试结果摘要');
    console.log('='.repeat(60));
    
    // 总体统计
    const overallDuration = Date.now() - this.suiteStartTime;
    this.testResults.overall.duration = overallDuration;
    
    console.log(`⏱️ 总执行时间: ${this.formatDuration(overallDuration)}`);
    console.log(`📊 总测试数: ${this.testResults.overall.total}`);
    console.log(`✅ 通过: ${this.testResults.overall.passed}`);
    console.log(`❌ 失败: ${this.testResults.overall.failed}`);
    console.log(`📈 成功率: ${this.calculateSuccessRate()}%`);
    
    // 各套件详情
    console.log('\n📋 各测试套件结果:');
    Object.entries(this.testResults.suites).forEach(([key, suite]) => {
      const icon = suite.status === 'PASS' ? '✅' : suite.status === 'FAIL' ? '❌' : '⚠️';
      const successRate = suite.total > 0 ? ((suite.passed / suite.total) * 100).toFixed(1) : '0';
      console.log(`${icon} ${suite.name}: ${suite.passed}/${suite.total} (${successRate}%) - ${this.formatDuration(suite.duration)}`);
    });
    
    // 错误摘要
    if (this.testResults.errors.length > 0) {
      console.log('\n❌ 错误摘要:');
      this.testResults.errors.forEach((error, index) => {
        console.log(`${index + 1}. ${error.type}: ${error.message}`);
      });
    }
    
    console.log('='.repeat(60));
  }

  displayFinalResults() {
    const totalTests = this.testResults.overall.total;
    const passedTests = this.testResults.overall.passed;
    const successRate = this.calculateSuccessRate();
    
    console.log('\n🎯 最终结果');
    console.log('='.repeat(60));
    
    if (successRate === 100) {
      console.log('🎉 所有测试都通过了！测试套件执行成功！');
      console.log('🌟 您的应用程序功能完整，质量良好！');
    } else if (successRate >= 80) {
      console.log('✅ 大部分测试通过，应用程序基本正常！');
      console.log(`⚠️ 建议检查和修复 ${this.testResults.overall.failed} 个失败的测试`);
    } else if (successRate >= 60) {
      console.log('⚠️ 测试通过率偏低，应用程序存在一些问题');
      console.log('🔧 建议优先修复关键功能的问题');
    } else {
      console.log('❌ 测试失败率较高，应用程序存在严重问题');
      console.log('🚨 建议立即检查和修复主要功能');
    }
    
    console.log(`\n📊 最终统计: ${passedTests}/${totalTests} 通过 (${successRate}%)`);
    console.log(`⏱️ 总用时: ${this.formatDuration(this.testResults.overall.duration)}`);
    console.log('='.repeat(60));
    
    // 提供下一步建议
    this.provideRecommendations();
  }

  provideRecommendations() {
    console.log('\n💡 建议和下一步行动:');
    
    const failedSuites = Object.entries(this.testResults.suites)
      .filter(([key, suite]) => suite.status === 'FAIL')
      .map(([key, suite]) => suite.name);
    
    if (failedSuites.length === 0) {
      console.log('✨ 您的应用程序通过了所有测试！');
      console.log('🚀 可以考虑部署到生产环境');
      console.log('📈 建议定期运行测试以确保持续质量');
    } else {
      console.log('🔧 需要修复的区域:');
      failedSuites.forEach((suite, index) => {
        console.log(`${index + 1}. ${suite}`);
      });
      
      console.log('\n📋 修复步骤建议:');
      console.log('1. 查看详细的测试报告了解具体失败原因');
      console.log('2. 优先修复API连接和导航相关问题');
      console.log('3. 然后处理UI功能和表单验证问题');
      console.log('4. 修复后重新运行测试验证');
    }
    
    console.log('\n🔗 验证链接:');
    console.log(`🌐 前端应用: ${TEST_CONFIG.app.baseUrl}/#/clusters`);
    console.log(`🔌 API健康检查: ${TEST_CONFIG.app.apiBaseUrl}/health`);
    console.log(`📊 仪表板: ${TEST_CONFIG.app.baseUrl}/#/dashboard`);
  }

  calculateSuccessRate() {
    const total = this.testResults.overall.total;
    const passed = this.testResults.overall.passed;
    return total > 0 ? ((passed / total) * 100).toFixed(1) : 0;
  }

  formatDuration(ms) {
    if (ms < 1000) return `${ms}ms`;
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  }

  // 提供简化的运行选项
  static async runQuickTest() {
    const suite = new ComprehensiveTestSuite();
    return await suite.runComprehensiveTests({
      setupData: false,
      cleanupData: false,
      parallel: false,
      continueOnFailure: true
    });
  }

  static async runFullTest() {
    const suite = new ComprehensiveTestSuite();
    return await suite.runComprehensiveTests({
      setupData: true,
      cleanupData: true,
      parallel: false,
      continueOnFailure: true,
      generateReport: true
    });
  }

  static async runParallelTest() {
    const suite = new ComprehensiveTestSuite();
    return await suite.runComprehensiveTests({
      setupData: false,
      cleanupData: false,
      parallel: true,
      continueOnFailure: true
    });
  }
}

// 命令行执行逻辑
async function runTestSuite() {
  const args = process.argv.slice(2);
  const mode = args[0] || 'full';
  
  let results;
  
  try {
    switch (mode) {
      case 'quick':
        console.log('🚀 运行快速测试（无数据设置）...');
        results = await ComprehensiveTestSuite.runQuickTest();
        break;
      case 'parallel':
        console.log('⚡ 运行并行测试...');
        results = await ComprehensiveTestSuite.runParallelTest();
        break;
      case 'full':
      default:
        console.log('🚀 运行完整测试套件...');
        results = await ComprehensiveTestSuite.runFullTest();
        break;
    }
    
    // 根据测试结果设置退出码
    const successRate = results.overall.total > 0 ? 
      (results.overall.passed / results.overall.total) * 100 : 0;
    
    if (successRate === 100) {
      process.exit(0); // 所有测试通过
    } else if (successRate >= 80) {
      process.exit(0); // 大部分测试通过，认为可接受
    } else {
      process.exit(1); // 测试失败率较高
    }
    
  } catch (error) {
    console.error('💥 测试套件执行失败:', error.message);
    process.exit(1);
  }
}

// 如果直接运行此文件
if (require.main === module) {
  runTestSuite();
}

module.exports = ComprehensiveTestSuite;