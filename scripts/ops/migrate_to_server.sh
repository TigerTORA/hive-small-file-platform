#!/bin/bash

# 完整项目迁移到192.168.0.105服务器
# 包含环境安装、代码传输、配置调整、原生HDFS集成

set -e

SERVER_IP="192.168.0.105"
SERVER_USER="root"
SERVER_PASSWORD="!qaz2wsx3edC"
PROJECT_DIR="/opt/hive-platform"
LOCAL_PROJECT_DIR="/Users/luohu/new_project/hive-small-file-platform"

echo "🚀 开始完整项目迁移到HDFS服务器..."
echo "目标服务器: $SERVER_IP"
echo "项目目录: $PROJECT_DIR"
echo "迁移时间: $(date)"

# 检查本地项目目录
if [ ! -d "$LOCAL_PROJECT_DIR" ]; then
    echo "❌ 本地项目目录不存在: $LOCAL_PROJECT_DIR"
    exit 1
fi

# 1. 测试SSH连接
echo "🔌 测试服务器连接..."
if ! ping -c 2 $SERVER_IP > /dev/null 2>&1; then
    echo "❌ 无法ping通服务器 $SERVER_IP"
    exit 1
fi

echo "✅ 网络连接正常"

# 2. 创建项目打包文件
echo "📦 创建项目打包..."
cd /Users/luohu/new_project

# 创建临时目录
TEMP_DIR="/tmp/hive-platform-migration-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEMP_DIR"

# 复制项目文件（排除不必要的文件）
echo "复制项目文件..."
rsync -av --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='*.log' \
    --exclude='.env' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='.DS_Store' \
    --exclude='frontend/dist' \
    --exclude='frontend/node_modules' \
    --exclude='backend/hive_small_file_db.db' \
    hive-small-file-platform/ "$TEMP_DIR/"

# 3. 创建服务器环境安装脚本
cat > "$TEMP_DIR/setup_server_env.sh" << 'EOF'
#!/bin/bash
set -e

echo "🔧 配置服务器开发环境..."

# 更新系统
yum update -y
yum groupinstall -y "Development Tools"
yum install -y wget curl git vim htop tree unzip nc

# 安装Python 3.8+
yum install -y python38 python38-pip python38-devel
alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
python3 -m pip install --upgrade pip

# 安装Node.js 18
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
yum install -y nodejs

# 安装Claude Code CLI
npm install -g @anthropic/claude-code

# 配置防火墙
if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-port=8000/tcp
    firewall-cmd --permanent --add-port=5173/tcp
    firewall-cmd --permanent --add-port=3000/tcp
    firewall-cmd --reload
fi

echo "✅ 服务器环境配置完成"
EOF

# 4. 创建项目配置脚本
cat > "$TEMP_DIR/setup_project.sh" << 'EOF'
#!/bin/bash
set -e

cd /opt/hive-platform

echo "📦 安装项目依赖..."

# 后端依赖
cd backend
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn[standard] sqlalchemy pymysql
pip install requests python-multipart python-jose[cryptography]
pip install alembic celery redis pydantic

# 前端依赖
cd ../frontend
npm install

echo "✅ 项目依赖安装完成"
EOF

# 5. 创建原生HDFS配置脚本
cat > "$TEMP_DIR/configure_native_hdfs.sh" << 'EOF'
#!/bin/bash
set -e

cd /opt/hive-platform

echo "🐘 配置原生HDFS访问..."

# 测试HDFS命令
if command -v hdfs &> /dev/null; then
    echo "✅ HDFS命令可用"
    hdfs version | head -3
    
    # 测试HDFS访问
    echo "测试HDFS根目录访问..."
    if hdfs dfs -ls / > /dev/null 2>&1; then
        echo "✅ HDFS访问正常"
    else
        echo "⚠️  HDFS访问可能需要权限配置，尝试使用hdfs用户"
        sudo -u hdfs hdfs dfs -ls / || echo "❌ HDFS访问失败"
    fi
else
    echo "❌ HDFS命令不可用，请检查Hadoop安装"
fi

# 创建启动脚本
cat > start_backend.sh << 'BACKEND_EOF'
#!/bin/bash
cd /opt/hive-platform/backend
source venv/bin/activate
export PYTHONPATH=/opt/hive-platform/backend:$PYTHONPATH
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
BACKEND_EOF

cat > start_frontend.sh << 'FRONTEND_EOF'
#!/bin/bash
cd /opt/hive-platform/frontend
npm run dev -- --host 0.0.0.0 --port 5173
FRONTEND_EOF

chmod +x start_backend.sh start_frontend.sh

echo "✅ 原生HDFS配置完成"
EOF

# 6. 创建测试脚本
cat > "$TEMP_DIR/test_real_data.sh" << 'EOF'
#!/bin/bash
set -e

echo "🧪 测试真实HDFS数据获取..."

# 测试原生HDFS扫描器
python3 << 'PYTHON_EOF'
import sys
sys.path.append('/opt/hive-platform/backend')

from app.monitor.native_hdfs_scanner import NativeHDFSScanner

print("🔍 测试原生HDFS扫描器...")
scanner = NativeHDFSScanner()

# 测试连接
print("测试HDFS连接...")
result = scanner.test_connection()
print(f"连接状态: {result['status']}")
if result['status'] == 'success':
    print(f"Hadoop版本: {result.get('hadoop_version', 'Unknown')}")
    print(f"根目录样本: {result.get('sample_root_dirs', [])}")
else:
    print(f"连接失败: {result.get('message', 'Unknown error')}")

# 测试路径扫描
test_paths = ['/user', '/tmp', '/']
for path in test_paths:
    print(f"\n扫描路径: {path}")
    scan_result = scanner.scan_path(path)
    if scan_result['status'] == 'success':
        print(f"  文件数量: {scan_result['total_files']}")
        print(f"  小文件数: {scan_result['small_files_count']}")
        print(f"  总大小: {scan_result['total_size']} bytes")
        print(f"  扫描模式: {scan_result['scan_mode']}")
    else:
        print(f"  扫描失败: {scan_result.get('message', 'Unknown error')}")
    
    if scan_result['status'] == 'success':
        break  # 找到一个可访问的路径就停止

print("\n✅ HDFS扫描测试完成")
PYTHON_EOF

echo "🌐 启动服务进行Web测试..."
echo "后端: http://192.168.0.105:8000"
echo "前端: http://192.168.0.105:5173"
echo "API文档: http://192.168.0.105:8000/docs"
EOF

# 7. 设置脚本权限
chmod +x "$TEMP_DIR"/*.sh

# 8. 创建项目压缩包
echo "📁 创建项目压缩包..."
cd "$TEMP_DIR"
tar -czf hive-platform-complete.tar.gz *

echo "✅ 项目打包完成: $TEMP_DIR/hive-platform-complete.tar.gz"

# 9. 传输到服务器
echo "📤 传输项目到服务器..."

# 使用scp传输（需要手动输入密码）
echo "请输入服务器密码: $SERVER_PASSWORD"
scp "$TEMP_DIR/hive-platform-complete.tar.gz" "$SERVER_USER@$SERVER_IP:/tmp/"

# 10. 在服务器上执行安装
echo "⚙️  在服务器上执行安装..."
echo "请输入服务器密码进行SSH连接..."

ssh "$SERVER_USER@$SERVER_IP" << 'REMOTE_COMMANDS'
set -e

echo "📂 解压项目文件..."
cd /tmp
tar -xzf hive-platform-complete.tar.gz
mkdir -p /opt/hive-platform
cp -r * /opt/hive-platform/
cd /opt/hive-platform

echo "🔧 执行环境安装..."
chmod +x *.sh
./setup_server_env.sh

echo "📦 安装项目依赖..."
./setup_project.sh

echo "🐘 配置HDFS访问..."
./configure_native_hdfs.sh

echo "🧪 测试真实数据获取..."
./test_real_data.sh

echo ""
echo "🎉 项目迁移完成！"
echo ""
echo "📁 项目位置: /opt/hive-platform"
echo "🚀 启动命令:"
echo "  后端: cd /opt/hive-platform && ./start_backend.sh"
echo "  前端: cd /opt/hive-platform && ./start_frontend.sh"
echo ""
echo "🌐 访问地址:"
echo "  后端API: http://192.168.0.105:8000"
echo "  前端界面: http://192.168.0.105:5173"
echo "  API文档: http://192.168.0.105:8000/docs"
echo ""
echo "📝 下一步:"
echo "1. 启动后端服务"
echo "2. 启动前端服务"
echo "3. 测试真实HDFS数据获取"
echo "4. 开始在服务器上开发"

REMOTE_COMMANDS

# 清理临时文件
echo "🧹 清理临时文件..."
rm -rf "$TEMP_DIR"

echo ""
echo "🎊 完整迁移完成！"
echo ""
echo "🔗 SSH连接到服务器开始开发:"
echo "ssh $SERVER_USER@$SERVER_IP"
echo ""
echo "💡 建议:"
echo "1. 在服务器上安装VS Code Server或配置远程开发环境"
echo "2. 配置Git用户信息"
echo "3. 设置开发工具和代码编辑器"
echo ""