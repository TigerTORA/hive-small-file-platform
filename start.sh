#!/bin/bash

echo "🚀 启动 Hive 小文件治理平台"
echo "================================"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 停止可能运行的旧服务
echo "🛑 停止旧服务..."
docker-compose down

# 启动基础服务（数据库和缓存）
echo "📦 启动数据库和 Redis..."
docker run -d --name hive-platform-postgres \
    -e POSTGRES_DB=hive_small_file_db \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -p 5432:5432 \
    postgres:14 2>/dev/null || echo "PostgreSQL 已在运行"

docker run -d --name hive-platform-redis \
    -p 6379:6379 \
    redis:6-alpine 2>/dev/null || echo "Redis 已在运行"

# 等待数据库启动
echo "⏳ 等待数据库启动..."
sleep 10

# 检查端口
echo "🔍 检查端口占用..."
if lsof -i :8000 >/dev/null 2>&1; then
    echo "⚠️  端口 8000 被占用，请先停止占用进程"
    lsof -i :8000
fi

if lsof -i :3000 >/dev/null 2>&1; then
    echo "⚠️  端口 3000 被占用，请先停止占用进程"
    lsof -i :3000
fi

echo ""
echo "✅ 基础服务启动完成！"
echo ""
echo "📝 下一步手动启动应用："
echo "   1. 后端：cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000"
echo "   2. 前端：cd frontend && npm install && npm run dev"
echo ""
echo "🌐 访问地址："
echo "   - 前端界面: http://localhost:3000"
echo "   - API 文档: http://localhost:8000/docs"
echo ""