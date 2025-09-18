const { chromium } = require("@playwright/test");

async function verifyClusterStatus() {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 1000,
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });

  const page = await context.newPage();

  // 监听网络请求
  page.on("request", (request) => {
    if (request.url().includes("/api/")) {
      console.log(`🌐 API请求: ${request.method()} ${request.url()}`);
    }
  });

  page.on("response", (response) => {
    if (response.url().includes("/api/")) {
      console.log(`📡 API响应: ${response.status()} ${response.url()}`);
    }
  });

  // 监听控制台消息
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      console.log(`❌ 控制台错误: ${msg.text()}`);
    }
  });

  try {
    console.log("🚀 开始验证集群状态指示器...");

    // 1. 直接访问集群管理页面
    console.log("📍 访问集群管理页面");
    await page.goto("http://localhost:3000/#/clusters", {
      waitUntil: "networkidle",
      timeout: 30000,
    });

    // 等待10秒确保组件完全加载
    console.log("⏱️  等待10秒确保页面完全加载...");
    await page.waitForTimeout(10000);

    // 检查页面标题
    const title = await page.title();
    const url = page.url();
    console.log(`📍 页面标题: ${title}`);
    console.log(`📍 页面URL: ${url}`);

    // 截图看看当前状态
    await page.screenshot({
      path: "/Users/luohu/new_project/hive-small-file-platform/frontend/docs/screenshots/screenshot-clusters-current.png",
      fullPage: true,
    });
    console.log("📸 已保存当前页面截图");

    // 检查页面DOM结构
    const bodyHTML = await page.locator("body").innerHTML();

    // 检查是否包含集群管理相关元素
    if (bodyHTML.includes("clusters-management")) {
      console.log("✅ 页面包含集群管理容器");
    } else {
      console.log("❌ 页面不包含集群管理容器");
    }

    if (bodyHTML.includes("添加集群")) {
      console.log('✅ 页面包含"添加集群"按钮');
    }

    if (bodyHTML.includes("ConnectionStatusIndicator")) {
      console.log("✅ 页面包含连接状态指示器组件");
    }

    // 尝试查找集群卡片
    const clusterCards = page.locator(".cluster-card");
    const cardCount = await clusterCards.count();
    console.log(`📊 找到集群卡片数量: ${cardCount}`);

    if (cardCount > 0) {
      console.log("✅ 发现集群卡片，开始验证连接状态指示器");

      for (let i = 0; i < cardCount; i++) {
        const card = clusterCards.nth(i);
        console.log(`\n📋 检查集群卡片 ${i + 1}:`);

        // 查找连接状态指示器
        const indicator = card.locator(".connection-status-indicator");
        if (await indicator.isVisible()) {
          console.log("  ✅ 找到连接状态指示器");

          // 查找服务指示器
          const serviceIndicators = indicator.locator(".service-indicator");
          const serviceCount = await serviceIndicators.count();
          console.log(`  📊 服务指示器数量: ${serviceCount}`);

          if (serviceCount >= 3) {
            console.log("  ✅ 包含预期的3个服务指示器");

            // 检查每个服务的状态点
            for (let j = 0; j < Math.min(3, serviceCount); j++) {
              const service = serviceIndicators.nth(j);
              const statusDot = service.locator(".status-dot");

              if (await statusDot.isVisible()) {
                const dotClass = await statusDot.getAttribute("class");
                const styles = await statusDot.evaluate((el) => {
                  const computed = window.getComputedStyle(el);
                  return {
                    backgroundColor: computed.backgroundColor,
                    boxShadow: computed.boxShadow,
                  };
                });

                console.log(`  📍 服务 ${j + 1} 状态点:`);
                console.log(`     - 类名: ${dotClass}`);
                console.log(`     - 背景色: ${styles.backgroundColor}`);
                console.log(`     - 阴影: ${styles.boxShadow}`);

                // 判断状态
                if (dotClass?.includes("status-success")) {
                  console.log(`     ✅ 服务 ${j + 1} 状态: 成功 (绿色)`);
                } else if (dotClass?.includes("status-error")) {
                  console.log(`     ❌ 服务 ${j + 1} 状态: 错误 (红色)`);
                } else if (dotClass?.includes("status-testing")) {
                  console.log(`     🟡 服务 ${j + 1} 状态: 测试中 (黄色)`);
                } else {
                  console.log(`     ⚪ 服务 ${j + 1} 状态: 未知 (灰色)`);
                }
              }
            }

            // 测试点击第一个指示器
            console.log("  🖱️  测试点击第一个状态指示器...");
            const firstIndicator = serviceIndicators.first();
            await firstIndicator.click();
            await page.waitForTimeout(2000);
            console.log("  ✅ 点击测试完成");
          } else {
            console.log(
              `  ❌ 服务指示器数量不足，期望3个，实际${serviceCount}个`,
            );
          }
        } else {
          console.log("  ❌ 未找到连接状态指示器");
        }
      }
    } else {
      console.log("⚠️  没有找到集群卡片");

      // 检查是否有空状态
      const emptyState = page.locator(".empty-state, .el-empty");
      if (await emptyState.isVisible()) {
        console.log("📝 页面显示空状态");
      }

      // 检查是否有加载状态
      const loading = page.locator('[v-loading="true"], .el-loading-mask');
      if (await loading.isVisible()) {
        console.log("⏳ 页面仍在加载中");
      }
    }

    // 最终截图
    await page.screenshot({
      path: "/Users/luohu/new_project/hive-small-file-platform/frontend/docs/screenshots/screenshot-final-result.png",
      fullPage: true,
    });
    console.log("📸 已保存最终结果截图");

    console.log("\n✅ 验证完成！");

    return {
      success: true,
      cardCount,
      screenshots: [
        "/Users/luohu/new_project/hive-small-file-platform/frontend/docs/screenshots/screenshot-clusters-current.png",
        "/Users/luohu/new_project/hive-small-file-platform/frontend/docs/screenshots/screenshot-final-result.png",
      ],
    };
  } catch (error) {
    console.error("❌ 验证过程中出现错误:", error);

    await page.screenshot({
      path: "/Users/luohu/new_project/hive-small-file-platform/frontend/docs/screenshots/screenshot-error-detailed.png",
      fullPage: true,
    });

    return {
      success: false,
      error: error.message,
      screenshots: [
        "/Users/luohu/new_project/hive-small-file-platform/frontend/docs/screenshots/screenshot-error-detailed.png",
      ],
    };
  } finally {
    console.log("🔍 保持浏览器打开5秒供观察...");
    await page.waitForTimeout(5000);

    await context.close();
    await browser.close();
  }
}

// 运行验证
verifyClusterStatus()
  .then((result) => {
    console.log("\n📋 最终验证结果:");
    console.log(JSON.stringify(result, null, 2));
  })
  .catch(console.error);
