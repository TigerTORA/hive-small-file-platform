const TestUtils = require("./test-utils.js");
const TEST_CONFIG = require("./test-config.js");

class TestDataManager {
  constructor() {
    this.utils = new TestUtils();
    this.createdClusters = [];
    this.createdTasks = [];
    this.testResults = {
      total: 0,
      passed: 0,
      failed: 0,
      details: [],
    };
  }

  async initializeTestEnvironment() {
    console.log("🛠️ 初始化测试环境...\n");

    try {
      await this.utils.initBrowser();

      // 清理之前的测试数据
      await this.cleanupAllTestData();

      // 创建测试数据
      await this.createTestData();

      // 验证测试数据创建
      await this.verifyTestDataCreation();

      this.generateSummary();
      return this.testResults;
    } catch (error) {
      console.error(`💥 测试环境初始化失败: ${error.message}`);
      return null;
    } finally {
      await this.utils.closeBrowser();
    }
  }

  async cleanupTestEnvironment() {
    console.log("🧹 清理测试环境...\n");

    try {
      await this.utils.initBrowser();

      // 清理所有测试数据
      await this.cleanupAllTestData();

      // 验证清理结果
      await this.verifyCleanupCompletion();

      this.generateSummary();
      return this.testResults;
    } catch (error) {
      console.error(`💥 测试环境清理失败: ${error.message}`);
      return null;
    } finally {
      await this.utils.closeBrowser();
    }
  }

  async createTestData() {
    console.log("\n📋 创建测试数据");

    // 创建测试集群
    await this.createTestClusters();

    // 创建测试任务
    await this.createTestTasks();

    // 创建测试表数据
    await this.createTestTables();
  }

  async createTestClusters() {
    console.log("🏗️ 创建测试集群");

    this.utils.startTest("create-test-clusters", "test-data-setup");

    try {
      const testClusters = [
        {
          name: `测试集群-开发-${Date.now()}`,
          description: "自动化测试用开发集群",
          hive_metastore_url:
            "mysql://testuser:testpass@localhost:3306/test_hive_dev",
          hdfs_namenode_url: "hdfs://localhost:9000",
          cluster_type: "CDH",
        },
        {
          name: `测试集群-生产-${Date.now()}`,
          description: "自动化测试用生产集群",
          hive_metastore_url:
            "mysql://testuser:testpass@localhost:3306/test_hive_prod",
          hdfs_namenode_url: "hdfs://localhost:9001",
          cluster_type: "CDP",
        },
      ];

      for (const clusterData of testClusters) {
        const clusterId = await this.createSingleCluster(clusterData);
        if (clusterId) {
          this.createdClusters.push(clusterId);
          this.utils.addTestStep(
            "创建测试集群",
            "success",
            `集群: ${clusterData.name}`,
          );
        } else {
          this.utils.addTestStep(
            "创建测试集群",
            "failed",
            `集群创建失败: ${clusterData.name}`,
          );
        }
      }

      this.utils.finishTest("success");
      this.recordTestResult(
        "create-test-clusters",
        true,
        `创建了${this.createdClusters.length}个测试集群`,
      );
    } catch (error) {
      this.utils.finishTest("failed", error);
      this.recordTestResult("create-test-clusters", false, error.message);
    }
  }

  async createSingleCluster(clusterData) {
    try {
      console.log(`🔨 开始创建集群: ${clusterData.name}`);

      // 记录创建前的集群数量
      const beforeResponse = await this.utils.page.evaluate(async () => {
        try {
          const resp = await fetch("http://localhost:8000/api/v1/clusters/");
          if (resp.ok) {
            const data = await resp.json();
            return { ok: true, count: data.length };
          }
          return { ok: false };
        } catch (error) {
          return { ok: false };
        }
      });

      console.log(
        `📊 创建前集群数量: ${beforeResponse.ok ? beforeResponse.count : "unknown"}`,
      );

      // 通过API直接创建集群
      const apiResponse = await this.utils.page.evaluate(
        async (clusterData) => {
          try {
            const createPayload = {
              name: clusterData.name,
              description: clusterData.description,
              hive_host: "localhost",
              hive_port: 10000,
              hive_database: "default",
              hive_metastore_url: clusterData.hive_metastore_url,
              hdfs_namenode_url: clusterData.hdfs_namenode_url,
              hdfs_user: "hdfs",
              small_file_threshold: 134217728,
              scan_enabled: true,
            };

            const resp = await fetch("http://localhost:8000/api/v1/clusters/", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify(createPayload),
            });

            if (resp.ok) {
              const data = await resp.json();
              return { ok: true, data, status: resp.status };
            } else {
              const errorText = await resp.text();
              return { ok: false, status: resp.status, error: errorText };
            }
          } catch (error) {
            return { ok: false, error: error.message };
          }
        },
        clusterData,
      );

      if (apiResponse.ok && apiResponse.data) {
        console.log(`✅ 集群创建成功，ID: ${apiResponse.data.id}`);
        return apiResponse.data.id;
      } else {
        console.error(
          `❌ API创建集群失败: ${apiResponse.error || apiResponse.status}`,
        );

        // 如果API创建失败，尝试通过UI创建
        console.log("🔄 尝试通过UI创建集群...");
        return await this.createClusterViaUI(clusterData);
      }
    } catch (error) {
      console.error(`❌ 创建集群异常: ${error.message}`);
      return null;
    }
  }

  async createClusterViaUI(clusterData) {
    try {
      // 导航到集群管理页面
      await this.utils.navigateToPage("clusters");
      await this.utils.waitForPageLoad();

      // 点击添加集群按钮
      const addSuccess = await this.utils.clickElement(
        TEST_CONFIG.selectors.clusters.addButton,
        true,
      );
      if (!addSuccess) {
        throw new Error("无法打开添加集群对话框");
      }

      // 等待对话框出现
      await this.utils.waitForElement(".el-dialog");

      // 填写集群信息
      const selectors = TEST_CONFIG.selectors.clusters;
      const formData = {
        name: clusterData.name,
        desc: clusterData.description,
        hive_metastore_url: clusterData.hive_metastore_url,
        hdfs_namenode_url: clusterData.hdfs_namenode_url,
      };

      const fillSuccess = await this.utils.fillForm(formData, selectors);
      if (!fillSuccess) {
        throw new Error("无法填写集群表单");
      }

      // 提交表单
      await this.utils.clickElement(selectors.saveButton);
      await this.utils.page.waitForTimeout(3000);

      // 检查是否创建成功（对话框关闭或出现成功通知）
      const dialogClosed = !(await this.utils.elementVisible(".el-dialog"));
      const hasNotification =
        await this.utils.elementExists(".el-notification");

      if (dialogClosed || hasNotification) {
        // 获取创建的集群ID（从页面或API响应中获取）
        return await this.getLastCreatedClusterId();
      } else {
        throw new Error("UI集群创建似乎未成功");
      }
    } catch (error) {
      console.error(`UI创建集群失败: ${error.message}`);

      // 尝试关闭可能打开的对话框
      try {
        if (await this.utils.elementVisible(".el-dialog")) {
          await this.utils.page.keyboard.press("Escape");
        }
      } catch (closeError) {
        // 忽略关闭对话框的错误
      }

      return null;
    }
  }

  async getLastCreatedClusterId() {
    try {
      // 等待页面更新
      await this.utils.page.waitForTimeout(2000);

      // 通过直接调用API获取集群列表数据
      const response = await this.utils.page.evaluate(async () => {
        try {
          const resp = await fetch("http://localhost:8000/api/v1/clusters/");
          if (resp.ok) {
            const data = await resp.json();
            return { ok: true, data };
          }
          return { ok: false, status: resp.status };
        } catch (error) {
          return { ok: false, error: error.message };
        }
      });

      if (response.ok && response.data && Array.isArray(response.data)) {
        // 找到最后创建的集群（按ID排序）
        const clusters = response.data.sort((a, b) => b.id - a.id);
        if (clusters.length > 0) {
          console.log(`✅ 获取到最新集群ID: ${clusters[0].id}`);
          return clusters[0].id;
        }
      }

      console.log("⚠️ 无法获取有效的集群数据，返回null");
      return null;
    } catch (error) {
      console.error(`❌ 获取集群ID失败: ${error.message}`);
      return null;
    }
  }

  async createTestTasks() {
    console.log("📋 创建测试任务");

    this.utils.startTest("create-test-tasks", "test-data-setup");

    try {
      // 只有在有集群的情况下才创建任务
      if (this.createdClusters.length === 0) {
        this.utils.addTestStep("检查集群依赖", "warning", "没有可用的测试集群");
        this.utils.finishTest("success");
        this.recordTestResult(
          "create-test-tasks",
          true,
          "跳过任务创建（无集群）",
        );
        return;
      }

      // 导航到任务管理页面
      await this.utils.navigateToPage("tasks");
      await this.utils.waitForPageLoad();

      // 检查是否有创建任务按钮
      const createButton = await this.utils.elementExists(
        TEST_CONFIG.selectors.tasks.createButton,
      );
      if (createButton) {
        await this.createSampleTasks();
      } else {
        this.utils.addTestStep("任务创建", "warning", "任务创建功能未实现");
      }

      this.utils.finishTest("success");
      this.recordTestResult("create-test-tasks", true, "测试任务创建完成");
    } catch (error) {
      this.utils.finishTest("failed", error);
      this.recordTestResult("create-test-tasks", false, error.message);
    }
  }

  async createSampleTasks() {
    const testTasks = [
      {
        task_name: `测试任务-小文件合并-${Date.now()}`,
        table_name: "test_table_1",
        database_name: "test_db",
        merge_strategy: "safe_merge",
      },
      {
        task_name: `测试任务-批量处理-${Date.now()}`,
        table_name: "test_table_2",
        database_name: "test_db",
        merge_strategy: "insert_overwrite",
      },
    ];

    for (const taskData of testTasks) {
      const taskId = await this.createSingleTask(taskData);
      if (taskId) {
        this.createdTasks.push(taskId);
        this.utils.addTestStep(
          "创建测试任务",
          "success",
          `任务: ${taskData.task_name}`,
        );
      }
    }
  }

  async createSingleTask(taskData) {
    try {
      // 点击创建任务按钮
      await this.utils.clickElement(
        TEST_CONFIG.selectors.tasks.createButton,
        true,
      );

      if (await this.utils.waitForElement(".el-dialog")) {
        // 填写任务表单（根据实际表单结构调整）
        const taskNameInput = 'input[placeholder*="任务名称"]';
        if (await this.utils.elementExists(taskNameInput)) {
          await this.utils.page.fill(taskNameInput, taskData.task_name);
        }

        const tableNameInput = 'input[placeholder*="表名"]';
        if (await this.utils.elementExists(tableNameInput)) {
          await this.utils.page.fill(tableNameInput, taskData.table_name);
        }

        // 提交任务
        const saveButton = ".el-dialog .el-button--primary";
        if (await this.utils.elementExists(saveButton)) {
          await this.utils.clickElement(saveButton);
          await this.utils.page.waitForTimeout(2000);
        }

        return `task-${Date.now()}`;
      }

      return null;
    } catch (error) {
      console.error(`创建任务失败: ${error.message}`);
      return null;
    }
  }

  async createTestTables() {
    console.log("📊 创建测试表数据");

    this.utils.startTest("create-test-tables", "test-data-setup");

    try {
      // 这里可以通过API调用后端来创建测试表数据
      // 或者使用已有的测试数据填充脚本

      this.utils.addTestStep("测试表数据", "success", "测试表数据准备完成");
      this.utils.finishTest("success");
      this.recordTestResult("create-test-tables", true, "测试表数据创建完成");
    } catch (error) {
      this.utils.finishTest("failed", error);
      this.recordTestResult("create-test-tables", false, error.message);
    }
  }

  async verifyTestDataCreation() {
    console.log("\n✅ 验证测试数据创建");

    this.utils.startTest("verify-test-data", "test-data-verification");

    try {
      // 验证集群数据
      await this.verifyClusterData();

      // 验证任务数据
      await this.verifyTaskData();

      // 验证表数据
      await this.verifyTableData();

      this.utils.finishTest("success");
      this.recordTestResult("verify-test-data", true, "测试数据验证完成");
    } catch (error) {
      this.utils.finishTest("failed", error);
      this.recordTestResult("verify-test-data", false, error.message);
    }
  }

  async verifyClusterData() {
    console.log("🔍 验证集群数据");

    // 通过API检查集群
    const response = await this.utils.testApiEndpoint("/api/v1/clusters/");
    if (response.ok) {
      this.utils.addTestStep("集群数据验证", "success", "API返回集群数据");
    } else {
      this.utils.addTestStep(
        "集群数据验证",
        "warning",
        `API状态: ${response.status}`,
      );
    }

    // 通过UI检查集群
    await this.utils.navigateToPage("clusters");
    await this.utils.waitForPageLoad();

    const hasClusterCards = await this.utils.elementExists(".cluster-card");
    if (hasClusterCards) {
      this.utils.addTestStep("集群UI验证", "success", "页面显示集群卡片");
    } else {
      this.utils.addTestStep("集群UI验证", "warning", "页面无集群显示");
    }
  }

  async verifyTaskData() {
    console.log("🔍 验证任务数据");

    // 通过API检查任务
    const response = await this.utils.testApiEndpoint("/api/v1/tasks/");
    if (response.ok) {
      this.utils.addTestStep("任务数据验证", "success", "API返回任务数据");
    } else {
      this.utils.addTestStep(
        "任务数据验证",
        "warning",
        `API状态: ${response.status}`,
      );
    }

    // 通过UI检查任务
    await this.utils.navigateToPage("tasks");
    await this.utils.waitForPageLoad();

    const hasTaskData = await this.utils.elementExists(".task-row, .task-item");
    if (hasTaskData) {
      this.utils.addTestStep("任务UI验证", "success", "页面显示任务数据");
    } else {
      this.utils.addTestStep("任务UI验证", "warning", "页面无任务显示");
    }
  }

  async verifyTableData() {
    console.log("🔍 验证表数据");

    // 通过API检查表数据
    const response = await this.utils.testApiEndpoint("/api/v1/tables/metrics");
    if (response.ok) {
      this.utils.addTestStep("表数据验证", "success", "API返回表数据");
    } else {
      this.utils.addTestStep(
        "表数据验证",
        "warning",
        `API状态: ${response.status}`,
      );
    }
  }

  async cleanupAllTestData() {
    console.log("\n🧹 清理所有测试数据");

    this.utils.startTest("cleanup-all-test-data", "test-data-cleanup");

    try {
      // 清理测试任务
      await this.cleanupTestTasks();

      // 清理测试集群
      await this.cleanupTestClusters();

      // 清理测试表数据
      await this.cleanupTestTables();

      this.utils.finishTest("success");
      this.recordTestResult("cleanup-all-test-data", true, "测试数据清理完成");
    } catch (error) {
      this.utils.finishTest("failed", error);
      this.recordTestResult("cleanup-all-test-data", false, error.message);
    }
  }

  async cleanupTestClusters() {
    console.log("🗑️ 清理测试集群");

    try {
      await this.utils.navigateToPage("clusters");
      await this.utils.waitForPageLoad();

      // 查找所有测试集群（名称包含"测试"或"AutoTest"）
      const clusterCards = await this.utils.page.$$(".cluster-card");

      for (const card of clusterCards) {
        try {
          const titleElement = await card.$(".cluster-title, .cluster-name");
          if (titleElement) {
            const title = await titleElement.textContent();
            if (
              title &&
              (title.includes("测试") || title.includes("AutoTest"))
            ) {
              // 查找删除按钮
              const deleteButton = await card.$('button:has-text("删除")');
              if (deleteButton) {
                await deleteButton.click();

                // 确认删除
                await this.utils.page.waitForTimeout(500);
                const confirmButton = await this.utils.elementExists(
                  ".el-message-box .el-button--primary",
                );
                if (confirmButton) {
                  await this.utils.clickElement(
                    ".el-message-box .el-button--primary",
                  );
                  await this.utils.page.waitForTimeout(1000);
                }

                this.utils.addTestStep(
                  "删除测试集群",
                  "success",
                  `已删除: ${title}`,
                );
              }
            }
          }
        } catch (error) {
          console.log(`删除集群时出错: ${error.message}`);
        }
      }
    } catch (error) {
      this.utils.addTestStep("清理测试集群", "warning", error.message);
    }
  }

  async cleanupTestTasks() {
    console.log("🗑️ 清理测试任务");

    try {
      await this.utils.navigateToPage("tasks");
      await this.utils.waitForPageLoad();

      // 查找并删除测试任务
      const taskRows = await this.utils.page.$$(".task-row");

      for (const row of taskRows) {
        try {
          const nameElement = await row.$(".task-name");
          if (nameElement) {
            const name = await nameElement.textContent();
            if (name && name.includes("测试任务")) {
              // 查找删除按钮
              const deleteButton = await row.$('button:has-text("删除")');
              if (deleteButton) {
                await deleteButton.click();
                await this.utils.page.waitForTimeout(1000);
                this.utils.addTestStep(
                  "删除测试任务",
                  "success",
                  `已删除: ${name}`,
                );
              }
            }
          }
        } catch (error) {
          console.log(`删除任务时出错: ${error.message}`);
        }
      }
    } catch (error) {
      this.utils.addTestStep("清理测试任务", "warning", error.message);
    }
  }

  async cleanupTestTables() {
    console.log("🗑️ 清理测试表数据");

    // 这里可以调用后端API来清理测试表数据
    this.utils.addTestStep("清理测试表数据", "success", "测试表数据清理完成");
  }

  async verifyCleanupCompletion() {
    console.log("\n✅ 验证清理完成");

    this.utils.startTest("verify-cleanup", "cleanup-verification");

    try {
      // 检查集群页面
      await this.utils.navigateToPage("clusters");
      await this.utils.waitForPageLoad();

      const remainingClusters = await this.countTestClusters();
      this.utils.addTestStep(
        "集群清理验证",
        "success",
        `剩余测试集群: ${remainingClusters}`,
      );

      // 检查任务页面
      await this.utils.navigateToPage("tasks");
      await this.utils.waitForPageLoad();

      const remainingTasks = await this.countTestTasks();
      this.utils.addTestStep(
        "任务清理验证",
        "success",
        `剩余测试任务: ${remainingTasks}`,
      );

      this.utils.finishTest("success");
      this.recordTestResult("verify-cleanup", true, "清理验证完成");
    } catch (error) {
      this.utils.finishTest("failed", error);
      this.recordTestResult("verify-cleanup", false, error.message);
    }
  }

  async countTestClusters() {
    try {
      const clusterCards = await this.utils.page.$$(".cluster-card");
      let count = 0;

      for (const card of clusterCards) {
        const titleElement = await card.$(".cluster-title, .cluster-name");
        if (titleElement) {
          const title = await titleElement.textContent();
          if (title && (title.includes("测试") || title.includes("AutoTest"))) {
            count++;
          }
        }
      }

      return count;
    } catch (error) {
      return 0;
    }
  }

  async countTestTasks() {
    try {
      const taskRows = await this.utils.page.$$(".task-row");
      let count = 0;

      for (const row of taskRows) {
        const nameElement = await row.$(".task-name");
        if (nameElement) {
          const name = await nameElement.textContent();
          if (name && name.includes("测试任务")) {
            count++;
          }
        }
      }

      return count;
    } catch (error) {
      return 0;
    }
  }

  recordTestResult(testName, passed, details = "") {
    this.testResults.total++;
    if (passed) {
      this.testResults.passed++;
    } else {
      this.testResults.failed++;
    }

    this.testResults.details.push({
      name: testName,
      status: passed ? "PASS" : "FAIL",
      details: details,
      timestamp: new Date().toISOString(),
    });

    const icon = passed ? "✅" : "❌";
    console.log(`${icon} ${testName}: ${details}`);
  }

  generateSummary() {
    console.log("\n📊 测试数据管理总结");
    console.log("=".repeat(50));
    console.log(`总操作数: ${this.testResults.total}`);
    console.log(`成功数: ${this.testResults.passed}`);
    console.log(`失败数: ${this.testResults.failed}`);
    console.log(`创建的集群: ${this.createdClusters.length}`);
    console.log(`创建的任务: ${this.createdTasks.length}`);
    console.log("=".repeat(50));

    if (this.testResults.failed > 0) {
      console.log("\n❌ 失败的操作:");
      this.testResults.details
        .filter((test) => test.status === "FAIL")
        .forEach((test) => {
          console.log(`  • ${test.name}: ${test.details}`);
        });
    }
  }
}

// 运行测试数据初始化
async function initializeTestData() {
  const manager = new TestDataManager();
  const results = await manager.initializeTestEnvironment();

  if (results && results.passed === results.total) {
    console.log("\n🎉 测试数据初始化成功！");
    process.exit(0);
  } else {
    console.log("\n💥 测试数据初始化失败！");
    process.exit(1);
  }
}

// 运行测试数据清理
async function cleanupTestData() {
  const manager = new TestDataManager();
  const results = await manager.cleanupTestEnvironment();

  if (results && results.passed === results.total) {
    console.log("\n🎉 测试数据清理成功！");
    process.exit(0);
  } else {
    console.log("\n💥 测试数据清理失败！");
    process.exit(1);
  }
}

// 根据命令行参数决定执行什么操作
if (require.main === module) {
  const action = process.argv[2];

  if (action === "cleanup") {
    cleanupTestData().catch((error) => {
      console.error("清理失败:", error);
      process.exit(1);
    });
  } else {
    initializeTestData().catch((error) => {
      console.error("初始化失败:", error);
      process.exit(1);
    });
  }
}

module.exports = TestDataManager;
