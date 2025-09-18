import { test, expect } from "@playwright/test";

test("对接真实后端：创建集群并可见", async ({ page }) => {
  await page.goto("/#/clusters");

  // 打开创建对话框
  await page.getByRole("button", { name: "添加集群" }).click();

  // 填写表单（后端仅做URL前缀校验）
  await page.getByLabel("集群名称").fill("E2E-REAL");
  await page.getByLabel("Hive 主机").fill("localhost");
  await page.getByLabel("MetaStore URL").fill("sqlite:///./e2e_metastore.db");
  await page
    .getByLabel("HDFS/HttpFS 地址")
    .fill("http://localhost:9870/webhdfs/v1");

  // 创建
  await page.getByRole("button", { name: "创建" }).click();

  // 断言：集群卡片出现
  await expect(page.getByText("E2E-REAL")).toBeVisible();
});
