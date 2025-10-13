# 🔒 强制测试仪表板更新规则

## 概述

为了确保开发质量和测试数据的实时性，项目建立了**强制测试仪表板更新规则**。每次开发后，必须更新 http://localhost:3002/#/test-dashboard

## 🎯 规则强度级别

### 1. 🔴 **最强制级别 - Git Hooks（推荐）**

**自动执行：** 每次 `git commit` 时自动执行

```bash
# 一次性设置
npm run setup

# 手动设置Git Hooks
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
```

**执行效果：**
- ✅ 检查测试仪表板服务是否运行
- ✅ 强制刷新测试数据
- ✅ 验证数据更新成功
- ❌ **如果失败，阻止提交**

### 2. 🟡 **中等强制级别 - npm scripts**

**手动执行：** 开发完成后运行命令

```bash
# 更新测试仪表板
npm run dashboard

# 强制更新（忽略缓存）
npm run dashboard:force

# 验证更新
npm run validate
```

### 3. 🟢 **基础级别 - 直接调用**

```bash
# 直接运行更新脚本
./scripts/update-dashboard.sh

# 检查当前状态
npm run check
```

## 📋 完整工作流程

### 开发流程示例

```bash
# 1. 开发代码
vim src/components/NewFeature.vue

# 2. 测试功能
npm run dev

# 3. 强制更新仪表板（三选一）
npm run dashboard           # 方式1：npm命令
./scripts/update-dashboard.sh  # 方式2：直接脚本
git add . && git commit -m "add new feature"  # 方式3：Git Hook自动执行

# 4. 验证结果
curl -s http://localhost:3001/api/test/overview | jq .
```

## 🛠️ 技术实现

### 强制规则检查项

1. **服务状态验证**
   - 测试仪表板API服务 (port 3001)
   - 前端开发服务器 (port 3002)

2. **数据刷新强制执行**
   - 重新扫描所有测试文件
   - 更新测试分类和统计
   - 生成最新报告

3. **质量门槛检查**
   - 最低成功率要求 (可配置)
   - 测试覆盖率验证

### 文件结构

```
项目根目录/
├── .githooks/
│   └── pre-commit              # Git提交前强制检查
├── scripts/
│   └── update-dashboard.sh     # 主要更新脚本
├── .claude/hooks/
│   └── post-task.sh           # Claude Code自动Hook
├── package.json               # npm scripts定义
└── DASHBOARD-RULES.md         # 本文档
```

## 🔧 配置选项

### 修改强制规则严格程度

编辑 `.githooks/pre-commit`：

```bash
# 设置最低成功率要求
MIN_SUCCESS_RATE=30  # 修改为所需百分比

# 是否允许低成功率提交
if [[ $SUCCESS_RATE -lt $MIN_SUCCESS_RATE ]]; then
    exit 1  # 强制失败
    # echo "警告但允许提交"  # 仅警告
fi
```

### 跳过强制检查（紧急情况）

```bash
# 临时跳过Git Hook
git commit --no-verify -m "emergency fix"

# 临时禁用Hook
git config core.hooksPath ""
```

## 📊 验证效果

### 成功示例输出

```
🎯 强制更新测试仪表板
═══════════════════════════════════════
✅ API服务正常运行
✅ 前端服务正常运行  
✅ 测试数据刷新成功
═══════════════════════════════════════
📈 测试仪表板已更新！
   总测试数: 178
   通过测试: 65
   成功率: 37%
🔗 访问地址: http://localhost:3002/#/test-dashboard
═══════════════════════════════════════
✅ 提交允许继续
```

### 失败示例输出

```
❌ 测试仪表板API服务未运行！
💡 请先启动服务：cd frontend && node test-dashboard-integration.js &
🚫 提交被阻止 - 测试仪表板服务必须运行
```

## 🎯 最佳实践

1. **推荐设置方式**：使用Git Hooks实现全自动强制更新
2. **开发习惯**：每次开发完成后访问仪表板确认数据
3. **团队协作**：所有开发者都必须遵循相同规则
4. **监控验证**：定期检查 `.last-dashboard-update` 时间戳

## 🔗 快速链接

- **测试仪表板**：http://localhost:3002/#/test-dashboard
- **API服务状态**：http://localhost:3001/api/health
- **测试统计API**：http://localhost:3001/api/test/overview

---

**⚠️ 重要提醒**：此规则确保测试数据实时性，提高开发质量。请严格遵守执行！