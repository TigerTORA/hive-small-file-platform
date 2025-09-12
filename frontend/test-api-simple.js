const express = require('express');
const cors = require('cors');

const app = express();
const port = 3002;

// 中间件
app.use(cors({
    origin: ['http://localhost:3001', 'http://localhost:3000'],
    credentials: true
}));

app.use(express.json());

// 请求日志
app.use((req, res, next) => {
    console.log(`📨 ${req.method} ${req.url} - ${new Date().toISOString()}`);
    next();
});

// 简单的API路由
app.get('/api/test/overview', (req, res) => {
    console.log('🎯 收到overview请求');
    res.json({
        success: true,
        data: {
            totalTests: 36,
            totalPassed: 15,
            totalFailed: 11,
            totalSkipped: 10,
            successRate: 42,
            lastUpdate: new Date().toISOString()
        }
    });
});

app.get('/api/test/categories', (req, res) => {
    console.log('🎯 收到categories请求');
    res.json({
        success: true,
        data: [
            { name: "导航功能测试", testCount: 14, passedTests: 7, failedTests: 5, successRate: 50 },
            { name: "数据完整性验证", testCount: 9, passedTests: 2, failedTests: 4, successRate: 22 },
            { name: "API连接状态验证", testCount: 5, passedTests: 2, failedTests: 0, successRate: 40 },
            { name: "用户界面元素检查", testCount: 8, passedTests: 2, failedTests: 2, successRate: 25 }
        ]
    });
});

// 启动服务器
app.listen(port, () => {
    console.log(`🚀 简单API测试服务启动`);
    console.log(`📡 服务地址: http://localhost:${port}`);
    console.log('等待来自前端的请求...');
});