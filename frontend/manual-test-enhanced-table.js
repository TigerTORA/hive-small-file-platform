const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    console.log('正在导航到应用...');
    await page.goto('http://localhost:3002');
    await page.waitForLoadState('networkidle');
    
    // 等待页面完全加载
    await page.waitForTimeout(3000);
    
    console.log('截图首页...');
    await page.screenshot({ 
      path: 'test-results/01-homepage.png',
      fullPage: true 
    });
    
    console.log('导航到表管理页面...');
    // 尝试找到表管理链接
    const tablesLink = page.locator('text=表管理').or(page.locator('text=Tables')).or(page.locator('[href*="table"]'));
    if (await tablesLink.count() > 0) {
      await tablesLink.first().click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000);
      
      console.log('截图表管理页面...');
      await page.screenshot({ 
        path: 'test-results/02-tables-page.png',
        fullPage: true 
      });
      
      // 查找可点击的表名
      const clickableTableNames = page.locator('.table-name-link, .clickable-table-name, [class*="table-name"][class*="link"], a[href*="table"], .el-link');
      const count = await clickableTableNames.count();
      console.log(`找到 ${count} 个可能的可点击表名`);
      
      if (count > 0) {
        console.log('测试悬停效果...');
        await clickableTableNames.first().hover();
        await page.waitForTimeout(1000);
        
        await page.screenshot({ 
          path: 'test-results/03-table-name-hover.png',
          fullPage: true 
        });
        
        console.log('点击表名...');
        await clickableTableNames.first().click();
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(3000);
        
        console.log('截图表详情页面...');
        await page.screenshot({ 
          path: 'test-results/04-table-detail-page.png',
          fullPage: true 
        });
        
        // 检查URL变化
        const currentUrl = page.url();
        console.log(`当前URL: ${currentUrl}`);
        
      } else {
        console.log('没有找到可点击的表名，查找表格中的任何链接...');
        const allLinks = page.locator('a, .el-link, [role="button"], .clickable');
        const linkCount = await allLinks.count();
        console.log(`找到 ${linkCount} 个链接/可点击元素`);
        
        for (let i = 0; i < Math.min(linkCount, 5); i++) {
          const linkText = await allLinks.nth(i).textContent();
          console.log(`链接 ${i}: ${linkText}`);
        }
      }
    } else {
      console.log('没有找到表管理链接，查看当前页面内容...');
      const pageContent = await page.textContent('body');
      console.log('页面内容:', pageContent.substring(0, 500));
    }
    
    // 保持浏览器打开一段时间以便手动检查
    console.log('等待60秒以便手动检查...');
    await page.waitForTimeout(60000);
    
  } catch (error) {
    console.error('测试过程中出现错误:', error);
    await page.screenshot({ 
      path: 'test-results/error-screenshot.png',
      fullPage: true 
    });
  } finally {
    await browser.close();
  }
})();