const { chromium } = require('playwright');

(async () => {
  console.log('🎯 最终验证：测试前端是否显示真实集群数据');
  
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    // 监听网络请求
    page.on('response', response => {
      if (response.url().includes('/api/v1/clusters')) {
        console.log(`📡 API请求: ${response.url()}`);
        console.log(`📡 响应状态: ${response.status()}`);
        console.log(`📡 响应头: ${JSON.stringify(response.headers())}`);
      }
    });
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('❌ 前端控制台错误:', msg.text());
      }
    });
    
    // 访问集群管理页面 (现在使用3000端口)
    console.log('📋 访问集群管理页面 http://localhost:3000/#/clusters');
    await page.goto('http://localhost:3000/#/clusters');
    
    // 等待数据加载
    console.log('⏳ 等待5秒数据加载...');
    await page.waitForTimeout(5000);
    
    // 检查页面中是否包含CDP-14数据
    const pageContent = await page.textContent('body');
    
    if (pageContent.includes('CDP-14')) {
      console.log('✅ 成功！页面显示了真实的CDP-14集群数据');
    } else {
      console.log('❌ 页面仍然没有显示CDP-14集群数据');
    }
    
    // 检查集群卡片数量
    const clusterCards = await page.locator('.cluster-card, .el-card').count();
    console.log(`📊 页面显示的集群卡片数量: ${clusterCards}`);
    
    // 尝试查找具体的集群名称
    const clusterNames = await page.locator('.cluster-name, .cluster-title h3, h3').allTextContents();
    console.log('📋 找到的集群名称:', clusterNames);
    
    // 检查是否有192.168.0.105（CDP-14的主机地址）
    if (pageContent.includes('192.168.0.105')) {
      console.log('✅ 页面包含CDP-14的主机地址');
    } else {
      console.log('❌ 页面不包含CDP-14的主机地址');
    }
    
    // 截图
    await page.screenshot({ path: 'cluster-verification.png', fullPage: true });
    console.log('📸 已保存页面截图: cluster-verification.png');
    
  } catch (error) {
    console.error('❌ 测试过程中出现错误:', error);
  } finally {
    await browser.close();
  }
})();