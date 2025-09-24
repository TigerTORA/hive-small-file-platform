const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // 导航到主页面
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });

    // 等待页面加载
    await page.waitForTimeout(2000);

    // 查找并点击任务管理或其他可能的仪表板链接
    try {
      // 尝试点击任务管理
      await page.click('text=任务管理');
      await page.waitForTimeout(1000);
    } catch (e) {
      console.log('任务管理 not found, trying other options...');
    }

    // 如果没有找到任务管理，尝试直接访问可能的仪表板路由
    try {
      await page.goto('http://localhost:3000/dashboard', { waitUntil: 'networkidle' });
      await page.waitForTimeout(2000);
    } catch (e) {
      console.log('Dashboard route not accessible, trying tables route...');
      await page.goto('http://localhost:3000/tables', { waitUntil: 'networkidle' });
      await page.waitForTimeout(2000);
    }

    // 截取当前页面
    await page.screenshot({
      path: '/Users/luohu/new_project/hive-small-file-platform/.playwright-mcp/dashboard-with-charts.png',
      fullPage: true
    });

    // 尝试查找冷数据分布相关的元素
    const chartElements = await page.$$eval('*', els =>
      els.filter(el =>
        el.textContent?.includes('最后访问时间分布') ||
        el.textContent?.includes('冷数据') ||
        el.textContent?.includes('分布')
      ).map(el => ({
        tagName: el.tagName,
        textContent: el.textContent?.substring(0, 100),
        id: el.id,
        className: el.className
      }))
    );

    console.log('Found chart-related elements:', chartElements);

    console.log('Screenshot with charts saved successfully');
  } catch (error) {
    console.error('Error taking screenshot:', error);
  } finally {
    await browser.close();
  }
})();