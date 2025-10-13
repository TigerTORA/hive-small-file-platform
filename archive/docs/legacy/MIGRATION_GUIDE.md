# 项目迁移到192.168.0.105服务器指南

## 🎯 目标
将整个Hive小文件管理平台迁移到HDFS节点(192.168.0.105)上开发，实现：
- 原生HDFS访问，获取100%真实数据
- 避免macOS兼容性问题
- 在生产环境中直接开发

## 📋 迁移步骤

### 步骤1: 准备项目打包
```bash
# 在macOS上执行
cd /Users/luohu/new_project
tar -czf hive-platform.tar.gz \
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
```

### 步骤2: 传输到服务器
```bash
# 传输项目压缩包
scp hive-platform.tar.gz root@192.168.0.105:/tmp/

# SSH登录到服务器
ssh root@192.168.0.105
# 密码: !qaz2wsx3edC
```

### 步骤3: 在服务器上安装环境
```bash
# 在192.168.0.105上执行

# 解压项目
cd /tmp
tar -xzf hive-platform.tar.gz
mkdir -p /opt/hive-platform
mv hive-small-file-platform/* /opt/hive-platform/
cd /opt/hive-platform

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
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --permanent --add-port=5173/tcp
firewall-cmd --reload
```

### 步骤4: 安装项目依赖
```bash
# 在/opt/hive-platform目录下执行

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
```

### 步骤5: 测试HDFS访问
```bash
# 测试HDFS命令
hdfs version
hdfs dfs -ls /

# 如果权限不足，尝试
sudo -u hdfs hdfs dfs -ls /
```

### 步骤6: 启动服务
```bash
# 启动后端 (终端1)
cd /opt/hive-platform/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端 (终端2)
cd /opt/hive-platform/frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

### 步骤7: 验证迁移
访问以下地址验证功能：
- 后端API: http://192.168.0.105:8000
- 前端界面: http://192.168.0.105:5173
- API文档: http://192.168.0.105:8000/docs

## 🔧 配置原生HDFS扫描器

### 修改混合表扫描器
编辑 `backend/app/monitor/hybrid_table_scanner.py`:

```python
# 在_initialize_hdfs_scanner方法中，添加原生HDFS扫描器
from app.monitor.native_hdfs_scanner import NativeHDFSScanner

def _initialize_hdfs_scanner(self):
    """智能初始化HDFS扫描器 - 优先使用原生扫描器"""
    if self.hdfs_scanner is not None:
        return
    
    try:
        # 优先使用原生HDFS扫描器
        native_scanner = NativeHDFSScanner(
            self.cluster.hdfs_namenode_url, 
            self.cluster.hdfs_user
        )
        result = native_scanner.test_connection()
        
        if result['status'] == 'success':
            logger.info(f"✅ 原生HDFS扫描器连接成功")
            self.hdfs_scanner = native_scanner
            self.hdfs_mode = 'native_real'
            return
    except Exception as e:
        logger.warning(f"原生HDFS扫描器失败: {e}")
    
    # 回退到智能混合扫描器（原有逻辑）
    # ... 原有代码
```

## 🚀 开发环境配置

### VS Code远程开发
1. 安装VS Code Server:
```bash
# 在服务器上安装code-server
curl -fsSL https://code-server.dev/install.sh | sh
sudo systemctl enable --now code-server@root
```

2. 配置访问:
```bash
# 编辑配置文件
vim ~/.config/code-server/config.yaml
# 设置:
# bind-addr: 0.0.0.0:8080
# password: your_password
```

### Git配置
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### SSH密钥设置（可选）
```bash
# 生成SSH密钥
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 添加到GitHub/GitLab
cat ~/.ssh/id_rsa.pub
```

## 📊 验证真实数据获取

### 测试原生HDFS扫描器
```bash
cd /opt/hive-platform/backend
source venv/bin/activate
python3 -c "
from app.monitor.native_hdfs_scanner import NativeHDFSScanner
scanner = NativeHDFSScanner()
result = scanner.test_connection()
print('连接状态:', result['status'])
if result['status'] == 'success':
    scan_result = scanner.scan_path('/user')
    print('扫描结果:', scan_result['total_files'], '个文件')
"
```

### 测试API端点
```bash
# 测试集群连接
curl http://localhost:8000/api/v1/tables/test-connection/1

# 测试单表扫描（应该返回真实数据）
curl -X POST http://localhost:8000/api/v1/tables/scan-table/1/default/test_table
```

## 🎯 预期结果

迁移完成后，你将获得：
- ✅ 100%真实的HDFS文件数据
- ✅ 无Kerberos兼容性问题
- ✅ 直接在生产环境开发
- ✅ 更快的文件扫描性能
- ✅ 准确的小文件分析结果

## 📝 开发工作流

1. **SSH连接到服务器**: `ssh root@192.168.0.105`
2. **启动开发服务**: 
   - 后端: `cd /opt/hive-platform/backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
   - 前端: `cd /opt/hive-platform/frontend && npm run dev -- --host 0.0.0.0`
3. **代码编辑**: 使用vim/nano或VS Code Server
4. **测试**: 通过浏览器访问 http://192.168.0.105:5173
5. **提交代码**: 正常的Git工作流

## 🆘 常见问题

### HDFS权限问题
```bash
# 如果hdfs命令权限不足
sudo -u hdfs hdfs dfs -ls /

# 或检查当前用户是否在hdfs组
groups
usermod -a -G hdfs root
```

### 端口访问问题
```bash
# 检查防火墙
firewall-cmd --list-ports
systemctl status firewalld

# 检查端口占用
netstat -tlnp | grep 8000
```

### Node.js版本问题
```bash
# 如果Node.js版本不对
node --version  # 应该是v18+
npm --version
```