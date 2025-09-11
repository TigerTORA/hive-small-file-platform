#!/bin/bash

echo "🚀 启动小文件合并平台演示"
echo "================================"

# 检查依赖
echo "📦 检查依赖..."
cd backend

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "❌ Python 未安装"
    exit 1
fi

echo "✅ Python: $(python --version)"

# 安装依赖（如果需要）
if [ ! -f "requirements_installed.flag" ]; then
    echo "📦 安装Python依赖..."
    pip install -r requirements.txt || echo "⚠️  部分依赖安装失败，将使用Mock模式"
    touch requirements_installed.flag
fi

# 启动后端服务
echo "🖥️  启动后端API服务..."
echo "   地址: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo ""

# 创建数据库表（如果需要）
python -c "
import sys
sys.path.append('.')
from app.config.database import engine, Base
Base.metadata.create_all(bind=engine)
print('✅ 数据库表创建完成')
"

# 启动FastAPI服务
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0 &
BACKEND_PID=$!

echo "🔧 后端服务PID: $BACKEND_PID"
echo ""

# 检查前端
cd ../frontend

if [ -f "package.json" ]; then
    echo "🎨 启动前端开发服务器..."
    
    # 安装依赖（如果需要）
    if [ ! -d "node_modules" ]; then
        echo "📦 安装前端依赖..."
        npm install || echo "⚠️  前端依赖安装失败"
    fi
    
    # 启动前端服务
    echo "   地址: http://localhost:5173"
    npm run dev &
    FRONTEND_PID=$!
    echo "🔧 前端服务PID: $FRONTEND_PID"
else
    echo "⚠️  前端项目不存在，仅启动后端服务"
fi

echo ""
echo "🎉 服务启动完成！"
echo "================================"
echo ""
echo "📋 可用服务:"
echo "   🔗 后端API: http://localhost:8000"
echo "   📚 API文档: http://localhost:8000/docs"
if [ -f "../frontend/package.json" ]; then
    echo "   🎨 前端界面: http://localhost:5173"
fi
echo ""
echo "🧪 测试端点:"
echo "   GET  /health                    - 健康检查"
echo "   GET  /api/v1/tasks/             - 任务列表"
echo "   POST /api/v1/tasks/             - 创建任务"
echo "   GET  /api/v1/tasks/{id}/preview - 任务预览"
echo "   GET  /api/v1/tasks/{id}/logs    - 任务日志"
echo ""
echo "💡 使用 Ctrl+C 停止所有服务"
echo ""

# 等待用户输入停止
wait