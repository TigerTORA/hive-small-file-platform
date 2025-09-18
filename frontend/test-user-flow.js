const { test, expect, chromium } = require("@playwright/test");

(async () => {
  let browser;
  let context;
  let page;

  try {
    console.log("🚀 启动用户流程测试...\n");

    // 启动浏览器
    browser = await chromium.launch({
      headless: false, // 设置为 false 可以看到浏览器操作
      slowMo: 1000, // 减慢操作速度便于观察
    });

    context = await browser.newContext();
    page = await context.newPage();

    // 监听控制台日志
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        console.log("❌ 控制台错误:", msg.text());
      }
    });

    // 监听请求
    page.on("request", (request) => {
      if (request.url().includes("/api/")) {
        console.log("🌐 API请求:", request.method(), request.url());
      }
    });

    // 监听响应
    page.on("response", (response) => {
      if (response.url().includes("/api/") && !response.ok()) {
        console.log("❌ API响应错误:", response.status(), response.url());
      }
    });

    console.log("1️⃣ 测试访问根路径 http://localhost:3002/");
    await page.goto("http://localhost:3002/");

    // 等待页面加载完成
    await page.waitForLoadState("networkidle");

    // 检查当前URL
    const currentUrl = page.url();
    console.log("📍 当前URL:", currentUrl);

    // 验证是否重定向到集群管理页面
    if (currentUrl.includes("/clusters")) {
      console.log("✅ 成功重定向到集群管理页面");

      // 检查是否有集群选择提示
      const noticeExists =
        (await page.locator(".cluster-selection-notice").count()) > 0;
      if (noticeExists) {
        console.log("✅ 显示集群选择提示");

        // 检查提示内容
        const noticeText = await page
          .locator(".cluster-selection-notice .notice-text h4")
          .textContent();
        console.log("💡 提示内容:", noticeText);
      }

      // 等待集群数据加载
      console.log("⏳ 等待集群数据加载...");
      await page.waitForTimeout(3000);

      // 查找集群卡片
      const clusterCards = await page.locator(".cluster-card").count();
      console.log(`🏢 找到 ${clusterCards} 个集群`);

      if (clusterCards > 0) {
        console.log("2️⃣ 选择第一个集群");

        // 获取第一个集群的名称
        const clusterName = await page
          .locator(".cluster-card .cluster-name")
          .first()
          .textContent();
        console.log(`🎯 选择集群: ${clusterName}`);

        // 点击第一个集群卡片
        await page.locator(".cluster-card").first().click();

        // 等待跳转
        await page.waitForTimeout(2000);

        // 检查是否成功跳转回监控中心
        const newUrl = page.url();
        console.log("📍 跳转后URL:", newUrl);

        if (newUrl.includes("/#/") && !newUrl.includes("clusters")) {
          console.log("✅ 成功重定向回监控中心");

          console.log("3️⃣ 验证监控中心页面内容");

          // 等待监控中心加载
          await page.waitForTimeout(5000);

          // 检查页面标题
          const pageTitle = await page
            .locator(".dashboard-title")
            .textContent();
          console.log("📋 页面标题:", pageTitle);

          // 检查是否显示业务价值指标
          const valueMetrics = await page
            .locator(".value-metrics-grid .cloudera-metric-card")
            .count();
          console.log(`📊 业务价值指标卡片数量: ${valueMetrics}`);

          if (valueMetrics > 0) {
            console.log("✅ 监控中心正常显示业务价值指标");

            // 检查每个指标卡片的内容
            for (let i = 0; i < Math.min(valueMetrics, 4); i++) {
              const card = page
                .locator(".value-metrics-grid .cloudera-metric-card")
                .nth(i);
              const label = await card.locator(".metric-label").textContent();
              const value = await card.locator(".metric-value").textContent();
              console.log(`  📈 指标 ${i + 1}: ${label} - ${value}`);
            }

            console.log("4️⃣ 测试集群切换器功能");

            // 查找集群切换器
            const clusterSwitcher = await page
              .locator(".cluster-switcher")
              .count();
            if (clusterSwitcher > 0) {
              console.log("✅ 找到集群切换器");

              // 点击集群切换器
              await page.locator(".cluster-switcher .el-select").click();
              await page.waitForTimeout(1000);

              // 检查下拉选项
              const options = await page
                .locator(".el-select-dropdown__item")
                .count();
              console.log(`🔄 集群切换选项数量: ${options}`);

              if (options > 1) {
                console.log("✅ 集群切换器功能正常");

                // 选择另一个集群（如果存在）
                await page.locator(".el-select-dropdown__item").nth(1).click();
                await page.waitForTimeout(2000);

                console.log("✅ 测试切换到其他集群成功");
              }
            } else {
              console.log("⚠️ 未找到集群切换器");
            }

            console.log("5️⃣ 检查localStorage中的集群状态");

            // 检查localStorage
            const selectedCluster = await page.evaluate(() => {
              return localStorage.getItem("monitoring-store");
            });

            if (selectedCluster) {
              console.log("✅ localStorage中保存了集群选择状态");
              const clusterData = JSON.parse(selectedCluster);
              console.log(
                "💾 存储的集群ID:",
                clusterData.settings?.selectedCluster,
              );
            } else {
              console.log("⚠️ localStorage中未找到集群状态");
            }
          } else {
            console.log("❌ 监控中心未显示业务价值指标");
          }
        } else {
          console.log("❌ 未能成功重定向回监控中心");
          console.log("🔍 当前URL:", newUrl);
        }
      } else {
        console.log("❌ 未找到可选择的集群");

        // 检查是否有空状态提示
        const emptyState = await page.locator(".empty-state").count();
        if (emptyState > 0) {
          console.log("ℹ️ 显示空状态提示（暂无集群数据）");
        }
      }
    } else {
      console.log("❌ 未能重定向到集群管理页面");
      console.log("🔍 实际URL:", currentUrl);
    }

    // 截图记录
    console.log("📸 保存测试截图...");
    await page.screenshot({ path: "test-results.png", fullPage: true });

    console.log("\n🎉 用户流程测试完成！");
  } catch (error) {
    console.error("❌ 测试过程中出现错误:", error);

    // 错误截图
    if (page) {
      await page.screenshot({ path: "test-error.png", fullPage: true });
    }
  } finally {
    if (browser) {
      await browser.close();
    }
  }
})();
