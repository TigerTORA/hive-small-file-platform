const { chromium } = require('playwright');

async function testTableDetailNavigation() {
  console.log('🚀 Starting table detail navigation tests...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 1000 // Slow down for better visibility
  });
  
  const context = await browser.newContext({
    viewport: { width: 1400, height: 900 }
  });
  
  const page = await context.newPage();

  try {
    // Step 1: Navigate to the application
    console.log('📍 Step 1: Loading application...');
    await page.goto('http://localhost:3003');
    await page.waitForLoadState('networkidle');
    
    // Step 2: Navigate to the tables page
    console.log('📍 Step 2: Navigating to tables page...');
    await page.click('text=表管理');
    await page.waitForLoadState('networkidle');
    
    // Wait for data to load
    await page.waitForTimeout(2000);
    
    // Step 3: Take screenshot of tables list page
    console.log('📍 Step 3: Taking screenshot of tables list...');
    await page.screenshot({
      path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/tables-list-page.png',
      fullPage: true
    });
    
    // Step 4: Look for table links and verify hover effects
    console.log('📍 Step 4: Checking for clickable table names...');
    
    // Wait for table data to load
    await page.waitForSelector('.table-name-link', { timeout: 10000 });
    
    const tableLinks = await page.locator('.table-name-link');
    const count = await tableLinks.count();
    console.log(`Found ${count} clickable table names`);
    
    if (count === 0) {
      console.log('⚠️ No table links found. Let me check for table data...');
      
      // Check if we need to trigger a scan first
      const scanButton = await page.locator('text=扫描表');
      if (await scanButton.isVisible()) {
        console.log('📍 Triggering table scan first...');
        
        // Select a cluster first
        const clusterSelect = await page.locator('.el-select');
        await clusterSelect.first().click();
        await page.waitForTimeout(500);
        
        // Select the first cluster option
        const clusterOption = await page.locator('.el-option');
        if (await clusterOption.count() > 0) {
          await clusterOption.first().click();
          await page.waitForTimeout(1000);
          
          // Click scan button
          await scanButton.click();
          console.log('📍 Scan triggered, waiting for data...');
          await page.waitForTimeout(5000);
          
          // Take screenshot after scan
          await page.screenshot({
            path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/tables-after-scan.png',
            fullPage: true
          });
          
          // Check for links again
          const linksAfterScan = await page.locator('.table-name-link');
          const newCount = await linksAfterScan.count();
          console.log(`Found ${newCount} table links after scan`);
        }
      }
    }
    
    // Step 5: Test hover effects on table names
    console.log('📍 Step 5: Testing hover effects...');
    const firstLink = await page.locator('.table-name-link').first();
    if (await firstLink.isVisible()) {
      await firstLink.hover();
      await page.waitForTimeout(500);
      
      // Take screenshot with hover effect
      await page.screenshot({
        path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/table-link-hover.png',
        fullPage: true
      });
      
      // Get table name for detail page navigation
      const tableName = await firstLink.innerText();
      console.log(`📍 Testing navigation to table: ${tableName}`);
      
      // Step 6: Click on table name to navigate to detail page
      console.log('📍 Step 6: Clicking table name to navigate to detail page...');
      await firstLink.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000); // Wait for data to load
      
      // Step 7: Verify we're on the table detail page
      console.log('📍 Step 7: Verifying table detail page loaded...');
      
      // Check for breadcrumb navigation
      const breadcrumb = await page.locator('.el-breadcrumb');
      if (await breadcrumb.isVisible()) {
        console.log('✅ Breadcrumb navigation found');
      } else {
        console.log('❌ Breadcrumb navigation not found');
      }
      
      // Check for table detail header
      const tableDetailHeader = await page.locator('text=表详情');
      if (await tableDetailHeader.isVisible()) {
        console.log('✅ Table detail header found');
      } else {
        console.log('❌ Table detail header not found');
      }
      
      // Step 8: Take screenshot of table detail page
      console.log('📍 Step 8: Taking screenshot of table detail page...');
      await page.screenshot({
        path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/table-detail-page.png',
        fullPage: true
      });
      
      // Step 9: Check for enhanced metadata sections
      console.log('📍 Step 9: Verifying enhanced metadata sections...');
      
      const sections = [
        { name: '基本信息', selector: 'text=基本信息' },
        { name: '文件统计', selector: 'text=文件统计' },
        { name: '扫描信息', selector: 'text=扫描信息' },
        { name: '智能优化建议', selector: 'text=智能优化建议' }
      ];
      
      for (const section of sections) {
        const element = await page.locator(section.selector);
        if (await element.isVisible()) {
          console.log(`✅ ${section.name} section found`);
        } else {
          console.log(`❌ ${section.name} section not found`);
        }
      }
      
      // Step 10: Check for different table type indicators
      console.log('📍 Step 10: Checking table type and format indicators...');
      
      // Look for storage format tag
      const storageFormatTags = await page.locator('.el-tag').allTextContents();
      console.log('Storage format and type tags found:', storageFormatTags);
      
      // Step 11: Check for optimization recommendations
      console.log('📍 Step 11: Checking for optimization recommendations...');
      const alerts = await page.locator('.el-alert');
      const alertCount = await alerts.count();
      console.log(`Found ${alertCount} optimization recommendations`);
      
      if (alertCount > 0) {
        // Take screenshot focusing on recommendations
        const recommendationsSection = await page.locator('text=智能优化建议').locator('..').locator('..');
        if (await recommendationsSection.isVisible()) {
          await recommendationsSection.scrollIntoViewIfNeeded();
          await page.screenshot({
            path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/optimization-recommendations.png',
            fullPage: true
          });
        }
        
        // Read recommendation texts
        for (let i = 0; i < Math.min(alertCount, 3); i++) {
          const alertTitle = await alerts.nth(i).locator('.el-alert__title').innerText();
          console.log(`Recommendation ${i + 1}: ${alertTitle}`);
        }
      }
      
      // Step 12: Test back navigation
      console.log('📍 Step 12: Testing back navigation...');
      const backButton = await page.locator('text=表管理').first();
      if (await backButton.isVisible()) {
        await backButton.click();
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000);
        
        // Verify we're back to the tables list
        const tablesHeader = await page.locator('text=表管理');
        if (await tablesHeader.isVisible()) {
          console.log('✅ Back navigation successful');
        } else {
          console.log('❌ Back navigation failed');
        }
        
        // Take screenshot of return to tables page
        await page.screenshot({
          path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/back-to-tables.png',
          fullPage: true
        });
      }
      
      // Step 13: Test navigation to different table types
      console.log('📍 Step 13: Testing different table types navigation...');
      
      const allLinks = await page.locator('.table-name-link');
      const linkCount = await allLinks.count();
      
      if (linkCount > 1) {
        // Navigate to second table if available
        console.log('Testing navigation to second table...');
        const secondLink = await allLinks.nth(1);
        const secondTableName = await secondLink.innerText();
        console.log(`Navigating to second table: ${secondTableName}`);
        
        await secondLink.click();
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(3000);
        
        // Take screenshot of second table detail
        await page.screenshot({
          path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/second-table-detail.png',
          fullPage: true
        });
        
        // Check if recommendations differ for different table types
        const secondTableAlerts = await page.locator('.el-alert');
        const secondAlertCount = await secondTableAlerts.count();
        console.log(`Second table has ${secondAlertCount} optimization recommendations`);
        
        if (secondAlertCount > 0) {
          for (let i = 0; i < Math.min(secondAlertCount, 2); i++) {
            const alertTitle = await secondTableAlerts.nth(i).locator('.el-alert__title').innerText();
            console.log(`Second table recommendation ${i + 1}: ${alertTitle}`);
          }
        }
      }
      
    } else {
      console.log('❌ No table links found to test navigation');
    }
    
    console.log('✅ Table detail navigation test completed!');
    
  } catch (error) {
    console.error('❌ Test failed:', error);
    await page.screenshot({
      path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/error-screenshot.png',
      fullPage: true
    });
  } finally {
    await browser.close();
  }
}

// Create test results directory
const fs = require('fs');
const path = require('path');
const testResultsDir = '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results';
if (!fs.existsSync(testResultsDir)) {
  fs.mkdirSync(testResultsDir, { recursive: true });
}

testTableDetailNavigation();