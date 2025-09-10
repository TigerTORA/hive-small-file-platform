const { chromium } = require('playwright');
const path = require('path');

async function takeScreenshots() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Navigate to the frontend application
    console.log('Navigating to http://localhost:3000');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    
    // Wait for the page to load
    await page.waitForTimeout(3000);
    
    // Take screenshot of the initial page
    await page.screenshot({ 
      path: path.join(__dirname, 'screenshot-homepage.png'), 
      fullPage: true 
    });
    console.log('Screenshot saved: screenshot-homepage.png');
    
    // Navigate to Dashboard using Chinese text
    console.log('Navigating to Dashboard (监控仪表板)...');
    try {
      await page.click('text=监控仪表板', { timeout: 10000 });
      await page.waitForTimeout(3000);
      
      // Take screenshot of Dashboard
      await page.screenshot({ 
        path: path.join(__dirname, 'screenshot-dashboard.png'), 
        fullPage: true 
      });
      console.log('Screenshot saved: screenshot-dashboard.png');
      
      // Try to find and click table view tabs or buttons
      try {
        // Look for different possible table view selectors
        const selectors = [
          'text=表',
          'text=Table', 
          'text=表格',
          '[role="tab"]:has-text("表")',
          'button:has-text("表")',
          '.el-tabs__item:has-text("表")'
        ];
        
        for (let selector of selectors) {
          try {
            const element = await page.locator(selector).first();
            if (await element.isVisible({ timeout: 2000 })) {
              console.log(`Found table view with selector: ${selector}`);
              await element.click();
              await page.waitForTimeout(2000);
              
              // Take screenshot of table view
              await page.screenshot({ 
                path: path.join(__dirname, 'screenshot-table-view.png'), 
                fullPage: true 
              });
              console.log('Screenshot saved: screenshot-table-view.png');
              break;
            }
          } catch (e) {
            continue;
          }
        }
      } catch (e) {
        console.log('Table view button not found, continuing...');
      }
      
    } catch (e) {
      console.log('Dashboard navigation failed:', e.message);
    }
    
    // Navigate to Table Management page using Chinese text
    console.log('Navigating to Table Management (表管理)...');
    try {
      await page.click('text=表管理', { timeout: 10000 });
      await page.waitForTimeout(3000);
      
      // Take screenshot of Tables page
      await page.screenshot({ 
        path: path.join(__dirname, 'screenshot-tables.png'), 
        fullPage: true 
      });
      console.log('Screenshot saved: screenshot-tables.png');
      
    } catch (e) {
      console.log('Tables navigation failed:', e.message);
    }
    
    // Try to navigate directly to different routes
    console.log('Trying direct navigation routes...');
    const routes = [
      { path: '/dashboard', name: 'dashboard-direct' },
      { path: '/tables', name: 'tables-direct' },
      { path: '/clusters', name: 'clusters-direct' }
    ];
    
    for (let route of routes) {
      try {
        console.log(`Navigating to ${route.path}...`);
        await page.goto(`http://localhost:3000${route.path}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        
        await page.screenshot({ 
          path: path.join(__dirname, `screenshot-${route.name}.png`), 
          fullPage: true 
        });
        console.log(`Screenshot saved: screenshot-${route.name}.png`);
      } catch (e) {
        console.log(`Failed to navigate to ${route.path}:`, e.message);
      }
    }
    
  } catch (error) {
    console.error('Error taking screenshots:', error);
  } finally {
    await browser.close();
  }
}

takeScreenshots().catch(console.error);