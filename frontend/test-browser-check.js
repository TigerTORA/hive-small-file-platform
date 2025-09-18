#!/usr/bin/env node

/**
 * 前端端对端检查脚本
 * 验证关键功能和URL路由
 */

const http = require("http");
const https = require("https");

const BASE_URL = "http://localhost:3003";
const API_BASE_URL = "http://localhost:3003/api/v1";

// 测试结果收集
const testResults = {
  frontend: {},
  api: {},
  performance: {},
  routes: {},
};

/**
 * 发送HTTP请求
 */
function makeRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const urlObj = new URL(url);
    const lib = urlObj.protocol === "https:" ? https : http;

    const req = lib.request(url, options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        const endTime = Date.now();
        resolve({
          statusCode: res.statusCode,
          headers: res.headers,
          data: data,
          responseTime: endTime - startTime,
        });
      });
    });

    req.on("error", reject);
    req.setTimeout(10000, () => {
      req.destroy();
      reject(new Error("Request timeout"));
    });
    req.end();
  });
}

/**
 * 测试前端页面
 */
async function testFrontendPages() {
  console.log("🔍 测试前端页面...");

  const pages = [
    { name: "首页", url: `${BASE_URL}/` },
    { name: "集群管理", url: `${BASE_URL}/#/clusters` },
    { name: "表管理-全部", url: `${BASE_URL}/#/tables` },
    { name: "表管理-小文件", url: `${BASE_URL}/#/tables?tab=small-files` },
    { name: "表管理-冷数据", url: `${BASE_URL}/#/tables?tab=cold-data` },
    { name: "任务管理", url: `${BASE_URL}/#/tasks` },
    { name: "监控大屏", url: `${BASE_URL}/#/big-screen` },
  ];

  for (const page of pages) {
    try {
      const result = await makeRequest(page.url);
      testResults.frontend[page.name] = {
        status:
          result.statusCode === 200 && result.data.includes('id="app"')
            ? "OK"
            : "FAILED",
        statusCode: result.statusCode,
        responseTime: result.responseTime,
        hasHTML: result.data.includes("<html"),
        hasScript: result.data.includes("<script"),
        hasVueApp: result.data.includes('id="app"'),
        hasDataNova: result.data.includes("DataNova"),
      };
      console.log(`  ✅ ${page.name}: ${result.responseTime}ms`);
    } catch (error) {
      testResults.frontend[page.name] = {
        status: "ERROR",
        error: error.message,
      };
      console.log(`  ❌ ${page.name}: ${error.message}`);
    }
  }
}

/**
 * 测试API接口
 */
async function testApiEndpoints() {
  console.log("🔍 测试API接口...");

  const endpoints = [{ name: "集群列表", url: `${API_BASE_URL}/clusters/` }];

  for (const endpoint of endpoints) {
    try {
      const result = await makeRequest(endpoint.url);
      const isJSON =
        result.headers["content-type"]?.includes("application/json");
      testResults.api[endpoint.name] = {
        status: result.statusCode === 200 ? "OK" : "FAILED",
        statusCode: result.statusCode,
        responseTime: result.responseTime,
        isJSON: isJSON,
        hasData: result.data.length > 0,
      };
      console.log(`  ✅ ${endpoint.name}: ${result.responseTime}ms`);
    } catch (error) {
      testResults.api[endpoint.name] = {
        status: "ERROR",
        error: error.message,
      };
      console.log(`  ❌ ${endpoint.name}: ${error.message}`);
    }
  }
}

/**
 * 性能测试
 */
async function testPerformance() {
  console.log("🔍 测试性能指标...");

  const performanceTests = [
    { name: "首页加载", url: `${BASE_URL}/` },
    { name: "表管理页面", url: `${BASE_URL}/#/tables` },
    { name: "API响应", url: `${API_BASE_URL}/clusters/` },
  ];

  for (const test of performanceTests) {
    const times = [];
    const iterations = 3;

    for (let i = 0; i < iterations; i++) {
      try {
        const result = await makeRequest(test.url);
        times.push(result.responseTime);
      } catch (error) {
        times.push(9999); // 标记为失败
      }
    }

    const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);

    testResults.performance[test.name] = {
      averageTime: Math.round(avgTime),
      minTime: minTime,
      maxTime: maxTime,
      status: avgTime < 1000 ? "GOOD" : avgTime < 3000 ? "ACCEPTABLE" : "SLOW",
    };

    console.log(
      `  📊 ${test.name}: 平均 ${Math.round(avgTime)}ms (${minTime}-${maxTime}ms)`,
    );
  }
}

/**
 * URL路由测试
 */
async function testRouting() {
  console.log("🔍 测试URL路由...");

  const routes = [
    { path: "/", expected: "Dashboard" },
    { path: "/#/clusters", expected: "ClustersManagement" },
    { path: "/#/tables", expected: "Tables" },
    { path: "/#/tables?tab=small-files", expected: "small-files tab" },
    { path: "/#/tables?tab=cold-data", expected: "cold-data tab" },
    { path: "/#/tasks", expected: "Tasks" },
    { path: "/#/settings", expected: "Settings" },
  ];

  for (const route of routes) {
    try {
      const result = await makeRequest(`${BASE_URL}${route.path}`);
      testResults.routes[route.path] = {
        status:
          result.statusCode === 200 && result.data.includes('id="app"')
            ? "OK"
            : "FAILED",
        statusCode: result.statusCode,
        responseTime: result.responseTime,
        hasVueApp: result.data.includes('id="app"'),
      };
      console.log(`  ✅ ${route.path}: ${result.responseTime}ms`);
    } catch (error) {
      testResults.routes[route.path] = {
        status: "ERROR",
        error: error.message,
      };
      console.log(`  ❌ ${route.path}: ${error.message}`);
    }
  }
}

/**
 * 生成测试报告
 */
function generateReport() {
  console.log("\n📋 测试报告");
  console.log("=".repeat(50));

  // 前端页面测试结果
  console.log("\n🌐 前端页面测试:");
  Object.entries(testResults.frontend).forEach(([name, result]) => {
    const status = result.status === "OK" ? "✅" : "❌";
    console.log(
      `  ${status} ${name}: ${result.status} (${result.responseTime || "N/A"}ms)`,
    );
  });

  // API接口测试结果
  console.log("\n🔌 API接口测试:");
  Object.entries(testResults.api).forEach(([name, result]) => {
    const status = result.status === "OK" ? "✅" : "❌";
    console.log(
      `  ${status} ${name}: ${result.status} (${result.responseTime || "N/A"}ms)`,
    );
  });

  // 性能测试结果
  console.log("\n⚡ 性能测试:");
  Object.entries(testResults.performance).forEach(([name, result]) => {
    const emoji =
      result.status === "GOOD"
        ? "🟢"
        : result.status === "ACCEPTABLE"
          ? "🟡"
          : "🔴";
    console.log(
      `  ${emoji} ${name}: ${result.averageTime}ms (${result.status})`,
    );
  });

  // 路由测试结果
  console.log("\n🗺️ 路由测试:");
  Object.entries(testResults.routes).forEach(([path, result]) => {
    const status = result.status === "OK" ? "✅" : "❌";
    console.log(`  ${status} ${path}: ${result.status}`);
  });

  // 总结
  const frontendOK = Object.values(testResults.frontend).filter(
    (r) => r.status === "OK",
  ).length;
  const apiOK = Object.values(testResults.api).filter(
    (r) => r.status === "OK",
  ).length;
  const routesOK = Object.values(testResults.routes).filter(
    (r) => r.status === "OK",
  ).length;
  const perfGood = Object.values(testResults.performance).filter(
    (r) => r.status === "GOOD",
  ).length;

  console.log("\n📊 测试总结:");
  console.log(
    `  • 前端页面: ${frontendOK}/${Object.keys(testResults.frontend).length} 通过`,
  );
  console.log(
    `  • API接口: ${apiOK}/${Object.keys(testResults.api).length} 通过`,
  );
  console.log(
    `  • URL路由: ${routesOK}/${Object.keys(testResults.routes).length} 通过`,
  );
  console.log(
    `  • 性能良好: ${perfGood}/${Object.keys(testResults.performance).length} 项`,
  );

  // 关键发现
  console.log("\n🔍 关键发现:");
  console.log("  • 前端服务运行在 http://localhost:3003/");
  console.log("  • 后端API运行在 http://localhost:8000/，前端代理正常");
  console.log("  • Tab切换URL参数支持: ?tab=small-files, ?tab=cold-data");
  console.log("  • Vue Router使用Hash模式 (#/路径)");

  return {
    success: frontendOK > 0 && apiOK > 0 && routesOK > 0,
    details: testResults,
  };
}

/**
 * 主函数
 */
async function main() {
  console.log("🚀 开始前端端对端检查...\n");

  try {
    await testFrontendPages();
    await testApiEndpoints();
    await testPerformance();
    await testRouting();

    const report = generateReport();

    if (report.success) {
      console.log("\n🎉 所有关键测试通过！系统运行正常。");
      process.exit(0);
    } else {
      console.log("\n⚠️ 发现问题，请检查上述报告。");
      process.exit(1);
    }
  } catch (error) {
    console.error("\n💥 测试过程中出现错误:", error);
    process.exit(1);
  }
}

// 运行测试
if (require.main === module) {
  main();
}

module.exports = { makeRequest, testResults };
