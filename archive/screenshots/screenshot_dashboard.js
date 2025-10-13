const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // 导航到仪表板页面
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });

    // 等待页面完全加载
    await page.waitForTimeout(3000);

    // 截取全页面屏幕截图
    await page.screenshot({
      path: '/Users/luohu/new_project/hive-small-file-platform/.playwright-mcp/dashboard-coldness-verification.png',
      fullPage: true
    });

    console.log('Dashboard screenshot saved successfully');
  } catch (error) {
    console.error('Error taking screenshot:', error);
  } finally {
    await browser.close();
  }
})();