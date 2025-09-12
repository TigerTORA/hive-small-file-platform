const { chromium } = require('playwright');

(async () => {
  console.log('🎯 测试数据库扫描进度追踪功能');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    // 监听网络请求
    page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/v1/tables/scan') || url.includes('/scan-progress')) {
        console.log(`📡 API请求: ${response.url()}`);
        console.log(`📡 响应状态: ${response.status()}`);
      }
    });
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('❌ 前端控制台错误:', msg.text());
      } else if (msg.text().includes('scan') || msg.text().includes('progress')) {
        console.log('📋 前端日志:', msg.text());
      }
    });
    
    // 导航到集群详情页面
    console.log('📋 导航到集群详情页面...');
    await page.goto('http://localhost:3000/#/clusters/1');
    
    // 等待页面加载
    await page.waitForTimeout(3000);
    
    console.log('🔍 查找扫描数据库按钮...');
    
    // 查找并点击"扫描数据库"按钮
    const scanButton = await page.locator('button:has-text("扫描数据库")').first();
    if (await scanButton.count() > 0) {
      console.log('✅ 找到扫描数据库按钮，点击...');
      await scanButton.click();
      
      // 等待扫描对话框出现
      await page.waitForTimeout(2000);
      
      console.log('🔍 查找扫描模式选项...');
      
      // 选择"扫描所有数据库"选项
      const allDatabasesRadio = await page.locator('input[value="all"]').first();
      if (await allDatabasesRadio.count() > 0) {
        console.log('✅ 选择扫描所有数据库...');
        await allDatabasesRadio.check();
      }
      
      // 点击开始扫描按钮
      const startScanButton = await page.locator('button:has-text("开始扫描")').first();
      if (await startScanButton.count() > 0) {
        console.log('🚀 开始扫描...');
        await startScanButton.click();
        
        // 等待进度对话框出现
        await page.waitForTimeout(3000);
        
        console.log('🔍 检查进度对话框是否出现...');
        
        // 检查进度对话框
        const progressDialog = await page.locator('[role="dialog"]:has-text("数据库扫描进度")').first();
        if (await progressDialog.count() > 0) {
          console.log('✅ 进度对话框已显示');
          
          // 检查进度条
          const progressBar = await page.locator('.el-progress').first();
          if (await progressBar.count() > 0) {
            console.log('✅ 进度条已显示');
          } else {
            console.log('❌ 进度条未找到');
          }
          
          // 检查日志区域
          const logsSection = await page.locator('.logs-section').first();
          if (await logsSection.count() > 0) {
            console.log('✅ 日志区域已显示');
            
            // 等待日志内容出现
            await page.waitForTimeout(5000);
            
            const logEntries = await page.locator('.log-entry').count();
            console.log(`📋 找到 ${logEntries} 条日志记录`);
          } else {
            console.log('❌ 日志区域未找到');
          }
          
          // 等待扫描完成或超时
          console.log('⏳ 等待扫描完成 (最多60秒)...');
          let scanCompleted = false;
          let attempts = 0;
          const maxAttempts = 30;
          
          while (attempts < maxAttempts && !scanCompleted) {
            await page.waitForTimeout(2000);
            attempts++;
            
            // 检查是否有"已完成"状态
            const completedTag = await page.locator('el-tag:has-text("已完成")').first();
            if (await completedTag.count() > 0) {
              console.log('✅ 扫描已完成！');
              scanCompleted = true;
            }
            
            // 检查进度百分比
            const progressText = await page.locator('.progress-text').first();
            if (await progressText.count() > 0) {
              const progressValue = await progressText.textContent();
              console.log(`📊 当前进度: ${progressValue}`);
              
              if (progressValue === '100%') {
                scanCompleted = true;
              }
            }
            
            console.log(`⏳ 等待扫描完成... (${attempts}/${maxAttempts})`);
          }
          
          if (scanCompleted) {
            console.log('🎉 扫描进度追踪功能测试成功！');
            
            // 检查最终统计
            const statsSection = await page.locator('.stats-section').first();
            if (await statsSection.count() > 0) {
              console.log('✅ 扫描统计信息已显示');
              
              const statistics = await page.locator('.el-statistic').all();
              for (const stat of statistics) {
                const title = await stat.locator('.el-statistic__head').textContent();
                const value = await stat.locator('.el-statistic__content').textContent();
                console.log(`📊 ${title}: ${value}`);
              }
            }
          } else {
            console.log('⚠️ 扫描未在预期时间内完成');
          }
          
        } else {
          console.log('❌ 进度对话框未出现');
        }
      } else {
        console.log('❌ 开始扫描按钮未找到');
      }
    } else {
      console.log('❌ 扫描数据库按钮未找到');
    }
    
    // 截图
    await page.screenshot({ path: 'scan-progress-test.png', fullPage: true });
    console.log('📸 已保存测试截图: scan-progress-test.png');
    
  } catch (error) {
    console.error('❌ 测试过程中出现错误:', error);
  } finally {
    await browser.close();
  }
})();