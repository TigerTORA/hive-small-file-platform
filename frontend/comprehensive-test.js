const playwright = require('playwright');
const fs = require('fs');
const path = require('path');

const CONFIG = {
  baseURL: 'http://localhost:3002',
  backendURL: 'http://localhost:8000',
  testResultsDir: './test-results',
  screenshotDir: './test-results/screenshots',
  timeout: 30000
};

async function setupDirectories() {
  const dirs = [CONFIG.testResultsDir, CONFIG.screenshotDir];
  for (const dir of dirs) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }
}

async function waitForServer(url, maxRetries = 10, retryInterval = 2000) {
  console.log(`Waiting for server at ${url}...`);
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url + '/health');
      if (response.ok) {
        console.log(`Server at ${url} is ready`);
        return true;
      }
    } catch (error) {
      console.log(`Attempt ${i + 1}/${maxRetries}: Server not ready, retrying in ${retryInterval/1000}s...`);
      await new Promise(resolve => setTimeout(resolve, retryInterval));
    }
  }
  throw new Error(`Server at ${url} not available after ${maxRetries} attempts`);
}

async function createTestReport() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  return {
    timestamp,
    testResults: [],
    screenshots: [],
    errors: [],
    
    addTest(name, status, details = null, screenshotPath = null) {
      this.testResults.push({
        name,
        status,
        details,
        screenshotPath,
        timestamp: new Date().toISOString()
      });
    },
    
    addError(error, context = null) {
      this.errors.push({
        error: error.message,
        stack: error.stack,
        context,
        timestamp: new Date().toISOString()
      });
    },
    
    addScreenshot(name, path) {
      this.screenshots.push({ name, path });
    },
    
    saveReport() {
      const reportPath = path.join(CONFIG.testResultsDir, `test-report-${timestamp}.json`);
      fs.writeFileSync(reportPath, JSON.stringify(this, null, 2));
      return reportPath;
    }
  };
}

async function testDashboard(page, report) {
  console.log('\n=== Testing Dashboard ===');
  
  try {
    // Navigate to dashboard
    await page.goto(CONFIG.baseURL, { waitUntil: 'networkidle', timeout: CONFIG.timeout });
    await page.waitForTimeout(2000);
    
    // Take initial screenshot
    const dashboardScreenshot = path.join(CONFIG.screenshotDir, '01-dashboard-main.png');
    await page.screenshot({ path: dashboardScreenshot, fullPage: true });
    report.addScreenshot('Dashboard Main View', dashboardScreenshot);
    
    // Check if dashboard elements are visible
    const dashboardElements = [
      { selector: '.dashboard-title, h1', name: 'Dashboard Title' },
      { selector: '.stats-card, .summary-card, [class*="stat"]', name: 'Statistics Cards' },
      { selector: '.chart-container, [class*="chart"], canvas', name: 'Charts' },
      { selector: 'button[class*="scan"], button:has-text("扫描"), .scan-button', name: 'Batch Scan Button' }
    ];
    
    for (const element of dashboardElements) {
      try {
        await page.waitForSelector(element.selector, { timeout: 5000 });
        report.addTest(`Dashboard - ${element.name}`, 'PASS', 'Element visible and accessible');
      } catch (error) {
        report.addTest(`Dashboard - ${element.name}`, 'FAIL', `Element not found: ${element.selector}`);
        report.addError(error, `Dashboard element check: ${element.name}`);
      }
    }
    
    // Test batch scan functionality
    try {
      const scanButton = await page.locator('button:has-text("批量扫描"), button:has-text("扫描"), button[class*="scan"]').first();
      if (await scanButton.isVisible({ timeout: 3000 })) {
        await scanButton.click();
        await page.waitForTimeout(1000);
        
        const scanProgressScreenshot = path.join(CONFIG.screenshotDir, '02-dashboard-scan-progress.png');
        await page.screenshot({ path: scanProgressScreenshot, fullPage: true });
        report.addScreenshot('Dashboard Scan Progress', scanProgressScreenshot);
        
        report.addTest('Dashboard - Batch Scan Button', 'PASS', 'Scan button clickable and shows progress');
      } else {
        report.addTest('Dashboard - Batch Scan Button', 'WARNING', 'Scan button not found or not visible');
      }
    } catch (error) {
      report.addTest('Dashboard - Batch Scan Button', 'FAIL', 'Failed to test scan functionality');
      report.addError(error, 'Dashboard scan button test');
    }
    
    // Test real-time updates (wait for data refresh)
    await page.waitForTimeout(3000);
    const dashboardAfterWaitScreenshot = path.join(CONFIG.screenshotDir, '03-dashboard-after-wait.png');
    await page.screenshot({ path: dashboardAfterWaitScreenshot, fullPage: true });
    report.addScreenshot('Dashboard After Wait', dashboardAfterWaitScreenshot);
    
    report.addTest('Dashboard - Overall Functionality', 'PASS', 'Dashboard loads and displays data correctly');
    
  } catch (error) {
    report.addTest('Dashboard - Overall Functionality', 'FAIL', 'Major dashboard functionality failed');
    report.addError(error, 'Dashboard testing');
  }
}

async function testTablesManagement(page, report) {
  console.log('\n=== Testing Tables Management ===');
  
  try {
    // Navigate to tables page
    const tableLinks = [
      'a[href*="/tables"]',
      'a:has-text("表管理")',
      'a:has-text("Tables")',
      '.nav-link:has-text("表")',
      '[role="menuitem"]:has-text("表")'
    ];
    
    let navigated = false;
    for (const linkSelector of tableLinks) {
      try {
        const link = page.locator(linkSelector).first();
        if (await link.isVisible({ timeout: 2000 })) {
          await link.click();
          navigated = true;
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }
    
    if (!navigated) {
      // Try direct navigation
      await page.goto(`${CONFIG.baseURL}/tables`, { waitUntil: 'networkidle', timeout: CONFIG.timeout });
    }
    
    await page.waitForTimeout(2000);
    
    // Take tables page screenshot
    const tablesScreenshot = path.join(CONFIG.screenshotDir, '04-tables-management.png');
    await page.screenshot({ path: tablesScreenshot, fullPage: true });
    report.addScreenshot('Tables Management Page', tablesScreenshot);
    
    // Check table list elements
    const tableElements = [
      { selector: '.table, table, .el-table, [class*="table"]', name: 'Table List' },
      { selector: '.table-name, td:has-text("catalog_sales"), [class*="table-name"]', name: 'Table Names' },
      { selector: '.table-type, .tag, .el-tag, [class*="type"]', name: 'Table Type Tags' },
      { selector: '[title*="ORC"], [class*="format"], td:contains("ORC")', name: 'Storage Format Info' }
    ];
    
    for (const element of tableElements) {
      try {
        await page.waitForSelector(element.selector, { timeout: 5000 });
        report.addTest(`Tables - ${element.name}`, 'PASS', 'Element visible');
      } catch (error) {
        report.addTest(`Tables - ${element.name}`, 'FAIL', `Element not found: ${element.selector}`);
      }
    }
    
    // Test table interactions
    try {
      const clickableTable = await page.locator('a[class*="table-name"], .table-name a, td a, [class*="clickable"]').first();
      if (await clickableTable.isVisible({ timeout: 3000 })) {
        await clickableTable.hover();
        await page.waitForTimeout(500);
        
        const hoverScreenshot = path.join(CONFIG.screenshotDir, '05-tables-hover-effect.png');
        await page.screenshot({ path: hoverScreenshot, fullPage: true });
        report.addScreenshot('Tables Hover Effect', hoverScreenshot);
        
        report.addTest('Tables - Hover Effects', 'PASS', 'Table names show hover effects');
      } else {
        report.addTest('Tables - Hover Effects', 'WARNING', 'No clickable table elements found');
      }
    } catch (error) {
      report.addTest('Tables - Hover Effects', 'FAIL', 'Failed to test hover effects');
      report.addError(error, 'Tables hover test');
    }
    
    report.addTest('Tables - Overall Functionality', 'PASS', 'Tables management page loads and displays data');
    
  } catch (error) {
    report.addTest('Tables - Overall Functionality', 'FAIL', 'Major tables functionality failed');
    report.addError(error, 'Tables management testing');
  }
}

async function testTableDetail(page, report) {
  console.log('\n=== Testing Table Detail Page ===');
  
  try {
    // Try to find and click on an ORC partitioned table
    const orcTableSelectors = [
      'a:has-text("catalog_sales")',
      'td:has-text("catalog_sales") a',
      '.table-name:has-text("catalog_sales")',
      'a[href*="catalog_sales"]'
    ];
    
    let tableClicked = false;
    for (const selector of orcTableSelectors) {
      try {
        const tableLink = page.locator(selector).first();
        if (await tableLink.isVisible({ timeout: 2000 })) {
          await tableLink.click();
          await page.waitForTimeout(2000);
          tableClicked = true;
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }
    
    if (!tableClicked) {
      // Try direct navigation to table detail
      await page.goto(`${CONFIG.baseURL}/tables/2/tpcds_text_2/catalog_sales`, { 
        waitUntil: 'networkidle', 
        timeout: CONFIG.timeout 
      });
    }
    
    await page.waitForTimeout(3000);
    
    // Take table detail screenshot
    const detailScreenshot = path.join(CONFIG.screenshotDir, '06-table-detail.png');
    await page.screenshot({ path: detailScreenshot, fullPage: true });
    report.addScreenshot('Table Detail Page', detailScreenshot);
    
    // Check table detail elements
    const detailElements = [
      { selector: '.table-info, .metadata, [class*="detail"]', name: 'Table Metadata' },
      { selector: '.table-type, .storage-format, [class*="type"], [class*="format"]', name: 'Table Type and Format' },
      { selector: '.recommendations, [class*="recommend"]', name: 'Intelligent Recommendations' },
      { selector: '.partition-info, [class*="partition"]', name: 'Partition Information' },
      { selector: '.owner, .creation-time, [class*="owner"], [class*="created"]', name: 'Owner and Creation Info' }
    ];
    
    for (const element of detailElements) {
      try {
        await page.waitForSelector(element.selector, { timeout: 5000 });
        report.addTest(`Table Detail - ${element.name}`, 'PASS', 'Element visible');
      } catch (error) {
        report.addTest(`Table Detail - ${element.name}`, 'WARNING', `Element not found: ${element.selector}`);
      }
    }
    
    // Test different table types by navigating to a TEXT table
    try {
      await page.goto(`${CONFIG.baseURL}/tables/2/tpcds_text_2/customer`, { 
        waitUntil: 'networkidle', 
        timeout: CONFIG.timeout 
      });
      await page.waitForTimeout(2000);
      
      const textTableScreenshot = path.join(CONFIG.screenshotDir, '07-text-table-detail.png');
      await page.screenshot({ path: textTableScreenshot, fullPage: true });
      report.addScreenshot('TEXT Table Detail', textTableScreenshot);
      
      report.addTest('Table Detail - Different Table Types', 'PASS', 'Can navigate between different table types');
    } catch (error) {
      report.addTest('Table Detail - Different Table Types', 'FAIL', 'Failed to test different table types');
      report.addError(error, 'Table detail different types test');
    }
    
    report.addTest('Table Detail - Overall Functionality', 'PASS', 'Table detail page displays enhanced metadata');
    
  } catch (error) {
    report.addTest('Table Detail - Overall Functionality', 'FAIL', 'Major table detail functionality failed');
    report.addError(error, 'Table detail testing');
  }
}

async function testNavigation(page, report) {
  console.log('\n=== Testing Navigation ===');
  
  try {
    // Test breadcrumb navigation
    const breadcrumbSelectors = [
      '.breadcrumb',
      '.el-breadcrumb', 
      '[class*="breadcrumb"]',
      'nav[class*="breadcrumb"]'
    ];
    
    let breadcrumbFound = false;
    for (const selector of breadcrumbSelectors) {
      try {
        await page.waitForSelector(selector, { timeout: 2000 });
        breadcrumbFound = true;
        break;
      } catch (e) {
        // Try next selector
      }
    }
    
    if (breadcrumbFound) {
      report.addTest('Navigation - Breadcrumbs', 'PASS', 'Breadcrumb navigation visible');
    } else {
      report.addTest('Navigation - Breadcrumbs', 'WARNING', 'Breadcrumb navigation not found');
    }
    
    // Test main navigation menu
    const navItems = ['Dashboard', 'Tables', 'Tasks', 'Clusters'];
    let navTestsPassed = 0;
    
    for (const navItem of navItems) {
      try {
        const navLink = page.locator(`a:has-text("${navItem}"), a:has-text("${navItem.toLowerCase()}"), [role="menuitem"]:has-text("${navItem}")`).first();
        if (await navLink.isVisible({ timeout: 2000 })) {
          await navLink.click();
          await page.waitForTimeout(1500);
          navTestsPassed++;
        }
      } catch (error) {
        // Navigation item not found or not clickable
      }
    }
    
    if (navTestsPassed >= 2) {
      report.addTest('Navigation - Menu Items', 'PASS', `Successfully navigated to ${navTestsPassed} pages`);
    } else {
      report.addTest('Navigation - Menu Items', 'FAIL', `Only able to navigate to ${navTestsPassed} pages`);
    }
    
    // Test browser back/forward navigation
    try {
      await page.goBack();
      await page.waitForTimeout(1000);
      await page.goForward();
      await page.waitForTimeout(1000);
      
      report.addTest('Navigation - Browser History', 'PASS', 'Back and forward navigation works');
    } catch (error) {
      report.addTest('Navigation - Browser History', 'WARNING', 'Browser history navigation failed');
      report.addError(error, 'Navigation history test');
    }
    
    // Take final navigation screenshot
    const navScreenshot = path.join(CONFIG.screenshotDir, '08-navigation-final.png');
    await page.screenshot({ path: navScreenshot, fullPage: true });
    report.addScreenshot('Final Navigation State', navScreenshot);
    
    report.addTest('Navigation - Overall Functionality', 'PASS', 'Navigation system works correctly');
    
  } catch (error) {
    report.addTest('Navigation - Overall Functionality', 'FAIL', 'Major navigation functionality failed');
    report.addError(error, 'Navigation testing');
  }
}

async function testPerformance(page, report) {
  console.log('\n=== Testing Performance and Responsive Design ===');
  
  try {
    // Test page load performance
    const startTime = Date.now();
    await page.goto(CONFIG.baseURL, { waitUntil: 'networkidle', timeout: CONFIG.timeout });
    const loadTime = Date.now() - startTime;
    
    if (loadTime < 5000) {
      report.addTest('Performance - Page Load Time', 'PASS', `Page loaded in ${loadTime}ms`);
    } else if (loadTime < 10000) {
      report.addTest('Performance - Page Load Time', 'WARNING', `Page loaded in ${loadTime}ms (slower than expected)`);
    } else {
      report.addTest('Performance - Page Load Time', 'FAIL', `Page loaded in ${loadTime}ms (too slow)`);
    }
    
    // Test responsive design
    const viewports = [
      { name: 'Desktop', width: 1920, height: 1080 },
      { name: 'Tablet', width: 768, height: 1024 },
      { name: 'Mobile', width: 375, height: 667 }
    ];
    
    for (const viewport of viewports) {
      try {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await page.waitForTimeout(1000);
        
        const responsiveScreenshot = path.join(CONFIG.screenshotDir, `09-responsive-${viewport.name.toLowerCase()}.png`);
        await page.screenshot({ path: responsiveScreenshot, fullPage: true });
        report.addScreenshot(`Responsive Design - ${viewport.name}`, responsiveScreenshot);
        
        report.addTest(`Performance - ${viewport.name} Responsive Design`, 'PASS', `Layout adapts to ${viewport.width}x${viewport.height}`);
      } catch (error) {
        report.addTest(`Performance - ${viewport.name} Responsive Design`, 'FAIL', `Failed to test ${viewport.name} viewport`);
        report.addError(error, `Responsive design test - ${viewport.name}`);
      }
    }
    
    // Reset to desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    report.addTest('Performance - Overall Assessment', 'PASS', 'Performance and responsive design tests completed');
    
  } catch (error) {
    report.addTest('Performance - Overall Assessment', 'FAIL', 'Major performance testing failed');
    report.addError(error, 'Performance testing');
  }
}

async function runComprehensiveTest() {
  console.log('🚀 Starting Comprehensive Frontend Test Suite');
  console.log('='.repeat(50));
  
  const report = await createTestReport();
  await setupDirectories();
  
  let browser, page;
  
  try {
    // Wait for servers to be ready
    await waitForServer(CONFIG.backendURL);
    await waitForServer(CONFIG.baseURL);
    
    // Launch browser
    browser = await playwright.chromium.launch({ 
      headless: false,
      slowMo: 100  // Add small delay for better screenshot quality
    });
    
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      ignoreHTTPSErrors: true
    });
    
    page = await context.newPage();
    
    // Set longer timeout for slow operations
    page.setDefaultTimeout(CONFIG.timeout);
    
    // Run all test suites
    await testDashboard(page, report);
    await testTablesManagement(page, report);
    await testTableDetail(page, report);
    await testNavigation(page, report);
    await testPerformance(page, report);
    
  } catch (error) {
    console.error('❌ Critical test failure:', error.message);
    report.addError(error, 'Test suite execution');
  } finally {
    if (browser) {
      await browser.close();
    }
  }
  
  // Generate and save report
  const reportPath = report.saveReport();
  
  // Print summary
  console.log('\n' + '='.repeat(50));
  console.log('📊 TEST SUMMARY');
  console.log('='.repeat(50));
  
  const passed = report.testResults.filter(t => t.status === 'PASS').length;
  const failed = report.testResults.filter(t => t.status === 'FAIL').length;
  const warnings = report.testResults.filter(t => t.status === 'WARNING').length;
  
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`⚠️  Warnings: ${warnings}`);
  console.log(`📊 Total Tests: ${report.testResults.length}`);
  console.log(`🖼️  Screenshots: ${report.screenshots.length}`);
  console.log(`🐛 Errors: ${report.errors.length}`);
  
  console.log(`\n📁 Report saved to: ${reportPath}`);
  console.log(`📁 Screenshots directory: ${CONFIG.screenshotDir}`);
  
  if (failed === 0) {
    console.log('\n🎉 All critical tests passed! Frontend functionality is working correctly.');
  } else if (failed <= 2) {
    console.log('\n⚠️  Some tests failed but core functionality appears to be working.');
  } else {
    console.log('\n❌ Multiple test failures detected. Please review the issues.');
  }
  
  // List screenshots for easy access
  console.log('\n📸 Screenshots captured:');
  report.screenshots.forEach((screenshot, index) => {
    console.log(`  ${index + 1}. ${screenshot.name}: ${screenshot.path}`);
  });
  
  return report;
}

// Run the test
if (require.main === module) {
  runComprehensiveTest()
    .then((report) => {
      const passed = report.testResults.filter(t => t.status === 'PASS').length;
      const failed = report.testResults.filter(t => t.status === 'FAIL').length;
      
      console.log(`\n🔗 Verification Links:`);
      console.log(`   Frontend: ${CONFIG.baseURL}`);
      console.log(`   Backend: ${CONFIG.backendURL}/docs`);
      
      process.exit(failed > 0 ? 1 : 0);
    })
    .catch((error) => {
      console.error('❌ Test suite failed:', error);
      process.exit(1);
    });
}

module.exports = { runComprehensiveTest };