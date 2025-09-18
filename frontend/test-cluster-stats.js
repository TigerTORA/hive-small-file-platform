const axios = require("axios");

async function testClusterStats() {
  console.log("测试集群统计数据来源...\n");

  try {
    // 测试后端API
    console.log("=== 测试后端API ===");
    const backendResponse = await axios.get(
      "http://localhost:8001/api/v1/clusters/1/stats",
    );
    console.log(
      "后端API返回数据:",
      JSON.stringify(backendResponse.data, null, 2),
    );

    // 测试前端API调用
    console.log("\n=== 测试前端可访问性 ===");
    try {
      const frontendResponse = await axios.get("http://localhost:3001");
      console.log("前端页面访问正常，状态码:", frontendResponse.status);
    } catch (frontendError) {
      console.log("前端页面访问失败:", frontendError.message);
    }

    // 验证数据一致性
    console.log("\n=== 数据一致性验证 ===");
    const expectedData = {
      total_databases: 11,
      total_tables: 1564,
      total_small_files: 37996,
    };

    const actualData = backendResponse.data;

    console.log("期望数据:", expectedData);
    console.log("实际数据:", actualData);

    const isConsistent =
      actualData.total_databases === expectedData.total_databases &&
      actualData.total_tables === expectedData.total_tables &&
      actualData.total_small_files === expectedData.total_small_files;

    console.log("数据一致性检查:", isConsistent ? "✅ 通过" : "❌ 失败");

    if (isConsistent) {
      console.log("\n🎉 修复成功！前端现在应该显示正确的统计数据");
    } else {
      console.log("\n⚠️  数据不一致，需要进一步检查");
    }
  } catch (error) {
    console.error("测试失败:", error.message);
  }
}

testClusterStats();
