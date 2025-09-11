#!/bin/bash

# 强制更新测试仪表板脚本
# 使用方法: ./scripts/update-dashboard.sh [--force]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🎯 强制更新测试仪表板"
echo "═══════════════════════════════════════"
echo "📁 项目目录: $PROJECT_ROOT"

cd "$PROJECT_ROOT"

# 检查必要的依赖
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm 未安装" 
    exit 1
fi

# 进入前端目录
cd frontend

echo "🔍 检查服务状态..."

# 检查并启动测试仪表板API服务
API_PID=$(pgrep -f "test-dashboard-integration.js" || true)
if [[ -z "$API_PID" ]]; then
    echo "🚀 启动测试仪表板API服务..."
    nohup node test-dashboard-integration.js > ../logs/dashboard-api.log 2>&1 &
    API_PID=$!
    sleep 3
    echo "✅ API服务已启动 (PID: $API_PID)"
else
    echo "✅ API服务已运行 (PID: $API_PID)"
fi

# 检查并启动前端开发服务器
FRONTEND_PID=$(pgrep -f "npm run dev\|vite" || true)
if [[ -z "$FRONTEND_PID" ]]; then
    echo "🚀 启动前端开发服务器..."
    nohup npm run dev > ../logs/frontend-dev.log 2>&1 &
    FRONTEND_PID=$!
    sleep 5
    echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"
else
    echo "✅ 前端服务已运行 (PID: $FRONTEND_PID)"
fi

# 等待服务启动完成
echo "⏳ 等待服务启动完成..."
sleep 3

# 验证服务可用性
echo "🔧 验证服务可用性..."

# 检查API服务
for i in {1..10}; do
    if curl -s -f "http://localhost:3001/api/health" > /dev/null; then
        echo "✅ API服务响应正常"
        break
    fi
    if [[ $i -eq 10 ]]; then
        echo "❌ API服务启动失败"
        exit 1
    fi
    echo "⏳ 等待API服务启动... ($i/10)"
    sleep 2
done

# 检查前端服务
for i in {1..10}; do
    if curl -s -f "http://localhost:3002" > /dev/null; then
        echo "✅ 前端服务响应正常"
        break
    fi
    if [[ $i -eq 10 ]]; then
        echo "❌ 前端服务启动失败"
        exit 1
    fi
    echo "⏳ 等待前端服务启动... ($i/10)"
    sleep 2
done

# 强制刷新测试数据
echo "🔄 强制刷新测试数据..."
REFRESH_RESULT=$(curl -s -X POST "http://localhost:3001/api/test/refresh")

if echo "$REFRESH_RESULT" | jq -e '.success' > /dev/null; then
    echo "✅ 测试数据刷新成功"
else
    echo "❌ 测试数据刷新失败"
    echo "$REFRESH_RESULT"
    exit 1
fi

# 获取并显示最新统计
echo "📊 获取最新测试统计..."
OVERVIEW=$(curl -s "http://localhost:3001/api/test/overview")

if echo "$OVERVIEW" | jq -e '.success' > /dev/null; then
    TOTAL_TESTS=$(echo "$OVERVIEW" | jq -r '.data.totalTests')
    TOTAL_PASSED=$(echo "$OVERVIEW" | jq -r '.data.totalPassed')
    TOTAL_FAILED=$(echo "$OVERVIEW" | jq -r '.data.totalFailed')
    SUCCESS_RATE=$(echo "$OVERVIEW" | jq -r '.data.successRate')
    LAST_UPDATE=$(echo "$OVERVIEW" | jq -r '.data.lastUpdate')
    
    echo "═══════════════════════════════════════"
    echo "📈 测试仪表板已更新！"
    echo "═══════════════════════════════════════"
    echo "📊 统计数据:"
    echo "   总测试数: $TOTAL_TESTS"
    echo "   通过测试: $TOTAL_PASSED"
    echo "   失败测试: $TOTAL_FAILED"
    echo "   成功率: ${SUCCESS_RATE}%"
    echo "   更新时间: $LAST_UPDATE"
    echo ""
    echo "🔗 访问地址:"
    echo "   测试仪表板: http://localhost:3002/#/test-dashboard"
    echo "   API服务: http://localhost:3001/api/test/overview"
    echo "═══════════════════════════════════════"
    
    # 记录更新时间戳
    echo "$LAST_UPDATE" > "$PROJECT_ROOT/.last-dashboard-update"
    
else
    echo "❌ 获取测试统计失败"
    echo "$OVERVIEW"
    exit 1
fi

echo "🎉 测试仪表板强制更新完成！"