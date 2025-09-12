// 简单的验证脚本，测试自动化测试框架是否正常工作
const TEST_CONFIG = require('./test-config.js');

async function quickVerification() {
  console.log('🧪 快速验证自动化测试框架...\n');
  
  let passedTests = 0;
  let totalTests = 0;
  
  // 测试1: 配置文件加载
  totalTests++;
  try {
    if (TEST_CONFIG && TEST_CONFIG.app && TEST_CONFIG.app.baseUrl) {
      console.log('✅ 配置文件加载正常');
      passedTests++;
    } else {
      console.log('❌ 配置文件加载失败');
    }
  } catch (error) {
    console.log(`❌ 配置文件错误: ${error.message}`);
  }
  
  // 测试2: 测试工具类加载
  totalTests++;
  try {
    const TestUtils = require('./test-utils.js');
    if (TestUtils) {
      console.log('✅ 测试工具类加载正常');
      passedTests++;
    } else {
      console.log('❌ 测试工具类加载失败');
    }
  } catch (error) {
    console.log(`❌ 测试工具类错误: ${error.message}`);
  }
  
  // 测试3: 各个测试模块加载
  totalTests++;
  try {
    const ButtonFunctionalityTester = require('./test-buttons-comprehensive.js');
    const FormValidationTester = require('./test-forms-validation.js');
    const NavigationRoutingTester = require('./test-navigation-routing.js');
    const ApiConnectionTester = require('./test-api-connection.js');
    
    if (ButtonFunctionalityTester && FormValidationTester && NavigationRoutingTester && ApiConnectionTester) {
      console.log('✅ 所有测试模块加载正常');
      passedTests++;
    } else {
      console.log('❌ 部分测试模块加载失败');
    }
  } catch (error) {
    console.log(`❌ 测试模块加载错误: ${error.message}`);
  }
  
  // 测试4: 数据管理器加载
  totalTests++;
  try {
    const TestDataManager = require('./test-data-manager.js');
    if (TestDataManager) {
      console.log('✅ 数据管理器加载正常');
      passedTests++;
    } else {
      console.log('❌ 数据管理器加载失败');
    }
  } catch (error) {
    console.log(`❌ 数据管理器错误: ${error.message}`);
  }
  
  // 测试5: 报告生成器加载
  totalTests++;
  try {
    const TestReporter = require('./test-reporter.js');
    if (TestReporter) {
      console.log('✅ 报告生成器加载正常');
      passedTests++;
    } else {
      console.log('❌ 报告生成器加载失败');
    }
  } catch (error) {
    console.log(`❌ 报告生成器错误: ${error.message}`);
  }
  
  // 测试6: 主测试套件加载
  totalTests++;
  try {
    const ComprehensiveTestSuite = require('./comprehensive-test-suite.js');
    if (ComprehensiveTestSuite) {
      console.log('✅ 主测试套件加载正常');
      passedTests++;
    } else {
      console.log('❌ 主测试套件加载失败');
    }
  } catch (error) {
    console.log(`❌ 主测试套件错误: ${error.message}`);
  }
  
  // 测试7: API连通性检查
  totalTests++;
  try {
    const response = await fetch(TEST_CONFIG.app.apiBaseUrl + '/health');
    if (response.status < 500) {
      console.log(`✅ API服务器连通性正常 (${response.status})`);
      passedTests++;
    } else {
      console.log(`⚠️ API服务器响应异常 (${response.status})`);
    }
  } catch (error) {
    console.log(`❌ API连接失败: ${error.message}`);
  }
  
  // 测试8: 前端服务检查
  totalTests++;
  try {
    const response = await fetch(TEST_CONFIG.app.baseUrl);
    if (response.status < 500) {
      console.log(`✅ 前端服务连通性正常 (${response.status})`);
      passedTests++;
    } else {
      console.log(`⚠️ 前端服务响应异常 (${response.status})`);
    }
  } catch (error) {
    console.log(`❌ 前端连接失败: ${error.message}`);
  }
  
  // 显示总结
  console.log('\n📊 验证结果总结');
  console.log('='.repeat(40));
  console.log(`总验证项: ${totalTests}`);
  console.log(`通过项: ${passedTests}`);
  console.log(`失败项: ${totalTests - passedTests}`);
  console.log(`成功率: ${((passedTests / totalTests) * 100).toFixed(1)}%`);
  console.log('='.repeat(40));
  
  if (passedTests === totalTests) {
    console.log('🎉 所有验证项都通过了！自动化测试框架已就绪！');
    console.log('\n🚀 您现在可以运行以下命令开始测试：');
    console.log('  node comprehensive-test-suite.js quick    # 快速测试');
    console.log('  node comprehensive-test-suite.js full     # 完整测试');
    console.log('  node comprehensive-test-suite.js parallel # 并行测试');
    console.log('\n🔗 验证链接：');
    console.log(`  🌐 前端应用: ${TEST_CONFIG.app.baseUrl}/#/clusters`);
    console.log(`  🔌 API健康检查: ${TEST_CONFIG.app.apiBaseUrl}/health`);
    return true;
  } else {
    console.log('❌ 部分验证项失败，请检查相关配置和依赖！');
    console.log('\n🔧 可能的解决方案：');
    console.log('  1. 确保前端和后端服务都在运行');
    console.log('  2. 检查网络连接和端口配置');
    console.log('  3. 验证所有依赖模块都已正确安装');
    return false;
  }
}

// 运行验证
quickVerification()
  .then(success => {
    process.exit(success ? 0 : 1);
  })
  .catch(error => {
    console.error('验证过程中出现错误:', error);
    process.exit(1);
  });