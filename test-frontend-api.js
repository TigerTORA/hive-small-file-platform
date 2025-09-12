const { chromium } = require('playwright');

(async () => {
  console.log('🔍 测试前端API调用和数据显示');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    // 监听网络请求
    page.on('response', response => {
      if (response.url().includes('/api/v1/clusters')) {
        console.log(`📡 API请求: ${response.url()} - 状态: ${response.status()}`);
      }
    });
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('❌ 前端错误:', msg.text());
      }
    });
    
    // 访问集群管理页面
    console.log('📋 访问集群管理页面');
    await page.goto('http://localhost:3001/#/clusters');
    
    // 等待数据加载
    console.log('⏳ 等待数据加载...');
    await page.waitForTimeout(5000);
    
    // 检查页面元素
    const clusters = await page.locator('.cluster-card, .el-card').count();
    console.log(`📊 页面中的集群卡片数量: ${clusters}`);
    
    // 检查是否有加载指示器
    const loading = await page.locator('.el-loading').count();
    console.log(`⏳ 加载指示器数量: ${loading}`);
    
    // 检查是否有错误信息
    const errorMessages = await page.locator('.el-message--error').count();
    console.log(`❌ 错误消息数量: ${errorMessages}`);
    
    // 尝试手动刷新数据
    console.log('🔄 尝试刷新页面数据');
    await page.reload();
    await page.waitForTimeout(3000);
    
    const clustersAfterReload = await page.locator('.cluster-card, .el-card').count();
    console.log(`📊 刷新后的集群卡片数量: ${clustersAfterReload}`);
    
    // 检查页面内容
    const pageText = await page.textContent('body');
    if (pageText.includes('CDP-14')) {
      console.log('✅ 页面包含CDP-14集群数据');
    } else {
      console.log('❌ 页面不包含CDP-14集群数据');
    }
    
    if (pageText.includes('暂无集群')) {
      console.log('⚠️ 页面显示"暂无集群"消息');
    }
    
    // 尝试打开开发者工具网络面板检查
    await page.waitForTimeout(2000);
    
  } catch (error) {
    console.error('❌ 测试过程中出现错误:', error);
  } finally {
    await browser.close();
  }
})();