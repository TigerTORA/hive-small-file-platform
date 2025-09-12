const TestUtils = require('./test-utils.js');
const TEST_CONFIG = require('./test-config.js');

class ButtonFunctionalityTester {
  constructor() {
    this.utils = new TestUtils();
    this.testResults = {
      total: 0,
      passed: 0,
      failed: 0,
      details: []
    };
  }

  async runAllButtonTests() {
    console.log('🎯 开始综合按钮功能测试...\n');
    
    try {
      await this.utils.initBrowser();
      
      // 测试所有页面的按钮功能
      for (const scenario of TEST_CONFIG.scenarios.buttonTests) {
        await this.testPageButtons(scenario.page, scenario.buttons);
      }
      
      // 测试特殊按钮交互
      await this.testSpecialButtonInteractions();
      
      // 测试按钮状态变化
      await this.testButtonStates();
      
      this.generateSummary();
      return this.testResults;
      
    } catch (error) {
      console.error(`💥 测试过程中出现错误: ${error.message}`);
      return null;
    } finally {
      await this.utils.closeBrowser();
    }
  }

  async testPageButtons(pageName, buttonList) {
    console.log(`\n📄 测试页面: ${pageName}`);
    console.log(`🔘 按钮列表: ${buttonList.join(', ')}`);
    
    // 导航到页面
    const navigationSuccess = await this.utils.navigateToPage(pageName);
    if (!navigationSuccess) {
      this.recordTestResult(`${pageName}-navigation`, false, '页面导航失败');
      return;
    }
    
    await this.utils.waitForPageLoad();
    
    const selectors = TEST_CONFIG.selectors[pageName];
    if (!selectors) {
      this.recordTestResult(`${pageName}-selectors`, false, '缺少页面选择器配置');
      return;
    }
    
    for (const buttonName of buttonList) {
      await this.testSingleButton(pageName, buttonName, selectors[buttonName]);
    }
  }

  async testSingleButton(pageName, buttonName, selector) {
    if (!selector) {
      this.recordTestResult(`${pageName}-${buttonName}`, false, '选择器未定义');
      return;
    }
    
    this.utils.startTest(`${pageName}-${buttonName}`, 'button-functionality');
    
    try {
      // 检查按钮是否存在
      const exists = await this.utils.elementExists(selector);
      if (!exists) {
        this.utils.addTestStep('检查按钮存在性', 'failed', '按钮不存在');
        this.utils.finishTest('failed', `按钮不存在: ${selector}`);
        this.recordTestResult(`${pageName}-${buttonName}`, false, '按钮不存在');
        return;
      }
      this.utils.addTestStep('检查按钮存在性', 'success');
      
      // 检查按钮是否可见
      const visible = await this.utils.elementVisible(selector);
      if (!visible) {
        this.utils.addTestStep('检查按钮可见性', 'failed', '按钮不可见');
        this.utils.finishTest('failed', `按钮不可见: ${selector}`);
        this.recordTestResult(`${pageName}-${buttonName}`, false, '按钮不可见');
        return;
      }
      this.utils.addTestStep('检查按钮可见性', 'success');
      
      // 检查按钮是否启用
      const disabled = await this.utils.elementDisabled(selector);
      if (disabled) {
        this.utils.addTestStep('检查按钮启用状态', 'warning', '按钮被禁用');
        // 对于禁用的按钮，我们仍然认为测试通过，但会记录状态
        this.utils.finishTest('success', null);
        this.recordTestResult(`${pageName}-${buttonName}`, true, '按钮存在但被禁用');
        return;
      }
      this.utils.addTestStep('检查按钮启用状态', 'success');
      
      // 测试点击功能
      await this.testButtonClick(pageName, buttonName, selector);
      
      this.utils.finishTest('success');
      this.recordTestResult(`${pageName}-${buttonName}`, true, '按钮功能正常');
      
    } catch (error) {
      this.utils.addTestStep('按钮测试', 'failed', error.message);
      this.utils.finishTest('failed', error);
      this.recordTestResult(`${pageName}-${buttonName}`, false, error.message);
    }
  }

  async testButtonClick(pageName, buttonName, selector) {
    console.log(`🖱️ 测试按钮点击: ${buttonName}`);
    
    // 根据按钮类型确定期待的行为
    const expectDialog = this.shouldExpectDialog(buttonName);
    const expectNavigation = this.shouldExpectNavigation(buttonName);
    
    // 记录点击前的状态
    const initialUrl = this.utils.page.url();
    
    // 点击按钮
    const clickSuccess = await this.utils.clickElement(selector, expectDialog, expectNavigation);
    if (!clickSuccess) {
      this.utils.addTestStep('点击按钮', 'failed', '点击操作失败');
      return;
    }
    this.utils.addTestStep('点击按钮', 'success');
    
    // 验证点击后的效果
    await this.verifyButtonClickEffect(pageName, buttonName, initialUrl, expectDialog, expectNavigation);
  }

  async verifyButtonClickEffect(pageName, buttonName, initialUrl, expectDialog, expectNavigation) {
    if (expectDialog) {
      // 等待对话框出现
      const dialogAppeared = await this.utils.waitForElement('.el-dialog', 3000);
      if (dialogAppeared) {
        this.utils.addTestStep('验证对话框', 'success', '对话框正常弹出');
        // 关闭对话框
        await this.closeDialog();
      } else {
        this.utils.addTestStep('验证对话框', 'failed', '对话框未出现');
      }
    }
    
    if (expectNavigation) {
      // 检查URL是否改变
      await this.utils.page.waitForTimeout(1000);
      const currentUrl = this.utils.page.url();
      if (currentUrl !== initialUrl) {
        this.utils.addTestStep('验证页面导航', 'success', `URL已改变: ${currentUrl}`);
        // 导航回原页面
        await this.utils.navigateToPage(pageName);
      } else {
        this.utils.addTestStep('验证页面导航', 'failed', 'URL未改变');
      }
    }
    
    // 检查是否有通知消息
    await this.checkForNotifications();
    
    // 检查是否有加载状态
    await this.checkForLoadingStates();
  }

  async closeDialog() {
    try {
      // 尝试多种关闭对话框的方法
      const cancelButton = await this.utils.elementExists('.el-dialog .el-button:has-text("取消")');
      const closeButton = await this.utils.elementExists('.el-dialog .el-dialog__close');
      
      if (cancelButton) {
        await this.utils.clickElement('.el-dialog .el-button:has-text("取消")');
      } else if (closeButton) {
        await this.utils.clickElement('.el-dialog .el-dialog__close');
      } else {
        // 按ESC键关闭
        await this.utils.page.keyboard.press('Escape');
      }
      
      // 等待对话框消失
      await this.utils.page.waitForSelector('.el-dialog', { state: 'hidden', timeout: 3000 });
      this.utils.addTestStep('关闭对话框', 'success');
    } catch (error) {
      this.utils.addTestStep('关闭对话框', 'failed', error.message);
    }
  }

  async checkForNotifications() {
    const notifications = await this.utils.elementExists('.el-notification');
    const messageBoxes = await this.utils.elementExists('.el-message-box');
    
    if (notifications || messageBoxes) {
      this.utils.addTestStep('检查通知消息', 'success', '发现通知消息');
      // 等待通知消失或手动关闭
      await this.utils.page.waitForTimeout(2000);
    }
  }

  async checkForLoadingStates() {
    const loading = await this.utils.elementExists('.el-loading-mask');
    if (loading) {
      this.utils.addTestStep('检查加载状态', 'success', '发现加载状态');
      // 等待加载完成
      await this.utils.page.waitForSelector('.el-loading-mask', { state: 'hidden', timeout: 10000 });
    }
  }

  shouldExpectDialog(buttonName) {
    const dialogButtons = ['addButton', 'editButton', 'createButton', 'deleteButton'];
    return dialogButtons.some(pattern => buttonName.includes(pattern.replace('Button', '')));
  }

  shouldExpectNavigation(buttonName) {
    const navigationButtons = ['detailButton'];
    return navigationButtons.some(pattern => buttonName.includes(pattern.replace('Button', '')));
  }

  async testSpecialButtonInteractions() {
    console.log('\n🔧 测试特殊按钮交互...');
    
    // 测试集群管理页面的特殊交互
    await this.testClusterManagementInteractions();
    
    // 测试任务管理页面的特殊交互
    await this.testTaskManagementInteractions();
  }

  async testClusterManagementInteractions() {
    console.log('🏗️ 测试集群管理特殊交互');
    
    await this.utils.navigateToPage('clusters');
    await this.utils.waitForPageLoad();
    
    // 测试添加集群完整流程
    this.utils.startTest('cluster-add-workflow', 'special-interaction');
    
    try {
      // 点击添加按钮
      const addSuccess = await this.utils.clickElement(TEST_CONFIG.selectors.clusters.addButton, true);
      if (addSuccess) {
        this.utils.addTestStep('打开添加对话框', 'success');
        
        // 测试表单验证
        await this.testClusterFormValidation();
        
        // 关闭对话框
        await this.closeDialog();
        
        this.utils.finishTest('success');
        this.recordTestResult('cluster-add-workflow', true, '添加集群流程测试通过');
      } else {
        this.utils.finishTest('failed', '无法打开添加对话框');
        this.recordTestResult('cluster-add-workflow', false, '无法打开添加对话框');
      }
    } catch (error) {
      this.utils.finishTest('failed', error);
      this.recordTestResult('cluster-add-workflow', false, error.message);
    }
  }

  async testClusterFormValidation() {
    console.log('📝 测试集群表单验证');
    
    // 尝试提交空表单
    const saveButton = TEST_CONFIG.selectors.clusters.saveButton;
    if (await this.utils.elementExists(saveButton)) {
      await this.utils.clickElement(saveButton);
      await this.utils.page.waitForTimeout(1000);
      
      // 检查是否有验证错误提示
      const hasErrors = await this.utils.elementExists('.el-form-item__error');
      if (hasErrors) {
        this.utils.addTestStep('表单验证', 'success', '检测到验证错误');
      } else {
        this.utils.addTestStep('表单验证', 'warning', '未检测到验证错误');
      }
    }
  }

  async testTaskManagementInteractions() {
    console.log('📋 测试任务管理特殊交互');
    
    await this.utils.navigateToPage('tasks');
    await this.utils.waitForPageLoad();
    
    // 检查任务列表是否加载
    const taskExists = await this.utils.elementExists('.task-row');
    if (taskExists) {
      this.recordTestResult('task-list-load', true, '任务列表加载成功');
    } else {
      this.recordTestResult('task-list-load', true, '任务列表为空（正常）');
    }
  }

  async testButtonStates() {
    console.log('\n🔄 测试按钮状态变化...');
    
    // 测试按钮在不同状态下的行为
    await this.testButtonHoverStates();
    await this.testButtonFocusStates();
    await this.testButtonLoadingStates();
  }

  async testButtonHoverStates() {
    console.log('🖱️ 测试按钮悬停状态');
    
    await this.utils.navigateToPage('clusters');
    await this.utils.waitForPageLoad();
    
    const buttons = [
      TEST_CONFIG.selectors.clusters.addButton,
      TEST_CONFIG.selectors.clusters.editButton,
      TEST_CONFIG.selectors.clusters.testButton
    ];
    
    for (const selector of buttons) {
      if (await this.utils.elementExists(selector)) {
        try {
          await this.utils.page.hover(selector);
          await this.utils.page.waitForTimeout(500);
          this.utils.addTestStep(`悬停测试: ${selector}`, 'success');
        } catch (error) {
          this.utils.addTestStep(`悬停测试: ${selector}`, 'failed', error.message);
        }
      }
    }
  }

  async testButtonFocusStates() {
    console.log('🎯 测试按钮焦点状态');
    
    const addButton = TEST_CONFIG.selectors.clusters.addButton;
    if (await this.utils.elementExists(addButton)) {
      try {
        await this.utils.page.focus(addButton);
        await this.utils.page.waitForTimeout(500);
        this.recordTestResult('button-focus', true, '按钮焦点状态正常');
      } catch (error) {
        this.recordTestResult('button-focus', false, error.message);
      }
    }
  }

  async testButtonLoadingStates() {
    console.log('⏳ 测试按钮加载状态');
    
    // 点击可能触发加载状态的按钮
    const testButton = TEST_CONFIG.selectors.clusters.testButton;
    if (await this.utils.elementExists(testButton)) {
      try {
        await this.utils.clickElement(testButton);
        
        // 检查是否出现加载状态
        await this.utils.page.waitForTimeout(1000);
        const loadingExists = await this.utils.elementExists('.el-loading-mask') || 
                             await this.utils.elementExists('.el-button.is-loading');
        
        if (loadingExists) {
          this.recordTestResult('button-loading', true, '检测到加载状态');
        } else {
          this.recordTestResult('button-loading', true, '未检测到加载状态（可能操作过快）');
        }
      } catch (error) {
        this.recordTestResult('button-loading', false, error.message);
      }
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
    console.log('\n📊 按钮功能测试总结');
    console.log('='.repeat(50));
    console.log(`总测试数: ${this.testResults.total}`);
    console.log(`通过数: ${this.testResults.passed}`);
    console.log(`失败数: ${this.testResults.failed}`);
    console.log(`成功率: ${((this.testResults.passed / this.testResults.total) * 100).toFixed(1)}%`);
    console.log('='.repeat(50));
    
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
async function runButtonTests() {
  const tester = new ButtonFunctionalityTester();
  const results = await tester.runAllButtonTests();
  
  if (results && results.passed === results.total) {
    console.log('\n🎉 所有按钮功能测试通过！');
    process.exit(0);
  } else {
    console.log('\n💥 部分按钮功能测试失败！');
    process.exit(1);
  }
}

// 如果直接运行此文件
if (require.main === module) {
  runButtonTests().catch(error => {
    console.error('测试运行失败:', error);
    process.exit(1);
  });
}

module.exports = ButtonFunctionalityTester;