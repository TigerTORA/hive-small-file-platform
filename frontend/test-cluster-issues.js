/**
 * TDD端到端测试：复现用户报告的集群管理问题
 * 
 * 这个测试文件专门用于验证用户报告的两个核心问题：
 * 1. 集群详情页面点击进入后报错
 * 2. 快速测试功能报错
 * 
 * TDD方法：先确保测试失败（Red阶段），然后修复代码让测试通过（Green阶段）
 */

const puppeteer = require('playwright');
const assert = require('assert');

class ClusterIssuesTester {
    constructor() {
        this.browser = null;
        this.context = null;
        this.page = null;
        this.baseUrl = 'http://localhost:3001';
        this.apiUrl = 'http://localhost:8000';
        this.testResults = {
            clusterDetailAccess: null,
            quickTestFunction: null,
            detailedTestFunction: null,
            errors: []
        };
    }

    async init() {
        console.log('🚀 启动集群问题诊断测试...');
        
        this.browser = await puppeteer.chromium.launch({
            headless: false,
            devtools: true
        });
        
        this.context = await this.browser.newContext();
        this.page = await this.context.newPage();
        
        // 监听控制台错误
        this.page.on('console', msg => {
            if (msg.type() === 'error') {
                console.log('❌ 前端控制台错误:', msg.text());
                this.testResults.errors.push({
                    type: 'console',
                    message: msg.text(),
                    timestamp: new Date().toISOString()
                });
            }
        });

        // 监听网络请求失败
        this.page.on('response', response => {
            if (!response.ok() && response.url().includes('/api/')) {
                console.log(`❌ API请求失败: ${response.status()} ${response.url()}`);
                this.testResults.errors.push({
                    type: 'network',
                    status: response.status(),
                    url: response.url(),
                    timestamp: new Date().toISOString()
                });
            }
        });
    }

    async testClusterPageAccess() {
        console.log('\n📋 测试1：集群详情页面访问');
        
        try {
            // 导航到集群管理页面
            console.log('  → 访问集群管理页面...');
            await this.page.goto(`${this.baseUrl}/#/clusters`);
            await this.page.waitForTimeout(2000);

            // 检查是否有集群数据
            const clusters = await this.page.$$('[data-testid="cluster-row"], .el-table__row');
            console.log(`  → 找到 ${clusters.length} 个集群`);

            if (clusters.length === 0) {
                console.log('  → 没有找到集群，尝试创建测试集群...');
                await this.createTestCluster();
                await this.page.reload();
                await this.page.waitForTimeout(2000);
            }

            // 尝试点击进入集群详情
            const clusterRows = await this.page.$$('.el-table__row');
            if (clusterRows.length > 0) {
                console.log('  → 点击进入第一个集群详情...');
                
                // 记录点击前的错误数量
                const errorsBefore = this.testResults.errors.length;
                
                await clusterRows[0].click();
                await this.page.waitForTimeout(3000);

                // 检查是否有新的错误
                const errorsAfter = this.testResults.errors.length;
                if (errorsAfter > errorsBefore) {
                    this.testResults.clusterDetailAccess = {
                        success: false,
                        errors: this.testResults.errors.slice(errorsBefore)
                    };
                    console.log('  ❌ 集群详情页面访问失败');
                } else {
                    this.testResults.clusterDetailAccess = { success: true };
                    console.log('  ✅ 集群详情页面访问成功');
                }
            } else {
                throw new Error('无法找到集群行进行测试');
            }

        } catch (error) {
            console.log('  ❌ 集群详情页面测试异常:', error.message);
            this.testResults.clusterDetailAccess = {
                success: false,
                exception: error.message
            };
        }
    }

    async testQuickTestFunction() {
        console.log('\n🔧 测试2：快速测试功能');
        
        try {
            // 确保在集群管理页面
            await this.page.goto(`${this.baseUrl}/#/clusters`);
            await this.page.waitForTimeout(2000);

            // 寻找Mock测试按钮
            const mockTestButtons = await this.page.$$('button:has-text("Mock测试"), .el-button:has-text("Mock测试")');
            console.log(`  → 找到 ${mockTestButtons.length} 个Mock测试按钮`);

            if (mockTestButtons.length > 0) {
                console.log('  → 点击Mock测试按钮...');
                
                const errorsBefore = this.testResults.errors.length;
                
                await mockTestButtons[0].click();
                await this.page.waitForTimeout(3000);

                const errorsAfter = this.testResults.errors.length;
                if (errorsAfter > errorsBefore) {
                    this.testResults.quickTestFunction = {
                        success: false,
                        errors: this.testResults.errors.slice(errorsBefore)
                    };
                    console.log('  ❌ Mock测试功能失败');
                } else {
                    this.testResults.quickTestFunction = { success: true };
                    console.log('  ✅ Mock测试功能成功');
                }
            } else {
                throw new Error('无法找到Mock测试按钮');
            }

        } catch (error) {
            console.log('  ❌ 快速测试功能异常:', error.message);
            this.testResults.quickTestFunction = {
                success: false,
                exception: error.message
            };
        }
    }

    async testDetailedTestFunction() {
        console.log('\n🔍 测试3：详细测试功能');
        
        try {
            await this.page.goto(`${this.baseUrl}/#/clusters`);
            await this.page.waitForTimeout(2000);

            const detailedTestButtons = await this.page.$$('button:has-text("详细测试"), .el-button:has-text("详细测试")');
            console.log(`  → 找到 ${detailedTestButtons.length} 个详细测试按钮`);

            if (detailedTestButtons.length > 0) {
                console.log('  → 点击详细测试按钮...');
                
                const errorsBefore = this.testResults.errors.length;
                
                await detailedTestButtons[0].click();
                await this.page.waitForTimeout(3000);

                const errorsAfter = this.testResults.errors.length;
                if (errorsAfter > errorsBefore) {
                    this.testResults.detailedTestFunction = {
                        success: false,
                        errors: this.testResults.errors.slice(errorsBefore)
                    };
                    console.log('  ❌ 详细测试功能失败');
                } else {
                    this.testResults.detailedTestFunction = { success: true };
                    console.log('  ✅ 详细测试功能成功');
                }
            }

        } catch (error) {
            console.log('  ❌ 详细测试功能异常:', error.message);
            this.testResults.detailedTestFunction = {
                success: false,
                exception: error.message
            };
        }
    }

    async createTestCluster() {
        console.log('  → 创建测试集群...');
        
        try {
            // 使用API直接创建集群，避免UI表单复杂性
            const clusterData = {
                name: 'TDD测试集群',
                description: '用于TDD测试的集群',
                hive_host: 'localhost',
                hive_port: 10000,
                hive_database: 'default',
                hive_metastore_url: 'mysql://test:test@localhost:3306/hive',
                hdfs_namenode_url: 'hdfs://localhost:9000',
                hdfs_user: 'hdfs',
                hdfs_password: 'test123',
                small_file_threshold: 134217728,
                scan_enabled: true
            };

            const response = await fetch(`${this.apiUrl}/api/v1/clusters/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(clusterData)
            });

            if (response.ok) {
                const result = await response.json();
                console.log('  ✅ 测试集群创建完成，ID:', result.id);
                return result;
            } else {
                const error = await response.text();
                console.log('  ❌ 集群创建失败:', response.status, error);
                throw new Error(`API返回错误: ${response.status}`);
            }
        } catch (error) {
            console.log('  ⚠️ 创建测试集群失败:', error.message);
            throw error;
        }
    }

    generateReport() {
        console.log('\n📊 TDD测试报告');
        console.log('=' .repeat(50));
        
        const issues = [];
        
        // 分析测试结果
        if (!this.testResults.clusterDetailAccess?.success) {
            issues.push({
                category: 'UI Navigation',
                severity: 'High',
                description: '集群详情页面无法正常访问',
                errors: this.testResults.clusterDetailAccess?.errors || []
            });
        }

        if (!this.testResults.quickTestFunction?.success) {
            issues.push({
                category: 'API Integration',
                severity: 'Medium',
                description: 'Mock测试功能异常',
                errors: this.testResults.quickTestFunction?.errors || []
            });
        }

        if (!this.testResults.detailedTestFunction?.success) {
            issues.push({
                category: 'API Integration',
                severity: 'Medium',
                description: '详细测试功能异常',
                errors: this.testResults.detailedTestFunction?.errors || []
            });
        }

        // 生成问题摘要
        console.log(`发现 ${issues.length} 个问题需要修复:\n`);
        
        issues.forEach((issue, index) => {
            console.log(`${index + 1}. [${issue.severity}] ${issue.description}`);
            console.log(`   类别: ${issue.category}`);
            if (issue.errors.length > 0) {
                console.log('   错误详情:');
                issue.errors.forEach(error => {
                    if (error.type === 'network') {
                        console.log(`   - API错误: ${error.status} ${error.url}`);
                    } else {
                        console.log(`   - ${error.type}: ${error.message}`);
                    }
                });
            }
            console.log('');
        });

        // 生成修复建议
        console.log('🔧 修复建议:');
        const networkErrors = this.testResults.errors.filter(e => e.type === 'network');
        const apiErrors = networkErrors.map(e => ({
            status: e.status,
            endpoint: e.url.replace(/^.*\/api/, '/api')
        }));

        const uniqueApiErrors = Array.from(new Map(apiErrors.map(e => [e.endpoint, e])).values());
        
        if (uniqueApiErrors.length > 0) {
            console.log('1. 修复以下API端点:');
            uniqueApiErrors.forEach(error => {
                console.log(`   - ${error.status}: ${error.endpoint}`);
            });
        }

        console.log('2. 运行数据库迁移确保schema一致');
        console.log('3. 检查前后端路由参数匹配');
        
        return {
            totalIssues: issues.length,
            issues: issues,
            apiErrors: uniqueApiErrors,
            allErrors: this.testResults.errors
        };
    }

    async cleanup() {
        if (this.browser) {
            await this.browser.close();
        }
    }

    async run() {
        try {
            await this.init();
            
            // 按顺序运行所有测试
            await this.testClusterPageAccess();
            await this.testQuickTestFunction();
            await this.testDetailedTestFunction();
            
            // 生成报告
            const report = this.generateReport();
            
            // 断言：如果是TDD的Red阶段，我们期望测试失败
            if (report.totalIssues === 0) {
                console.log('⚠️  意外：所有测试都通过了！这与用户报告的问题不符。');
                console.log('   可能需要重新检查测试场景。');
            } else {
                console.log(`✅ TDD Red阶段：成功复现了 ${report.totalIssues} 个用户报告的问题`);
                console.log('   现在可以开始修复这些问题，让测试进入Green阶段。');
            }
            
            return report;
            
        } catch (error) {
            console.error('❌ 测试执行失败:', error);
            throw error;
        } finally {
            await this.cleanup();
        }
    }
}

// 执行测试
if (require.main === module) {
    (async () => {
        const tester = new ClusterIssuesTester();
        try {
            const report = await tester.run();
            process.exit(report.totalIssues > 0 ? 1 : 0); // TDD: 有问题时退出码为1
        } catch (error) {
            console.error('测试执行异常:', error);
            process.exit(2);
        }
    })();
}

module.exports = ClusterIssuesTester;