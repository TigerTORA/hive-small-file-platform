const puppeteer = require('puppeteer');

(async () => {
  console.log('🚀 Starting Enhanced Browser Automation Testing...');
  const browser = await puppeteer.launch({ headless: false, slowMo: 200 });
  const page = await browser.newPage();
  
  // Set viewport for consistent testing
  await page.setViewport({ width: 1366, height: 768 });
  
  try {
    console.log('📝 测试全库扫描用户界面工作流程...');
    
    // 1. 访问应用主页
    await page.goto('http://localhost:3002');
    await page.waitForTimeout(2000);
    console.log('✅ 1. 成功访问应用主页');
    
    // 2. 导航到集群管理页面
    await page.click('[data-test="clusters-nav"]');
    await page.waitForTimeout(2000);
    console.log('✅ 2. 成功导航到集群管理页面');
    
    // 3. 点击进入集群详情（第一个集群）
    const firstClusterButton = await page.$('[data-test="enter-cluster-btn"]');
    if (firstClusterButton) {
      await firstClusterButton.click();
      await page.waitForTimeout(3000);
      console.log('✅ 3. 成功进入集群详情页面');
    } else {
      // 如果没有找到按钮，尝试其他导航方式
      const clusterLink = await page.$('tr:first-child td:last-child button');
      if (clusterLink) {
        await clusterLink.click();
        await page.waitForTimeout(3000);
        console.log('✅ 3. 通过替代方式进入集群详情页面');
      } else {
        console.log('❌ 3. 无法找到进入集群的按钮');
      }
    }
    
    // 4. 等待集群详情页面加载并查找扫描按钮
    await page.waitForTimeout(2000);
    
    // 尝试多种可能的扫描按钮选择器
    const scanSelectors = [
      '[data-test="scan-database-btn"]',
      'button:contains("扫描数据库")',
      'button:contains("全库扫描")',
      '.el-button:contains("扫描")',
      'button'
    ];
    
    let scanButton = null;
    for (const selector of scanSelectors) {
      try {
        scanButton = await page.$(selector);
        if (scanButton) {
          const buttonText = await page.evaluate(el => el.textContent, scanButton);
          if (buttonText && (buttonText.includes('扫描') || buttonText.includes('scan'))) {
            console.log(`✅ 4. 找到扫描按钮: "${buttonText}"`);
            break;
          }
        }
      } catch (e) {
        // 继续尝试其他选择器
      }
    }
    
    if (!scanButton) {
      // 获取页面所有按钮文本用于调试
      const buttons = await page.$$eval('button', btns => 
        btns.map(btn => btn.textContent.trim()).filter(text => text.length > 0)
      );
      console.log('🔍 页面上的所有按钮:', buttons);
      
      // 尝试查找包含扫描相关文本的按钮
      const scanBtnXPath = "//button[contains(text(), '扫描') or contains(text(), 'scan') or contains(text(), 'Scan')]";
      const scanBtnElements = await page.$x(scanBtnXPath);
      
      if (scanBtnElements.length > 0) {
        scanButton = scanBtnElements[0];
        console.log('✅ 4. 通过XPath找到扫描按钮');
      } else {
        console.log('❌ 4. 无法找到扫描按钮');
        console.log('🔍 当前页面URL:', page.url());
        
        // 截图以供调试
        await page.screenshot({ path: 'cluster-detail-page.png' });
        console.log('📸 已保存页面截图: cluster-detail-page.png');
      }
    }
    
    // 5. 点击扫描按钮
    if (scanButton) {
      await scanButton.click();
      await page.waitForTimeout(1000);
      console.log('✅ 5. 成功点击扫描按钮');
      
      // 6. 检查是否出现扫描进度对话框
      const progressDialog = await page.$('.el-dialog');
      if (progressDialog) {
        console.log('✅ 6. 扫描进度对话框已出现');
        
        // 7. 监听进度更新（等待几秒钟观察）
        await page.waitForTimeout(5000);
        
        const progressText = await page.$eval('.el-progress__text', el => el.textContent);
        console.log(`✅ 7. 观察到进度更新: ${progressText}`);
        
        // 8. 检查日志输出
        const logElements = await page.$$('.scan-log .log-item');
        if (logElements.length > 0) {
          const logTexts = await Promise.all(
            logElements.map(el => page.evaluate(element => element.textContent, el))
          );
          console.log(`✅ 8. 发现扫描日志 (${logTexts.length} 条):`);
          logTexts.forEach((log, i) => console.log(`   ${i + 1}. ${log}`));
        } else {
          console.log('ℹ️ 8. 暂无扫描日志显示');
        }
        
      } else {
        console.log('❌ 6. 扫描进度对话框未出现');
      }
    }
    
    // 9. Validate table data display after scan
    console.log('\n📊 9. 验证表数据显示');
    
    // Wait for scan to potentially complete and navigate to see results
    await page.waitForTimeout(3000);
    
    // Check if we can navigate to task management
    const tasksNavButton = await page.$('a[href*="tasks"], button:contains("任务"), button:contains("Tasks")');
    if (tasksNavButton) {
      await tasksNavButton.click();
      await page.waitForTimeout(2000);
      console.log('✅ 9. 成功导航到任务管理页面');
      
      // Check for task entries
      const taskItems = await page.$$('.task-item, .el-table__row, tr');
      if (taskItems.length > 0) {
        console.log(`✅ 发现 ${taskItems.length} 个任务条目`);
      } else {
        console.log('ℹ️ 暂无任务显示（可能扫描正在进行中）');
      }
    }
    
    // 10. Validate data integrity and UI consistency
    console.log('\n🔍 10. 验证数据完整性和UI一致性');
    
    // Check for error messages
    const errorElements = await page.$$('.error, .el-message--error, .alert-error');
    if (errorElements.length > 0) {
      console.log(`⚠️ 发现 ${errorElements.length} 个错误消息`);
      for (let i = 0; i < errorElements.length; i++) {
        const errorText = await page.evaluate(el => el.textContent, errorElements[i]);
        console.log(`   错误 ${i + 1}: ${errorText}`);
      }
    } else {
      console.log('✅ 未发现UI错误消息');
    }
    
    // Check for loading states
    const loadingElements = await page.$$('.loading, .el-loading, .spinner');
    console.log(`ℹ️ 当前加载状态元素: ${loadingElements.length} 个`);
    
    // Final screenshot for validation
    await page.screenshot({ path: 'enhanced-ui-validation.png', fullPage: true });
    console.log('📸 已保存增强UI验证截图: enhanced-ui-validation.png');
    
    console.log('\n🎯 增强的全库扫描界面测试完成!');
    
  } catch (error) {
    console.error('❌ 测试过程中发生错误:', error);
    await page.screenshot({ path: 'error-screenshot.png' });
    console.log('📸 已保存错误截图: error-screenshot.png');
  }
  
  // 保持浏览器开启10秒供观察
  console.log('🔍 浏览器将保持开启10秒供观察...');
  await page.waitForTimeout(10000);
  
  await browser.close();
})();