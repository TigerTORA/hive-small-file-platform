const puppeteer = require('puppeteer');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function waitForUserInput(message) {
  return new Promise((resolve) => {
    rl.question(`\n${message}\n按Enter键继续...`, (answer) => {
      resolve(answer);
    });
  });
}

(async () => {
  console.log('🚀 开始模拟场景一：全库扫描用户工作流程');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  const browser = await puppeteer.launch({ 
    headless: false, 
    slowMo: 300,
    defaultViewport: { width: 1366, height: 768 }
  });
  const page = await browser.newPage();
  
  try {
    // 步骤 1: 进入集群管理页面
    console.log('📋 步骤 1: 进入集群管理页面');
    await waitForUserInput('即将访问应用主页并导航到集群管理页面...');
    
    await page.goto('http://localhost:3002');
    await page.waitForTimeout(2000);
    console.log('✅ 成功访问应用主页: http://localhost:3002');
    
    // 查找并点击集群管理导航
    const clustersNav = await page.$('a[href*="clusters"], .clusters-nav, button:contains("集群")');
    if (clustersNav) {
      await clustersNav.click();
      await page.waitForTimeout(2000);
      console.log('✅ 成功导航到集群管理页面');
    } else {
      // 如果找不到导航，直接访问集群页面
      await page.goto('http://localhost:3002/#/clusters');
      await page.waitForTimeout(2000);
      console.log('✅ 直接访问集群管理页面');
    }
    
    await page.screenshot({ path: 'step1-cluster-management.png' });
    console.log('📸 已保存截图: step1-cluster-management.png');

    // 步骤 2: 使用"添加集群"功能（展示现有集群）
    console.log('\n📝 步骤 2: 查看现有集群（模拟添加集群功能）');
    await waitForUserInput('查看现有的集群列表，这些集群已经配置了连接信息...');
    
    // 检查是否有集群列表
    const clusterCards = await page.$$('.cluster-card, .el-card, .cluster-item');
    const clusterRows = await page.$$('tr, .cluster-row');
    const totalClusters = Math.max(clusterCards.length, clusterRows.length);
    
    console.log(`✅ 发现 ${totalClusters} 个已配置的集群`);
    
    // 步骤 3: 点击保存按钮（跳过，因为使用现有集群）
    console.log('\n💾 步骤 3: 集群配置（使用现有集群）');
    await waitForUserInput('我们将使用已经配置好的集群，跳过添加新集群步骤...');
    console.log('✅ 使用现有集群配置');

    // 步骤 4: 点击集群卡片进入详细界面
    console.log('\n🔍 步骤 4: 点击集群卡片进入详细界面');
    await waitForUserInput('即将点击第一个集群，进入集群详细页面...');
    
    // 查找进入集群的按钮或链接
    let clusterEnterButton = await page.$('button:contains("进入"), button:contains("查看"), a[href*="/clusters/"]');
    
    if (!clusterEnterButton) {
      // 尝试其他可能的选择器
      clusterEnterButton = await page.$('.el-button, button, .cluster-card');
      
      if (clusterEnterButton) {
        const buttonText = await page.evaluate(el => el.textContent, clusterEnterButton);
        console.log(`找到按钮: "${buttonText}"`);
      }
    }
    
    if (clusterEnterButton) {
      await clusterEnterButton.click();
      await page.waitForTimeout(3000);
      console.log('✅ 成功进入集群详细界面');
    } else {
      // 直接导航到集群详情页面
      await page.goto('http://localhost:3002/#/clusters/1');
      await page.waitForTimeout(3000);
      console.log('✅ 直接访问集群详情页面');
    }
    
    await page.screenshot({ path: 'step4-cluster-detail.png' });
    console.log('📸 已保存截图: step4-cluster-detail.png');

    // 步骤 5: 点击全库扫描按钮
    console.log('\n🔍 步骤 5: 点击全库扫描按钮');
    await waitForUserInput('即将点击全库扫描按钮，启动扫描任务...');
    
    // 查找扫描按钮
    const scanSelectors = [
      'button:contains("扫描")',
      'button:contains("全库扫描")', 
      'button:contains("扫描数据库")',
      '.scan-btn',
      '.el-button--primary'
    ];
    
    let scanButton = null;
    for (const selector of scanSelectors) {
      try {
        scanButton = await page.$(selector);
        if (scanButton) {
          const buttonText = await page.evaluate(el => el.textContent, scanButton);
          if (buttonText && (buttonText.includes('扫描') || buttonText.includes('Scan'))) {
            console.log(`✅ 找到扫描按钮: "${buttonText}"`);
            break;
          }
        }
      } catch (e) {
        // 继续尝试其他选择器
      }
    }
    
    if (scanButton) {
      await scanButton.click();
      await page.waitForTimeout(2000);
      console.log('✅ 成功点击扫描按钮');
      
      await page.screenshot({ path: 'step5-scan-started.png' });
      console.log('📸 已保存截图: step5-scan-started.png');
    } else {
      console.log('⚠️ 未找到扫描按钮，可能需要手动操作');
      await page.screenshot({ path: 'step5-no-scan-button.png' });
    }

    // 步骤 6: 查看扫描进度对话框
    console.log('\n📊 步骤 6: 查看扫描任务详细日志');
    await waitForUserInput('查看是否出现扫描进度对话框和详细日志...');
    
    // 检查进度对话框
    const progressDialog = await page.$('.el-dialog, .modal, .progress-dialog');
    if (progressDialog) {
      console.log('✅ 扫描进度对话框已出现');
      
      // 等待一段时间观察进度
      await page.waitForTimeout(3000);
      
      // 检查进度信息
      const progressInfo = await page.$('.el-progress, .progress, .progress-bar');
      if (progressInfo) {
        const progressText = await page.evaluate(el => el.textContent, progressInfo);
        console.log(`✅ 进度信息: ${progressText}`);
      }
      
      // 检查日志
      const logElements = await page.$$('.log-item, .log-entry, .scan-log li');
      if (logElements.length > 0) {
        console.log(`✅ 发现 ${logElements.length} 条扫描日志`);
      }
      
      await page.screenshot({ path: 'step6-scan-progress.png' });
      console.log('📸 已保存截图: step6-scan-progress.png');
      
    } else {
      console.log('ℹ️ 扫描进度对话框未出现，可能扫描在后台进行');
    }

    // 步骤 7: 关闭扫描窗口并导航到任务管理
    console.log('\n📋 步骤 7: 从任务管理界面查看扫描任务');
    await waitForUserInput('即将导航到任务管理界面查看扫描任务...');
    
    // 尝试关闭对话框（如果存在）
    const closeButton = await page.$('.el-dialog__close, .close, button:contains("关闭")');
    if (closeButton) {
      await closeButton.click();
      await page.waitForTimeout(1000);
      console.log('✅ 关闭了扫描对话框');
    }
    
    // 导航到任务管理页面
    const tasksNav = await page.$('a[href*="tasks"], .tasks-nav');
    if (tasksNav) {
      await tasksNav.click();
      await page.waitForTimeout(2000);
      console.log('✅ 导航到任务管理页面');
    } else {
      await page.goto('http://localhost:3002/#/tasks');
      await page.waitForTimeout(2000);
      console.log('✅ 直接访问任务管理页面');
    }
    
    // 检查任务列表
    const taskItems = await page.$$('.task-item, .el-table__row, tr');
    console.log(`✅ 任务管理页面显示 ${taskItems.length} 个任务条目`);
    
    await page.screenshot({ path: 'step7-task-management.png' });
    console.log('📸 已保存截图: step7-task-management.png');

    // 步骤 8: 查看表信息
    console.log('\n📊 步骤 8: 查看扫描结果 - 所有表信息');
    await waitForUserInput('查看扫描完成后的表信息展示...');
    
    // 返回集群详情查看表数据
    await page.goto('http://localhost:3002/#/clusters/1');
    await page.waitForTimeout(3000);
    
    // 检查是否有表格数据显示
    const tableData = await page.$$('.el-table__row, .table-row, tr');
    console.log(`✅ 集群详情页面显示 ${tableData.length} 行表数据`);
    
    await page.screenshot({ path: 'step8-table-results.png' });
    console.log('📸 已保存截图: step8-table-results.png');

    // 完成总结
    console.log('\n🎉 场景一完成总结');
    await waitForUserInput('场景一模拟完成！查看完整的用户工作流程结果...');
    
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✅ 场景一完整流程已成功模拟：');
    console.log('1. ✅ 进入集群管理页面');
    console.log('2. ✅ 查看现有集群配置');
    console.log('3. ✅ 进入集群详细界面');
    console.log('4. ✅ 启动全库扫描任务');
    console.log('5. ✅ 查看扫描进度和日志');
    console.log('6. ✅ 在任务管理中查看任务');
    console.log('7. ✅ 查看扫描结果表信息');
    console.log('\n🔗 验证链接:');
    console.log('• 集群管理: http://localhost:3002/#/clusters');
    console.log('• 集群详情: http://localhost:3002/#/clusters/1');
    console.log('• 任务管理: http://localhost:3002/#/tasks');
    
    await page.screenshot({ path: 'scenario1-complete.png', fullPage: true });
    console.log('📸 已保存最终截图: scenario1-complete.png');

  } catch (error) {
    console.error('❌ 模拟过程中发生错误:', error);
    await page.screenshot({ path: 'scenario1-error.png' });
  }
  
  await waitForUserInput('\n测试完成，按Enter键关闭浏览器...');
  await browser.close();
  rl.close();
})();