const { chromium } = require('playwright');
const path = require('path');

async function captureTableDetails() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Navigate to tables page
    console.log('Navigating to tables page...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    // Click on table management
    await page.click('text=表管理');
    await page.waitForTimeout(3000);
    
    // Take a screenshot focused on the table headers
    const tableContainer = await page.locator('.el-table');
    if (await tableContainer.isVisible()) {
      await tableContainer.screenshot({ 
        path: path.join(__dirname, 'table-headers-detail.png')
      });
      console.log('Table headers screenshot saved: table-headers-detail.png');
    }
    
    // Take a screenshot of just the first few rows to show the data
    await page.screenshot({ 
      path: path.join(__dirname, 'table-data-sample.png'),
      clip: { x: 250, y: 0, width: 1200, height: 600 }
    });
    console.log('Table data sample screenshot saved: table-data-sample.png');
    
  } catch (error) {
    console.error('Error capturing table details:', error);
  } finally {
    await browser.close();
  }
}

captureTableDetails().catch(console.error);