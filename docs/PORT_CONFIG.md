# 端口配置说明文档

## 🔍 问题解释

**你看到的端口变化是正常的！** 那些变化的端口（如 50357, 50436, 51171 等）是**客户端动态端口**，不是服务器端口。

## 📍 固定端口配置

### 服务器端口（固定不变）
- **后端 API 服务**: `8000` 端口 
- **前端 Web 服务**: `3000` 端口

### 客户端端口（动态分配）
- 每次浏览器或工具发起请求时，操作系统会分配一个临时端口
- 这些端口通常在 49152-65535 范围内
- 在日志中显示为：`127.0.0.1:50357 - "GET /api/v1/clusters/ HTTP/1.1" 200 OK`

## 🔧 配置文件位置

### 后端配置 (`backend/.env`)
```env
SERVER_HOST=localhost
SERVER_PORT=8000
```

### 前端配置 (`frontend/.env`)
```env
VITE_DEV_PORT=3000
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## 📋 验证命令

### 检查服务状态
```bash
# 检查后端
curl http://localhost:8000/health

# 检查前端
curl http://localhost:3000

# 查看端口占用
lsof -i :8000 -i :3000
```

### 启动服务
```bash
# 使用统一启动脚本
./start.sh

# 或手动启动
cd backend && python -m app.main
cd frontend && npm run dev
```

## 🚀 访问地址

- **前端界面**: http://localhost:3000
- **API 接口**: http://localhost:8000/api/v1
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 💡 日志理解

### 正常日志格式
```
INFO: 127.0.0.1:50357 - "GET /api/v1/clusters/ HTTP/1.1" 200 OK
```

**解释**:
- `127.0.0.1:50357` - 客户端地址和动态端口
- 服务器监听在固定端口 8000
- 50357 是客户端临时分配的端口，每次请求都可能不同

### 服务器启动日志
```
🚀 启动 Hive Small File Platform 后端服务
📍 服务地址: http://localhost:8000
INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

## ✅ 总结

**端口配置完全正常！**
- 服务器端口固定：后端 8000，前端 3000
- 客户端端口动态变化是正常行为
- 配置文件确保端口稳定性
- 启动脚本避免端口冲突