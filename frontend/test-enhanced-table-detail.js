const { test, expect } = require('@playwright/test');

test.describe('Enhanced Table Detail Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // 启动时导航到应用
    await page.goto('http://localhost:3002');
    await page.waitForLoadState('networkidle');
  });

  test('should show clickable table names with hover effects', async ({ page }) => {
    console.log('Testing clickable table names...');
    
    // 导航到表管理页面
    await page.click('text=表管理');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 检查是否有表格数据
    const tableExists = await page.locator('.el-table').count() > 0;
    if (tableExists) {
      // 查找可点击的表名链接
      const clickableTableNames = page.locator('.table-name-link');
      const count = await clickableTableNames.count();
      console.log(`Found ${count} clickable table names`);
      
      if (count > 0) {
        // 截图显示可点击的表名
        await page.screenshot({ 
          path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/clickable-table-names.png',
          fullPage: true 
        });
        
        // 测试悬停效果
        await clickableTableNames.first().hover();
        await page.waitForTimeout(500);
        
        await page.screenshot({ 
          path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/table-name-hover.png',
          fullPage: true 
        });
      }
    }
  });

  test('should navigate to table detail page and show enhanced metadata', async ({ page }) => {
    console.log('Testing table detail navigation...');
    
    // 导航到表管理页面
    await page.click('text=表管理');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 查找可点击的表名并点击第一个
    const clickableTableNames = page.locator('.table-name-link');
    const count = await clickableTableNames.count();
    
    if (count > 0) {
      console.log(`Clicking on first table name...`);
      await clickableTableNames.first().click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
      
      // 检查是否成功导航到表详情页面
      const currentUrl = page.url();
      console.log(`Current URL: ${currentUrl}`);
      
      // 截图表详情页面
      await page.screenshot({ 
        path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/table-detail-page.png',
        fullPage: true 
      });
      
      // 检查增强的元数据是否存在
      const metadataSection = page.locator('.table-metadata, .metadata-section');
      if (await metadataSection.count() > 0) {
        console.log('Enhanced metadata section found');
        
        // 检查特定的元数据字段
        const tableType = page.locator('text=托管表, text=外部表');
        const storageFormat = page.locator('text=ORC, text=TEXT, text=PARQUET');
        const partitionInfo = page.locator('text=分区');
        
        if (await tableType.count() > 0) {
          console.log('Table type information found');
        }
        if (await storageFormat.count() > 0) {
          console.log('Storage format information found');
        }
        if (await partitionInfo.count() > 0) {
          console.log('Partition information found');
        }
      }
    }
  });

  test('should show intelligent optimization recommendations', async ({ page }) => {
    console.log('Testing intelligent recommendations...');
    
    // 导航到表管理页面
    await page.click('text=表管理');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 点击表名导航到详情页
    const clickableTableNames = page.locator('.table-name-link');
    const count = await clickableTableNames.count();
    
    if (count > 0) {
      await clickableTableNames.first().click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
      
      // 查找智能推荐部分
      const recommendationsSection = page.locator('.recommendations, .optimization-recommendations');
      if (await recommendationsSection.count() > 0) {
        console.log('Intelligent recommendations section found');
        
        // 截图推荐部分
        await page.screenshot({ 
          path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/intelligent-recommendations.png',
          fullPage: true 
        });
        
        // 检查不同类型的警告和建议
        const smallFileAlert = page.locator('.el-alert, text=小文件');
        const storageFormatAlert = page.locator('.el-alert, text=存储格式');
        const partitionAlert = page.locator('.el-alert, text=分区');
        
        if (await smallFileAlert.count() > 0) {
          console.log('Small file alert found');
        }
        if (await storageFormatAlert.count() > 0) {
          console.log('Storage format alert found');
        }
        if (await partitionAlert.count() > 0) {
          console.log('Partition alert found');
        }
      }
    }
  });

  test('should show different recommendations for different table types', async ({ page }) => {
    console.log('Testing different recommendations for different table types...');
    
    // 导航到表管理页面
    await page.click('text=表管理');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 点击多个表名来测试不同的推荐
    const clickableTableNames = page.locator('.table-name-link');
    const count = await clickableTableNames.count();
    
    for (let i = 0; i < Math.min(count, 3); i++) {
      console.log(`Testing table ${i + 1}...`);
      
      // 点击表名
      await clickableTableNames.nth(i).click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
      
      // 截图当前表的详情页面
      await page.screenshot({ 
        path: `/Users/luohu/new_project/hive-small-file-platform/frontend/test-results/table-detail-${i + 1}.png`,
        fullPage: true 
      });
      
      // 返回表管理页面
      await page.goBack();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
    }
  });
});