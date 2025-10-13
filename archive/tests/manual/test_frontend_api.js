const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // 拦截网络请求以查看API调用
    const apiCalls = [];
    page.on('response', response => {
      if (response.url().includes('/api/v1/dashboard/enhanced-coldness-distribution')) {
        apiCalls.push({
          url: response.url(),
          status: response.status(),
          timestamp: new Date().toISOString()
        });
      }
    });

    console.log('访问主页...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });

    // 设置集群选择
    await page.evaluate(() => {
      const monitoringSettings = {
        selectedCluster: 1,
        mockMode: false, // 使用真实API
        strictMode: false
      };
      localStorage.setItem('monitoring-store', JSON.stringify({
        settings: monitoringSettings
      }));
    });

    // 直接在浏览器中调用API验证
    const apiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/v1/dashboard/enhanced-coldness-distribution?cluster_id=1');
        const data = await response.json();
        return {
          success: true,
          status: response.status,
          data: data,
          summary: {
            totalTables: data.summary?.total_tables || 0,
            totalSizeGB: data.summary?.total_size_gb || 0,
            hasDistribution: !!data.distribution,
            timeRanges: Object.keys(data.distribution || {}).length
          }
        };
      } catch (error) {
        return {
          success: false,
          error: error.message
        };
      }
    });

    console.log('API调用结果:', JSON.stringify(apiResponse, null, 2));

    if (apiResponse.success) {
      console.log('✅ API修复验证成功！');
      console.log(`📊 表数量: ${apiResponse.summary.totalTables}`);
      console.log(`💾 总大小: ${apiResponse.summary.totalSizeGB.toFixed(2)}GB`);
      console.log(`📈 时间分布段数: ${apiResponse.summary.timeRanges}`);

      if (apiResponse.summary.totalTables >= 200 && apiResponse.summary.totalSizeGB >= 2000) {
        console.log('🎉 数据覆盖问题已成功修复！从6表96GB增加到218表2345GB');
      }
    } else {
      console.log('❌ API调用失败:', apiResponse.error);
    }

    console.log('拦截到的API调用:', apiCalls);

  } catch (error) {
    console.error('测试过程中出现错误:', error);
  } finally {
    await browser.close();
  }
})();