#!/bin/bash

# 快速项目迁移脚本 - 立即开始在192.168.0.105上开发

set -e

SERVER_IP="192.168.0.105"
SERVER_USER="root"

echo "🚀 快速迁移项目到HDFS服务器..."
echo "目标: $SERVER_IP"
echo "时间: $(date)"

# 1. 创建项目压缩包（排除不必要文件）
echo "📦 打包项目..."
cd /Users/luohu/new_project
tar -czf hive-platform-quick.tar.gz \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='dist' \
  --exclude='build' \
  --exclude='*.log' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='.DS_Store' \
  --exclude='frontend/dist' \
  --exclude='frontend/node_modules' \
  --exclude='backend/hive_small_file_db.db' \
  hive-small-file-platform/

echo "✅ 项目打包完成"

# 2. 传输到服务器
echo "📤 传输到服务器..."
echo "请输入服务器密码: !qaz2wsx3edC"
scp hive-platform-quick.tar.gz "$SERVER_USER@$SERVER_IP:/tmp/"

echo "✅ 传输完成"

# 3. 创建服务器设置脚本
cat > server_setup.sh << 'EOF'
#!/bin/bash
set -e

echo "🔧 在服务器上设置开发环境..."

# 解压项目
cd /tmp
tar -xzf hive-platform-quick.tar.gz
rm -rf /opt/hive-platform 2>/dev/null || true
mkdir -p /opt/hive-platform
mv hive-small-file-platform/* /opt/hive-platform/ 2>/dev/null || true
cd /opt/hive-platform

echo "📦 快速安装必要依赖..."

# 检查Python
if ! command -v python3 &> /dev/null || [[ $(python3 --version | cut -d. -f2) -lt 8 ]]; then
    echo "安装Python 3.8..."
    yum install -y python38 python38-pip python38-devel
    alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
fi

# 检查Node.js
if ! command -v node &> /dev/null || [[ $(node --version | cut -d. -f1 | tr -d 'v') -lt 16 ]]; then
    echo "安装Node.js..."
    curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
    yum install -y nodejs
fi

# 安装Python依赖
echo "安装后端依赖..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn sqlalchemy pymysql requests python-multipart pydantic

# 安装前端依赖
echo "安装前端依赖..."
cd ../frontend
npm install --force

# 配置防火墙
echo "配置防火墙..."
if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-port=8000/tcp --quiet || true
    firewall-cmd --permanent --add-port=5173/tcp --quiet || true
    firewall-cmd --reload --quiet || true
fi

# 测试HDFS
echo "🐘 测试HDFS访问..."
if command -v hdfs &> /dev/null; then
    echo "✅ HDFS命令可用"
    hdfs version | head -1
    if hdfs dfs -ls / &> /dev/null; then
        echo "✅ HDFS访问正常"
    else
        echo "⚠️  HDFS需要权限配置"
    fi
else
    echo "❌ HDFS命令未找到"
fi

# 创建启动脚本
cat > /opt/hive-platform/start_dev.sh << 'START_SCRIPT'
#!/bin/bash
echo "🚀 启动Hive小文件管理平台开发环境..."

# 检查端口占用
if netstat -tlnp | grep :8000 &> /dev/null; then
    echo "⚠️  端口8000已被占用，尝试终止进程..."
    pkill -f "uvicorn.*8000" || true
    sleep 2
fi

if netstat -tlnp | grep :5173 &> /dev/null; then
    echo "⚠️  端口5173已被占用，尝试终止进程..."
    pkill -f "vite.*5173" || true
    sleep 2
fi

# 启动后端
echo "启动后端服务..."
cd /opt/hive-platform/backend
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo "启动前端服务..."
cd /opt/hive-platform/frontend
nohup npm run dev -- --host 0.0.0.0 --port 5173 > ../frontend.log 2>&1 &
FRONTEND_PID=$!

echo ""
echo "🎉 开发环境启动完成！"
echo ""
echo "📊 服务状态:"
echo "  后端PID: $BACKEND_PID"
echo "  前端PID: $FRONTEND_PID"
echo ""
echo "🌐 访问地址:"
echo "  前端界面: http://192.168.0.105:5173"
echo "  后端API:  http://192.168.0.105:8000"
echo "  API文档:  http://192.168.0.105:8000/docs"
echo ""
echo "📋 日志文件:"
echo "  后端日志: /opt/hive-platform/backend.log"
echo "  前端日志: /opt/hive-platform/frontend.log"
echo ""
echo "🛑 停止服务: pkill -f uvicorn && pkill -f vite"
echo ""
START_SCRIPT

chmod +x /opt/hive-platform/start_dev.sh

echo ""
echo "🎊 服务器环境设置完成！"
echo ""
echo "🚀 快速启动命令:"
echo "  /opt/hive-platform/start_dev.sh"
echo ""
echo "📁 项目目录: /opt/hive-platform"
echo ""
echo "🌐 访问地址:"
echo "  前端: http://192.168.0.105:5173"
echo "  后端: http://192.168.0.105:8000"
echo ""
EOF

# 4. 传输设置脚本并执行
echo "📤 传输设置脚本..."
scp server_setup.sh "$SERVER_USER@$SERVER_IP:/tmp/"

echo "⚙️  在服务器上执行设置..."
ssh "$SERVER_USER@$SERVER_IP" "chmod +x /tmp/server_setup.sh && /tmp/server_setup.sh"

# 5. 清理本地文件
rm -f hive-platform-quick.tar.gz server_setup.sh

echo ""
echo "🎉 快速迁移完成！"
echo ""
echo "🔗 现在可以SSH到服务器开始开发:"
echo "ssh $SERVER_USER@$SERVER_IP"
echo ""
echo "🚀 启动开发环境:"
echo "/opt/hive-platform/start_dev.sh"
echo ""
echo "🌐 直接访问:"
echo "前端: http://$SERVER_IP:5173"
echo "后端: http://$SERVER_IP:8000"
echo ""
echo "💡 下一步:"
echo "1. SSH登录到服务器"
echo "2. 运行启动脚本"
echo "3. 在浏览器中测试功能"
echo "4. 开始获取真实HDFS数据！"
echo ""