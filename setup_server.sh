#!/bin/bash

# Hive Small File Platform - Server Setup Script
# 在192.168.0.105 (CentOS/RHEL) 上安装开发环境

set -e

echo "🚀 开始安装Hive小文件管理平台开发环境..."
echo "目标服务器: 192.168.0.105"
echo "安装时间: $(date)"

# 检查是否为root用户
if [[ $EUID -ne 0 ]]; then
   echo "❌ 请以root用户运行此脚本"
   exit 1
fi

# 1. 系统更新和基础工具
echo "📦 步骤1: 更新系统和安装基础工具..."
yum update -y
yum groupinstall -y "Development Tools"
yum install -y wget curl git vim htop tree unzip nc

# 2. 安装Python 3.8+
echo "🐍 步骤2: 安装Python 3.8..."
yum install -y python38 python38-pip python38-devel

# 设置Python 3.8为默认python3
alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1

# 升级pip
python3 -m pip install --upgrade pip

echo "✅ Python版本: $(python3 --version)"

# 3. 安装Node.js 18
echo "📦 步骤3: 安装Node.js 18..."
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
yum install -y nodejs

echo "✅ Node.js版本: $(node --version)"
echo "✅ NPM版本: $(npm --version)"

# 4. 安装Claude Code CLI
echo "🤖 步骤4: 安装Claude Code CLI..."
npm install -g @anthropic/claude-code

echo "✅ Claude Code版本: $(claude-code --version)"

# 5. 创建项目目录
echo "📁 步骤5: 创建项目目录..."
mkdir -p /opt/hive-platform
cd /opt/hive-platform

# 设置目录权限
chown -R root:root /opt/hive-platform
chmod -R 755 /opt/hive-platform

# 6. 配置防火墙
echo "🔥 步骤6: 配置防火墙..."
# 检查防火墙状态
if systemctl is-active --quiet firewalld; then
    echo "配置防火墙规则..."
    firewall-cmd --permanent --add-port=8000/tcp   # FastAPI后端
    firewall-cmd --permanent --add-port=5173/tcp   # Vite开发服务器
    firewall-cmd --permanent --add-port=3000/tcp   # 备用端口
    firewall-cmd --reload
    echo "✅ 防火墙规则已配置"
else
    echo "⚠️  防火墙未运行，跳过配置"
fi

# 7. 测试HDFS命令可用性
echo "🐘 步骤7: 测试HDFS命令..."
if command -v hdfs &> /dev/null; then
    echo "✅ HDFS命令可用"
    hdfs version | head -3
    
    # 测试HDFS访问
    echo "测试HDFS根目录访问..."
    hdfs dfs -ls / | head -5 || echo "⚠️  HDFS访问可能需要权限配置"
else
    echo "❌ HDFS命令不可用，请检查Hadoop安装"
fi

# 8. 创建系统服务用户（可选）
echo "👤 步骤8: 创建应用用户..."
if ! id "hiveapp" &>/dev/null; then
    useradd -r -s /bin/bash -d /opt/hive-platform hiveapp
    echo "✅ 已创建hiveapp用户"
else
    echo "✅ hiveapp用户已存在"
fi

# 9. 安装常用Python包
echo "🐍 步骤9: 预安装Python依赖..."
pip3 install --upgrade pip setuptools wheel
pip3 install fastapi uvicorn[standard] sqlalchemy pymysql
pip3 install requests python-multipart python-jose[cryptography]
pip3 install alembic celery redis pydantic

echo "✅ 基础Python包安装完成"

# 10. 系统信息总结
echo ""
echo "🎉 服务器环境安装完成！"
echo "=============================="
echo "服务器IP: 192.168.0.105"
echo "Python版本: $(python3 --version)"
echo "Node.js版本: $(node --version)"
echo "项目目录: /opt/hive-platform"
echo "防火墙端口: 8000, 5173, 3000"
echo ""
echo "📝 下一步操作："
echo "1. 上传项目代码到 /opt/hive-platform/"
echo "2. 安装项目依赖"
echo "3. 配置数据库连接"
echo "4. 启动开发服务"
echo ""
echo "🔧 快速启动命令："
echo "cd /opt/hive-platform/backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo "cd /opt/hive-platform/frontend && npm run dev -- --host 0.0.0.0"
echo ""
echo "🌐 访问地址："
echo "后端API: http://192.168.0.105:8000"
echo "前端界面: http://192.168.0.105:5173"
echo "API文档: http://192.168.0.105:8000/docs"
echo ""