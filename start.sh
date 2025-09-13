#!/bin/bash

# Hive Small File Platform 统一启动脚本
# 用于确保端口配置正确且进程不冲突

echo "🚀 Hive Small File Platform 启动脚本"
echo "=================================="

# 检查端口占用
check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  端口 $port 已被占用 ($service)"
        echo "正在尝试停止占用进程..."
        lsof -ti :$port | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# 停止现有进程
echo "🔄 停止现有进程..."
pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
pkill -f "python.*app.main" 2>/dev/null || true
pkill -f "vite.*frontend" 2>/dev/null || true
sleep 3

# 检查并清理端口占用
check_port 8000 "后端服务"
check_port 3000 "前端服务"

# 启动后端
echo "🔧 启动后端服务 (端口: 8000)..."
cd backend
python -m app.main &
BACKEND_PID=$!
echo "后端进程 PID: $BACKEND_PID"

# 等待后端启动
echo "⏳ 等待后端服务启动..."
sleep 5

# 检查后端健康状态
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ 后端服务启动成功"
    # 显示后端配置信息
    echo "📊 后端配置信息:"
    curl -s http://localhost:8000/health | python3 -m json.tool
else
    echo "❌ 后端服务启动失败"
    exit 1
fi

# 启动前端
echo "🎨 启动前端服务 (端口: 3000)..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "前端进程 PID: $FRONTEND_PID"

# 等待前端启动
echo "⏳ 等待前端服务启动..."
sleep 8

# 检查前端健康状态
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ 前端服务启动成功"
else
    echo "⚠️  前端服务可能还在启动中..."
fi

echo ""
echo "🎉 启动完成!"
echo "=================================="
echo "📍 后端服务: http://localhost:8000"
echo "📍 前端服务: http://localhost:3000"
echo "📖 API文档: http://localhost:8000/docs"
echo ""
echo "💡 端口配置说明:"
echo "   - 后端固定端口: 8000 (配置在 backend/.env)"
echo "   - 前端固定端口: 3000 (配置在 frontend/.env)"
echo "   - 日志中的动态端口(如50xxx)是客户端端口，非服务端口"
echo ""
echo "⚡ 使用 Ctrl+C 停止服务"

# 等待用户中断
wait