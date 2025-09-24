const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // 导航到首页
    console.log('访问主页...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // 如果当前页面是集群管理页面，选择一个集群
    const currentTitle = await page.title();
    console.log('当前页面标题:', currentTitle);

    if (currentTitle.includes('集群管理') || await page.$('text=CDP-14')) {
      console.log('检测到集群管理页面，尝试选择集群...');

      // 查找并点击CDP-14集群的连接测试按钮（这会选择该集群）
      try {
        // 等待集群卡片加载
        await page.waitForSelector('.cluster-card', { timeout: 5000 });

        // 点击第一个集群的连接测试按钮来选择集群
        const testButton = await page.$('button:has-text("连接测试")');
        if (testButton) {
          console.log('点击连接测试按钮...');
          await testButton.click();
          await page.waitForTimeout(2000);
        }

        // 导航到仪表板
        console.log('导航到仪表板...');
        await page.goto('http://localhost:3000/#/', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);

      } catch (e) {
        console.log('自动选择集群失败，手动设置localStorage...');

        // 手动设置选择的集群到localStorage
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

        // 重新导航到仪表板
        await page.goto('http://localhost:3000/#/', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
      }
    }

    // 检查是否成功进入仪表板
    const finalTitle = await page.title();
    console.log('最终页面标题:', finalTitle);

    // 等待图表加载完成
    console.log('等待图表加载...');
    await page.waitForTimeout(5000);

    // 查找冷数据分布图表
    const coldnessChart = await page.$('text=最后访问时间分布');
    if (coldnessChart) {
      console.log('找到冷数据分布图表！');
    } else {
      console.log('未找到冷数据分布图表，但继续截图...');
    }

    // 截取全页面屏幕截图
    console.log('截取屏幕截图...');
    await page.screenshot({
      path: '/Users/luohu/new_project/hive-small-file-platform/.playwright-mcp/dashboard-coldness-final.png',
      fullPage: true
    });

    console.log('仪表板截图保存成功！');

    // 输出页面上的图表相关信息
    const chartInfo = await page.evaluate(() => {
      const charts = document.querySelectorAll('.chart-card h3');
      const chartTitles = Array.from(charts).map(chart => chart.textContent?.trim());

      // 查找冷数据相关的数字
      const coldDataElements = document.querySelectorAll('*');
      const coldDataTexts = Array.from(coldDataElements)
        .map(el => el.textContent)
        .filter(text => text && (text.includes('GB') || text.includes('表') || text.includes('分布')))
        .slice(0, 10); // 只取前10个避免太多内容

      return {
        chartTitles,
        coldDataTexts
      };
    });

    console.log('图表标题:', chartInfo.chartTitles);
    console.log('页面数据摘要:', chartInfo.coldDataTexts);

  } catch (error) {
    console.error('截图过程中出现错误:', error);
  } finally {
    await browser.close();
  }
})();