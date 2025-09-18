/**
 * 手动端对端测试检查清单
 * 这个脚本提供了检查步骤，但需要人工在浏览器中执行
 */

console.log(`
=== DataNova 前端端对端检查清单 ===

服务状态验证：
✅ 前端服务: http://localhost:3002/ (HTTP 200)
✅ 后端服务: http://localhost:8000/api/v1/clusters/ (5个集群)

🔍 请按以下步骤手动检查：

1. 【首页访问测试】
   访问: http://localhost:3002/
   预期: 页面正常加载，显示侧边栏和主内容区域
   检查: 控制台是否有错误

2. 【表管理访问测试】
   访问: http://localhost:3002/#/tables
   预期: 自动重定向到 /clusters 页面（因为未选择集群）

3. 【集群选择流程】
   在 /clusters 页面：
   - 应该看到提示"请选择要使用的集群"
   - 点击任意集群卡片
   - 预期: 自动跳转回 /tables 页面

4. 【Tab切换功能测试】
   在 /tables 页面：
   - 默认应该在"全部表"Tab
   - 点击"小文件管理"Tab
   - 检查: URL应该变为 ?tab=small-files
   - 点击"冷数据管理"Tab
   - 检查: URL应该变为 ?tab=cold-data
   - 点击"全部表"Tab
   - 检查: URL应该回到 /tables（无tab参数）

5. 【数据加载测试】
   - 检查表格是否显示数据
   - 检查集群选择框是否有选项
   - 检查数据库选择框是否有选项

6. 【控制台检查】
   打开开发者工具：
   - Console: 检查是否有JavaScript错误
   - Network: 检查API请求是否成功返回200状态码
   - 重点关注 /api/v1/clusters/ 和 /api/v1/tables/ 请求

⚡ 如果发现问题，重点检查：
- 浏览器控制台错误信息
- Network标签页中失败的请求
- 集群是否正确选择并保存到localStorage

💡 调试提示：
- localStorage中应该有'monitoring-settings'键，包含selectedCluster
- 如果Tab切换不工作，检查Vue Router的hash模式路由
- 如果数据不加载，检查API请求的响应状态

🎯 成功标准：
✅ 能正常选择集群并进入表管理页面
✅ Tab切换功能正常，URL正确更新
✅ 表格数据正常加载
✅ 无控制台错误
`)
