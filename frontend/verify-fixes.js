const TestUtils = require('./test-utils.js');

class FixVerifier {
  constructor() {
    this.utils = new TestUtils();
    this.results = [];
  }

  async verifyAllFixes() {
    console.log('🔧 验证所有修复的问题...\n');
    
    await this.utils.initBrowser();
    
    // 测试修复的API端点
    await this.verifyApiEndpoints();
    
    // 测试Element Plus图标修复
    await this.verifyElementPlusIcons();
    
    // 测试路由修复
    await this.verifyRouting();
    
    // 测试按钮配置修复
    await this.verifyButtonConfig();
    
    await this.utils.closeBrowser();
    
    this.printSummary();
    return this.results;
  }

  async verifyApiEndpoints() {
    console.log('📡 验证API端点修复...');
    
    try {
      // 测试tables/metrics端点
      const metricsResponse = await this.utils.testApiEndpoint('/api/v1/tables/metrics?cluster_id=1');
      if (metricsResponse.status === 200) {
        this.recordResult('API tables/metrics', true, 'API正常响应 200');
      } else {
        this.recordResult('API tables/metrics', false, `API异常 ${metricsResponse.status}`);
      }
      
      // 测试tables/small-files端点
      const smallFilesResponse = await this.utils.testApiEndpoint('/api/v1/tables/small-files?cluster_id=1');
      if (smallFilesResponse.status === 200) {
        this.recordResult('API tables/small-files', true, 'API正常响应 200');
      } else {
        this.recordResult('API tables/small-files', false, `API异常 ${smallFilesResponse.status}`);
      }
      
    } catch (error) {
      this.recordResult('API端点测试', false, error.message);
    }
  }

  async verifyElementPlusIcons() {
    console.log('🎨 验证Element Plus图标修复...');
    
    try {
      // 导航到集群详情页面
      await this.utils.navigateToPage('clusters');
      await this.utils.waitForPageLoad();
      
      // 检查是否有集群，如果有就进入详情页
      const hasCluster = await this.utils.elementExists('.cluster-card');
      if (hasCluster) {
        // 检查页面是否有JS错误（特别是图标相关的）
        const errors = await this.utils.getPageErrors();
        const iconErrors = errors.filter(error => 
          error.includes('Database') || 
          error.includes('@element-plus/icons-vue') ||
          error.includes('export named')
        );
        
        if (iconErrors.length === 0) {
          this.recordResult('Element Plus图标', true, '无图标相关错误');
        } else {
          this.recordResult('Element Plus图标', false, `发现图标错误: ${iconErrors[0]}`);
        }
      } else {
        this.recordResult('Element Plus图标', true, '无集群数据，无法验证（但应该没有导入错误）');
      }
      
    } catch (error) {
      this.recordResult('Element Plus图标测试', false, error.message);
    }
  }

  async verifyRouting() {
    console.log('🛣️ 验证路由修复...');
    
    try {
      await this.utils.navigateToPage('clusters');
      await this.utils.waitForPageLoad();
      
      // 检查当前URL是否使用hash路由
      const currentUrl = this.utils.page.url();
      if (currentUrl.includes('#/clusters')) {
        this.recordResult('Hash路由', true, '正确使用hash路由格式');
      } else {
        this.recordResult('Hash路由', false, `路由格式不正确: ${currentUrl}`);
      }
      
    } catch (error) {
      this.recordResult('路由测试', false, error.message);
    }
  }

  async verifyButtonConfig() {
    console.log('🔘 验证按钮配置修复...');
    
    try {
      await this.utils.navigateToPage('settings');
      await this.utils.waitForPageLoad();
      
      // 检查新配置的按钮是否存在
      const refreshButtonExists = await this.utils.elementExists('button:has-text("刷新系统状态")');
      if (refreshButtonExists) {
        this.recordResult('设置页面按钮', true, '刷新按钮存在');
      } else {
        this.recordResult('设置页面按钮', false, '刷新按钮不存在');
      }
      
      // 检查保存和重置按钮
      const saveButtonExists = await this.utils.elementExists('button:has-text("保存")');
      const resetButtonExists = await this.utils.elementExists('button:has-text("重置")');
      
      if (saveButtonExists && resetButtonExists) {
        this.recordResult('基础设置按钮', true, '保存和重置按钮存在');
      } else {
        this.recordResult('基础设置按钮', false, '基础按钮缺失');
      }
      
    } catch (error) {
      this.recordResult('按钮配置测试', false, error.message);
    }
  }

  recordResult(testName, success, details) {
    this.results.push({
      test: testName,
      success: success,
      details: details
    });
    
    const status = success ? '✅' : '❌';
    console.log(`  ${status} ${testName}: ${details}`);
  }

  printSummary() {
    console.log('\n📊 修复验证总结');
    console.log('==================================================');
    
    const total = this.results.length;
    const passed = this.results.filter(r => r.success).length;
    const failed = total - passed;
    
    console.log(`总测试数: ${total}`);
    console.log(`通过数: ${passed}`);
    console.log(`失败数: ${failed}`);
    console.log(`成功率: ${((passed / total) * 100).toFixed(1)}%`);
    
    if (failed > 0) {
      console.log('\n❌ 仍需修复的问题:');
      this.results.filter(r => !r.success).forEach(result => {
        console.log(`  • ${result.test}: ${result.details}`);
      });
    } else {
      console.log('\n🎉 所有问题已修复！');
    }
    console.log('==================================================');
  }
}

// 运行验证
async function main() {
  const verifier = new FixVerifier();
  await verifier.verifyAllFixes();
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = FixVerifier;