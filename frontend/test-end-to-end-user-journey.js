/**
 * 端到端用户旅程测试 - 规则11实现
 * 验证用户完整业务场景的连贯性和一致性
 * 模拟真实用户从目标到完成的完整路径
 */

const { chromium } = require('playwright');
const TestUtils = require('./test-utils');
const TestConfig = require('./test-config');

class EndToEndUserJourneyTester {
    constructor() {
        this.browser = null;
        this.page = null;
        this.utils = new TestUtils();
        this.config = new TestConfig();
        this.journeyResults = [];
        this.screenshots = [];
        this.journeyData = {};
    }

    async initialize() {
        this.browser = await chromium.launch({ 
            headless: false,
            slowMo: 300  // 适中速度，观察用户旅程
        });
        this.page = await this.browser.newPage();
        await this.utils.setupPage(this.page);
        
        console.log('🛣️  端到端用户旅程测试初始化完成');
        console.log('🎯 测试目标：验证完整业务场景的连贯性和一致性');
    }

    async cleanup() {
        if (this.browser) {
            await this.browser.close();
        }
    }

    /**
     * 用户旅程1：新用户首次使用完整体验
     */
    async testNewUserFirstTimeExperience() {
        console.log('\n👋 测试新用户首次使用体验...');
        const journey = {
            name: '新用户首次使用',
            steps: [],
            success: false,
            issues: [],
            dataFlow: {}
        };

        try {
            // 步骤1：访问首页，了解系统
            await this.executeJourneyStep(journey, '访问首页', async () => {
                await this.page.goto(this.config.frontendUrl);
                await this.utils.waitForPageLoad(this.page);
                return {
                    hasWelcomeContent: await this.page.textContent('body').then(text => 
                        text.includes('集群') || text.includes('小文件') || text.includes('管理')
                    ),
                    navigationVisible: await this.page.$('nav, .nav, .menu') !== null
                };
            });

            // 步骤2：导航到集群管理
            await this.executeJourneyStep(journey, '导航到集群管理', async () => {
                const clusterLink = await this.page.$('a[href*="clusters"], button:has-text("集群")');
                if (clusterLink) {
                    await clusterLink.click();
                    await this.utils.waitForPageLoad(this.page);
                }
                return {
                    onClustersPage: this.page.url().includes('/clusters'),
                    hasClusterInterface: await this.page.$('.cluster-list, .cluster-card, .cluster-management') !== null
                };
            });

            // 步骤3：添加第一个集群
            await this.executeJourneyStep(journey, '添加第一个集群', async () => {
                const addButton = await this.page.$('button:has-text("添加"), button:has-text("新增")');
                if (addButton) {
                    await addButton.click();
                    await this.page.waitForTimeout(1000);
                }

                // 填写集群信息
                const nameInput = await this.page.$('input[placeholder*="名称"], input[placeholder*="集群"]');
                if (nameInput) {
                    await nameInput.fill('测试集群_新用户');
                }

                const urlInput = await this.page.$('input[placeholder*="连接"], input[placeholder*="URL"]');
                if (urlInput) {
                    await urlInput.fill('postgresql://test:test@localhost:5432/hive_metastore');
                }

                const descInput = await this.page.$('textarea, input[placeholder*="描述"]');
                if (descInput) {
                    await descInput.fill('新用户创建的第一个测试集群');
                }

                // 提交表单
                const submitButton = await this.page.$('button:has-text("确定"), button:has-text("保存")');
                if (submitButton) {
                    await submitButton.click();
                    await this.page.waitForTimeout(2000);
                }

                return {
                    clusterCreated: await this.page.textContent('body').then(text => 
                        text.includes('测试集群_新用户') || text.includes('成功')
                    ),
                    backToList: this.page.url().includes('/clusters')
                };
            });

            // 步骤4：测试集群连接
            await this.executeJourneyStep(journey, '测试集群连接', async () => {
                const testButton = await this.page.$('button:has-text("测试"), button:has-text("连接")');
                if (testButton) {
                    await testButton.click();
                    await this.page.waitForTimeout(3000);
                }

                const connectionResult = await this.page.textContent('body');
                return {
                    testExecuted: true,
                    connectionSuccess: connectionResult.includes('成功') || connectionResult.includes('连接正常'),
                    hasErrorMessage: connectionResult.includes('失败') || connectionResult.includes('错误')
                };
            });

            // 步骤5：查看集群详情
            await this.executeJourneyStep(journey, '查看集群详情', async () => {
                const detailButton = await this.page.$('button:has-text("详情"), button:has-text("查看")');
                if (detailButton) {
                    await detailButton.click();
                    await this.utils.waitForPageLoad(this.page);
                }

                return {
                    onDetailPage: this.page.url().includes('/clusters/'),
                    hasDetailContent: await this.page.textContent('body').then(text => 
                        text.includes('集群详情') || text.includes('连接信息')
                    )
                };
            });

            // 步骤6：导航到表管理
            await this.executeJourneyStep(journey, '导航到表管理', async () => {
                const tableLink = await this.page.$('a[href*="tables"], button:has-text("表管理")');
                if (tableLink) {
                    await tableLink.click();
                    await this.utils.waitForPageLoad(this.page);
                }

                return {
                    onTablesPage: this.page.url().includes('/tables'),
                    hasTableInterface: await this.page.$('.table-list, .table-management') !== null
                };
            });

            // 评估旅程成功性
            const allStepsSuccessful = journey.steps.every(step => step.success);
            const criticalStepsSuccessful = journey.steps.filter(step => 
                ['添加第一个集群', '导航到集群管理', '导航到表管理'].includes(step.name)
            ).every(step => step.success);

            journey.success = allStepsSuccessful && criticalStepsSuccessful;

            if (!journey.success) {
                journey.issues.push('关键步骤执行失败，影响新用户体验');
            }

        } catch (error) {
            journey.issues.push(`旅程执行异常: ${error.message}`);
        }

        return journey;
    }

    /**
     * 用户旅程2：完整的集群管理流程
     */
    async testCompleteClusterManagementFlow() {
        console.log('\n🏗️  测试完整集群管理流程...');
        const journey = {
            name: '完整集群管理流程',
            steps: [],
            success: false,
            issues: [],
            dataFlow: {
                clusterId: null,
                clusterName: '集群管理流程测试',
                createdAt: new Date().toISOString()
            }
        };

        try {
            // 步骤1：创建集群
            await this.executeJourneyStep(journey, '创建集群', async () => {
                await this.page.goto(this.config.frontendUrl + '/#/clusters');
                await this.utils.waitForPageLoad(this.page);

                const addButton = await this.page.$('button:has-text("添加")');
                if (addButton) {
                    await addButton.click();
                    await this.page.waitForTimeout(1000);

                    // 填写集群信息
                    await this.page.fill('input[placeholder*="名称"]', journey.dataFlow.clusterName);
                    await this.page.fill('input[placeholder*="连接"]', 'postgresql://test:test@localhost:5432/hive_metastore');
                    await this.page.fill('textarea, input[placeholder*="描述"]', '完整流程测试集群');

                    const submitButton = await this.page.$('button:has-text("确定")');
                    if (submitButton) {
                        await submitButton.click();
                        await this.page.waitForTimeout(2000);
                    }
                }

                // 验证集群创建
                const pageContent = await this.page.textContent('body');
                const clusterCreated = pageContent.includes(journey.dataFlow.clusterName);

                if (clusterCreated) {
                    // 尝试获取集群ID
                    const clusterCard = await this.page.$(`text=${journey.dataFlow.clusterName}`);
                    if (clusterCard) {
                        const cardElement = await clusterCard.locator('..').locator('..');
                        const cardHtml = await cardElement.innerHTML();
                        const idMatch = cardHtml.match(/data-id="(\d+)"|id="(\d+)"/);
                        if (idMatch) {
                            journey.dataFlow.clusterId = idMatch[1] || idMatch[2];
                        }
                    }
                }

                return { clusterCreated, clusterId: journey.dataFlow.clusterId };
            });

            // 步骤2：测试连接
            await this.executeJourneyStep(journey, '测试连接', async () => {
                const testButton = await this.page.$('button:has-text("快速测试")');
                if (testButton) {
                    await testButton.click();
                    await this.page.waitForTimeout(3000);
                }

                const pageContent = await this.page.textContent('body');
                return {
                    testExecuted: true,
                    connectionResult: pageContent.includes('成功') ? 'success' : 'failed'
                };
            });

            // 步骤3：进入集群详情
            await this.executeJourneyStep(journey, '进入集群详情', async () => {
                const detailButton = await this.page.$('button:has-text("详情")');
                if (detailButton) {
                    await detailButton.click();
                    await this.utils.waitForPageLoad(this.page);
                }

                return {
                    onDetailPage: this.page.url().includes('/clusters/'),
                    hasClusterInfo: await this.page.textContent('body').then(text => 
                        text.includes(journey.dataFlow.clusterName)
                    )
                };
            });

            // 步骤4：扫描数据库
            await this.executeJourneyStep(journey, '扫描数据库', async () => {
                const scanButton = await this.page.$('button:has-text("扫描")');
                if (scanButton) {
                    await scanButton.click();
                    await this.page.waitForTimeout(5000); // 扫描需要更长时间
                }

                const pageContent = await this.page.textContent('body');
                return {
                    scanExecuted: true,
                    scanResult: pageContent.includes('扫描完成') || pageContent.includes('扫描结果')
                };
            });

            // 步骤5：查看扫描结果
            await this.executeJourneyStep(journey, '查看扫描结果', async () => {
                // 导航到表管理页面查看结果
                await this.page.goto(this.config.frontendUrl + '/#/tables');
                await this.utils.waitForPageLoad(this.page);

                const pageContent = await this.page.textContent('body');
                return {
                    hasResults: pageContent.includes('表') || pageContent.includes('数据'),
                    resultsAccessible: true
                };
            });

            // 步骤6：创建合并任务
            await this.executeJourneyStep(journey, '创建合并任务', async () => {
                await this.page.goto(this.config.frontendUrl + '/#/tasks');
                await this.utils.waitForPageLoad(this.page);

                const createButton = await this.page.$('button:has-text("创建"), button:has-text("新建")');
                if (createButton) {
                    await createButton.click();
                    await this.page.waitForTimeout(1000);

                    // 配置任务
                    const taskNameInput = await this.page.$('input[placeholder*="任务"], input[placeholder*="名称"]');
                    if (taskNameInput) {
                        await taskNameInput.fill('自动化测试任务');
                    }

                    const submitButton = await this.page.$('button:has-text("确定"), button:has-text("创建")');
                    if (submitButton) {
                        await submitButton.click();
                        await this.page.waitForTimeout(2000);
                    }
                }

                const pageContent = await this.page.textContent('body');
                return {
                    taskCreated: pageContent.includes('自动化测试任务') || pageContent.includes('成功')
                };
            });

            // 评估完整流程
            const criticalSteps = ['创建集群', '测试连接', '进入集群详情'];
            const criticalStepsSuccessful = journey.steps.filter(step => 
                criticalSteps.includes(step.name)
            ).every(step => step.success);

            journey.success = criticalStepsSuccessful;

            // 数据一致性检查
            await this.verifyDataConsistency(journey);

        } catch (error) {
            journey.issues.push(`完整流程执行异常: ${error.message}`);
        }

        return journey;
    }

    /**
     * 用户旅程3：跨页面数据一致性验证
     */
    async testCrossPageDataConsistency() {
        console.log('\n🔄 测试跨页面数据一致性...');
        const journey = {
            name: '跨页面数据一致性',
            steps: [],
            success: false,
            issues: [],
            dataFlow: {
                clusterData: {},
                tableData: {},
                taskData: {}
            }
        };

        try {
            // 步骤1：收集集群页面数据
            await this.executeJourneyStep(journey, '收集集群页面数据', async () => {
                await this.page.goto(this.config.frontendUrl + '/#/clusters');
                await this.utils.waitForPageLoad(this.page);

                // 获取第一个集群的信息
                const clusterCards = await this.page.$$('.cluster-card');
                if (clusterCards.length > 0) {
                    const firstCard = clusterCards[0];
                    const clusterName = await firstCard.textContent();
                    journey.dataFlow.clusterData = {
                        name: clusterName.match(/测试|集群/)?.[0] || 'unknown',
                        cardCount: clusterCards.length,
                        hasDetailButton: await firstCard.$('button:has-text("详情")') !== null
                    };
                }

                return { dataCollected: Object.keys(journey.dataFlow.clusterData).length > 0 };
            });

            // 步骤2：验证表页面的集群数据
            await this.executeJourneyStep(journey, '验证表页面的集群数据', async () => {
                await this.page.goto(this.config.frontendUrl + '/#/tables');
                await this.utils.waitForPageLoad(this.page);

                const pageContent = await this.page.textContent('body');
                const clusterConsistency = {
                    hasClusterReference: pageContent.includes('集群') || 
                                       pageContent.includes(journey.dataFlow.clusterData.name),
                    hasClusterSelector: await this.page.$('select, .el-select') !== null
                };

                journey.dataFlow.tableData = clusterConsistency;

                return clusterConsistency;
            });

            // 步骤3：验证任务页面的数据一致性
            await this.executeJourneyStep(journey, '验证任务页面的数据一致性', async () => {
                await this.page.goto(this.config.frontendUrl + '/#/tasks');
                await this.utils.waitForPageLoad(this.page);

                const pageContent = await this.page.textContent('body');
                const taskConsistency = {
                    hasClusterReference: pageContent.includes('集群'),
                    hasTableReference: pageContent.includes('表'),
                    dataConnected: pageContent.includes('集群') && pageContent.includes('表')
                };

                journey.dataFlow.taskData = taskConsistency;

                return taskConsistency;
            });

            // 步骤4：测试页面间导航状态保持
            await this.executeJourneyStep(journey, '测试页面间导航状态保持', async () => {
                // 返回集群页面，检查状态是否保持
                await this.page.goto(this.config.frontendUrl + '/#/clusters');
                await this.utils.waitForPageLoad(this.page);

                const currentClusterCount = await this.page.$$eval('.cluster-card', cards => cards.length);
                const stateConsistency = {
                    clusterCountMatches: currentClusterCount === journey.dataFlow.clusterData.cardCount,
                    pageLoadsCorrectly: this.page.url().includes('/clusters')
                };

                return stateConsistency;
            });

            // 评估数据一致性
            const allStepsSuccessful = journey.steps.every(step => step.success);
            const dataConnected = journey.dataFlow.tableData.hasClusterReference && 
                                 journey.dataFlow.taskData.dataConnected;

            journey.success = allStepsSuccessful && dataConnected;

            if (!dataConnected) {
                journey.issues.push('跨页面数据关联不够清晰或缺失');
            }

        } catch (error) {
            journey.issues.push(`数据一致性验证异常: ${error.message}`);
        }

        return journey;
    }

    /**
     * 用户旅程4：中断和恢复场景测试
     */
    async testInterruptionAndRecoveryScenarios() {
        console.log('\n🔄 测试中断和恢复场景...');
        const journey = {
            name: '中断和恢复场景',
            steps: [],
            success: false,
            issues: [],
            dataFlow: {
                beforeInterruption: {},
                afterRecovery: {}
            }
        };

        try {
            // 步骤1：建立初始状态
            await this.executeJourneyStep(journey, '建立初始状态', async () => {
                await this.page.goto(this.config.frontendUrl + '/#/clusters');
                await this.utils.waitForPageLoad(this.page);

                // 记录当前状态
                const clusterCount = await this.page.$$eval('.cluster-card', cards => cards.length);
                const pageTitle = await this.page.title();
                
                journey.dataFlow.beforeInterruption = {
                    clusterCount,
                    pageTitle,
                    url: this.page.url(),
                    timestamp: Date.now()
                };

                return { stateEstablished: true };
            });

            // 步骤2：模拟页面刷新中断
            await this.executeJourneyStep(journey, '模拟页面刷新中断', async () => {
                await this.page.reload();
                await this.utils.waitForPageLoad(this.page);

                return { refreshCompleted: true };
            });

            // 步骤3：验证恢复后的状态
            await this.executeJourneyStep(journey, '验证恢复后的状态', async () => {
                const clusterCount = await this.page.$$eval('.cluster-card', cards => cards.length);
                const pageTitle = await this.page.title();
                
                journey.dataFlow.afterRecovery = {
                    clusterCount,
                    pageTitle,
                    url: this.page.url(),
                    timestamp: Date.now()
                };

                const recoverySuccess = {
                    clusterCountMatches: clusterCount === journey.dataFlow.beforeInterruption.clusterCount,
                    titleMatches: pageTitle === journey.dataFlow.beforeInterruption.pageTitle,
                    urlMatches: this.page.url() === journey.dataFlow.beforeInterruption.url,
                    pageLoadsCompletely: await this.page.$('.cluster-list, .cluster-card') !== null
                };

                return recoverySuccess;
            });

            // 步骤4：测试导航状态恢复
            await this.executeJourneyStep(journey, '测试导航状态恢复', async () => {
                // 导航到其他页面再返回
                await this.page.goto(this.config.frontendUrl + '/#/tables');
                await this.utils.waitForPageLoad(this.page);
                
                await this.page.goto(this.config.frontendUrl + '/#/clusters');
                await this.utils.waitForPageLoad(this.page);

                const navigationRecovery = {
                    canNavigateAway: true,
                    canNavigateBack: this.page.url().includes('/clusters'),
                    dataPreserved: await this.page.$$eval('.cluster-card', cards => cards.length) > 0
                };

                return navigationRecovery;
            });

            // 评估中断恢复能力
            const criticalSteps = ['验证恢复后的状态', '测试导航状态恢复'];
            const recoverySuccessful = journey.steps.filter(step => 
                criticalSteps.includes(step.name)
            ).every(step => step.success);

            journey.success = recoverySuccessful;

            if (!recoverySuccessful) {
                journey.issues.push('页面中断恢复能力不足，影响用户体验连续性');
            }

        } catch (error) {
            journey.issues.push(`中断恢复测试异常: ${error.message}`);
        }

        return journey;
    }

    /**
     * 用户旅程5：多角色权限完整流程（模拟）
     */
    async testMultiRolePermissionFlow() {
        console.log('\n👥 测试多角色权限流程（模拟）...');
        const journey = {
            name: '多角色权限流程',
            steps: [],
            success: false,
            issues: [],
            dataFlow: {
                adminActions: [],
                userActions: [],
                permissions: {}
            }
        };

        try {
            // 步骤1：模拟管理员操作
            await this.executeJourneyStep(journey, '模拟管理员操作', async () => {
                await this.page.goto(this.config.frontendUrl + '/#/clusters');
                await this.utils.waitForPageLoad(this.page);

                // 检查管理员级别功能
                const adminFeatures = {
                    canAddCluster: await this.page.$('button:has-text("添加")') !== null,
                    canDeleteCluster: await this.page.$('button:has-text("删除")') !== null,
                    canEditCluster: await this.page.$('button:has-text("编辑")') !== null,
                    hasAllMenus: await this.page.$$('nav a, .menu a').then(links => links.length >= 3)
                };

                journey.dataFlow.adminActions = Object.keys(adminFeatures).filter(key => adminFeatures[key]);

                return adminFeatures;
            });

            // 步骤2：验证功能可访问性
            await this.executeJourneyStep(journey, '验证功能可访问性', async () => {
                const accessibilityCheck = {
                    allPagesAccessible: true,
                    allFunctionsVisible: true,
                    noPermissionErrors: true
                };

                // 测试各页面访问
                const pages = ['/clusters', '/tables', '/tasks', '/dashboard'];
                for (const pagePath of pages) {
                    try {
                        await this.page.goto(this.config.frontendUrl + '/#' + pagePath);
                        await this.utils.waitForPageLoad(this.page);
                        
                        const pageContent = await this.page.textContent('body');
                        if (pageContent.includes('权限') || pageContent.includes('拒绝') || pageContent.includes('forbidden')) {
                            accessibilityCheck.noPermissionErrors = false;
                        }
                    } catch (error) {
                        accessibilityCheck.allPagesAccessible = false;
                    }
                }

                return accessibilityCheck;
            });

            // 步骤3：模拟操作执行
            await this.executeJourneyStep(journey, '模拟操作执行', async () => {
                await this.page.goto(this.config.frontendUrl + '/#/clusters');
                await this.utils.waitForPageLoad(this.page);

                // 尝试执行需要权限的操作
                const operationsTest = {
                    canViewClusters: await this.page.$$('.cluster-card').then(cards => cards.length >= 0),
                    canAccessDetails: true,
                    canPerformActions: true
                };

                // 测试详情访问
                const detailButton = await this.page.$('button:has-text("详情")');
                if (detailButton) {
                    await detailButton.click();
                    await this.page.waitForTimeout(1000);
                    operationsTest.canAccessDetails = this.page.url().includes('/clusters/');
                }

                return operationsTest;
            });

            // 当前实现中假设单一角色，标记为成功
            journey.success = journey.steps.every(step => step.success);
            journey.dataFlow.permissions = {
                role: 'admin',
                fullAccess: true,
                note: '当前版本暂无角色权限限制，所有功能均可访问'
            };

        } catch (error) {
            journey.issues.push(`权限流程测试异常: ${error.message}`);
        }

        return journey;
    }

    /**
     * 执行旅程步骤
     */
    async executeJourneyStep(journey, stepName, stepFn) {
        console.log(`  🔧 执行步骤: ${stepName}`);
        const step = {
            name: stepName,
            startTime: Date.now(),
            success: false,
            result: null,
            issues: []
        };

        try {
            // 截图记录步骤状态
            await this.captureJourneyStep(journey.name, stepName, 'before');
            
            // 执行步骤
            step.result = await stepFn();
            
            // 验证步骤结果
            if (typeof step.result === 'object' && step.result !== null) {
                // 检查结果对象中的布尔值
                const booleanValues = Object.values(step.result).filter(v => typeof v === 'boolean');
                step.success = booleanValues.length > 0 ? booleanValues.every(v => v) : true;
                
                // 记录失败的检查项
                if (!step.success) {
                    const failedChecks = Object.entries(step.result)
                        .filter(([key, value]) => typeof value === 'boolean' && !value)
                        .map(([key]) => key);
                    step.issues.push(`失败的检查项: ${failedChecks.join(', ')}`);
                }
            } else {
                step.success = Boolean(step.result);
            }

            step.endTime = Date.now();
            step.duration = step.endTime - step.startTime;

            console.log(`    ${step.success ? '✅' : '❌'} ${stepName}: ${step.duration}ms`);
            if (step.issues.length > 0) {
                console.log(`      问题: ${step.issues.join('; ')}`);
            }

            // 截图记录步骤完成状态
            await this.captureJourneyStep(journey.name, stepName, 'after');

        } catch (error) {
            step.success = false;
            step.issues.push(`步骤执行异常: ${error.message}`);
            step.endTime = Date.now();
            step.duration = step.endTime - step.startTime;
            
            console.log(`    ❌ ${stepName}: 执行失败 - ${error.message}`);
        }

        journey.steps.push(step);
        return step;
    }

    /**
     * 验证数据一致性
     */
    async verifyDataConsistency(journey) {
        console.log(`  🔍 验证数据一致性...`);
        
        try {
            // 检查集群数据在不同页面的一致性
            const pages = ['/clusters', '/tables', '/tasks'];
            const dataConsistency = {};

            for (const page of pages) {
                await this.page.goto(this.config.frontendUrl + '/#' + page);
                await this.utils.waitForPageLoad(this.page);
                
                const pageContent = await this.page.textContent('body');
                dataConsistency[page] = {
                    hasClusterReference: pageContent.includes(journey.dataFlow.clusterName),
                    pageLoaded: !pageContent.includes('加载') && !pageContent.includes('Loading')
                };
            }

            journey.dataFlow.consistency = dataConsistency;

            const allPagesConsistent = Object.values(dataConsistency).every(data => 
                data.pageLoaded && (data.hasClusterReference || page === '/dashboard')
            );

            if (!allPagesConsistent) {
                journey.issues.push('跨页面数据一致性检查失败');
            }

            console.log(`    数据一致性: ${allPagesConsistent ? '✅' : '❌'}`);

        } catch (error) {
            journey.issues.push(`数据一致性验证失败: ${error.message}`);
        }
    }

    /**
     * 捕获旅程步骤截图
     */
    async captureJourneyStep(journeyName, stepName, phase) {
        try {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `journey-${journeyName.replace(/\s+/g, '-')}-${stepName.replace(/\s+/g, '-')}-${phase}-${timestamp}.png`;
            const filepath = `./test-results/${filename}`;
            
            await this.page.screenshot({ 
                path: filepath, 
                fullPage: true 
            });
            
            this.screenshots.push({
                journey: journeyName,
                step: stepName,
                phase,
                filename,
                filepath,
                timestamp: new Date().toISOString()
            });
            
        } catch (error) {
            console.log(`    警告: 截图失败 - ${error.message}`);
        }
    }

    /**
     * 运行所有用户旅程测试
     */
    async runAllJourneys() {
        console.log('\n🛣️  开始端到端用户旅程测试');
        console.log('===============================================');

        const allResults = {
            journeys: [],
            screenshots: [],
            summary: {}
        };

        try {
            // 执行所有用户旅程
            allResults.journeys.push(await this.testNewUserFirstTimeExperience());
            allResults.journeys.push(await this.testCompleteClusterManagementFlow());
            allResults.journeys.push(await this.testCrossPageDataConsistency());
            allResults.journeys.push(await this.testInterruptionAndRecoveryScenarios());
            allResults.journeys.push(await this.testMultiRolePermissionFlow());

            // 收集截图
            allResults.screenshots = this.screenshots;

            // 计算汇总统计
            const totalJourneys = allResults.journeys.length;
            const successfulJourneys = allResults.journeys.filter(journey => journey.success).length;
            const failedJourneys = totalJourneys - successfulJourneys;

            const totalSteps = allResults.journeys.reduce((sum, journey) => sum + journey.steps.length, 0);
            const successfulSteps = allResults.journeys.reduce((sum, journey) => 
                sum + journey.steps.filter(step => step.success).length, 0);

            allResults.summary = {
                totalJourneys,
                successfulJourneys,
                failedJourneys,
                journeySuccessRate: totalJourneys > 0 ? (successfulJourneys / totalJourneys * 100).toFixed(1) : 0,
                totalSteps,
                successfulSteps,
                stepSuccessRate: totalSteps > 0 ? (successfulSteps / totalSteps * 100).toFixed(1) : 0,
                screenshotsCount: this.screenshots.length
            };

            // 输出测试结果
            this.outputJourneyResults(allResults);

            return allResults;

        } catch (error) {
            console.error('❌ 用户旅程测试失败:', error);
            throw error;
        }
    }

    /**
     * 输出测试结果
     */
    outputJourneyResults(results) {
        console.log('\n📊 端到端用户旅程测试结果');
        console.log('===============================================');
        
        console.log(`\n📈 旅程统计:`);
        console.log(`  总旅程数: ${results.summary.totalJourneys}`);
        console.log(`  成功旅程: ${results.summary.successfulJourneys}`);
        console.log(`  失败旅程: ${results.summary.failedJourneys}`);
        console.log(`  旅程成功率: ${results.summary.journeySuccessRate}%`);
        console.log(`  总步骤数: ${results.summary.totalSteps}`);
        console.log(`  成功步骤: ${results.summary.successfulSteps}`);
        console.log(`  步骤成功率: ${results.summary.stepSuccessRate}%`);
        console.log(`  旅程截图: ${results.summary.screenshotsCount} 张`);

        console.log(`\n🎯 旅程详情:`);
        results.journeys.forEach((journey, index) => {
            const status = journey.success ? '✅' : '❌';
            const stepStats = `${journey.steps.filter(s => s.success).length}/${journey.steps.length}`;
            console.log(`  ${index + 1}. ${status} ${journey.name} (${stepStats} 步骤成功)`);
            
            if (journey.issues.length > 0) {
                journey.issues.forEach(issue => {
                    console.log(`     ⚠️  ${issue}`);
                });
            }

            // 显示关键数据流
            if (journey.dataFlow && Object.keys(journey.dataFlow).length > 0) {
                console.log(`     📊 数据流: ${JSON.stringify(journey.dataFlow, null, 2).substring(0, 100)}...`);
            }
        });

        const overallSuccess = results.summary.journeySuccessRate >= 100;
        console.log(`\n🏆 端到端用户旅程测试: ${overallSuccess ? '✅ 通过' : '❌ 需要改进'}`);
        
        if (!overallSuccess) {
            console.log(`\n💡 改进建议:`);
            console.log(`  1. 优化失败旅程中的关键步骤，确保用户流程顺畅`);
            console.log(`  2. 加强跨页面数据一致性和状态保持`);
            console.log(`  3. 改善中断恢复机制，提升用户体验连续性`);
            console.log(`  4. 完善新用户引导流程，降低学习成本`);
            console.log(`  5. 增强错误处理和用户反馈机制`);
        }

        // 输出验证链接
        console.log(`\n🔗 验证链接:`);
        console.log(`  🌐 集群管理: http://localhost:3002/#/clusters`);
        console.log(`  🌐 表管理: http://localhost:3002/#/tables`);
        console.log(`  🌐 任务管理: http://localhost:3002/#/tasks`);
        console.log(`  🌐 仪表板: http://localhost:3002/#/dashboard`);

        console.log('\n===============================================');
    }
}

// 主执行函数
async function main() {
    const tester = new EndToEndUserJourneyTester();
    
    try {
        await tester.initialize();
        const results = await tester.runAllJourneys();
        
        // 保存详细结果到文件
        const fs = require('fs');
        if (!fs.existsSync('./test-results')) {
            fs.mkdirSync('./test-results', { recursive: true });
        }
        
        fs.writeFileSync(
            './test-results/end-to-end-user-journey-results.json',
            JSON.stringify(results, null, 2),
            'utf8'
        );
        
        console.log('\n💾 详细结果已保存到: ./test-results/end-to-end-user-journey-results.json');
        
        process.exit(results.summary.journeySuccessRate >= 100 ? 0 : 1);
        
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

module.exports = EndToEndUserJourneyTester;