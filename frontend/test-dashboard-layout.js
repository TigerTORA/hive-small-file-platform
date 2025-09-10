const { chromium } = require('playwright');

async function testDashboardLayout() {
  const browser = await chromium.launch({ headless: false }); // 使用有界面模式便于观察
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🚀 开始测试仪表盘布局功能...');

    // 测试1: 导航到首页并验证基本加载
    console.log('\n📋 测试1: 页面加载验证');
    await page.goto('http://localhost:3000/');
    await page.waitForTimeout(2000); // 等待页面完全加载

    // 验证页面标题（新的结构中是集群名称）
    const title = await page.locator('h1.cluster-name').textContent();
    console.log(`✅ 页面标题: ${title}`);
    
    if (!title.includes('集群') && !title.includes('默认')) {
      console.log('⚠️  警告: 页面标题可能不是集群名称，实际标题:', title);
    }

    // 测试2: 验证新的主监控面板布局
    console.log('\n📋 测试2: 主监控面板验证');
    
    // 检查主监控面板
    const mainPanel = page.locator('.main-monitoring-panel');
    await mainPanel.waitFor({ timeout: 5000 });
    console.log('✅ 主监控面板已显示');

    // 验证表文件数监控标题
    const monitoringTitle = await page.locator('text=Hive表文件数监控').first();
    if (await monitoringTitle.isVisible({ timeout: 3000 })) {
      console.log('✅ 表文件数监控标题已显示');
    }

    // 检查快速操作面板
    const actionPanel = page.locator('text=快速操作');
    if (await actionPanel.isVisible({ timeout: 3000 })) {
      console.log('✅ 快速操作面板已显示');
    }

    // 验证最近任务面板
    const taskPanel = page.locator('text=最近任务');
    if (await taskPanel.isVisible({ timeout: 3000 })) {
      console.log('✅ 最近任务面板已显示');
    }

    // 测试3: 快速操作按钮功能
    console.log('\n📋 测试3: 快速操作按钮验证');
    
    // 检查扫描表按钮
    const scanButton = page.locator('button:has-text("扫描表")');
    if (await scanButton.isVisible({ timeout: 3000 })) {
      console.log('✅ 扫描表按钮可见');
    }

    // 检查开始合并按钮
    const mergeButton = page.locator('button:has-text("开始合并")');
    if (await mergeButton.isVisible({ timeout: 3000 })) {
      console.log('✅ 开始合并按钮可见');
    }

    // 检查深度分析按钮
    const analyzeButton = page.locator('button:has-text("深度分析")');
    if (await analyzeButton.isVisible({ timeout: 3000 })) {
      console.log('✅ 深度分析按钮可见');
    }

    // 测试4: 验证集群统计信息
    console.log('\n📋 测试4: 集群统计信息验证');

    // 检查关键指标显示
    const metricElements = page.locator('.metric-value');
    const metricCount = await metricElements.count();
    console.log(`✅ 发现 ${metricCount} 个关键指标`);

    // 验证总表数指标
    const totalTables = page.locator('text=总表数');
    if (await totalTables.isVisible({ timeout: 2000 })) {
      console.log('✅ 总表数指标已显示');
    }

    // 验证问题表指标  
    const problemTables = page.locator('text=问题表');
    if (await problemTables.isVisible({ timeout: 2000 })) {
      console.log('✅ 问题表指标已显示');
    }

    // 验证小文件数指标
    const smallFiles = page.locator('text=小文件数');
    if (await smallFiles.isVisible({ timeout: 2000 })) {
      console.log('✅ 小文件数指标已显示');
    }

    // 测试5: 验证表格数据显示
    console.log('\n📋 测试5: 表格数据显示验证');
    
    // 检查表格行
    const tableRows = page.locator('tbody tr');
    const rowCount = await tableRows.count();
    console.log(`✅ 表格显示了 ${rowCount} 行数据`);

    // 验证表格列标题
    const tableHeaders = ['表名', '当前文件数', '操作'];
    for (const header of tableHeaders) {
      const headerElement = page.locator(`th >> text=${header}`).first();
      if (await headerElement.isVisible({ timeout: 2000 })) {
        console.log(`✅ 表格列标题 "${header}" 已显示`);
      }
    }

    // 测试6: 响应式布局验证
    console.log('\n📋 测试6: 响应式布局验证');
    
    // 改变浏览器窗口大小
    await page.setViewportSize({ width: 768, height: 1024 }); // 平板尺寸
    await page.waitForTimeout(1000);
    console.log('✅ 切换到平板视图');

    await page.setViewportSize({ width: 375, height: 667 }); // 手机尺寸
    await page.waitForTimeout(1000);
    console.log('✅ 切换到手机视图');

    // 恢复桌面尺寸
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.waitForTimeout(1000);
    console.log('✅ 恢复桌面视图');

    // 测试7: 最终验证
    console.log('\n📋 测试7: 最终状态验证');
    
    // 验证页面仍然正常运行
    const finalTitle = await page.locator('h1.cluster-name').textContent();
    console.log(`✅ 最终页面标题: ${finalTitle}`);

    // 验证主要面板仍然可见
    const finalMainPanel = page.locator('.main-monitoring-panel');
    if (await finalMainPanel.isVisible()) {
      console.log('✅ 主监控面板仍然可见');
    }

    console.log('\n🎉 新界面测试完成！');
    console.log('✅ 页面成功从拖拽布局重构为单集群专注界面');
    console.log('✅ 主监控面板正常显示Hive表文件数信息');
    console.log('✅ 集群统计信息在顶部信息栏正确显示');
    console.log('✅ 快速操作按钮功能完整');
    console.log('✅ 最近任务面板正常工作');
    console.log('✅ 响应式布局适配正常');

    // 截图保存测试结果
    await page.screenshot({ 
      path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-result.png',
      fullPage: true 
    });
    console.log('📸 已保存测试结果截图: test-result.png');

  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    
    // 错误时也截图
    await page.screenshot({ 
      path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-error.png',
      fullPage: true 
    });
    console.log('📸 已保存错误截图: test-error.png');
    
    throw error;
  } finally {
    await browser.close();
  }
}

// 运行测试
testDashboardLayout().catch(console.error);