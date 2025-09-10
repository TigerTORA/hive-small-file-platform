const { chromium } = require('playwright');

(async () => {
  console.log('Starting comprehensive Dashboard debugging...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 500 
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  
  const page = await context.newPage();
  
  // 监听控制台错误
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('🔴 Browser Error:', msg.text());
    } else if (msg.type() === 'warning') {
      console.log('🟡 Browser Warning:', msg.text());
    } else {
      console.log('📝 Console:', msg.text());
    }
  });
  
  // 监听网络错误
  page.on('response', response => {
    if (!response.ok()) {
      console.log(`🌐 Network Error: ${response.status()} ${response.url()}`);
    }
  });
  
  try {
    console.log('1. Navigating to Dashboard...');
    await page.goto('http://localhost:3003', { waitUntil: 'networkidle', timeout: 15000 });
    
    // 等待页面完全加载
    console.log('2. Waiting for initial load...');
    await page.waitForTimeout(3000);
    
    // 检查是否有任何元素加载
    console.log('3. Checking for basic elements...');
    const title = await page.title();
    console.log(`Page title: ${title}`);
    
    const headerText = await page.textContent('h1').catch(() => 'No h1 found');
    console.log(`Header text: ${headerText}`);
    
    // 检查 Dashboard 数据
    console.log('4. Checking Dashboard data visibility...');
    
    // 检查关键指标
    const totalTablesElement = await page.locator('.metric-value').first();
    const totalTablesVisible = await totalTablesElement.isVisible().catch(() => false);
    console.log(`Total tables metric visible: ${totalTablesVisible}`);
    
    if (totalTablesVisible) {
      const totalTablesText = await totalTablesElement.textContent();
      console.log(`Total tables value: ${totalTablesText}`);
    }
    
    // 检查是否有图表组件
    console.log('5. Checking for chart components...');
    const chartExists = await page.locator('canvas, .echarts, [id*="chart"]').count();
    console.log(`Chart elements found: ${chartExists}`);
    
    // 检查API调用状态
    console.log('6. Testing API calls directly...');
    const apiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/v1/dashboard/summary');
        const data = await response.json();
        return { status: response.status, data };
      } catch (error) {
        return { error: error.message };
      }
    });
    
    console.log('API Response:', JSON.stringify(apiResponse, null, 2));
    
    // 截图以查看当前状态
    console.log('7. Taking screenshot...');
    await page.screenshot({ 
      path: 'dashboard-debug.png', 
      fullPage: true 
    });
    
    // 检查 Vue 应用状态
    console.log('8. Checking Vue app state...');
    const vueAppStatus = await page.evaluate(() => {
      const app = document.querySelector('#app');
      if (app) {
        return {
          hasApp: true,
          innerHTML: app.innerHTML.substring(0, 500),
          children: app.children.length
        };
      }
      return { hasApp: false };
    });
    
    console.log('Vue app status:', vueAppStatus);
    
    // 等待更长时间看是否有延迟加载
    console.log('9. Waiting for potential delayed loading...');
    await page.waitForTimeout(5000);
    
    // 再次检查
    const finalCheck = await page.evaluate(() => {
      const metrics = document.querySelectorAll('.metric-value');
      const cards = document.querySelectorAll('.el-card');
      const charts = document.querySelectorAll('canvas, .echarts');
      
      return {
        metricsCount: metrics.length,
        cardsCount: cards.length,
        chartsCount: charts.length,
        metricsText: Array.from(metrics).map(m => m.textContent).slice(0, 3)
      };
    });
    
    console.log('Final check results:', finalCheck);
    
    // 最终截图
    await page.screenshot({ 
      path: 'dashboard-debug-final.png', 
      fullPage: true 
    });
    
    console.log('Debug completed successfully!');
    console.log('Screenshots saved:');
    console.log('- dashboard-debug.png');
    console.log('- dashboard-debug-final.png');
    
  } catch (error) {
    console.error('Error during debugging:', error.message);
    
    await page.screenshot({ 
      path: 'dashboard-debug-error.png', 
      fullPage: true 
    });
    console.log('Error screenshot saved as dashboard-debug-error.png');
  } finally {
    await browser.close();
  }
})();