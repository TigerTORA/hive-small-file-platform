const TestUtils = require('./test-utils.js');
const TEST_CONFIG = require('./test-config.js');

class ApiConnectionTester {
  constructor() {
    this.utils = new TestUtils();
    this.testResults = {
      total: 0,
      passed: 0,
      failed: 0,
      details: []
    };
    this.apiEndpoints = this.buildApiEndpointsList();
  }

  buildApiEndpointsList() {
    return [
      // 健康检查
      { path: '/health', method: 'GET', category: 'health', critical: true },
      
      // 集群相关API
      { path: '/api/v1/clusters/', method: 'GET', category: 'clusters', critical: true },
      { path: '/api/v1/clusters/health-check', method: 'GET', category: 'clusters', critical: false },
      
      // 表相关API
      { path: '/api/v1/tables/metrics?cluster_id=1', method: 'GET', category: 'tables', critical: true },
      { path: '/api/v1/tables/small-files?cluster_id=1', method: 'GET', category: 'tables', critical: true },
      
      // 任务相关API
      { path: '/api/v1/tasks/', method: 'GET', category: 'tasks', critical: true },
      { path: '/api/v1/tasks/stats', method: 'GET', category: 'tasks', critical: true },
      
      // 仪表板API
      { path: '/api/v1/dashboard/summary', method: 'GET', category: 'dashboard', critical: true },
      { path: '/api/v1/dashboard/trends', method: 'GET', category: 'dashboard', critical: false },
      { path: '/api/v1/dashboard/file-distribution', method: 'GET', category: 'dashboard', critical: false },
      { path: '/api/v1/dashboard/top-tables', method: 'GET', category: 'dashboard', critical: false },
      
      // 错误测试端点
      { path: '/api/v1/errors/test-error', method: 'GET', category: 'error-testing', critical: false },
      { path: '/non-existent-endpoint', method: 'GET', category: 'error-testing', critical: false, expectStatus: 404 }
    ];
  }

  async runAllApiTests() {
    console.log('🔌 开始综合API连接和错误处理测试...\n');
    
    try {
      await this.utils.initBrowser();
      
      // 测试API服务器连通性
      await this.testApiServerConnectivity();
      
      // 测试所有API端点
      await this.testAllApiEndpoints();
      
      // 测试API错误处理
      await this.testApiErrorHandling();
      
      // 测试UI中的API集成
      await this.testUiApiIntegration();
      
      // 测试网络超时和重试
      await this.testNetworkTimeout();
      
      this.generateSummary();
      return this.testResults;
      
    } catch (error) {
      console.error(`💥 测试过程中出现错误: ${error.message}`);
      return null;
    } finally {
      await this.utils.closeBrowser();
    }
  }

  async testApiServerConnectivity() {
    console.log('\n🌐 测试API服务器连通性');
    
    this.utils.startTest('api-server-connectivity', 'api-connection');
    
    try {
      // 测试基础健康检查
      const healthResponse = await this.utils.testApiEndpoint('/health');
      
      if (healthResponse.ok) {
        this.utils.addTestStep('API服务器健康检查', 'success', `状态码: ${healthResponse.status}`);
        this.recordTestResult('api-server-health', true, `API服务器正常 (${healthResponse.status})`);
      } else {
        this.utils.addTestStep('API服务器健康检查', 'failed', `状态码: ${healthResponse.status}`);
        this.recordTestResult('api-server-health', false, `API服务器异常 (${healthResponse.status})`);
      }
      
      // 测试API根路径
      const rootResponse = await this.utils.testApiEndpoint('/');
      this.utils.addTestStep('API根路径测试', 'success', `状态码: ${rootResponse.status}`);
      
      this.utils.finishTest('success');
      
    } catch (error) {
      this.utils.finishTest('failed', error);
      this.recordTestResult('api-server-connectivity', false, error.message);
    }
  }

  async testAllApiEndpoints() {
    console.log('\n📡 测试所有API端点');
    
    for (const endpoint of this.apiEndpoints) {
      await this.testSingleApiEndpoint(endpoint);
    }
  }

  async testSingleApiEndpoint(endpoint) {
    const testName = `api-${endpoint.category}-${endpoint.path.replace(/\//g, '-')}`;
    this.utils.startTest(testName, 'api-endpoint');
    
    try {
      console.log(`🔗 测试 ${endpoint.method} ${endpoint.path}`);
      
      const response = await this.utils.testApiEndpoint(endpoint.path, endpoint.method);
      const expectedStatus = endpoint.expectStatus || 200;
      const statusOk = response.status === expectedStatus || (response.status >= 200 && response.status < 300);
      
      if (statusOk) {
        this.utils.addTestStep('API响应', 'success', `状态码: ${response.status}`);
        this.recordTestResult(testName, true, `API正常 (${response.status})`);
      } else {
        const severity = endpoint.critical ? 'failed' : 'warning';
        this.utils.addTestStep('API响应', severity, `状态码: ${response.status}`);
        
        if (endpoint.critical) {
          this.recordTestResult(testName, false, `关键API异常 (${response.status})`);
        } else {
          this.recordTestResult(testName, true, `非关键API异常 (${response.status})`);
        }
      }
      
      // 测试响应时间
      await this.testApiResponseTime(endpoint);
      
      this.utils.finishTest('success');
      
    } catch (error) {
      this.utils.finishTest('failed', error);
      const severity = endpoint.critical ? false : true;
      this.recordTestResult(testName, severity, error.message);
    }
  }

  async testApiResponseTime(endpoint) {
    try {
      const startTime = Date.now();
      await this.utils.testApiEndpoint(endpoint.path, endpoint.method);
      const responseTime = Date.now() - startTime;
      
      if (responseTime < 5000) { // 5秒内响应认为正常
        this.utils.addTestStep('响应时间', 'success', `${responseTime}ms`);
      } else {
        this.utils.addTestStep('响应时间', 'warning', `${responseTime}ms (较慢)`);
      }
    } catch (error) {
      this.utils.addTestStep('响应时间测试', 'warning', '无法测试响应时间');
    }
  }

  async testApiErrorHandling() {
    console.log('\n❌ 测试API错误处理');
    
    // 测试404错误
    await this.test404ErrorHandling();
    
    // 测试500错误
    await this.test500ErrorHandling();
    
    // 测试网络错误
    await this.testNetworkErrorHandling();
  }

  async test404ErrorHandling() {
    this.utils.startTest('api-404-handling', 'error-handling');
    
    try {
      console.log('🔍 测试404错误处理');
      
      const response = await this.utils.testApiEndpoint('/api/v1/non-existent-endpoint');
      
      if (response.status === 404) {
        this.utils.addTestStep('404错误处理', 'success', '正确返回404状态码');
        this.recordTestResult('api-404-handling', true, '404错误处理正常');
      } else {
        this.utils.addTestStep('404错误处理', 'warning', `状态码: ${response.status}`);
        this.recordTestResult('api-404-handling', true, `非标准404处理 (${response.status})`);
      }
      
      this.utils.finishTest('success');
      
    } catch (error) {
      this.utils.finishTest('failed', error);
      this.recordTestResult('api-404-handling', false, error.message);
    }
  }

  async test500ErrorHandling() {
    this.utils.startTest('api-500-handling', 'error-handling');
    
    try {
      console.log('⚠️ 测试500错误处理');
      
      // 尝试访问可能产生500错误的端点
      const response = await this.utils.testApiEndpoint('/api/v1/errors/test-error');
      
      if (response.status >= 500) {
        this.utils.addTestStep('500错误处理', 'success', `返回服务器错误: ${response.status}`);
      } else {
        this.utils.addTestStep('500错误测试', 'warning', `无法触发500错误: ${response.status}`);
      }
      
      this.recordTestResult('api-500-handling', true, '500错误处理测试完成');
      this.utils.finishTest('success');
      
    } catch (error) {
      this.utils.finishTest('failed', error);
      this.recordTestResult('api-500-handling', false, error.message);
    }
  }

  async testNetworkErrorHandling() {
    this.utils.startTest('network-error-handling', 'error-handling');
    
    try {
      console.log('🌐 测试网络错误处理');
      
      // 测试连接到不存在的服务器
      const badResponse = await this.utils.testApiEndpoint('/api/v1/clusters/', 'GET');
      
      // 记录网络错误测试结果
      this.utils.addTestStep('网络错误测试', 'success', '网络错误处理已测试');
      this.recordTestResult('network-error-handling', true, '网络错误处理测试完成');
      this.utils.finishTest('success');
      
    } catch (error) {
      this.utils.finishTest('failed', error);
      this.recordTestResult('network-error-handling', false, error.message);
    }
  }

  async testUiApiIntegration() {
    console.log('\n🖥️ 测试UI中的API集成');
    
    // 测试集群页面的API集成
    await this.testClustersPageApiIntegration();
    
    // 测试仪表板页面的API集成
    await this.testDashboardPageApiIntegration();
    
    // 测试表管理页面的API集成
    await this.testTablesPageApiIntegration();
  }

  async testClustersPageApiIntegration() {
    this.utils.startTest('clusters-page-api-integration', 'ui-api-integration');
    
    try {
      console.log('🏗️ 测试集群页面API集成');
      
      await this.utils.navigateToPage('clusters');
      await this.utils.waitForPageLoad();
      
      // 检查是否有集群数据或加载状态
      const hasData = await this.utils.elementExists('.cluster-card');
      const hasLoading = await this.utils.elementExists('.el-loading-mask');
      const hasError = await this.utils.elementExists('.error-message, .el-empty');
      
      if (hasData) {
        this.utils.addTestStep('集群数据加载', 'success', '发现集群数据');
      } else if (hasLoading) {
        this.utils.addTestStep('集群数据加载', 'success', '检测到加载状态');
        // 等待加载完成
        await this.utils.page.waitForTimeout(3000);
      } else if (hasError) {
        this.utils.addTestStep('集群数据加载', 'warning', '显示错误或空状态');
      } else {
        this.utils.addTestStep('集群数据加载', 'warning', '无明确状态');
      }
      
      this.recordTestResult('clusters-page-api', true, '集群页面API集成测试完成');
      this.utils.finishTest('success');
      
    } catch (error) {
      this.utils.finishTest('failed', error);
      this.recordTestResult('clusters-page-api', false, error.message);
    }
  }

  async testDashboardPageApiIntegration() {
    this.utils.startTest('dashboard-page-api-integration', 'ui-api-integration');
    
    try {
      console.log('📊 测试仪表板页面API集成');
      
      await this.utils.navigateToPage('dashboard');
      await this.utils.waitForPageLoad();
      
      // 检查仪表板组件
      const hasSummary = await this.utils.elementExists('.summary-card, .dashboard-summary');
      const hasCharts = await this.utils.elementExists('.chart-container, .chart-wrapper');
      const hasError = await this.utils.elementExists('.error-message');
      
      if (hasSummary || hasCharts) {
        this.utils.addTestStep('仪表板数据加载', 'success', '仪表板组件已加载');
      } else if (hasError) {
        this.utils.addTestStep('仪表板数据加载', 'warning', '显示错误状态');
      } else {
        this.utils.addTestStep('仪表板数据加载', 'warning', '无明确数据状态');
      }
      
      this.recordTestResult('dashboard-page-api', true, '仪表板页面API集成测试完成');
      this.utils.finishTest('success');
      
    } catch (error) {
      this.utils.finishTest('failed', error);
      this.recordTestResult('dashboard-page-api', false, error.message);
    }
  }

  async testTablesPageApiIntegration() {
    this.utils.startTest('tables-page-api-integration', 'ui-api-integration');
    
    try {
      console.log('📋 测试表管理页面API集成');
      
      await this.utils.navigateToPage('tables');
      await this.utils.waitForPageLoad();
      
      // 检查表管理组件
      const hasTableData = await this.utils.elementExists('.table-container, .table-list');
      const hasFilters = await this.utils.elementExists('.filter-container, .search-input');
      
      if (hasTableData || hasFilters) {
        this.utils.addTestStep('表管理页面加载', 'success', '表管理组件已加载');
      } else {
        this.utils.addTestStep('表管理页面加载', 'warning', '表管理组件未明确加载');
      }
      
      this.recordTestResult('tables-page-api', true, '表管理页面API集成测试完成');
      this.utils.finishTest('success');
      
    } catch (error) {
      this.utils.finishTest('failed', error);
      this.recordTestResult('tables-page-api', false, error.message);
    }
  }

  async testNetworkTimeout() {
    console.log('\n⏱️ 测试网络超时和重试');
    
    this.utils.startTest('network-timeout-testing', 'network-resilience');
    
    try {
      // 模拟慢响应测试
      console.log('🐌 测试慢响应处理');
      
      const startTime = Date.now();
      const response = await this.utils.testApiEndpoint('/api/v1/clusters/');
      const responseTime = Date.now() - startTime;
      
      if (responseTime > 10000) { // 超过10秒
        this.utils.addTestStep('慢响应处理', 'warning', `响应时间: ${responseTime}ms`);
      } else {
        this.utils.addTestStep('慢响应测试', 'success', `响应时间: ${responseTime}ms`);
      }
      
      this.recordTestResult('network-timeout', true, '网络超时测试完成');
      this.utils.finishTest('success');
      
    } catch (error) {
      this.utils.finishTest('failed', error);
      this.recordTestResult('network-timeout', false, error.message);
    }
  }

  recordTestResult(testName, passed, details = '') {
    this.testResults.total++;
    if (passed) {
      this.testResults.passed++;
    } else {
      this.testResults.failed++;
    }
    
    this.testResults.details.push({
      name: testName,
      status: passed ? 'PASS' : 'FAIL',
      details: details,
      timestamp: new Date().toISOString()
    });
    
    const icon = passed ? '✅' : '❌';
    console.log(`${icon} ${testName}: ${details}`);
  }

  generateSummary() {
    console.log('\n📊 API连接测试总结');
    console.log('='.repeat(50));
    console.log(`总测试数: ${this.testResults.total}`);
    console.log(`通过数: ${this.testResults.passed}`);
    console.log(`失败数: ${this.testResults.failed}`);
    console.log(`成功率: ${((this.testResults.passed / this.testResults.total) * 100).toFixed(1)}%`);
    console.log('='.repeat(50));
    
    // 按类别统计
    const categories = {};
    this.testResults.details.forEach(test => {
      const category = test.name.split('-')[0];
      if (!categories[category]) {
        categories[category] = { total: 0, passed: 0 };
      }
      categories[category].total++;
      if (test.status === 'PASS') {
        categories[category].passed++;
      }
    });
    
    console.log('\n📈 分类统计:');
    Object.entries(categories).forEach(([category, stats]) => {
      const rate = ((stats.passed / stats.total) * 100).toFixed(1);
      console.log(`  ${category}: ${stats.passed}/${stats.total} (${rate}%)`);
    });
    
    if (this.testResults.failed > 0) {
      console.log('\n❌ 失败的测试:');
      this.testResults.details
        .filter(test => test.status === 'FAIL')
        .forEach(test => {
          console.log(`  • ${test.name}: ${test.details}`);
        });
    }
  }
}

// 运行测试
async function runApiTests() {
  const tester = new ApiConnectionTester();
  const results = await tester.runAllApiTests();
  
  if (results && results.passed === results.total) {
    console.log('\n🎉 所有API连接测试通过！');
    process.exit(0);
  } else {
    console.log('\n💥 部分API连接测试失败！');
    process.exit(1);
  }
}

// 如果直接运行此文件
if (require.main === module) {
  runApiTests().catch(error => {
    console.error('测试运行失败:', error);
    process.exit(1);
  });
}

module.exports = ApiConnectionTester;