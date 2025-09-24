const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // 绕过路由守卫，直接设置localStorage
    console.log('访问主页并设置集群选择...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });

    // 直接在localStorage中设置选择的集群
    await page.evaluate(() => {
      const monitoringSettings = {
        selectedCluster: 1,
        mockMode: true,
        strictMode: false
      };
      localStorage.setItem('monitoring-store', JSON.stringify({
        settings: monitoringSettings
      }));
    });

    console.log('强制导航到仪表板...');
    // 强制导航到根路径（仪表板）
    await page.goto('http://localhost:3000/#/', { waitUntil: 'networkidle' });

    // 等待更长时间让页面加载
    await page.waitForTimeout(5000);

    // 检查页面内容
    const pageContent = await page.evaluate(() => {
      return {
        title: document.title,
        hasCharts: !!document.querySelector('.chart-card'),
        hasColdness: !!document.querySelector('*[text*="最后访问时间分布"]') ||
                     document.body.textContent.includes('最后访问时间分布'),
        hasDashboard: document.body.textContent.includes('监控中心') ||
                     document.body.textContent.includes('总文件数') ||
                     document.body.textContent.includes('小文件比例'),
        bodyText: document.body.textContent.substring(0, 500)
      };
    });

    console.log('页面分析:', pageContent);

    // 如果仍然不是仪表板，尝试点击左侧导航
    if (!pageContent.hasDashboard) {
      console.log('尝试点击任务管理菜单...');
      const taskMenu = await page.$('[data-name="任务管理"]');
      if (taskMenu) {
        await taskMenu.click();
        await page.waitForTimeout(2000);
      }

      // 再次检查是否有监控相关的菜单
      const menuItems = await page.$$eval('.el-menu-item', items =>
        items.map(item => item.textContent?.trim()).filter(text =>
          text?.includes('监控') || text?.includes('仪表') || text?.includes('Dashboard')
        )
      );
      console.log('找到的菜单项:', menuItems);
    }

    // 无论如何都截图
    console.log('截取当前页面...');
    await page.screenshot({
      path: '/Users/luohu/new_project/hive-small-file-platform/.playwright-mcp/dashboard-forced-screenshot.png',
      fullPage: true
    });

    // 获取最终页面状态
    const finalState = await page.evaluate(() => {
      const chartElements = Array.from(document.querySelectorAll('*')).filter(el =>
        el.textContent?.includes('最后访问时间分布') ||
        el.textContent?.includes('冷数据') ||
        el.textContent?.includes('GB') && el.textContent?.includes('总')
      );

      return {
        title: document.title,
        url: window.location.href,
        chartElementsCount: chartElements.length,
        chartTexts: chartElements.slice(0, 5).map(el => el.textContent?.substring(0, 100)),
        hasVisibleCharts: document.querySelectorAll('.chart-card').length,
        totalGBElements: Array.from(document.querySelectorAll('*')).filter(el =>
          el.textContent?.includes('GB') && el.textContent?.match(/\d+.*GB/)
        ).slice(0, 5).map(el => el.textContent?.trim())
      };
    });

    console.log('最终页面状态:', finalState);

    if (finalState.hasVisibleCharts > 0) {
      console.log('✅ 成功找到图表！');
    } else {
      console.log('❌ 未找到预期的图表');
    }

    console.log('截图已保存');

  } catch (error) {
    console.error('执行过程中出现错误:', error);
  } finally {
    await browser.close();
  }
})();