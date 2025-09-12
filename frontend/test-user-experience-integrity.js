/**
 * 用户体验完整性测试 - 规则10实现
 * 验证用户操作的完整体验而非仅技术实现
 * 重点解决"绿色测试，红色现实"问题
 */

const { chromium } = require('playwright');
const TestUtils = require('./test-utils');
const TestConfig = require('./test-config');

class UserExperienceIntegrityTester {
    constructor() {
        this.browser = null;
        this.page = null;
        this.utils = new TestUtils();
        this.config = new TestConfig();
        this.testResults = [];
        this.screenshots = [];
        this.userActions = [];
    }

    async initialize() {
        this.browser = await chromium.launch({ 
            headless: false,
            slowMo: 500  // 慢速执行以便观察用户体验
        });
        this.page = await this.browser.newPage();
        await this.utils.setupPage(this.page);
        
        console.log('🎭 用户体验完整性测试初始化完成');
        console.log('📋 测试目标：验证用户实际可见结果和体验质量');
    }

    async cleanup() {
        if (this.browser) {
            await this.browser.close();
        }
    }

    /**
     * 测试按钮点击后的用户可见结果
     */
    async testButtonUserVisibleResults() {
        console.log('\n🔘 测试按钮用户可见结果...');
        const results = [];

        await this.page.goto(this.config.frontendUrl + '/#/clusters');
        await this.utils.waitForPageLoad(this.page);

        // 记录初始状态
        await this.captureUserState('按钮测试开始');

        // 测试快速测试按钮的用户体验
        const quickTestButton = await this.page.$('button:has-text("快速测试")');
        if (quickTestButton) {
            // 记录点击前状态
            const beforeState = await this.captureUIState('快速测试按钮点击前');
            
            // 执行用户操作
            await this.recordUserAction('点击快速测试按钮', async () => {
                await quickTestButton.click();
            });

            // 等待用户期望的反馈
            await this.page.waitForTimeout(2000);
            
            // 验证用户可见结果
            const afterState = await this.captureUIState('快速测试按钮点击后');
            const userFeedback = await this.analyzeUserFeedback(beforeState, afterState);
            
            results.push({
                action: '快速测试按钮',
                beforeState,
                afterState,
                userFeedback,
                userSatisfied: userFeedback.success && !userFeedback.showsError
            });

            console.log(`  ✓ 快速测试按钮用户体验: ${userFeedback.success ? '✅' : '❌'}`);
            console.log(`    用户看到: ${userFeedback.userMessage}`);
        }

        // 测试集群详情按钮
        const clusterCards = await this.page.$$('.cluster-card');
        if (clusterCards.length > 0) {
            const detailButton = await clusterCards[0].$('button:has-text("详情")');
            if (detailButton) {
                const beforeState = await this.captureUIState('集群详情按钮点击前');
                
                await this.recordUserAction('点击集群详情按钮', async () => {
                    await detailButton.click();
                });

                // 验证页面跳转和内容加载
                await this.page.waitForTimeout(2000);
                const currentUrl = this.page.url();
                const pageContent = await this.page.textContent('body');
                
                const navigationSuccess = currentUrl.includes('/clusters/') && 
                                        pageContent.includes('集群详情');
                
                results.push({
                    action: '集群详情按钮',
                    navigationSuccess,
                    targetUrl: currentUrl,
                    userSatisfied: navigationSuccess
                });

                console.log(`  ✓ 集群详情按钮导航: ${navigationSuccess ? '✅' : '❌'}`);
            }
        }

        return results;
    }

    /**
     * 测试错误消息的用户友好性
     */
    async testErrorMessageUserFriendliness() {
        console.log('\n❌ 测试错误消息用户友好性...');
        const results = [];

        // 测试无效连接的错误提示
        await this.page.goto(this.config.frontendUrl + '/#/clusters');
        await this.utils.waitForPageLoad(this.page);

        // 尝试触发错误场景
        const addButton = await this.page.$('button:has-text("添加集群")');
        if (addButton) {
            await addButton.click();
            await this.page.waitForTimeout(1000);

            // 提交空表单触发错误
            const submitButton = await this.page.$('button:has-text("确定")');
            if (submitButton) {
                await this.recordUserAction('提交空表单', async () => {
                    await submitButton.click();
                });

                await this.page.waitForTimeout(1000);
                
                // 检查错误提示的用户友好性
                const errorMessages = await this.page.$$eval('.el-form-item__error', 
                    elements => elements.map(el => el.textContent));
                
                const userFriendlyCheck = {
                    hasErrors: errorMessages.length > 0,
                    errorMessages,
                    isUserFriendly: errorMessages.every(msg => 
                        msg.length > 5 && !msg.includes('undefined') && !msg.includes('null')
                    ),
                    isActionable: errorMessages.every(msg => 
                        msg.includes('请') || msg.includes('必须') || msg.includes('不能')
                    )
                };

                results.push({
                    scenario: '空表单提交',
                    ...userFriendlyCheck,
                    userSatisfied: userFriendlyCheck.isUserFriendly && userFriendlyCheck.isActionable
                });

                console.log(`  ✓ 错误提示用户友好性: ${userFriendlyCheck.isUserFriendly ? '✅' : '❌'}`);
                console.log(`    错误消息: ${errorMessages.join(', ')}`);
            }
        }

        return results;
    }

    /**
     * 测试加载状态和用户反馈
     */
    async testLoadingStatesAndFeedback() {
        console.log('\n⏳ 测试加载状态和用户反馈...');
        const results = [];

        await this.page.goto(this.config.frontendUrl + '/#/tables');
        await this.utils.waitForPageLoad(this.page);

        // 测试扫描操作的加载状态
        const scanButton = await this.page.$('button:has-text("扫描")');
        if (scanButton) {
            // 记录点击前状态
            const beforeScan = await this.captureUIState('扫描前状态');
            
            await this.recordUserAction('开始表扫描', async () => {
                await scanButton.click();
            });

            // 检查加载指示器
            let hasLoadingIndicator = false;
            let loadingText = '';
            
            try {
                // 检查是否显示加载状态
                await this.page.waitForSelector('.el-loading-mask', { timeout: 2000 });
                hasLoadingIndicator = true;
                loadingText = await this.page.textContent('.el-loading-text') || '加载中...';
            } catch (e) {
                // 检查其他可能的加载指示器
                const loadingElements = await this.page.$$('[loading="true"], .loading, .el-button.is-loading');
                hasLoadingIndicator = loadingElements.length > 0;
            }

            // 等待操作完成
            await this.page.waitForTimeout(3000);
            const afterScan = await this.captureUIState('扫描后状态');

            results.push({
                action: '表扫描操作',
                hasLoadingIndicator,
                loadingText,
                beforeState: beforeScan,
                afterState: afterScan,
                userSatisfied: hasLoadingIndicator && afterScan.hasVisibleContent
            });

            console.log(`  ✓ 加载指示器: ${hasLoadingIndicator ? '✅' : '❌'}`);
            console.log(`    加载提示: ${loadingText}`);
        }

        return results;
    }

    /**
     * 测试响应内容语义完整性
     */
    async testResponseSemanticIntegrity() {
        console.log('\n🧠 测试响应内容语义完整性...');
        const results = [];

        // 测试API响应的语义正确性
        const apiTests = [
            {
                name: '集群列表API',
                url: `${this.config.backendUrl}/api/v1/clusters/`,
                expectedFields: ['id', 'name', 'description', 'connection_url']
            },
            {
                name: '表扫描API',
                url: `${this.config.backendUrl}/api/v1/tables/scan/1/default`,
                expectedFields: ['scan_duration', 'tables_scanned', 'total_tables']
            }
        ];

        for (const test of apiTests) {
            try {
                const response = await this.page.evaluate(async (url) => {
                    const res = await fetch(url);
                    return {
                        status: res.status,
                        data: res.status === 200 ? await res.json() : null
                    };
                }, test.url);

                const semanticCheck = {
                    httpSuccess: response.status === 200,
                    hasData: response.data !== null,
                    hasExpectedFields: false,
                    missingFields: [],
                    businessSuccess: false
                };

                if (response.data) {
                    if (Array.isArray(response.data)) {
                        // 检查数组中的对象
                        if (response.data.length > 0) {
                            const item = response.data[0];
                            semanticCheck.missingFields = test.expectedFields.filter(field => !(field in item));
                            semanticCheck.hasExpectedFields = semanticCheck.missingFields.length === 0;
                        }
                    } else {
                        // 检查单个对象
                        semanticCheck.missingFields = test.expectedFields.filter(field => !(field in response.data));
                        semanticCheck.hasExpectedFields = semanticCheck.missingFields.length === 0;
                    }
                    
                    semanticCheck.businessSuccess = semanticCheck.httpSuccess && semanticCheck.hasExpectedFields;
                }

                results.push({
                    api: test.name,
                    ...semanticCheck,
                    userSatisfied: semanticCheck.businessSuccess
                });

                console.log(`  ✓ ${test.name}: HTTP ${response.status} | 语义 ${semanticCheck.businessSuccess ? '✅' : '❌'}`);
                if (semanticCheck.missingFields.length > 0) {
                    console.log(`    缺失字段: ${semanticCheck.missingFields.join(', ')}`);
                }

            } catch (error) {
                results.push({
                    api: test.name,
                    error: error.message,
                    userSatisfied: false
                });
                console.log(`  ✗ ${test.name}: 请求失败 - ${error.message}`);
            }
        }

        return results;
    }

    /**
     * 记录用户操作
     */
    async recordUserAction(actionName, actionFn) {
        const startTime = Date.now();
        console.log(`  👤 用户操作: ${actionName}`);
        
        try {
            await actionFn();
            const duration = Date.now() - startTime;
            this.userActions.push({
                action: actionName,
                timestamp: new Date().toISOString(),
                duration,
                success: true
            });
        } catch (error) {
            const duration = Date.now() - startTime;
            this.userActions.push({
                action: actionName,
                timestamp: new Date().toISOString(),
                duration,
                success: false,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * 捕获UI状态
     */
    async captureUIState(stateName) {
        await this.captureUserState(stateName);
        
        const state = {
            url: this.page.url(),
            title: await this.page.title(),
            hasVisibleContent: false,
            visibleText: '',
            errorMessages: [],
            successMessages: [],
            loadingIndicators: 0
        };

        try {
            // 检查可见内容
            const bodyText = await this.page.textContent('body');
            state.hasVisibleContent = bodyText.trim().length > 100;
            state.visibleText = bodyText.substring(0, 200) + '...';

            // 检查错误消息
            const errorSelectors = ['.el-message--error', '.error', '.el-form-item__error', '[class*="error"]'];
            for (const selector of errorSelectors) {
                try {
                    const elements = await this.page.$$(selector);
                    for (const element of elements) {
                        const text = await element.textContent();
                        if (text && text.trim()) {
                            state.errorMessages.push(text.trim());
                        }
                    }
                } catch (e) {
                    // 忽略选择器错误
                }
            }

            // 检查成功消息
            const successSelectors = ['.el-message--success', '.success', '[class*="success"]'];
            for (const selector of successSelectors) {
                try {
                    const elements = await this.page.$$(selector);
                    for (const element of elements) {
                        const text = await element.textContent();
                        if (text && text.trim()) {
                            state.successMessages.push(text.trim());
                        }
                    }
                } catch (e) {
                    // 忽略选择器错误
                }
            }

            // 检查加载指示器
            const loadingSelectors = ['.el-loading-mask', '.loading', '[loading="true"]'];
            for (const selector of loadingSelectors) {
                try {
                    const elements = await this.page.$$(selector);
                    state.loadingIndicators += elements.length;
                } catch (e) {
                    // 忽略选择器错误
                }
            }

        } catch (error) {
            console.log(`    警告: 无法完全捕获UI状态 - ${error.message}`);
        }

        return state;
    }

    /**
     * 分析用户反馈
     */
    async analyzeUserFeedback(beforeState, afterState) {
        const feedback = {
            success: false,
            showsError: afterState.errorMessages.length > 0,
            showsSuccess: afterState.successMessages.length > 0,
            hasVisualChange: false,
            userMessage: '',
            actionable: true
        };

        // 检查是否有视觉变化
        feedback.hasVisualChange = beforeState.visibleText !== afterState.visibleText ||
                                 beforeState.url !== afterState.url;

        // 确定用户看到的主要消息
        if (afterState.errorMessages.length > 0) {
            feedback.userMessage = afterState.errorMessages[0];
            feedback.success = false;
        } else if (afterState.successMessages.length > 0) {
            feedback.userMessage = afterState.successMessages[0];
            feedback.success = true;
        } else if (feedback.hasVisualChange) {
            feedback.userMessage = '页面内容已更新';
            feedback.success = true;
        } else {
            feedback.userMessage = '无明显反馈';
            feedback.success = false;
            feedback.actionable = false;
        }

        return feedback;
    }

    /**
     * 捕获用户状态截图
     */
    async captureUserState(stateName) {
        try {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `user-state-${stateName.replace(/\s+/g, '-')}-${timestamp}.png`;
            const filepath = `./test-results/${filename}`;
            
            await this.page.screenshot({ 
                path: filepath, 
                fullPage: true 
            });
            
            this.screenshots.push({
                name: stateName,
                filename,
                filepath,
                timestamp: new Date().toISOString()
            });
            
            console.log(`    📸 用户状态截图: ${filename}`);
        } catch (error) {
            console.log(`    警告: 截图失败 - ${error.message}`);
        }
    }

    /**
     * 运行所有用户体验测试
     */
    async runAllTests() {
        console.log('\n🎭 开始用户体验完整性测试');
        console.log('===============================================');

        const allResults = {
            buttonResults: [],
            errorMessageResults: [],
            loadingResults: [],
            semanticResults: [],
            userActions: [],
            screenshots: [],
            summary: {}
        };

        try {
            // 测试按钮用户可见结果
            allResults.buttonResults = await this.testButtonUserVisibleResults();
            
            // 测试错误消息友好性
            allResults.errorMessageResults = await this.testErrorMessageUserFriendliness();
            
            // 测试加载状态
            allResults.loadingResults = await this.testLoadingStatesAndFeedback();
            
            // 测试语义完整性
            allResults.semanticResults = await this.testResponseSemanticIntegrity();

            // 收集所有结果
            allResults.userActions = this.userActions;
            allResults.screenshots = this.screenshots;

            // 计算汇总统计
            const allTests = [
                ...allResults.buttonResults,
                ...allResults.errorMessageResults, 
                ...allResults.loadingResults,
                ...allResults.semanticResults
            ];

            const totalTests = allTests.length;
            const passedTests = allTests.filter(test => test.userSatisfied).length;
            const failedTests = totalTests - passedTests;

            allResults.summary = {
                totalTests,
                passedTests,
                failedTests,
                successRate: totalTests > 0 ? (passedTests / totalTests * 100).toFixed(1) : 0,
                userActionsCount: this.userActions.length,
                screenshotsCount: this.screenshots.length
            };

            // 输出测试结果
            this.outputTestResults(allResults);

            return allResults;

        } catch (error) {
            console.error('❌ 用户体验测试失败:', error);
            throw error;
        }
    }

    /**
     * 输出测试结果
     */
    outputTestResults(results) {
        console.log('\n📊 用户体验完整性测试结果');
        console.log('===============================================');
        
        console.log(`\n📈 测试统计:`);
        console.log(`  总测试数: ${results.summary.totalTests}`);
        console.log(`  通过测试: ${results.summary.passedTests}`);
        console.log(`  失败测试: ${results.summary.failedTests}`);
        console.log(`  成功率: ${results.summary.successRate}%`);
        console.log(`  用户操作: ${results.summary.userActionsCount} 次`);
        console.log(`  状态截图: ${results.summary.screenshotsCount} 张`);

        console.log(`\n🎯 关键发现:`);
        
        // 分析按钮体验
        const buttonIssues = results.buttonResults.filter(r => !r.userSatisfied);
        if (buttonIssues.length > 0) {
            console.log(`  ❌ 按钮体验问题: ${buttonIssues.length} 个`);
            buttonIssues.forEach(issue => {
                console.log(`    - ${issue.action}: ${issue.userFeedback?.userMessage || '无反馈'}`);
            });
        }

        // 分析错误消息质量
        const errorIssues = results.errorMessageResults.filter(r => !r.userSatisfied);
        if (errorIssues.length > 0) {
            console.log(`  ❌ 错误消息问题: ${errorIssues.length} 个`);
            errorIssues.forEach(issue => {
                console.log(`    - ${issue.scenario}: 消息不够友好或可操作`);
            });
        }

        // 分析语义完整性
        const semanticIssues = results.semanticResults.filter(r => !r.userSatisfied);
        if (semanticIssues.length > 0) {
            console.log(`  ❌ 语义完整性问题: ${semanticIssues.length} 个`);
            semanticIssues.forEach(issue => {
                console.log(`    - ${issue.api}: 缺失字段或语义错误`);
            });
        }

        const overallSuccess = results.summary.successRate >= 100;
        console.log(`\n🏆 用户体验完整性测试: ${overallSuccess ? '✅ 通过' : '❌ 需要改进'}`);
        
        if (!overallSuccess) {
            console.log(`\n💡 改进建议:`);
            console.log(`  1. 确保所有用户操作都有明确的视觉反馈`);
            console.log(`  2. 优化错误消息的用户友好性和可操作性`);
            console.log(`  3. 验证API响应的语义完整性，而非仅状态码`);
            console.log(`  4. 增加加载状态指示器提升用户体验`);
        }

        console.log('\n===============================================');
    }
}

// 主执行函数
async function main() {
    const tester = new UserExperienceIntegrityTester();
    
    try {
        await tester.initialize();
        const results = await tester.runAllTests();
        
        // 保存详细结果到文件
        const fs = require('fs');
        if (!fs.existsSync('./test-results')) {
            fs.mkdirSync('./test-results', { recursive: true });
        }
        
        fs.writeFileSync(
            './test-results/user-experience-integrity-results.json',
            JSON.stringify(results, null, 2),
            'utf8'
        );
        
        console.log('\n💾 详细结果已保存到: ./test-results/user-experience-integrity-results.json');
        
        process.exit(results.summary.successRate >= 100 ? 0 : 1);
        
    } catch (error) {
        console.error('❌ 测试执行失败:', error);
        process.exit(1);
    } finally {
        await tester.cleanup();
    }
}

// 如果直接运行此文件，执行测试
if (require.main === module) {
    main();
}

module.exports = UserExperienceIntegrityTester;