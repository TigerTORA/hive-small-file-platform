#!/bin/bash

# Hive Small File Platform - Project Transfer Script
# 将项目代码传输到192.168.0.105服务器

set -e

SERVER_IP="192.168.0.105"
SERVER_USER="root"
PROJECT_DIR="/opt/hive-platform"
LOCAL_PROJECT_DIR="/Users/luohu/new_project/hive-small-file-platform"

echo "📂 开始传输项目代码到服务器..."
echo "目标服务器: $SERVER_IP"
echo "项目目录: $PROJECT_DIR"
echo "传输时间: $(date)"

# 检查本地项目目录
if [ ! -d "$LOCAL_PROJECT_DIR" ]; then
    echo "❌ 本地项目目录不存在: $LOCAL_PROJECT_DIR"
    exit 1
fi

echo "📋 传输项目文件..."

# 创建临时排除文件列表
cat > /tmp/rsync_exclude.txt << EOF
.git/
node_modules/
__pycache__/
*.pyc
.pytest_cache/
.coverage
dist/
build/
*.log
.env
.venv
venv/
.DS_Store
.vscode/
.idea/
*.swp
*.swo
frontend/dist/
frontend/node_modules/
backend/__pycache__/
backend/.pytest_cache/
backend/alembic/versions/*.py
backend/hive_small_file_db.db
EOF

# 使用rsync传输项目文件
echo "🚀 开始rsync传输..."
rsync -avz --progress \
    --exclude-from=/tmp/rsync_exclude.txt \
    "$LOCAL_PROJECT_DIR/" \
    "$SERVER_USER@$SERVER_IP:$PROJECT_DIR/"

# 清理临时文件
rm -f /tmp/rsync_exclude.txt

echo "✅ 项目代码传输完成"

# 在服务器上设置权限和安装依赖
echo "⚙️  配置服务器项目环境..."

ssh "$SERVER_USER@$SERVER_IP" << 'EOF'
cd /opt/hive-platform

# 设置目录权限
chown -R root:root /opt/hive-platform
find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;
chmod +x *.sh

echo "📦 安装后端Python依赖..."
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    # 安装基础依赖
    pip install fastapi uvicorn[standard] sqlalchemy pymysql
    pip install requests python-multipart python-jose[cryptography]
    pip install alembic celery redis pydantic requests-gssapi
fi

echo "📦 安装前端Node.js依赖..."
cd ../frontend

# 安装前端依赖
npm install

echo "🎉 项目环境配置完成！"
echo ""
echo "📁 项目结构："
ls -la /opt/hive-platform/

echo ""
echo "🚀 启动服务命令："
echo "后端: cd /opt/hive-platform/backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo "前端: cd /opt/hive-platform/frontend && npm run dev -- --host 0.0.0.0"

EOF

echo ""
echo "🎊 项目传输和配置完成！"
echo ""
echo "🌐 访问地址："
echo "后端API: http://$SERVER_IP:8000"
echo "前端界面: http://$SERVER_IP:5173"
echo "API文档: http://$SERVER_IP:8000/docs"
echo ""
echo "📝 下一步："
echo "1. SSH登录到服务器: ssh $SERVER_USER@$SERVER_IP"
echo "2. 启动后端服务"
echo "3. 启动前端服务" 
echo "4. 配置原生HDFS扫描器"
echo ""