import { test, expect } from "@playwright/test"

test("basic test", async ({ page }) => {
  await page.goto("http://localhost:3002")
  await expect(page).toHaveTitle(/Hive|小文件|管理|平台|Frontend|Vue/)
})
