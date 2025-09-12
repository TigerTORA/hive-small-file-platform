/**
 * TDD第1阶段：Red - 真实集群连接测试功能验证
 * 
 * 测试目标：验证点击"快速测试"和"详细测试"按钮时，系统能否提供完整的连接测试结果
 * 预期：测试失败，因为当前缺少Beeline连接测试和详细的结果展示
 */

const puppeteer = require('playwright');
const http = require('http');

class RealConnectionTestValidator {
    constructor() {
        this.browser = null;
        this.page = null;
        this.baseUrl = 'http://localhost:3001';
        this.apiUrl = 'http://localhost:8000';
        this.testResults = {
            mockTest: null,
            realTest: null, 
            apiDirectTest: null,
            errors: []
        };
    }

    async init() {
        console.log('🚀 启动真实集群连接测试功能验证...');
        
        this.browser = await puppeteer.chromium.launch({
            headless: false,
            devtools: false
        });
        
        this.page = await this.browser.newPage();
        
        // 监听控制台错误和网络请求
        this.page.on('console', msg => {
            if (msg.type() === 'error') {
                console.log('❌ 前端错误:', msg.text());
                this.testResults.errors.push({
                    type: 'console',
                    message: msg.text()
                });
            }
        });
    }

    async httpRequest(url) {
        return new Promise((resolve, reject) => {
            const urlObj = new URL(url);
            const options = {
                hostname: urlObj.hostname,
                port: urlObj.port,
                path: urlObj.pathname + urlObj.search,
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            };

            const req = http.request(options, (res) => {
                let data = '';
                res.on('data', (chunk) => {
                    data += chunk;
                });
                res.on('end', () => {
                    try {
                        const jsonData = JSON.parse(data);
                        resolve({
                            ok: res.statusCode >= 200 && res.statusCode < 300,
                            status: res.statusCode,
                            json: () => Promise.resolve(jsonData)
                        });
                    } catch (e) {
                        resolve({
                            ok: res.statusCode >= 200 && res.statusCode < 300,
                            status: res.statusCode,
                            json: () => Promise.resolve({ message: data })
                        });
                    }
                });
            });

            req.on('error', (err) => {
                reject(err);
            });

            req.end();
        });
    }

    async testApiConnectionDirectly() {
        console.log('\n📡 测试1：直接API连接测试');
        
        try {
            // 测试集群1的连接
            const response = await this.httpRequest(`${this.apiUrl}/api/v1/clusters/1/test-connection?mode=real`);
            const result = await response.json();
            
            console.log('API响应状态:', response.status);
            console.log('API响应内容:', JSON.stringify(result, null, 2));
            
            // 验证API响应结构
            const requiredFields = ['overall_status', 'test_time', 'tests'];
            const requiredTests = ['metastore', 'hdfs', 'beeline'];
            
            let validationErrors = [];
            
            // 检查顶级字段
            requiredFields.forEach(field => {
                if (!result.hasOwnProperty(field)) {
                    validationErrors.push(`缺少必需字段: ${field}`);
                }
            });
            
            // 检查测试项
            if (result.tests) {
                requiredTests.forEach(test => {
                    if (!result.tests.hasOwnProperty(test)) {
                        validationErrors.push(`缺少必需的连接测试: ${test}`);
                    } else {
                        const testResult = result.tests[test];
                        if (!testResult.status) {
                            validationErrors.push(`${test}测试缺少status字段`);
                        }
                        if (!testResult.message) {
                            validationErrors.push(`${test}测试缺少message字段`);
                        }
                    }
                });
            }
            
            this.testResults.apiDirectTest = {
                success: response.ok && validationErrors.length === 0,
                status: response.status,
                result: result,
                validationErrors: validationErrors
            };
            
            if (validationErrors.length > 0) {
                console.log('❌ API响应结构验证失败:');
                validationErrors.forEach(error => console.log(`   - ${error}`));
            } else {
                console.log('✅ API响应结构验证通过');
            }
            
        } catch (error) {
            console.log('❌ API直接测试失败:', error.message);
            this.testResults.apiDirectTest = {
                success: false,
                error: error.message
            };
        }
    }

    async testFrontendMockButton() {
        console.log('\n🖱️ 测试2：前端Mock测试按钮');
        
        try {
            await this.page.goto(`${this.baseUrl}/#/clusters`);
            await this.page.waitForTimeout(3000);
            
            // 查找Mock测试按钮
            const mockButtons = await this.page.$$('button:has-text("Mock测试")');
            console.log(`找到 ${mockButtons.length} 个Mock测试按钮`);
            
            if (mockButtons.length > 0) {
                // 点击第一个Mock测试按钮
                await mockButtons[0].click();
                await this.page.waitForTimeout(2000);
                
                // 检查是否有消息提示或对话框出现
                const messageBox = await this.page.$('.el-message');
                const dialog = await this.page.$('.el-dialog');
                
                this.testResults.mockTest = {
                    success: true,
                    hasMessage: !!messageBox,
                    hasDialog: !!dialog,
                    buttonClicked: true
                };
                
                console.log('✅ Mock测试按钮功能正常');
                if (messageBox) console.log('   - 显示了消息提示');
                if (dialog) console.log('   - 打开了详细对话框');
                
            } else {
                throw new Error('未找到Mock测试按钮');
            }
            
        } catch (error) {
            console.log('❌ 前端Mock测试失败:', error.message);
            this.testResults.mockTest = {
                success: false,
                error: error.message
            };
        }
    }

    async testFrontendRealTestButton() {
        console.log('\n🔍 测试3：前端详细测试按钮');
        
        try {
            await this.page.goto(`${this.baseUrl}/#/clusters`);
            await this.page.waitForTimeout(3000);
            
            // 查找详细测试按钮
            const realTestButtons = await this.page.$$('button:has-text("详细测试")');
            console.log(`找到 ${realTestButtons.length} 个详细测试按钮`);
            
            if (realTestButtons.length > 0) {
                // 点击第一个详细测试按钮
                await realTestButtons[0].click();
                await this.page.waitForTimeout(5000);
                
                // 检查对话框内容
                const dialog = await this.page.$('.el-dialog');
                let dialogContent = null;
                let hasProgressSteps = false;
                let hasDetailedResults = false;
                
                if (dialog) {
                    dialogContent = await dialog.innerText();
                    hasProgressSteps = dialogContent.includes('MetaStore') && 
                                     dialogContent.includes('HDFS') && 
                                     dialogContent.includes('Beeline');
                    hasDetailedResults = dialogContent.includes('成功') || 
                                       dialogContent.includes('失败') ||
                                       dialogContent.includes('错误');
                }
                
                this.testResults.realTest = {
                    success: true,
                    hasDialog: !!dialog,
                    dialogContent: dialogContent,
                    hasProgressSteps: hasProgressSteps,
                    hasDetailedResults: hasDetailedResults,
                    buttonClicked: true
                };
                
                console.log('✅ 详细测试按钮功能正常');
                console.log(`   - 对话框状态: ${dialog ? '已打开' : '未打开'}`);
                console.log(`   - 包含进度步骤: ${hasProgressSteps ? '是' : '否'}`);
                console.log(`   - 包含详细结果: ${hasDetailedResults ? '是' : '否'}`);
                
            } else {
                throw new Error('未找到详细测试按钮');
            }
            
        } catch (error) {
            console.log('❌ 前端详细测试失败:', error.message);
            this.testResults.realTest = {
                success: false,
                error: error.message
            };
        }
    }

    generateTDDReport() {
        console.log('\n📊 TDD第1阶段验证报告 (Red阶段)');
        console.log('=' .repeat(60));
        
        const issues = [];
        let totalTests = 0;
        let passedTests = 0;
        
        // 分析API直接测试
        totalTests++;
        if (this.testResults.apiDirectTest?.success) {
            passedTests++;
            console.log('✅ API直接连接测试 - 通过');
        } else {
            console.log('❌ API直接连接测试 - 失败');
            if (this.testResults.apiDirectTest?.validationErrors) {
                issues.push(...this.testResults.apiDirectTest.validationErrors);
            }
            if (this.testResults.apiDirectTest?.error) {
                issues.push(`API测试错误: ${this.testResults.apiDirectTest.error}`);
            }
        }
        
        // 分析前端Mock测试
        totalTests++;
        if (this.testResults.mockTest?.success) {
            passedTests++;
            console.log('✅ 前端Mock测试按钮 - 通过');
        } else {
            console.log('❌ 前端Mock测试按钮 - 失败');
            if (this.testResults.mockTest?.error) {
                issues.push(`Mock测试错误: ${this.testResults.mockTest.error}`);
            }
        }
        
        // 分析前端详细测试 
        totalTests++;
        if (this.testResults.realTest?.success) {
            console.log('✅ 前端详细测试按钮 - 通过');
            
            // 但检查是否有完整的功能
            if (!this.testResults.realTest.hasProgressSteps) {
                issues.push('详细测试对话框缺少进度步骤显示(MetaStore/HDFS/Beeline)');
            }
            if (!this.testResults.realTest.hasDetailedResults) {
                issues.push('详细测试对话框缺少具体的测试结果展示');
            }
            
            if (this.testResults.realTest.hasProgressSteps && this.testResults.realTest.hasDetailedResults) {
                passedTests++;
            }
        } else {
            console.log('❌ 前端详细测试按钮 - 失败');
            if (this.testResults.realTest?.error) {
                issues.push(`详细测试错误: ${this.testResults.realTest.error}`);
            }
        }
        
        console.log('\n📋 测试统计');
        console.log(`通过: ${passedTests}/${totalTests}`);
        console.log(`失败: ${totalTests - passedTests}/${totalTests}`);
        
        console.log('\n🔧 需要实现的功能：');
        if (issues.length > 0) {
            issues.forEach((issue, index) => {
                console.log(`${index + 1}. ${issue}`);
            });
        } else {
            console.log('所有功能都已正确实现！');
        }
        
        // TDD Red阶段：我们期望有问题需要修复
        const isRed = issues.length > 0 || passedTests < totalTests;
        
        if (isRed) {
            console.log('\n✅ TDD Red阶段成功: 发现了需要实现的功能');
            console.log('   接下来进入Green阶段，实现这些功能让测试通过');
        } else {
            console.log('\n⚠️  意外：所有测试都通过了');
            console.log('   这可能意味着功能已经完整实现，或者测试不够严格');
        }
        
        return {
            totalTests,
            passedTests,
            issues,
            isRed,
            testResults: this.testResults
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
            
            // 运行所有测试
            await this.testApiConnectionDirectly();
            await this.testFrontendMockButton();
            await this.testFrontendRealTestButton();
            
            // 生成报告
            const report = this.generateTDDReport();
            
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
        const validator = new RealConnectionTestValidator();
        try {
            const report = await validator.run();
            // TDD Red阶段：期望有问题需要修复
            process.exit(report.isRed ? 1 : 0);
        } catch (error) {
            console.error('测试执行异常:', error);
            process.exit(2);
        }
    })();
}

module.exports = RealConnectionTestValidator;