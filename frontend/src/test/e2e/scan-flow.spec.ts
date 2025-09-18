import { test, expect } from "@playwright/test";

test("创建集群 -> 触发扫描 -> 任务页查看扫描任务与日志", async ({ page }) => {
  // 拦截并模拟后端 API
  const cluster = {
    id: 1,
    name: "Test Cluster",
    description: "E2E mock cluster",
    hive_host: "localhost",
    hive_port: 10000,
    hive_database: "default",
    hive_metastore_url: "mysql://user:pass@host:3306/hive",
    hdfs_namenode_url: "http://nn:9870/webhdfs/v1",
    hdfs_user: "hdfs",
    small_file_threshold: 134217728,
    scan_enabled: true,
    status: "active",
    created_time: new Date().toISOString(),
    updated_time: new Date().toISOString(),
  };

  const taskId = "e2e-task-1234";

  await page.route("**/api/v1/clusters/", async (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: [cluster] });
    }
    if (route.request().method() === "POST") {
      return route.fulfill({ json: cluster });
    }
    return route.fallback();
  });

  await page.route("**/api/v1/clusters/1", async (route) => {
    return route.fulfill({ json: cluster });
  });

  await page.route("**/api/v1/clusters/1/stats", async (route) => {
    return route.fulfill({
      json: {
        total_databases: 0,
        total_tables: 0,
        small_file_tables: 0,
        total_small_files: 0,
      },
    });
  });

  await page.route("**/api/v1/clusters/1/databases", async (route) => {
    return route.fulfill({ json: [] });
  });

  await page.route("**/api/v1/tables/scan/1", async (route) => {
    return route.fulfill({
      json: { cluster_id: 1, task_id: taskId, status: "started" },
    });
  });

  // 废弃API已移除，使用统一的scan-tasks API处理

  await page.route("**/api/v1/scan-tasks/**", async (route) => {
    // 列表/详情/日志统一返回已完成的任务
    const url = route.request().url();
    if (url.endsWith("/logs")) {
      return route.fulfill({
        json: [
          {
            timestamp: new Date().toISOString(),
            level: "INFO",
            message: "扫描完成",
          },
        ],
      });
    }
    if (url.includes("/scan-tasks/") && !url.endsWith("/logs")) {
      return route.fulfill({
        json: {
          id: 1,
          task_id: taskId,
          cluster_id: 1,
          task_type: "cluster",
          task_name: "扫描集群: Test Cluster",
          status: "completed",
          total_items: 10,
          completed_items: 10,
          progress_percentage: 100,
          estimated_remaining_seconds: 0,
          total_tables_scanned: 10,
          total_files_found: 100,
          total_small_files: 20,
          start_time: new Date().toISOString(),
        },
      });
    }
    return route.fulfill({
      json: [
        {
          id: 1,
          task_id: taskId,
          cluster_id: 1,
          task_type: "cluster",
          task_name: "扫描集群: Test Cluster",
          status: "completed",
          total_items: 10,
          completed_items: 10,
          progress_percentage: 100,
          estimated_remaining_seconds: 0,
          total_tables_scanned: 10,
          total_files_found: 100,
          total_small_files: 20,
          start_time: new Date().toISOString(),
        },
      ],
    });
  });

  // 进入集群管理
  await page.goto("/#/clusters");
  await expect(page.getByText("集群管理")).toBeVisible();

  // 进入集群详情
  await page
    .getByRole("button", { name: "进入集群详情" })
    .first()
    .click()
    .catch(async () => {
      // 如果没有专门的按钮，点击卡片
      const cards = page.locator(".cluster-card");
      if (await cards.count()) await cards.first().click();
    });
  await expect(page.getByText("任务管理")).toBeVisible();

  // 触发扫描
  await page.getByRole("button", { name: "扫描数据库" }).click();
  await page.getByRole("button", { name: "开始扫描" }).click();

  // 进度弹窗应出现并显示100%
  await expect(page.getByText("数据库扫描进度")).toBeVisible();
  await expect(page.getByText("100%")).toBeVisible();

  // 关闭弹窗（如果可关闭）
  const closeBtn = page.getByRole("button", { name: "关闭" });
  if (await closeBtn.isVisible()) await closeBtn.click();

  // 打开任务管理页并查看扫描任务
  await page.goto("/#/tasks");
  await page.getByRole("tab", { name: "扫描任务" }).click();
  await expect(page.getByText(taskId)).toBeVisible();
  await page.getByRole("button", { name: "查看日志" }).first().click();
  await expect(page.getByText("扫描完成")).toBeVisible();
});
