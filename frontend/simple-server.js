const http = require('http');
const fs = require('fs');
const path = require('path');

const server = http.createServer((req, res) => {
  // 设置 CORS 头
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.url === '/' || req.url === '/index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(`
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hive 小文件治理平台</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 600px;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 20px;
        }
        .status {
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .api-test {
            margin: 20px 0;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
        }
        button:hover {
            background: #0056b3;
        }
        .result {
            margin: 20px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Hive 小文件治理平台</h1>
        <div class="status">
            ✅ 前端服务运行正常！
        </div>
        
        <div class="api-test">
            <h3>API 连接测试</h3>
            <button onclick="testAPI()">测试后端连接</button>
            <button onclick="testHealth()">健康检查</button>
            <div id="result" class="result"></div>
        </div>

        <div style="margin-top: 30px;">
            <h3>🔧 下一步操作</h3>
            <p>1. 确保后端服务运行在 http://localhost:8000</p>
            <p>2. 访问 <a href="http://localhost:8000/docs" target="_blank">http://localhost:8000/docs</a> 查看 API 文档</p>
            <p>3. 在集群管理中配置您的 Hive/HDFS 连接</p>
        </div>
    </div>

    <script>
        async function testAPI() {
            const resultDiv = document.getElementById('result');
            resultDiv.textContent = '正在测试...';
            
            try {
                const response = await fetch('http://localhost:8000/');
                const data = await response.json();
                resultDiv.textContent = '✅ 后端连接成功!\\n' + JSON.stringify(data, null, 2);
            } catch (error) {
                resultDiv.textContent = '❌ 后端连接失败: ' + error.message + '\\n\\n请确保后端服务已启动';
            }
        }

        async function testHealth() {
            const resultDiv = document.getElementById('result');
            resultDiv.textContent = '正在检查健康状态...';
            
            try {
                const response = await fetch('http://localhost:8000/health');
                const data = await response.json();
                resultDiv.textContent = '✅ 系统健康检查通过!\\n' + JSON.stringify(data, null, 2);
            } catch (error) {
                resultDiv.textContent = '❌ 健康检查失败: ' + error.message;
            }
        }
    </script>
</body>
</html>
    `);
  } else {
    res.writeHead(404);
    res.end('Page not found');
  }
});

const PORT = 3000;
server.listen(PORT, () => {
  console.log('🚀 简化前端服务启动成功!');
  console.log('📍 访问地址: http://localhost:3000');
  console.log('🛑 按 Ctrl+C 停止服务');
});

// 优雅关闭
process.on('SIGINT', () => {
  console.log('\\n👋 服务已停止');
  process.exit(0);
});