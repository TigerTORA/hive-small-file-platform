/**
 * 测试仪表板集成脚本
 * 连接前端Vue组件和后端数据收集器/执行器
 * 提供API接口供前端调用
 */

const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const TestDashboardCollector = require('./test-dashboard-collector');
const TestRunnerAggregator = require('./test-runner-aggregator');

class TestDashboardIntegration {
    constructor() {
        this.app = express();
        this.port = 3001;
        this.testResultsDir = path.join(process.cwd(), 'test-results');
        this.collector = new TestDashboardCollector();
        this.aggregator = new TestRunnerAggregator();
        
        this.setupMiddleware();
        this.setupRoutes();
        this.ensureTestResultsDir();
    }

    /**
     * 设置中间件
     */
    setupMiddleware() {
        this.app.use(cors({
            origin: ['http://localhost:3002', 'http://localhost:3000', 'http://localhost:5173'],
            credentials: true
        }));
        
        this.app.use(express.json());
        this.app.use(express.static(this.testResultsDir));
    }

    /**
     * 设置路由
     */
    setupRoutes() {
        // 获取测试数据概览
        this.app.get('/api/test/overview', async (req, res) => {
            try {
                const data = await this.getTestOverview();
                res.json({ success: true, data });
            } catch (error) {
                console.error('获取测试概览失败:', error);
                res.status(500).json({ success: false, error: error.message });
            }
        });

        // 获取测试分类数据
        this.app.get('/api/test/categories', async (req, res) => {
            try {
                const data = await this.getTestCategories();
                res.json({ success: true, data });
            } catch (error) {
                console.error('获取测试分类失败:', error);
                res.status(500).json({ success: false, error: error.message });
            }
        });

        // 获取详细测试结果
        this.app.get('/api/test/results', async (req, res) => {
            try {
                const { category, status, page = 1, pageSize = 20 } = req.query;
                const data = await this.getTestResults({ category, status, page, pageSize });
                res.json({ success: true, data });
            } catch (error) {
                console.error('获取测试结果失败:', error);
                res.status(500).json({ success: false, error: error.message });
            }
        });

        // 执行所有测试
        this.app.post('/api/test/run-all', async (req, res) => {
            try {
                const { parallel = false, maxConcurrency = 3 } = req.body;
                
                // 异步执行测试，立即返回
                this.runAllTestsAsync({ parallel, maxConcurrency });
                
                res.json({ success: true, message: '测试执行已开始' });
            } catch (error) {
                console.error('启动测试执行失败:', error);
                res.status(500).json({ success: false, error: error.message });
            }
        });

        // 执行单个测试
        this.app.post('/api/test/run-single', async (req, res) => {
            try {
                const { testFile } = req.body;
                if (!testFile) {
                    return res.status(400).json({ success: false, error: '缺少testFile参数' });
                }

                const result = await this.runSingleTest(testFile);
                res.json({ success: true, data: result });
            } catch (error) {
                console.error('执行单个测试失败:', error);
                res.status(500).json({ success: false, error: error.message });
            }
        });

        // 刷新测试数据
        this.app.post('/api/test/refresh', async (req, res) => {
            try {
                await this.collector.collectAll();
                res.json({ success: true, message: '数据刷新完成' });
            } catch (error) {
                console.error('刷新测试数据失败:', error);
                res.status(500).json({ success: false, error: error.message });
            }
        });

        // 获取测试执行状态
        this.app.get('/api/test/status', async (req, res) => {
            try {
                const status = {
                    isRunning: this.aggregator.isRunning,
                    lastExecution: await this.getLastExecutionInfo()
                };
                res.json({ success: true, data: status });
            } catch (error) {
                console.error('获取测试状态失败:', error);
                res.status(500).json({ success: false, error: error.message });
            }
        });

        // 获取测试报告
        this.app.get('/api/test/reports', async (req, res) => {
            try {
                const reports = await this.getAvailableReports();
                res.json({ success: true, data: reports });
            } catch (error) {
                console.error('获取测试报告失败:', error);
                res.status(500).json({ success: false, error: error.message });
            }
        });

        // 下载测试报告
        this.app.get('/api/test/reports/:type', async (req, res) => {
            try {
                const { type } = req.params;
                const filePath = await this.getReportFilePath(type);
                
                if (!fs.existsSync(filePath)) {
                    return res.status(404).json({ success: false, error: '报告文件不存在' });
                }

                res.download(filePath);
            } catch (error) {
                console.error('下载测试报告失败:', error);
                res.status(500).json({ success: false, error: error.message });
            }
        });

        // 健康检查
        this.app.get('/api/health', (req, res) => {
            res.json({ 
                success: true, 
                service: 'test-dashboard-integration',
                timestamp: new Date().toISOString()
            });
        });
    }

    /**
     * 获取测试概览数据
     */
    async getTestOverview() {
        const summaryPath = path.join(this.testResultsDir, 'dashboard-summary.json');
        const livePath = path.join(this.testResultsDir, 'dashboard-live-data.json');

        let data = null;

        // 优先使用实时数据
        if (fs.existsSync(livePath)) {
            data = JSON.parse(fs.readFileSync(livePath, 'utf8'));
            if (data.lastExecution) {
                return {
                    totalTests: data.lastExecution.totalTests || 0,
                    totalPassed: data.lastExecution.passedTests || 0,
                    totalFailed: data.lastExecution.failedTests || 0,
                    totalSkipped: data.lastExecution.errorTests || 0,
                    successRate: data.lastExecution.successRate || 0,
                    lastUpdate: data.updatedAt
                };
            }
        }

        // 使用收集器数据
        if (fs.existsSync(summaryPath)) {
            data = JSON.parse(fs.readFileSync(summaryPath, 'utf8'));
            if (data.overview) {
                return {
                    totalTests: data.overview.totalTests || 0,
                    totalPassed: data.overview.totalPassed || 0,
                    totalFailed: data.overview.totalFailed || 0,
                    totalSkipped: data.overview.totalSkipped || 0,
                    successRate: data.overview.successRate || 0,
                    lastUpdate: data.lastCollected
                };
            }
        }

        // 返回默认数据
        return {
            totalTests: 0,
            totalPassed: 0,
            totalFailed: 0,
            totalSkipped: 0,
            successRate: 0,
            lastUpdate: new Date().toISOString()
        };
    }

    /**
     * 获取测试分类数据
     */
    async getTestCategories() {
        const summaryPath = path.join(this.testResultsDir, 'dashboard-summary.json');
        const livePath = path.join(this.testResultsDir, 'dashboard-live-data.json');

        // 优先使用实时数据
        if (fs.existsSync(livePath)) {
            const data = JSON.parse(fs.readFileSync(livePath, 'utf8'));
            if (data.categories) {
                return data.categories;
            }
        }

        // 使用收集器数据
        if (fs.existsSync(summaryPath)) {
            const data = JSON.parse(fs.readFileSync(summaryPath, 'utf8'));
            if (data.categories) {
                return data.categories;
            }
        }

        // 返回默认分类
        return this.getDefaultCategories();
    }

    /**
     * 获取详细测试结果
     */
    async getTestResults(filters) {
        const livePath = path.join(this.testResultsDir, 'dashboard-live-data.json');
        const dataPath = path.join(this.testResultsDir, 'dashboard-data.json');

        let testResults = [];

        // 优先使用实时数据
        if (fs.existsSync(livePath)) {
            const data = JSON.parse(fs.readFileSync(livePath, 'utf8'));
            testResults = data.testResults || [];
        } else if (fs.existsSync(dataPath)) {
            const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
            testResults = data.testResults || [];
        }

        // 应用过滤器
        let filtered = testResults;
        
        if (filters.category) {
            filtered = filtered.filter(test => test.category === filters.category);
        }
        
        if (filters.status) {
            filtered = filtered.filter(test => test.status === filters.status);
        }

        // 分页
        const page = parseInt(filters.page) || 1;
        const pageSize = parseInt(filters.pageSize) || 20;
        const startIndex = (page - 1) * pageSize;
        const endIndex = startIndex + pageSize;

        return {
            results: filtered.slice(startIndex, endIndex),
            total: filtered.length,
            page,
            pageSize,
            totalPages: Math.ceil(filtered.length / pageSize)
        };
    }

    /**
     * 异步执行所有测试
     */
    async runAllTestsAsync(options) {
        console.log('🚀 开始异步执行所有测试...');
        
        try {
            const results = await this.aggregator.runAllTests(options);
            console.log('✅ 所有测试执行完成');
        } catch (error) {
            console.error('❌ 测试执行失败:', error);
        }
    }

    /**
     * 执行单个测试
     */
    async runSingleTest(testFile) {
        console.log(`🧪 执行单个测试: ${testFile}`);
        
        const testFilePath = path.join(process.cwd(), testFile);
        
        if (!fs.existsSync(testFilePath)) {
            throw new Error(`测试文件不存在: ${testFile}`);
        }

        // 创建临时aggregator实例执行单个测试
        const singleTestResult = await this.aggregator.runSingleTest({
            filePath: testFile,
            fullPath: testFilePath,
            fileName: path.basename(testFile)
        });

        return singleTestResult;
    }

    /**
     * 获取最后执行信息
     */
    async getLastExecutionInfo() {
        const executionPath = path.join(this.testResultsDir, 'execution-report.json');
        
        if (fs.existsSync(executionPath)) {
            const data = JSON.parse(fs.readFileSync(executionPath, 'utf8'));
            return data.executionSummary;
        }

        return null;
    }

    /**
     * 获取可用报告
     */
    async getAvailableReports() {
        const reports = [];
        
        const reportFiles = [
            { type: 'json', name: 'JSON报告', file: 'execution-report.json' },
            { type: 'html', name: 'HTML报告', file: 'test-report.html' },
            { type: 'csv', name: 'CSV报告', file: 'test-results.csv' }
        ];

        for (const report of reportFiles) {
            const filePath = path.join(this.testResultsDir, report.file);
            if (fs.existsSync(filePath)) {
                const stats = fs.statSync(filePath);
                reports.push({
                    type: report.type,
                    name: report.name,
                    file: report.file,
                    size: stats.size,
                    lastModified: stats.mtime.toISOString()
                });
            }
        }

        return reports;
    }

    /**
     * 获取报告文件路径
     */
    async getReportFilePath(type) {
        const fileMap = {
            'json': 'execution-report.json',
            'html': 'test-report.html',
            'csv': 'test-results.csv'
        };

        const fileName = fileMap[type];
        if (!fileName) {
            throw new Error(`不支持的报告类型: ${type}`);
        }

        return path.join(this.testResultsDir, fileName);
    }

    /**
     * 获取默认分类
     */
    getDefaultCategories() {
        return [
            {
                id: 'data-integrity',
                name: '数据完整性验证',
                testCount: 0,
                passedTests: 0,
                failedTests: 0,
                successRate: 0
            },
            {
                id: 'navigation',
                name: '导航功能测试',
                testCount: 0,
                passedTests: 0,
                failedTests: 0,
                successRate: 0
            },
            {
                id: 'api-connection',
                name: 'API连接状态验证',
                testCount: 0,
                passedTests: 0,
                failedTests: 0,
                successRate: 0
            }
        ];
    }

    /**
     * 确保测试结果目录存在
     */
    ensureTestResultsDir() {
        if (!fs.existsSync(this.testResultsDir)) {
            fs.mkdirSync(this.testResultsDir, { recursive: true });
        }
    }

    /**
     * 启动服务器
     */
    async start() {
        // 初始化时收集一次数据
        try {
            console.log('🔄 初始化测试数据...');
            await this.collector.collectAll();
            console.log('✅ 初始化完成');
        } catch (error) {
            console.warn('⚠️ 初始化测试数据失败:', error.message);
        }

        return new Promise((resolve) => {
            this.server = this.app.listen(this.port, () => {
                console.log(`🚀 测试仪表板集成服务启动`);
                console.log(`📡 服务地址: http://localhost:${this.port}`);
                console.log(`📊 API端点:`);
                console.log(`  GET  /api/test/overview    - 获取测试概览`);
                console.log(`  GET  /api/test/categories  - 获取测试分类`);
                console.log(`  GET  /api/test/results     - 获取测试结果`);
                console.log(`  POST /api/test/run-all     - 执行所有测试`);
                console.log(`  POST /api/test/run-single  - 执行单个测试`);
                console.log(`  POST /api/test/refresh     - 刷新测试数据`);
                console.log(`  GET  /api/test/status      - 获取执行状态`);
                console.log(`  GET  /api/test/reports     - 获取可用报告`);
                resolve(this.server);
            });
        });
    }

    /**
     * 停止服务器
     */
    async stop() {
        if (this.server) {
            return new Promise((resolve) => {
                this.server.close(() => {
                    console.log('🔒 测试仪表板集成服务已停止');
                    resolve();
                });
            });
        }
    }
}

// 主执行函数
async function main() {
    const integration = new TestDashboardIntegration();
    
    try {
        await integration.start();
        
        // 优雅关闭处理
        process.on('SIGINT', async () => {
            console.log('\n📡 接收到停止信号，正在关闭服务...');
            await integration.stop();
            process.exit(0);
        });
        
        process.on('SIGTERM', async () => {
            console.log('\n📡 接收到终止信号，正在关闭服务...');
            await integration.stop();
            process.exit(0);
        });
        
    } catch (error) {
        console.error('💥 启动失败:', error.message);
        process.exit(1);
    }
}

// 如果直接运行此文件，启动服务
if (require.main === module) {
    main();
}

module.exports = TestDashboardIntegration;