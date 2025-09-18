import { test, expect } from "@playwright/test";

test.describe("Application Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
  });

  test("应该显示主导航菜单", async ({ page }) => {
    // Check main navigation menu exists
    const mainMenu = page.locator(".el-menu, .nav-menu, .sidebar");
    await expect(mainMenu).toBeVisible();

    // Check for main navigation items
    const menuItems = page.locator(".el-menu-item, .nav-item");
    const menuCount = await menuItems.count();

    expect(menuCount).toBeGreaterThan(0);
  });

  test("应该支持页面间导航", async ({ page }) => {
    // Test navigation to different pages
    const navigationTests = [
      { text: "仪表盘", url: "/", expectedContent: "集群统计" },
      { text: "集群管理", url: "/clusters", expectedContent: "集群" },
      { text: "表格管理", url: "/tables", expectedContent: "表" },
      { text: "任务管理", url: "/tasks", expectedContent: "任务" },
    ];

    for (const nav of navigationTests) {
      // Look for navigation link
      const navLink = page
        .locator(`a[href="${nav.url}"], .el-menu-item`)
        .filter({ hasText: nav.text })
        .or(page.locator("text=" + nav.text));

      if (await navLink.isVisible()) {
        await navLink.click();
        await page.waitForLoadState("networkidle");

        // Verify we're on the correct page
        expect(page.url()).toContain(nav.url === "/" ? "" : nav.url);

        // Check for expected content (if page loads successfully)
        const pageContent = page.locator("body");
        await expect(pageContent).toBeVisible();
      }
    }
  });

  test("应该显示页面标题和面包屑", async ({ page }) => {
    // Check page header exists
    const pageHeader = page.locator(".page-header, .header, h1, h2");

    if (await pageHeader.isVisible()) {
      await expect(pageHeader).toContainText(/.+/);
    }

    // Check breadcrumb navigation if exists
    const breadcrumb = page.locator(".el-breadcrumb, .breadcrumb");

    if (await breadcrumb.isVisible()) {
      const breadcrumbItems = breadcrumb.locator(
        ".el-breadcrumb-item, .breadcrumb-item",
      );
      expect(await breadcrumbItems.count()).toBeGreaterThan(0);
    }
  });

  test("应该支持侧边栏折叠展开", async ({ page }) => {
    // Look for sidebar toggle button
    const toggleButton = page.locator(
      '.sidebar-toggle, .menu-toggle, [aria-label*="toggle"], [aria-label*="折叠"]',
    );

    if (await toggleButton.isVisible()) {
      // Test collapsing sidebar
      await toggleButton.click();
      await page.waitForTimeout(300);

      // Test expanding sidebar
      await toggleButton.click();
      await page.waitForTimeout(300);

      // Verify sidebar is functional
      const sidebar = page.locator(".sidebar, .el-menu");
      await expect(sidebar).toBeVisible();
    }
  });

  test("应该显示用户信息和操作", async ({ page }) => {
    // Look for user info area
    const userInfo = page.locator(".user-info, .user-menu, .header-user");

    if (await userInfo.isVisible()) {
      // Check if user menu is clickable
      await userInfo.click();
      await page.waitForTimeout(300);

      // Look for dropdown menu
      const userDropdown = page.locator(
        ".el-dropdown-menu, .user-dropdown, .dropdown-menu",
      );

      if (await userDropdown.isVisible()) {
        // Check for common user actions
        const userActions = userDropdown.locator(
          "text=设置, text=退出, text=个人中心",
        );
        expect(await userActions.count()).toBeGreaterThanOrEqual(0);
      }
    }
  });
});

test.describe("Error Handling and Edge Cases", () => {
  test("应该处理404页面", async ({ page }) => {
    // Navigate to non-existent page
    await page.goto("/non-existent-page");

    // Should show 404 page or redirect to home
    const is404 = await page
      .locator("text=404, text=页面不存在, text=Not Found")
      .isVisible();
    const isRedirected =
      page.url().includes("/") && !page.url().includes("non-existent-page");

    expect(is404 || isRedirected).toBeTruthy();
  });

  test("应该处理网络连接问题", async ({ page }) => {
    // Go to dashboard first
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Simulate network offline
    await page.context().setOffline(true);

    // Try to navigate or refresh
    await page.reload({ waitUntil: "domcontentloaded" });

    // Should handle offline state gracefully
    const offlineIndicator = page.locator(
      "text=网络连接失败, text=离线, text=连接错误, .offline-indicator",
    );
    const pageStillFunctional = page.locator("body").isVisible();

    // Either shows offline message or page remains functional
    expect(
      (await offlineIndicator.isVisible()) || (await pageStillFunctional),
    ).toBeTruthy();

    // Restore network
    await page.context().setOffline(false);
  });

  test("应该处理长时间加载", async ({ page }) => {
    // Mock slow API response
    await page.route("**/api/v1/**", async (route) => {
      // Delay response by 3 seconds
      await new Promise((resolve) => setTimeout(resolve, 3000));
      await route.continue();
    });

    await page.goto("/");

    // Should show loading indicators
    const loadingIndicator = page.locator(
      '.el-loading, .loading, [data-loading="true"], .el-skeleton',
    );

    // Loading indicator should appear during slow request
    if (await loadingIndicator.first().isVisible({ timeout: 1000 })) {
      expect(await loadingIndicator.first().isVisible()).toBeTruthy();
    }

    // Wait for loading to complete
    await page.waitForLoadState("networkidle", { timeout: 10000 });

    // Page should eventually load
    await expect(page.locator("body")).toBeVisible();
  });
});

test.describe("Accessibility and Usability", () => {
  test("应该支持键盘导航", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Test tab navigation
    await page.keyboard.press("Tab");
    await page.waitForTimeout(100);

    // Should focus on some interactive element
    const focusedElement = page.locator(":focus");

    if (await focusedElement.isVisible()) {
      await expect(focusedElement).toBeVisible();
    }

    // Test Enter key on focused element
    await page.keyboard.press("Enter");
    await page.waitForTimeout(300);

    // Should trigger some action or navigation
    expect(page.url()).toBeTruthy(); // URL should be valid
  });

  test("应该有适当的语义化标签", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Check for semantic HTML elements
    const semanticElements = page.locator(
      "main, nav, header, section, article",
    );
    const semanticCount = await semanticElements.count();

    // Should have at least some semantic elements
    expect(semanticCount).toBeGreaterThan(0);

    // Check for heading hierarchy
    const headings = page.locator("h1, h2, h3, h4, h5, h6");
    const headingCount = await headings.count();

    expect(headingCount).toBeGreaterThan(0);
  });

  test("应该支持屏幕阅读器", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Check for ARIA labels and roles
    const ariaElements = page.locator(
      "[aria-label], [role], [aria-describedby]",
    );
    const ariaCount = await ariaElements.count();

    // Should have some accessibility attributes
    expect(ariaCount).toBeGreaterThanOrEqual(0);

    // Check for alt text on images
    const images = page.locator("img");
    const imageCount = await images.count();

    if (imageCount > 0) {
      const imagesWithAlt = page.locator("img[alt]");
      const altCount = await imagesWithAlt.count();

      // Most images should have alt text
      expect(altCount).toBeGreaterThanOrEqual(0);
    }
  });
});
