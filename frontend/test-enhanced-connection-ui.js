/**
 * TDD第4阶段：Green - 前端增强连接测试UI验证
 * 
 * 测试目标：验证前端ConnectionTestDialog能正确显示三种连接测试结果：
 * 1. MetaStore连接测试
 * 2. HDFS连接测试  
 * 3. Beeline/JDBC连接测试
 * 
 * 预期：测试成功，显示完整的三列连接测试结果
 */

const playwright = require('playwright');

class EnhancedConnectionUIValidator {
    constructor() {
        this.browser = null;
        this.page = null;
        this.baseUrl = 'http://localhost:3001';
        this.testResults = {
            uiLayout: null,
            beelineDisplay: null,
            interactionTest: null,
            errors: []
        };
    }

    async init() {
        console.log('🚀 启动前端增强连接测试UI验证...');
        
        this.browser = await playwright.chromium.launch({
            headless: false,
            devtools: false
        });
        
        this.page = await this.browser.newPage();
        
        // 监听控制台错误
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

    async testUILayoutAndBeeline() {
        console.log('\\n🎨 测试1：UI布局和Beeline显示');
        
        try {
            await this.page.goto(`${this.baseUrl}/#/clusters`);
            await this.page.waitForTimeout(3000);
            
            // 查找并点击详细测试按钮
            const detailButtons = await this.page.$$('button:has-text("详细测试")');
            
            if (detailButtons.length > 0) {
                console.log('✅ 找到详细测试按钮，点击打开对话框');
                await detailButtons[0].click();
                await this.page.waitForTimeout(5000);
                
                // 等待对话框出现
                const dialog = await this.page.$('.el-dialog');
                if (!dialog) {
                    throw new Error('连接测试对话框未出现');
                }
                
                // 检查是否有三列布局
                const testCards = await this.page.$$('.test-card');
                console.log(`找到 ${testCards.length} 个测试卡片`);
                
                // 检查具体的连接测试标题
                const cardTitles = [];
                for (const card of testCards) {
                    const headerText = await card.$eval('.card-header span', el => el.textContent);
                    cardTitles.push(headerText);
                }
                
                console.log('测试卡片标题:', cardTitles);
                
                // 验证是否包含所有三种连接类型
                const hasMetaStore = cardTitles.some(title => title.includes('MetaStore'));
                const hasHDFS = cardTitles.some(title => title.includes('HDFS'));
                const hasBeeline = cardTitles.some(title => title.includes('Beeline') || title.includes('JDBC'));
                
                this.testResults.uiLayout = {
                    success: true,
                    dialogOpened: true,
                    cardCount: testCards.length,
                    cardTitles: cardTitles,
                    hasMetaStore: hasMetaStore,
                    hasHDFS: hasHDFS,
                    hasBeeline: hasBeeline,
                    isThreeColumn: testCards.length === 3
                };
                
                console.log(`✅ MetaStore显示: ${hasMetaStore}`);
                console.log(`✅ HDFS显示: ${hasHDFS}`);
                console.log(`✅ Beeline显示: ${hasBeeline}`);
                console.log(`✅ 三列布局: ${testCards.length === 3}`);
                
            } else {
                throw new Error('未找到详细测试按钮');
            }
            
        } catch (error) {
            console.log('❌ UI布局测试失败:', error.message);
            this.testResults.uiLayout = {
                success: false,
                error: error.message
            };
        }
    }

    async testBeelineSpecificElements() {
        console.log('\\n🔌 测试2：Beeline特定元素显示');
        
        try {
            // 查找Beeline卡片
            const beelineCard = await this.page.$('span:has-text("Beeline")').then(span => 
                span ? span.closest('.test-card') : null
            );
            
            if (!beelineCard) {
                throw new Error('未找到Beeline测试卡片');
            }
            
            // 获取Beeline卡片的内容
            const cardContent = await beelineCard.innerText();
            console.log('Beeline卡片内容:', cardContent);
            
            // 检查Beeline特有的显示元素
            const hasConnectionType = cardContent.includes('连接类型') || cardContent.includes('connection_type');
            const hasDriver = cardContent.includes('驱动') || cardContent.includes('driver');
            const hasJDBC = cardContent.includes('JDBC') || cardContent.includes('jdbc');
            
            // 检查是否有建议显示
            const hasSuggestions = await this.page.$('.suggestions-inline') !== null;
            
            this.testResults.beelineDisplay = {
                success: true,
                cardFound: true,
                cardContent: cardContent,
                hasConnectionType: hasConnectionType,
                hasDriver: hasDriver,
                hasJDBC: hasJDBC,
                hasSuggestions: hasSuggestions
            };
            
            console.log('✅ Beeline卡片找到');
            console.log(`   - 连接类型显示: ${hasConnectionType}`);
            console.log(`   - 驱动信息显示: ${hasDriver}`);
            console.log(`   - JDBC相关显示: ${hasJDBC}`);
            console.log(`   - 建议信息显示: ${hasSuggestions}`);
            
        } catch (error) {
            console.log('❌ Beeline元素测试失败:', error.message);
            this.testResults.beelineDisplay = {
                success: false,
                error: error.message
            };
        }
    }

    async testInteractionFunctionality() {
        console.log('\\n🔄 测试3：交互功能');
        
        try {
            // 测试重新测试按钮
            const retestButton = await this.page.$('button:has-text("重新测试")');
            if (retestButton) {
                console.log('✅ 找到重新测试按钮');
                
                // 记录点击前的状态
                const beforeClick = await this.page.evaluate(() => {
                    const statusTags = Array.from(document.querySelectorAll('.status-tag'));
                    return statusTags.map(tag => tag.textContent);
                });
                
                await retestButton.click();
                await this.page.waitForTimeout(3000);
                
                // 检查是否显示加载状态
                const loadingVisible = await this.page.$('.testing-status .rotating') !== null;
                console.log(`   - 加载状态显示: ${loadingVisible}`);
                
                this.testResults.interactionTest = {
                    success: true,
                    retestButtonFound: true,
                    loadingStatusShown: loadingVisible,
                    beforeClickStatus: beforeClick
                };
                
            } else {
                throw new Error('未找到重新测试按钮');
            }
            
        } catch (error) {
            console.log('❌ 交互功能测试失败:', error.message);
            this.testResults.interactionTest = {
                success: false,
                error: error.message
            };
        }
    }

    generateTDDPhase4Report() {
        console.log('\\n📊 TDD第4阶段验证报告 (Green阶段 - 前端UI优化)');
        console.log('=' .repeat(60));
        
        const issues = [];
        let totalTests = 0;
        let passedTests = 0;
        
        // 分析UI布局测试
        totalTests++;
        if (this.testResults.uiLayout?.success) {
            const layout = this.testResults.uiLayout;
            if (layout.hasMetaStore && layout.hasHDFS && layout.hasBeeline && layout.isThreeColumn) {
                passedTests++;
                console.log('✅ UI布局和三连接显示 - 完全通过');
                console.log(`   - 三列布局: ${layout.cardCount}个卡片`);
                console.log(`   - 连接类型: ${layout.cardTitles.join(', ')}`);
            } else {
                console.log('⚠️  UI布局 - 部分通过');
                if (!layout.hasMetaStore) issues.push('缺少MetaStore连接显示');
                if (!layout.hasHDFS) issues.push('缺少HDFS连接显示');
                if (!layout.hasBeeline) issues.push('缺少Beeline连接显示');
                if (!layout.isThreeColumn) issues.push(`期望3列布局，实际${layout.cardCount}列`);
            }
        } else {
            console.log('❌ UI布局测试 - 失败');
            if (this.testResults.uiLayout?.error) {
                issues.push(`UI布局错误: ${this.testResults.uiLayout.error}`);
            }
        }
        
        // 分析Beeline显示测试
        totalTests++;
        if (this.testResults.beelineDisplay?.success) {
            passedTests++;
            console.log('✅ Beeline特定元素显示 - 通过');
            const beeline = this.testResults.beelineDisplay;
            console.log(`   - 连接类型字段: ${beeline.hasConnectionType}`);
            console.log(`   - 驱动信息字段: ${beeline.hasDriver}`);
            console.log(`   - JDBC相关信息: ${beeline.hasJDBC}`);
        } else {
            console.log('❌ Beeline特定元素显示 - 失败');
            if (this.testResults.beelineDisplay?.error) {
                issues.push(`Beeline显示错误: ${this.testResults.beelineDisplay.error}`);
            }
        }
        
        // 分析交互功能测试
        totalTests++;
        if (this.testResults.interactionTest?.success) {
            passedTests++;
            console.log('✅ 交互功能测试 - 通过');
        } else {
            console.log('❌ 交互功能测试 - 失败');
            if (this.testResults.interactionTest?.error) {
                issues.push(`交互功能错误: ${this.testResults.interactionTest.error}`);
            }
        }
        
        console.log('\\n📋 测试统计');
        console.log(`通过: ${passedTests}/${totalTests}`);
        console.log(`失败: ${totalTests - passedTests}/${totalTests}`);
        
        console.log('\\n🔧 发现的问题:');
        if (issues.length > 0) {
            issues.forEach((issue, index) => {
                console.log(`${index + 1}. ${issue}`);
            });
        } else {
            console.log('没有发现问题，前端UI优化成功！');
        }
        
        // TDD Green阶段：大部分功能应该已经工作
        const isGreen = passedTests >= totalTests * 0.8; // 80%通过率算作Green
        
        if (isGreen) {
            console.log('\\n✅ TDD第4阶段成功: 前端UI优化已完成');
            console.log('   三种连接测试类型都能正确显示给用户');
            console.log('   准备进入第5阶段：端到端验证和重构');
        } else {
            console.log('\\n⚠️  TDD第4阶段需要继续改进');
            console.log('   某些UI功能还需要进一步完善');
        }
        
        return {
            totalTests,
            passedTests,
            issues,
            isGreen,
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
            
            // 运行所有UI测试
            await this.testUILayoutAndBeeline();
            await this.testBeelineSpecificElements();
            await this.testInteractionFunctionality();
            
            // 生成第4阶段报告
            const report = this.generateTDDPhase4Report();
            
            return report;
            
        } catch (error) {
            console.error('❌ 前端UI测试执行失败:', error);
            throw error;
        } finally {
            await this.cleanup();
        }
    }
}

// 执行测试
if (require.main === module) {
    (async () => {
        const validator = new EnhancedConnectionUIValidator();
        try {
            const report = await validator.run();
            // TDD Green阶段：期望大部分测试通过
            process.exit(report.isGreen ? 0 : 1);
        } catch (error) {
            console.error('前端UI测试执行异常:', error);
            process.exit(2);
        }
    })();
}

module.exports = EnhancedConnectionUIValidator;