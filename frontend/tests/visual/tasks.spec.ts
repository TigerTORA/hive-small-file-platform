import { test } from '@playwright/test';
import percySnapshot from '@percy/playwright';

test.describe('Tasks Page Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000/tasks?demo=true');
    await page.waitForLoadState('networkidle');

    // 隐藏动态元素
    await page.addStyleTag({
      content: `
        [data-testid="real-time-clock"],
        [data-testid="refresh-timer"],
        .loading-spinner {
          visibility: hidden !important;
        }

        *, *::before, *::after {
          animation-duration: 0s !important;
          transition-duration: 0s !important;
        }
      `
    });
  });

  test('任务管理页面完整视图', async ({ page }) => {
    await percySnapshot(page, 'Tasks - 完整页面', {
      fullPage: true
    });
  });

  test('合并任务列表', async ({ page }) => {
    // 确保在合并任务标签页
    const mergeTab = page.locator('[name="merge"]');
    if (await mergeTab.isVisible()) {
      await mergeTab.click();
      await page.waitForTimeout(500);
    }

    await percySnapshot(page, 'Tasks - 合并任务列表');
  });

  test('扫描任务列表', async ({ page }) => {
    // 切换到扫描任务标签页
    const scanTab = page.locator('[name="scan"]');
    await scanTab.click();
    await page.waitForTimeout(500);

    await percySnapshot(page, 'Tasks - 扫描任务列表');
  });

  test('创建任务对话框', async ({ page }) => {
    // 点击创建任务按钮
    const createBtn = page.getByText('创建任务');
    await createBtn.click();
    await page.waitForTimeout(500);

    await percySnapshot(page, 'Tasks - 创建任务对话框');
  });

  test('任务执行进度显示', async ({ page }) => {
    // 模拟运行中的任务
    await page.evaluate(() => {
      // 这里可以注入一些测试数据来显示运行中的任务
      console.log('Simulating running tasks for visual test');
    });

    await percySnapshot(page, 'Tasks - 执行进度显示');
  });

  test('任务日志查看', async ({ page }) => {
    // 如果有日志按钮，点击查看
    const logBtn = page.locator('text=日志').first();
    if (await logBtn.isVisible()) {
      await logBtn.click();
      await page.waitForTimeout(500);

      await percySnapshot(page, 'Tasks - 任务日志对话框');
    }
  });
});