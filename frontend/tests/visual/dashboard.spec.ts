import { test } from '@playwright/test';
import percySnapshot from '@percy/playwright';

test.describe('Dashboard Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    // 设置为演示模式，使用固定的测试数据
    await page.goto('http://localhost:3000?demo=true');

    // 等待页面完全加载
    await page.waitForLoadState('networkidle');

    // 等待图表渲染完成
    await page.waitForSelector('[data-testid="dashboard-loaded"]', { timeout: 10000 });

    // 隐藏动态时间元素
    await page.addStyleTag({
      content: `
        [data-testid="real-time-clock"],
        [data-testid="refresh-timer"],
        .loading-spinner {
          visibility: hidden !important;
        }

        /* 禁用动画和过渡效果 */
        *, *::before, *::after {
          animation-duration: 0s !important;
          animation-delay: 0s !important;
          transition-duration: 0s !important;
          transition-delay: 0s !important;
        }
      `
    });
  });

  test('完整Dashboard页面截图', async ({ page }) => {
    await percySnapshot(page, 'Dashboard - 完整页面', {
      fullPage: true,
      enableJavaScript: true
    });
  });

  test('Dashboard头部信息栏', async ({ page }) => {
    const header = page.locator('.dashboard-header');
    await header.scrollIntoViewIfNeeded();

    await percySnapshot(page, 'Dashboard - 头部信息栏', {
      scope: '.dashboard-header'
    });
  });

  test('关键指标卡片', async ({ page }) => {
    const metrics = page.locator('.key-metrics');
    await metrics.scrollIntoViewIfNeeded();

    await percySnapshot(page, 'Dashboard - 关键指标', {
      scope: '.key-metrics'
    });
  });

  test('主监控图表', async ({ page }) => {
    // 等待图表完全渲染
    await page.waitForSelector('.main-chart canvas', { timeout: 15000 });
    await page.waitForTimeout(2000); // 额外等待图表动画完成

    const chartContainer = page.locator('.main-monitoring-panel');
    await chartContainer.scrollIntoViewIfNeeded();

    await percySnapshot(page, 'Dashboard - 主监控图表', {
      scope: '.main-monitoring-panel'
    });
  });

  test('快速操作面板', async ({ page }) => {
    const actionPanel = page.locator('.action-panel');
    await actionPanel.scrollIntoViewIfNeeded();

    await percySnapshot(page, 'Dashboard - 快速操作面板', {
      scope: '.action-panel'
    });
  });

  test('最近任务列表', async ({ page }) => {
    const taskPanel = page.locator('.recent-tasks-panel');
    await taskPanel.scrollIntoViewIfNeeded();

    await percySnapshot(page, 'Dashboard - 最近任务', {
      scope: '.recent-tasks-panel'
    });
  });

  test('响应式设计 - 移动端', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.waitForTimeout(1000);

    await percySnapshot(page, 'Dashboard - 移动端视图');
  });

  test('响应式设计 - 平板', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(1000);

    await percySnapshot(page, 'Dashboard - 平板视图');
  });

  test('大屏展示模式', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });

    // 切换到全屏模式（如果有的话）
    const fullscreenBtn = page.locator('[data-testid="fullscreen-toggle"]');
    if (await fullscreenBtn.isVisible()) {
      await fullscreenBtn.click();
      await page.waitForTimeout(1000);
    }

    await percySnapshot(page, 'Dashboard - 大屏展示模式');
  });
});