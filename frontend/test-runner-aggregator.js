/**
 * 测试执行聚合器
 * 批量执行所有测试套件，聚合不同格式的测试结果
 * 生成美观的HTML报告，支持实时更新
 */

const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');
const { glob } = require('glob');
const TestDashboardCollector = require('./test-dashboard-collector');

class TestRunnerAggregator {
    constructor() {
        this.projectRoot = process.cwd();
        this.testResultsDir = path.join(this.projectRoot, 'test-results');
        this.testFiles = [];
        this.runResults = [];
        this.isRunning = false;
        this.currentExecution = null;
        this.executionStartTime = null;
        this.collector = new TestDashboardCollector();
    }

    /**
     * 发现所有可执行的测试文件
     */
    async discoverTestFiles() {
        console.log('🔍 发现测试文件...');
        
        const patterns = [
            'test-*.js',
            'frontend/test-*.js'
        ];

        const testFiles = new Set();
        
        for (const pattern of patterns) {
            try {
                const files = await glob(pattern, {
                    cwd: this.projectRoot,
                    ignore: [
                        'node_modules/**',
                        'test-dashboard-*.js',
                        'test-config.js',
                        'test-utils.js',
                        'test-data-manager.js',
                        'test-reporter.js'
                    ]
                });
                
                files.forEach(file => testFiles.add(file));
            } catch (error) {
                console.warn(`警告: 扫描模式 "${pattern}" 失败:`, error.message);
            }
        }

        // 过滤出可执行的测试文件
        this.testFiles = Array.from(testFiles)
            .map(file => ({
                filePath: file,
                fullPath: path.join(this.projectRoot, file),
                fileName: path.basename(file),
                isExecutable: this.isExecutableTest(file)
            }))
            .filter(test => test.isExecutable);

        console.log(`✅ 发现 ${this.testFiles.length} 个可执行测试文件`);
        return this.testFiles;
    }

    /**
     * 判断是否为可执行的测试文件
     */
    isExecutableTest(filePath) {
        try {
            const content = fs.readFileSync(path.join(this.projectRoot, filePath), 'utf8');
            
            // 检查是否有主执行逻辑
            const hasMainExecution = content.includes('if (require.main === module)') ||
                                   content.includes('main()') ||
                                   content.includes('chromium.launch');
            
            // 排除工具类文件
            const isUtilityFile = filePath.includes('util') ||
                                filePath.includes('config') ||
                                filePath.includes('helper') ||
                                content.includes('class TestUtils') ||
                                content.includes('module.exports =');
            
            return hasMainExecution && !isUtilityFile;
        } catch (error) {
            return false;
        }
    }

    /**
     * 执行所有测试
     */
    async runAllTests(options = {}) {
        if (this.isRunning) {
            throw new Error('测试执行器已在运行中');
        }

        this.isRunning = true;
        this.executionStartTime = Date.now();
        this.runResults = [];

        console.log('🚀 开始批量执行测试...');
        console.log('===============================================');

        try {
            await this.discoverTestFiles();

            const {
                parallel = false,
                maxConcurrency = 3,
                timeout = 60000,
                continueOnFailure = true
            } = options;

            if (parallel) {
                await this.runTestsInParallel(maxConcurrency, timeout, continueOnFailure);
            } else {
                await this.runTestsSequentially(timeout, continueOnFailure);
            }

            // 聚合结果
            const aggregatedResults = await this.aggregateResults();

            // 生成报告
            await this.generateReports(aggregatedResults);

            console.log('\n✅ 所有测试执行完成!');
            console.log('===============================================');

            return aggregatedResults;

        } catch (error) {
            console.error('❌ 测试执行失败:', error);
            throw error;
        } finally {
            this.isRunning = false;
            this.currentExecution = null;
        }
    }

    /**
     * 顺序执行测试
     */
    async runTestsSequentially(timeout, continueOnFailure) {
        console.log(`📋 顺序执行 ${this.testFiles.length} 个测试...`);

        for (let i = 0; i < this.testFiles.length; i++) {
            const testFile = this.testFiles[i];
            console.log(`\n[${i + 1}/${this.testFiles.length}] 执行: ${testFile.fileName}`);

            try {
                const result = await this.runSingleTest(testFile, timeout);
                this.runResults.push(result);
                
                console.log(`  ✅ ${testFile.fileName}: ${result.status} (${result.duration}ms)`);
                
                if (result.status === 'failed' && !continueOnFailure) {
                    console.log('  🛑 测试失败，停止执行');
                    break;
                }
            } catch (error) {
                const errorResult = {
                    testFile: testFile.fileName,
                    status: 'error',
                    duration: 0,
                    error: error.message,
                    startTime: new Date().toISOString(),
                    endTime: new Date().toISOString()
                };
                
                this.runResults.push(errorResult);
                console.log(`  ❌ ${testFile.fileName}: 执行异常 - ${error.message}`);
                
                if (!continueOnFailure) {
                    console.log('  🛑 发生异常，停止执行');
                    break;
                }
            }
        }
    }

    /**
     * 并行执行测试
     */
    async runTestsInParallel(maxConcurrency, timeout, continueOnFailure) {
        console.log(`🔀 并行执行测试 (最大并发: ${maxConcurrency})...`);

        const chunks = [];
        for (let i = 0; i < this.testFiles.length; i += maxConcurrency) {
            chunks.push(this.testFiles.slice(i, i + maxConcurrency));
        }

        for (let chunkIndex = 0; chunkIndex < chunks.length; chunkIndex++) {
            const chunk = chunks[chunkIndex];
            console.log(`\n📦 执行批次 ${chunkIndex + 1}/${chunks.length} (${chunk.length} 个测试)`);

            const promises = chunk.map(async (testFile) => {
                try {
                    const result = await this.runSingleTest(testFile, timeout);
                    console.log(`  ✅ ${testFile.fileName}: ${result.status} (${result.duration}ms)`);
                    return result;
                } catch (error) {
                    console.log(`  ❌ ${testFile.fileName}: 执行异常 - ${error.message}`);
                    return {
                        testFile: testFile.fileName,
                        status: 'error',
                        duration: 0,
                        error: error.message,
                        startTime: new Date().toISOString(),
                        endTime: new Date().toISOString()
                    };
                }
            });

            const chunkResults = await Promise.allSettled(promises);
            chunkResults.forEach(result => {
                if (result.status === 'fulfilled') {
                    this.runResults.push(result.value);
                }
            });

            // 检查是否需要停止
            if (!continueOnFailure && this.runResults.some(r => r.status === 'failed' || r.status === 'error')) {
                console.log('  🛑 发现失败测试，停止后续执行');
                break;
            }
        }
    }

    /**
     * 执行单个测试
     */
    async runSingleTest(testFile, timeout = 60000) {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            const startTimeISO = new Date().toISOString();

            // 使用 Node.js 执行测试文件
            const childProcess = spawn('node', [testFile.fullPath], {
                cwd: this.projectRoot,
                stdio: ['pipe', 'pipe', 'pipe'],
                env: { ...process.env, NODE_ENV: 'test' }
            });

            let stdout = '';
            let stderr = '';
            let timedOut = false;

            // 设置超时
            const timeoutId = setTimeout(() => {
                timedOut = true;
                childProcess.kill('SIGTERM');
                
                setTimeout(() => {
                    if (!childProcess.killed) {
                        childProcess.kill('SIGKILL');
                    }
                }, 5000);
            }, timeout);

            childProcess.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            childProcess.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            childProcess.on('close', (code) => {
                clearTimeout(timeoutId);
                const endTime = Date.now();
                const duration = endTime - startTime;

                const result = {
                    testFile: testFile.fileName,
                    filePath: testFile.filePath,
                    status: timedOut ? 'timeout' : (code === 0 ? 'passed' : 'failed'),
                    exitCode: code,
                    duration,
                    startTime: startTimeISO,
                    endTime: new Date().toISOString(),
                    stdout: stdout.trim(),
                    stderr: stderr.trim(),
                    timedOut
                };

                // 尝试解析测试输出中的详细信息
                this.parseTestOutput(result);

                resolve(result);
            });

            childProcess.on('error', (error) => {
                clearTimeout(timeoutId);
                reject(error);
            });
        });
    }

    /**
     * 解析测试输出，提取详细信息
     */
    parseTestOutput(result) {
        const output = result.stdout + '\n' + result.stderr;

        // 提取测试统计信息
        const statsPattern = /(\d+)\s*测试.*?(\d+)\s*通过.*?(\d+)\s*失败/i;
        const statsMatch = output.match(statsPattern);
        if (statsMatch) {
            result.testStats = {
                total: parseInt(statsMatch[1]),
                passed: parseInt(statsMatch[2]),
                failed: parseInt(statsMatch[3])
            };
        }

        // 提取成功率信息
        const successRatePattern = /成功率[：:\s]*(\d+(?:\.\d+)?)%/i;
        const successRateMatch = output.match(successRatePattern);
        if (successRateMatch) {
            result.successRate = parseFloat(successRateMatch[1]);
        }

        // 提取错误信息
        if (result.status === 'failed' && output.includes('❌')) {
            const errorLines = output.split('\n')
                .filter(line => line.includes('❌') || line.includes('Error') || line.includes('Failed'));
            result.errors = errorLines.slice(0, 5); // 限制错误信息数量
        }

        // 检查是否有截图生成
        result.hasScreenshots = output.includes('截图') || output.includes('screenshot');

        return result;
    }

    /**
     * 聚合所有测试结果
     */
    async aggregateResults() {
        console.log('\n📊 聚合测试结果...');

        const totalDuration = Date.now() - this.executionStartTime;
        const totalTests = this.runResults.length;
        const passedTests = this.runResults.filter(r => r.status === 'passed').length;
        const failedTests = this.runResults.filter(r => r.status === 'failed').length;
        const errorTests = this.runResults.filter(r => r.status === 'error').length;
        const timeoutTests = this.runResults.filter(r => r.status === 'timeout').length;

        // 使用收集器收集额外的测试元数据
        const collectedData = await this.collector.collectAll();

        const aggregated = {
            executionSummary: {
                totalDuration,
                totalTests,
                passedTests,
                failedTests,
                errorTests,
                timeoutTests,
                successRate: totalTests > 0 ? Math.round((passedTests / totalTests) * 100) : 0,
                startTime: new Date(this.executionStartTime).toISOString(),
                endTime: new Date().toISOString()
            },
            testResults: this.runResults,
            collectedData,
            categories: this.categorizeResults(),
            performance: this.analyzePerformance(),
            recommendations: this.generateRecommendations()
        };

        console.log(`✅ 聚合完成: ${totalTests} 个测试, ${passedTests} 通过, ${failedTests} 失败`);
        return aggregated;
    }

    /**
     * 按分类统计结果
     */
    categorizeResults() {
        const categories = new Map();

        this.runResults.forEach(result => {
            // 从文件名推断分类
            const category = this.inferCategory(result.testFile);
            
            if (!categories.has(category)) {
                categories.set(category, {
                    name: category,
                    total: 0,
                    passed: 0,
                    failed: 0,
                    error: 0,
                    timeout: 0
                });
            }

            const categoryStats = categories.get(category);
            categoryStats.total++;
            categoryStats[result.status]++;
        });

        return Array.from(categories.values()).map(category => ({
            ...category,
            successRate: category.total > 0 ? 
                Math.round((category.passed / category.total) * 100) : 0
        }));
    }

    /**
     * 性能分析
     */
    analyzePerformance() {
        const durations = this.runResults.map(r => r.duration);
        const avgDuration = durations.reduce((a, b) => a + b, 0) / durations.length || 0;
        const maxDuration = Math.max(...durations);
        const minDuration = Math.min(...durations);

        const slowTests = this.runResults
            .filter(r => r.duration > avgDuration * 2)
            .sort((a, b) => b.duration - a.duration)
            .slice(0, 5);

        return {
            avgDuration,
            maxDuration,
            minDuration,
            slowTests: slowTests.map(t => ({
                testFile: t.testFile,
                duration: t.duration
            }))
        };
    }

    /**
     * 生成改进建议
     */
    generateRecommendations() {
        const recommendations = [];
        
        const failedTests = this.runResults.filter(r => r.status === 'failed');
        const errorTests = this.runResults.filter(r => r.status === 'error');
        const timeoutTests = this.runResults.filter(r => r.status === 'timeout');

        if (failedTests.length > 0) {
            recommendations.push({
                type: 'error',
                title: '失败测试需要修复',
                description: `${failedTests.length} 个测试失败，需要检查测试逻辑和被测功能`,
                tests: failedTests.map(t => t.testFile)
            });
        }

        if (timeoutTests.length > 0) {
            recommendations.push({
                type: 'warning',
                title: '超时测试需要优化',
                description: `${timeoutTests.length} 个测试超时，考虑增加超时时间或优化测试性能`,
                tests: timeoutTests.map(t => t.testFile)
            });
        }

        if (errorTests.length > 0) {
            recommendations.push({
                type: 'error',
                title: '执行错误需要解决',
                description: `${errorTests.length} 个测试执行出错，检查测试环境和依赖`,
                tests: errorTests.map(t => t.testFile)
            });
        }

        const successRate = this.runResults.length > 0 ? 
            (this.runResults.filter(r => r.status === 'passed').length / this.runResults.length) * 100 : 0;

        if (successRate < 80) {
            recommendations.push({
                type: 'warning',
                title: '测试成功率偏低',
                description: `当前成功率 ${successRate.toFixed(1)}%，建议提高到 90% 以上`,
                action: '优化失败测试，加强测试稳定性'
            });
        }

        return recommendations;
    }

    /**
     * 生成测试报告
     */
    async generateReports(aggregatedResults) {
        console.log('\n📄 生成测试报告...');

        // 确保结果目录存在
        if (!fs.existsSync(this.testResultsDir)) {
            fs.mkdirSync(this.testResultsDir, { recursive: true });
        }

        // 1. 生成JSON报告
        const jsonPath = path.join(this.testResultsDir, 'execution-report.json');
        fs.writeFileSync(jsonPath, JSON.stringify(aggregatedResults, null, 2), 'utf8');
        console.log(`  📋 JSON报告: ${jsonPath}`);

        // 2. 生成HTML报告
        const htmlPath = await this.generateHTMLReport(aggregatedResults);
        console.log(`  🌐 HTML报告: ${htmlPath}`);

        // 3. 生成CSV报告
        const csvPath = await this.generateCSVReport(aggregatedResults);
        console.log(`  📊 CSV报告: ${csvPath}`);

        // 4. 更新仪表板数据
        const dashboardPath = await this.updateDashboardData(aggregatedResults);
        console.log(`  📈 仪表板数据: ${dashboardPath}`);

        return { jsonPath, htmlPath, csvPath, dashboardPath };
    }

    /**
     * 生成HTML报告
     */
    async generateHTMLReport(results) {
        const htmlContent = this.generateHTMLTemplate(results);
        const htmlPath = path.join(this.testResultsDir, 'test-report.html');
        fs.writeFileSync(htmlPath, htmlContent, 'utf8');
        return htmlPath;
    }

    /**
     * 生成HTML模板
     */
    generateHTMLTemplate(results) {
        const { executionSummary, testResults, categories, performance } = results;
        
        return `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试执行报告</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
            color: #303133;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 24px;
            border-radius: 8px;
            margin-bottom: 24px;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
        }
        .header h1 {
            margin: 0;
            color: #409eff;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
        }
        .summary-card h3 {
            margin: 0 0 8px 0;
            font-size: 32px;
            font-weight: bold;
        }
        .summary-card p {
            margin: 0;
            color: #666;
        }
        .success { color: #67c23a; }
        .danger { color: #f56c6c; }
        .warning { color: #e6a23c; }
        .info { color: #409eff; }
        .results-table {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
            margin-bottom: 24px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ebeef5;
        }
        th {
            background-color: #fafafa;
            font-weight: 600;
            color: #303133;
        }
        .status-badge {
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-passed { background: #f0f9ff; color: #67c23a; }
        .status-failed { background: #fef0f0; color: #f56c6c; }
        .status-error { background: #fdf6ec; color: #e6a23c; }
        .status-timeout { background: #f4f4f5; color: #909399; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 测试执行报告</h1>
            <p>生成时间: ${new Date(executionSummary.endTime).toLocaleString('zh-CN')}</p>
            <p>执行耗时: ${Math.round(executionSummary.totalDuration / 1000)}秒</p>
        </div>

        <div class="summary">
            <div class="summary-card">
                <h3 class="info">${executionSummary.totalTests}</h3>
                <p>总测试数</p>
            </div>
            <div class="summary-card">
                <h3 class="success">${executionSummary.passedTests}</h3>
                <p>通过测试</p>
            </div>
            <div class="summary-card">
                <h3 class="danger">${executionSummary.failedTests}</h3>
                <p>失败测试</p>
            </div>
            <div class="summary-card">
                <h3 class="warning">${executionSummary.successRate}%</h3>
                <p>成功率</p>
            </div>
        </div>

        <div class="results-table">
            <table>
                <thead>
                    <tr>
                        <th>测试名称</th>
                        <th>状态</th>
                        <th>执行时间</th>
                        <th>成功率</th>
                        <th>详情</th>
                    </tr>
                </thead>
                <tbody>
                    ${testResults.map(result => `
                        <tr>
                            <td>${result.testFile}</td>
                            <td>
                                <span class="status-badge status-${result.status}">
                                    ${this.getStatusText(result.status)}
                                </span>
                            </td>
                            <td>${result.duration}ms</td>
                            <td>${result.successRate || 'N/A'}%</td>
                            <td>
                                ${result.errors ? result.errors.join('<br>') : '无'}
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>`;
    }

    /**
     * 生成CSV报告
     */
    async generateCSVReport(results) {
        const csvData = [
            ['测试名称', '状态', '执行时间(ms)', '成功率(%)', '错误信息']
        ];

        results.testResults.forEach(result => {
            csvData.push([
                result.testFile,
                result.status,
                result.duration,
                result.successRate || 'N/A',
                result.errors ? result.errors.join('; ') : ''
            ]);
        });

        const csvContent = csvData.map(row => 
            row.map(field => `"${String(field).replace(/"/g, '""')}"`).join(',')
        ).join('\n');

        const csvPath = path.join(this.testResultsDir, 'test-results.csv');
        fs.writeFileSync(csvPath, csvContent, 'utf8');
        return csvPath;
    }

    /**
     * 更新仪表板数据
     */
    async updateDashboardData(results) {
        const dashboardData = {
            lastExecution: results.executionSummary,
            categories: results.categories,
            testResults: results.testResults.map(result => ({
                id: result.testFile.replace('.js', ''),
                name: this.formatTestName(result.testFile),
                category: this.inferCategory(result.testFile),
                status: result.status,
                duration: result.duration,
                lastRun: result.endTime,
                filePath: result.filePath,
                logs: result.stdout,
                error: result.errors ? result.errors.join('\n') : null,
                screenshots: []
            })),
            performance: results.performance,
            recommendations: results.recommendations,
            updatedAt: new Date().toISOString()
        };

        const dashboardPath = path.join(this.testResultsDir, 'dashboard-live-data.json');
        fs.writeFileSync(dashboardPath, JSON.stringify(dashboardData, null, 2), 'utf8');
        return dashboardPath;
    }

    /**
     * 工具方法
     */
    inferCategory(testFileName) {
        const categoryMap = {
            'crud': '数据完整性验证',
            'deletion': '数据完整性验证',
            'constraint': '数据完整性验证',
            'navigation': '导航功能测试',
            'routing': '导航功能测试',
            'api': 'API连接状态验证',
            'connection': 'API连接状态验证',
            'buttons': '用户界面元素检查',
            'interface': '用户界面元素检查',
            'functionality': '交互功能测试',
            'user-experience': '交互功能测试',
            'forms': '表单验证测试',
            'validation': '表单验证测试',
            'end-to-end': '端到端用户流程',
            'journey': '端到端用户流程',
            'comprehensive': '端到端用户流程',
            'enhancement': '质量标准和错误处理',
            'status': '质量标准和错误处理'
        };

        const fileName = testFileName.toLowerCase();
        for (const [keyword, category] of Object.entries(categoryMap)) {
            if (fileName.includes(keyword)) {
                return category;
            }
        }

        return '其他测试';
    }

    formatTestName(fileName) {
        return fileName
            .replace('.js', '')
            .replace(/test-/, '')
            .replace(/-/g, ' ')
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    getStatusText(status) {
        const statusMap = {
            'passed': '通过',
            'failed': '失败',
            'error': '错误',
            'timeout': '超时'
        };
        return statusMap[status] || '未知';
    }

    /**
     * 停止当前执行
     */
    stop() {
        if (this.currentExecution) {
            this.currentExecution.kill('SIGTERM');
            this.isRunning = false;
            console.log('🛑 测试执行已停止');
        }
    }
}

// 主执行函数
async function main() {
    const aggregator = new TestRunnerAggregator();
    
    try {
        const options = {
            parallel: process.argv.includes('--parallel'),
            maxConcurrency: 3,
            timeout: 60000,
            continueOnFailure: true
        };

        console.log('🧪 测试执行聚合器启动');
        console.log(`📋 执行模式: ${options.parallel ? '并行' : '顺序'}`);
        
        const results = await aggregator.runAllTests(options);
        
        console.log('\n🎉 测试执行聚合完成!');
        console.log(`📊 总体统计:`);
        console.log(`  成功率: ${results.executionSummary.successRate}%`);
        console.log(`  总时长: ${Math.round(results.executionSummary.totalDuration / 1000)}秒`);
        console.log(`  通过测试: ${results.executionSummary.passedTests}/${results.executionSummary.totalTests}`);
        
        process.exit(results.executionSummary.successRate >= 90 ? 0 : 1);
        
    } catch (error) {
        console.error('💥 执行失败:', error.message);
        process.exit(1);
    }
}

// 如果直接运行此文件，执行聚合
if (require.main === module) {
    main();
}

module.exports = TestRunnerAggregator;