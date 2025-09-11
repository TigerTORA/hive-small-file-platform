#!/bin/bash

# Claude Code Hook - 任务完成后自动更新测试仪表板
# 当Claude完成任何开发任务后，自动刷新测试仪表板数据

echo "🤖 Claude Code Hook - 自动更新测试仪表板"
echo "═══════════════════════════════════════"

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# 检查是否需要更新测试仪表板
SHOULD_UPDATE=true

# 检查最近是否有代码变更
if [[ -f ".last-dashboard-update" ]]; then
    LAST_UPDATE=$(cat .last-dashboard-update)
    LAST_COMMIT=$(git log -1 --format="%ai" 2>/dev/null || echo "")
    
    if [[ "$LAST_COMMIT" < "$LAST_UPDATE" ]]; then
        echo "ℹ️  测试仪表板数据是最新的，跳过更新"
        SHOULD_UPDATE=false
    fi
fi

if [[ "$SHOULD_UPDATE" == "true" ]]; then
    echo "🔄 检测到代码变更，更新测试仪表板..."
    
    # 调用更新脚本
    if [[ -x "./scripts/update-dashboard.sh" ]]; then
        ./scripts/update-dashboard.sh
        echo "✅ 测试仪表板自动更新完成"
        echo "🔗 访问地址: http://localhost:3002/#/test-dashboard"
    else
        echo "⚠️  更新脚本不存在或不可执行"
        echo "💡 请运行: chmod +x scripts/update-dashboard.sh"
    fi
fi

echo "═══════════════════════════════════════"