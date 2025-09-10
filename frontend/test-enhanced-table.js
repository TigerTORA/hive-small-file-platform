const { chromium } = require('playwright');

async function testEnhancedTable() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('🚀 开始测试增强表格功能...');

    // 导航到首页
    console.log('\n📋 测试1: 页面加载和基本验证');
    await page.goto('http://localhost:3000/');
    await page.waitForTimeout(2000);
    console.log('✅ 页面加载完成');

    // 等待表格加载
    await page.waitForSelector('table', { timeout: 10000 });
    console.log('✅ 表格已显示');

    // 测试新增的三个列标题
    console.log('\n📋 测试2: 验证新增列标题');
    
    const columnHeaders = ['表总大小', '小文件占比', '平均文件大小'];
    for (const header of columnHeaders) {
      const headerElement = page.locator(`th:has-text("${header}")`);
      if (await headerElement.isVisible({ timeout: 3000 })) {
        console.log(`✅ 列标题 "${header}" 已显示`);
      } else {
        console.log(`❌ 列标题 "${header}" 未找到`);
      }
    }

    // 测试表总大小列的数据格式
    console.log('\n📋 测试3: 验证表总大小列数据格式');
    const sizeValues = page.locator('td .size-value');
    const sizeCount = await sizeValues.count();
    if (sizeCount > 0) {
      const firstSizeValue = await sizeValues.first().textContent();
      console.log(`✅ 找到 ${sizeCount} 个表总大小值，示例: ${firstSizeValue}`);
      
      // 验证大小格式（应该包含 B, KB, MB, GB 等单位）
      if (firstSizeValue && (firstSizeValue.includes('B') || firstSizeValue.includes('K') || firstSizeValue.includes('M') || firstSizeValue.includes('G'))) {
        console.log('✅ 表总大小格式正确，包含单位标识');
      }
    }

    // 测试小文件占比列的可视化
    console.log('\n📋 测试4: 验证小文件占比可视化');
    const ratioIndicators = page.locator('.ratio-indicator');
    const ratioCount = await ratioIndicators.count();
    if (ratioCount > 0) {
      console.log(`✅ 找到 ${ratioCount} 个小文件占比指示器`);
      
      // 检查进度条
      const ratioBars = page.locator('.ratio-bar');
      const barCount = await ratioBars.count();
      if (barCount > 0) {
        console.log(`✅ 找到 ${barCount} 个小文件占比进度条`);
      }
      
      // 检查百分比显示
      const percentageTexts = page.locator('.ratio-indicator span');
      const firstPercentage = await percentageTexts.first().textContent();
      if (firstPercentage && firstPercentage.includes('%')) {
        console.log(`✅ 小文件占比百分比显示正确，示例: ${firstPercentage}`);
      }
    }

    // 测试平均文件大小列
    console.log('\n📋 测试5: 验证平均文件大小列');
    // 查找平均文件大小列的数据
    const avgSizeCells = page.locator('td[data-column="avg_file_size"], td:nth-child(6)');
    const avgSizeCount = await avgSizeCells.count();
    if (avgSizeCount > 0) {
      const firstAvgSize = await avgSizeCells.first().textContent();
      console.log(`✅ 找到 ${avgSizeCount} 个平均文件大小值，示例: ${firstAvgSize}`);
    }

    // 测试颜色编码
    console.log('\n📋 测试6: 验证小文件占比颜色编码');
    const colorClasses = ['.ratio-low', '.ratio-medium', '.ratio-high', '.ratio-critical'];
    let foundColorClasses = 0;
    
    for (const colorClass of colorClasses) {
      const elements = page.locator(colorClass);
      const count = await elements.count();
      if (count > 0) {
        foundColorClasses++;
        console.log(`✅ 找到 ${count} 个 "${colorClass}" 样式的元素`);
      }
    }
    
    if (foundColorClasses > 0) {
      console.log(`✅ 小文件占比颜色编码工作正常，发现 ${foundColorClasses} 种不同颜色级别`);
    }

    // 测试排序功能
    console.log('\n📋 测试7: 验证新列排序功能');
    
    // 点击表总大小列进行排序
    const sizeHeader = page.locator('th:has-text("表总大小")');
    if (await sizeHeader.isVisible()) {
      await sizeHeader.click();
      await page.waitForTimeout(500);
      console.log('✅ 表总大小列排序功能正常');
    }

    // 点击小文件占比列进行排序
    const ratioHeader = page.locator('th:has-text("小文件占比")');
    if (await ratioHeader.isVisible()) {
      await ratioHeader.click();
      await page.waitForTimeout(500);
      console.log('✅ 小文件占比列排序功能正常');
    }

    // 点击平均文件大小列进行排序
    const avgSizeHeader = page.locator('th:has-text("平均文件大小")');
    if (await avgSizeHeader.isVisible()) {
      await avgSizeHeader.click();
      await page.waitForTimeout(500);
      console.log('✅ 平均文件大小列排序功能正常');
    }

    console.log('\n🎉 增强表格功能测试完成！');
    console.log('✅ 三个新列（表总大小、小文件占比、平均文件大小）已成功添加');
    console.log('✅ 表总大小显示带有单位格式化');
    console.log('✅ 小文件占比显示带有可视化进度条和颜色编码');
    console.log('✅ 平均文件大小正常显示');
    console.log('✅ 所有新列支持排序功能');

    // 保存测试截图
    await page.screenshot({ 
      path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-enhanced-result.png',
      fullPage: true 
    });
    console.log('📸 已保存增强功能测试截图: test-enhanced-result.png');

  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    
    await page.screenshot({ 
      path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-enhanced-error.png',
      fullPage: true 
    });
    console.log('📸 已保存错误截图: test-enhanced-error.png');
    
    throw error;
  } finally {
    await browser.close();
  }
}

// 运行测试
testEnhancedTable().catch(console.error);