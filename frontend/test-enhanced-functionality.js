const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    console.log("=== 测试增强的表详情功能 ===");

    console.log("1. 导航到应用首页...");
    await page.goto("http://localhost:3002");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: "test-results/01-homepage-updated.png",
      fullPage: true,
    });

    console.log("2. 导航到表管理页面...");
    // 点击表管理菜单
    await page.click("text=表管理");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);

    await page.screenshot({
      path: "test-results/02-tables-page-updated.png",
      fullPage: true,
    });

    console.log("3. 检查可点击的表名...");
    // 查找表名链接
    const tableNameLinks = page.locator(".table-name-link");
    const linkCount = await tableNameLinks.count();
    console.log(`找到 ${linkCount} 个可点击的表名`);

    if (linkCount > 0) {
      console.log("4. 测试悬停效果...");
      // 悬停在第一个表名上
      await tableNameLinks.first().hover();
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: "test-results/03-table-name-hover-effect.png",
        fullPage: true,
      });

      console.log("5. 点击表名导航到详情页...");
      // 获取第一个表名的文本内容以便后续验证
      const firstTableText = await tableNameLinks.first().textContent();
      console.log(`点击表名: ${firstTableText}`);

      await tableNameLinks.first().click();
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(3000);

      // 验证是否成功导航到详情页面
      const currentUrl = page.url();
      console.log(`当前URL: ${currentUrl}`);

      if (currentUrl.includes("/tables/")) {
        console.log("✅ 成功导航到表详情页面");

        await page.screenshot({
          path: "test-results/04-table-detail-enhanced.png",
          fullPage: true,
        });

        console.log("6. 检查增强的元数据信息...");
        // 检查基本信息部分
        const basicInfoSection = page.locator("text=基本信息");
        if ((await basicInfoSection.count()) > 0) {
          console.log("✅ 找到基本信息部分");
        }

        // 检查表类型信息
        const managedTableTag = page.locator(
          '.el-tag:has-text("托管表"), .el-tag:has-text("外部表")',
        );
        if ((await managedTableTag.count()) > 0) {
          const tableType = await managedTableTag.first().textContent();
          console.log(`✅ 表类型: ${tableType}`);
        }

        // 检查存储格式
        const storageFormatTags = page.locator(
          '.el-tag:has-text("ORC"), .el-tag:has-text("TEXT"), .el-tag:has-text("PARQUET")',
        );
        if ((await storageFormatTags.count()) > 0) {
          const storageFormat = await storageFormatTags.first().textContent();
          console.log(`✅ 存储格式: ${storageFormat}`);
        }

        // 检查分区信息
        const partitionTag = page.locator(
          '.el-tag:has-text("是"), .el-tag:has-text("否")',
        );
        if ((await partitionTag.count()) > 0) {
          const partitionInfo = await partitionTag.first().textContent();
          console.log(`✅ 分区表: ${partitionInfo}`);
        }

        console.log("7. 检查智能优化建议...");
        // 检查优化建议部分
        const recommendationsSection = page.locator("text=智能优化建议");
        if ((await recommendationsSection.count()) > 0) {
          console.log("✅ 找到智能优化建议部分");

          // 检查小文件警告
          const smallFileAlert = page.locator(
            '.el-alert:has-text("小文件问题")',
          );
          if ((await smallFileAlert.count()) > 0) {
            console.log("✅ 找到小文件问题警告");
          }

          // 检查存储格式建议
          const storageAlert = page.locator('.el-alert:has-text("存储格式")');
          if ((await storageAlert.count()) > 0) {
            console.log("✅ 找到存储格式建议");
          }

          // 检查分区优化建议
          const partitionAlert = page.locator('.el-alert:has-text("分区优化")');
          if ((await partitionAlert.count()) > 0) {
            console.log("✅ 找到分区优化建议");
          }

          // 检查健康状态
          const healthAlert = page.locator('.el-alert:has-text("表状态健康")');
          if ((await healthAlert.count()) > 0) {
            console.log("✅ 表状态健康");
          }

          await page.screenshot({
            path: "test-results/05-intelligent-recommendations-detailed.png",
            fullPage: true,
          });
        }

        console.log("8. 测试返回表管理页面...");
        // 点击面包屑导航返回表管理页面
        const tablesLink = page.locator(
          '.el-breadcrumb-item:has-text("表管理") a',
        );
        if ((await tablesLink.count()) > 0) {
          await tablesLink.click();
          await page.waitForLoadState("networkidle");
          await page.waitForTimeout(2000);

          await page.screenshot({
            path: "test-results/06-back-to-tables.png",
            fullPage: true,
          });
          console.log("✅ 成功返回表管理页面");
        }

        console.log("9. 测试多个不同表的详情页面...");
        // 测试多个表以验证不同的推荐内容
        const maxTablesToTest = Math.min(linkCount, 3);
        for (let i = 1; i < maxTablesToTest; i++) {
          console.log(`测试表 ${i + 1}...`);

          const tableNameLinks = page.locator(".table-name-link");
          const tableName = await tableNameLinks.nth(i).textContent();
          console.log(`点击表名: ${tableName}`);

          await tableNameLinks.nth(i).click();
          await page.waitForLoadState("networkidle");
          await page.waitForTimeout(2000);

          await page.screenshot({
            path: `test-results/07-table-detail-${i + 1}-${tableName?.replace(/[^a-zA-Z0-9]/g, "_")}.png`,
            fullPage: true,
          });

          // 返回表管理页面
          const backButton = page.locator(
            '.el-breadcrumb-item:has-text("表管理") a',
          );
          if ((await backButton.count()) > 0) {
            await backButton.click();
            await page.waitForLoadState("networkidle");
            await page.waitForTimeout(1000);
          } else {
            await page.goBack();
            await page.waitForLoadState("networkidle");
            await page.waitForTimeout(1000);
          }
        }
      } else {
        console.log("❌ 未能成功导航到表详情页面");
      }
    } else {
      console.log("❌ 没有找到可点击的表名链接");
    }

    console.log("=== 测试完成 ===");
    console.log("请查看 test-results/ 目录中的截图以验证功能");

    // 保持浏览器打开30秒供手动检查
    console.log("浏览器将在30秒后关闭，您可以手动检查功能...");
    await page.waitForTimeout(30000);
  } catch (error) {
    console.error("测试过程中出现错误:", error);
    await page.screenshot({
      path: "test-results/error-final.png",
      fullPage: true,
    });
  } finally {
    await browser.close();
  }
})();
