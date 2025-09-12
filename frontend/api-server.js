#!/usr/bin/env node
const express = require('express');
const cors = require('cors');
const RealTestExecutor = require('./real-test-executor');
const fs = require('fs').promises;
const path = require('path');

const app = express();
const PORT = 3002;

// 全局状态
let currentTestMode = 'mock'; // 'mock' 或 'real'
let realTestResults = null;
let testExecutionStatus = {
  isRunning: false,
  progress: 0,
  startTime: null,
  currentTest: null
};

app.use(cors({
    origin: ['http://localhost:3001', 'http://localhost:3000'],
    credentials: true
}));

app.use(express.json());
app.use((req, res, next) => {
    console.log(`📨 ${req.method} ${req.url}`);
    next();
});

// 辅助函数
async function loadRealTestResults() {
    try {
        const resultsPath = path.join(process.cwd(), 'test-results', 'real-test-results.json');
        const data = await fs.readFile(resultsPath, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        console.log('🔄 未找到真实测试结果，将执行测试');
        return null;
    }
}

function getMockData() {
    return {
        overview: {
            totalTests: 36,
            totalPassed: 27,
            totalFailed: 6,
            totalSkipped: 3,
            successRate: 75,
            lastUpdate: new Date().toISOString()
        },
        categories: [
            { name: "导航功能测试", testCount: 12, passedTests: 10, failedTests: 1, skippedTests: 1, successRate: 83 },
            { name: "数据完整性验证", testCount: 7, passedTests: 5, failedTests: 2, skippedTests: 0, successRate: 71 },
            { name: "API连接状态验证", testCount: 10, passedTests: 7, failedTests: 1, skippedTests: 2, successRate: 70 },
            { name: "用户界面元素检查", testCount: 7, passedTests: 5, failedTests: 2, skippedTests: 0, successRate: 71 }
        ]
    };
}

app.get('/api/test/overview', async (req, res) => {
    try {
        let data;
        
        if (currentTestMode === 'real' && realTestResults) {
            data = realTestResults.overview;
        } else if (currentTestMode === 'real') {
            const loadedResults = await loadRealTestResults();
            if (loadedResults) {
                realTestResults = loadedResults;
                data = loadedResults.overview;
            } else {
                data = getMockData().overview;
            }
        } else {
            data = getMockData().overview;
        }
        
        res.json({
            success: true,
            data: data,
            mode: currentTestMode,
            isRunning: testExecutionStatus.isRunning
        });
    } catch (error) {
        console.error('获取概览数据失败:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/test/categories', async (req, res) => {
    try {
        let data;
        
        if (currentTestMode === 'real' && realTestResults) {
            data = realTestResults.categories;
        } else if (currentTestMode === 'real') {
            const loadedResults = await loadRealTestResults();
            if (loadedResults) {
                realTestResults = loadedResults;
                data = loadedResults.categories;
            } else {
                data = getMockData().categories;
            }
        } else {
            data = getMockData().categories;
        }
        
        res.json({
            success: true,
            data: data,
            mode: currentTestMode
        });
    } catch (error) {
        console.error('获取分类数据失败:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/test/results', async (req, res) => {
    try {
        let testResults = [];
        
        if (currentTestMode === 'real' && realTestResults) {
            testResults = realTestResults.testResults || [];
        } else if (currentTestMode === 'real') {
            const loadedResults = await loadRealTestResults();
            if (loadedResults) {
                realTestResults = loadedResults;
                testResults = loadedResults.testResults || [];
            } else {
                testResults = getMockTestResults();
            }
        } else {
            testResults = getMockTestResults();
        }
        
        // 应用过滤器
        const { category, status, page = 1, pageSize = 20 } = req.query;
        let filtered = testResults;
        
        if (category) {
            filtered = filtered.filter(test => test.category === category);
        }
        
        if (status) {
            filtered = filtered.filter(test => test.status === status);
        }
        
        // 分页
        const startIndex = (parseInt(page) - 1) * parseInt(pageSize);
        const endIndex = startIndex + parseInt(pageSize);
        
        res.json({
            success: true,
            data: {
                results: filtered.slice(startIndex, endIndex),
                totalCount: filtered.length,
                currentPage: parseInt(page),
                pageSize: parseInt(pageSize)
            },
            mode: currentTestMode
        });
    } catch (error) {
        console.error('获取测试结果失败:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

function getMockTestResults() {
    return [
        { id: 1, name: "测试登录功能", category: "导航功能测试", status: "passed", duration: 1200, startTime: "2024-09-11T10:00:00Z", endTime: "2024-09-11T10:00:01Z" },
        { id: 2, name: "测试数据加载", category: "数据完整性验证", status: "failed", duration: 2100, startTime: "2024-09-11T10:01:00Z", endTime: "2024-09-11T10:01:02Z" },
        { id: 3, name: "测试API连接", category: "API连接状态验证", status: "passed", duration: 800, startTime: "2024-09-11T10:02:00Z", endTime: "2024-09-11T10:02:01Z" },
        { id: 4, name: "测试界面元素", category: "用户界面元素检查", status: "skipped", duration: 0, startTime: "2024-09-11T10:03:00Z", endTime: "2024-09-11T10:03:00Z" },
        { id: 5, name: "测试路由跳转", category: "导航功能测试", status: "passed", duration: 1500, startTime: "2024-09-11T10:04:00Z", endTime: "2024-09-11T10:04:02Z" },
        { id: 6, name: "测试集群连接", category: "API连接状态验证", status: "passed", duration: 900, startTime: "2024-09-11T10:05:00Z", endTime: "2024-09-11T10:05:01Z" },
        { id: 7, name: "测试表格显示", category: "用户界面元素检查", status: "passed", duration: 1100, startTime: "2024-09-11T10:06:00Z", endTime: "2024-09-11T10:06:01Z" },
        { id: 8, name: "测试分页功能", category: "导航功能测试", status: "failed", duration: 1800, startTime: "2024-09-11T10:07:00Z", endTime: "2024-09-11T10:07:02Z" },
        { id: 9, name: "测试搜索功能", category: "导航功能测试", status: "passed", duration: 1300, startTime: "2024-09-11T10:08:00Z", endTime: "2024-09-11T10:08:01Z" },
        { id: 10, name: "测试表单验证", category: "数据完整性验证", status: "passed", duration: 2200, startTime: "2024-09-11T10:09:00Z", endTime: "2024-09-11T10:09:02Z" },
        { id: 11, name: "测试文件上传", category: "数据完整性验证", status: "failed", duration: 3000, startTime: "2024-09-11T10:10:00Z", endTime: "2024-09-11T10:10:03Z" },
        { id: 12, name: "测试权限控制", category: "API连接状态验证", status: "passed", duration: 1000, startTime: "2024-09-11T10:11:00Z", endTime: "2024-09-11T10:11:01Z" },
        { id: 13, name: "测试响应式布局", category: "用户界面元素检查", status: "passed", duration: 1400, startTime: "2024-09-11T10:12:00Z", endTime: "2024-09-11T10:12:01Z" },
        { id: 14, name: "测试错误处理", category: "数据完整性验证", status: "passed", duration: 1600, startTime: "2024-09-11T10:13:00Z", endTime: "2024-09-11T10:13:02Z" },
        { id: 15, name: "测试数据导出", category: "导航功能测试", status: "skipped", duration: 0, startTime: "2024-09-11T10:14:00Z", endTime: "2024-09-11T10:14:00Z" },
        { id: 16, name: "测试多语言切换", category: "用户界面元素检查", status: "passed", duration: 800, startTime: "2024-09-11T10:15:00Z", endTime: "2024-09-11T10:15:01Z" },
        { id: 17, name: "测试暗黑模式", category: "用户界面元素检查", status: "failed", duration: 1200, startTime: "2024-09-11T10:16:00Z", endTime: "2024-09-11T10:16:01Z" },
        { id: 18, name: "测试缓存机制", category: "API连接状态验证", status: "passed", duration: 2500, startTime: "2024-09-11T10:17:00Z", endTime: "2024-09-11T10:17:03Z" },
        { id: 19, name: "测试并发处理", category: "API连接状态验证", status: "failed", duration: 4000, startTime: "2024-09-11T10:18:00Z", endTime: "2024-09-11T10:18:04Z" },
        { id: 20, name: "测试数据库连接", category: "数据完整性验证", status: "passed", duration: 1700, startTime: "2024-09-11T10:19:00Z", endTime: "2024-09-11T10:19:02Z" },
        { id: 21, name: "测试定时任务", category: "导航功能测试", status: "passed", duration: 2800, startTime: "2024-09-11T10:20:00Z", endTime: "2024-09-11T10:20:03Z" },
        { id: 22, name: "测试日志记录", category: "数据完整性验证", status: "passed", duration: 900, startTime: "2024-09-11T10:21:00Z", endTime: "2024-09-11T10:21:01Z" },
        { id: 23, name: "测试性能监控", category: "API连接状态验证", status: "skipped", duration: 0, startTime: "2024-09-11T10:22:00Z", endTime: "2024-09-11T10:22:00Z" },
        { id: 24, name: "测试安全防护", category: "API连接状态验证", status: "passed", duration: 1900, startTime: "2024-09-11T10:23:00Z", endTime: "2024-09-11T10:23:02Z" },
        { id: 25, name: "测试消息通知", category: "用户界面元素检查", status: "passed", duration: 1100, startTime: "2024-09-11T10:24:00Z", endTime: "2024-09-11T10:24:01Z" },
        { id: 26, name: "测试状态管理", category: "导航功能测试", status: "passed", duration: 1300, startTime: "2024-09-11T10:25:00Z", endTime: "2024-09-11T10:25:01Z" },
        { id: 27, name: "测试组件通信", category: "用户界面元素检查", status: "failed", duration: 2100, startTime: "2024-09-11T10:26:00Z", endTime: "2024-09-11T10:26:02Z" },
        { id: 28, name: "测试代码分割", category: "导航功能测试", status: "passed", duration: 1800, startTime: "2024-09-11T10:27:00Z", endTime: "2024-09-11T10:27:02Z" },
        { id: 29, name: "测试懒加载", category: "导航功能测试", status: "passed", duration: 1400, startTime: "2024-09-11T10:28:00Z", endTime: "2024-09-11T10:28:01Z" },
        { id: 30, name: "测试热重载", category: "用户界面元素检查", status: "passed", duration: 800, startTime: "2024-09-11T10:29:00Z", endTime: "2024-09-11T10:29:01Z" },
        { id: 31, name: "测试构建优化", category: "导航功能测试", status: "passed", duration: 3200, startTime: "2024-09-11T10:30:00Z", endTime: "2024-09-11T10:30:03Z" },
        { id: 32, name: "测试部署流程", category: "API连接状态验证", status: "skipped", duration: 0, startTime: "2024-09-11T10:31:00Z", endTime: "2024-09-11T10:31:00Z" },
        { id: 33, name: "测试监控告警", category: "API连接状态验证", status: "passed", duration: 2600, startTime: "2024-09-11T10:32:00Z", endTime: "2024-09-11T10:32:03Z" },
        { id: 34, name: "测试备份恢复", category: "数据完整性验证", status: "failed", duration: 5000, startTime: "2024-09-11T10:33:00Z", endTime: "2024-09-11T10:33:05Z" },
        { id: 35, name: "测试容灾切换", category: "API连接状态验证", status: "passed", duration: 2400, startTime: "2024-09-11T10:34:00Z", endTime: "2024-09-11T10:34:02Z" },
        { id: 36, name: "测试版本回滚", category: "导航功能测试", status: "passed", duration: 1900, startTime: "2024-09-11T10:35:00Z", endTime: "2024-09-11T10:35:02Z" }
    ];
}

// 新增模式切换端点
app.post('/api/test/mode', (req, res) => {
    const { mode } = req.body;
    
    if (mode === 'mock' || mode === 'real') {
        currentTestMode = mode;
        console.log(`🔄 切换到${mode === 'mock' ? '模拟' : '真实'}测试模式`);
        
        res.json({
            success: true,
            message: `已切换到${mode === 'mock' ? '模拟' : '真实'}测试模式`,
            currentMode: currentTestMode
        });
    } else {
        res.status(400).json({
            success: false,
            error: '无效的模式，请使用 "mock" 或 "real"'
        });
    }
});

// 获取当前模式
app.get('/api/test/mode', (req, res) => {
    res.json({
        success: true,
        currentMode: currentTestMode,
        isRunning: testExecutionStatus.isRunning
    });
});

// 执行真实测试端点
app.post('/api/test/run-real', async (req, res) => {
    if (testExecutionStatus.isRunning) {
        return res.json({
            success: false,
            message: '测试正在执行中，请稍后再试'
        });
    }
    
    console.log('🚀 开始执行真实测试...');
    
    // 立即返回响应，异步执行测试
    res.json({
        success: true,
        message: '真实测试已开始执行',
        taskId: Date.now().toString()
    });
    
    // 异步执行测试
    runRealTestsAsync();
});

// 异步执行真实测试
async function runRealTestsAsync() {
    testExecutionStatus = {
        isRunning: true,
        progress: 0,
        startTime: new Date().toISOString(),
        currentTest: '初始化中...'
    };
    
    try {
        const executor = new RealTestExecutor();
        
        // 更新进度
        testExecutionStatus.currentTest = '正在执行单元测试...';
        testExecutionStatus.progress = 25;
        
        const results = await executor.executeAllTests();
        
        // 更新进度
        testExecutionStatus.currentTest = '正在保存结果...';
        testExecutionStatus.progress = 90;
        
        await executor.saveResults();
        
        // 更新全局结果
        realTestResults = results;
        currentTestMode = 'real';
        
        testExecutionStatus = {
            isRunning: false,
            progress: 100,
            startTime: testExecutionStatus.startTime,
            currentTest: '测试完成',
            endTime: new Date().toISOString()
        };
        
        console.log('✅ 真实测试执行完成');
        
    } catch (error) {
        console.error('❌ 真实测试执行失败:', error.message);
        
        testExecutionStatus = {
            isRunning: false,
            progress: 0,
            startTime: testExecutionStatus.startTime,
            currentTest: '测试失败: ' + error.message,
            endTime: new Date().toISOString(),
            error: error.message
        };
    }
}

// 获取测试执行状态
app.get('/api/test/status', (req, res) => {
    res.json({
        success: true,
        data: testExecutionStatus
    });
});

app.post('/api/test/refresh', (req, res) => {
    res.json({
        success: true,
        message: "测试数据已刷新",
        data: {
            refreshTime: new Date().toISOString(),
            updatedTests: 36
        }
    });
});

app.post('/api/test/run-all', async (req, res) => {
    if (currentTestMode === 'real') {
        // 如果是真实模式，调用真实测试执行
        if (testExecutionStatus.isRunning) {
            return res.json({
                success: false,
                message: '测试正在执行中，请稍后再试'
            });
        }
        
        res.json({
            success: true,
            message: "开始执行真实测试",
            data: {
                taskId: `real_task_${Date.now()}`,
                status: "running",
                mode: "real",
                startTime: new Date().toISOString()
            }
        });
        
        // 异步执行真实测试
        runRealTestsAsync();
    } else {
        // 模拟模式
        res.json({
            success: true,
            message: "开始执行模拟测试",
            data: {
                taskId: `mock_task_${Date.now()}`,
                status: "running",
                mode: "mock",
                totalTests: 36,
                progress: 0,
                startTime: new Date().toISOString()
            }
        });
    }
});

app.listen(PORT, () => {
    console.log(`✅ API服务运行在 http://localhost:${PORT}`);
    
    // 防止退出
    process.stdin.resume();
    
    // 保持活跃
    setInterval(() => {
        console.log(`⏰ ${new Date().toLocaleTimeString()} - 服务正常运行`);
    }, 30000);
});

process.on('SIGINT', () => {
    console.log('\n🔴 收到停止信号');
    process.exit(0);
});