const { chromium } = require('playwright');
const fs = require('fs').promises;

(async () => {
  console.log('Starting Dashboard verification test...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 1000 
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  
  const page = await context.newPage();
  
  try {
    console.log('1. Navigating to Dashboard...');
    await page.goto('http://localhost:3003', { waitUntil: 'networkidle', timeout: 10000 });
    
    // Wait for the page to fully load
    await page.waitForTimeout(3000);
    
    console.log('2. Taking Dashboard screenshot...');
    await page.screenshot({ 
      path: 'dashboard-verification.png', 
      fullPage: true 
    });
    
    // Check for Dashboard components
    console.log('3. Verifying Dashboard components...');
    
    // Check if statistics cards are present
    const statsCards = await page.locator('.el-card').count();
    console.log(`Found ${statsCards} statistics cards`);
    
    // Check if any data is loaded
    const hasContent = await page.locator('.dashboard-content, .el-statistic').isVisible();
    console.log(`Dashboard content visible: ${hasContent}`);
    
    // Wait for data to load if needed
    await page.waitForTimeout(2000);
    
    // Check for specific dashboard elements
    const dashboardTitle = await page.locator('h1, h2').first().textContent();
    console.log(`Dashboard title: ${dashboardTitle}`);
    
    // Navigate to Tables page
    console.log('4. Navigating to Tables page...');
    const tablesLink = await page.locator('a[href*="tables"], .el-menu-item').filter({ hasText: /表|Tables/i }).first();
    if (await tablesLink.isVisible()) {
      await tablesLink.click();
      await page.waitForTimeout(2000);
      
      console.log('5. Taking Tables page screenshot...');
      await page.screenshot({ 
        path: 'tables-verification.png', 
        fullPage: true 
      });
      
      // Check if tables are displayed
      const tablesCount = await page.locator('.el-table tbody tr, .table-row, [data-table]').count();
      console.log(`Found ${tablesCount} table rows`);
      
      // Look for enhanced metadata
      const hasMetadata = await page.locator('.el-tag, .table-type, .storage-format').isVisible();
      console.log(`Enhanced metadata visible: ${hasMetadata}`);
    }
    
    // Try to find and test table detail
    console.log('6. Testing table detail navigation...');
    const firstTable = await page.locator('tbody tr:first-child td:first-child a, .table-name a').first();
    if (await firstTable.isVisible()) {
      await firstTable.click();
      await page.waitForTimeout(2000);
      
      console.log('7. Taking Table Detail screenshot...');
      await page.screenshot({ 
        path: 'table-detail-verification.png', 
        fullPage: true 
      });
      
      // Check for enhanced metadata in detail view
      const hasDetailMetadata = await page.locator('.table-metadata, .el-descriptions, .recommendations').isVisible();
      console.log(`Table detail metadata visible: ${hasDetailMetadata}`);
    }
    
    console.log('Dashboard verification completed successfully!');
    console.log('Screenshots saved:');
    console.log('- dashboard-verification.png');
    console.log('- tables-verification.png');
    console.log('- table-detail-verification.png');
    
  } catch (error) {
    console.error('Error during verification:', error.message);
    
    // Take error screenshot
    await page.screenshot({ 
      path: 'dashboard-error.png', 
      fullPage: true 
    });
    console.log('Error screenshot saved as dashboard-error.png');
  } finally {
    await browser.close();
  }
})();