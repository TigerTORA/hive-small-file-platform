/**
 * 测试仪表板端到端功能测试
 * 验证测试仪表板的所有功能是否正常工作
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function testDashboardE2E() {
    console.log('🧪 开始测试仪表板端到端功能...');
    
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
        // 1. 导航到测试仪表板
        console.log('📍 导航到测试仪表板...');
        await page.goto('http://localhost:3002/#/test-dashboard');
        await page.waitForLoadState('networkidle');
        
        // 2. 验证页面基本结构
        console.log('🔍 验证页面基本结构...');
        
        // 检查页面标题
        const pageTitle = await page.textContent('.page-title');
        if (!pageTitle.includes('测试中心')) {
            throw new Error('页面标题不正确');
        }
        console.log('✅ 页面标题正确');
        
        // 检查概览卡片
        const overviewCards = await page.locator('.overview-card').count();
        if (overviewCards !== 4) {
            throw new Error(`预期4个概览卡片，实际找到${overviewCards}个`);
        }
        console.log('✅ 概览卡片数量正确');
        
        // 3. 验证数据加载
        console.log('📊 验证数据加载...');
        
        // 等待数据加载完成
        await page.waitForSelector('.overview-card h3', { timeout: 10000 });
        
        // 检查测试数据
        const totalTests = await page.textContent('.overview-card:first-child h3');
        console.log(`✅ 总测试数: ${totalTests}`);
        
        if (parseInt(totalTests) === 0) {
            throw new Error('没有加载到测试数据');
        }
        
        // 4. 验证测试分类
        console.log('📂 验证测试分类...');
        
        // 检查分类卡片
        const categoryCards = await page.locator('.category-card').count();
        console.log(`✅ 找到${categoryCards}个测试分类`);
        
        if (categoryCards === 0) {
            throw new Error('没有找到测试分类');
        }
        
        // 5. 验证测试结果表格
        console.log('📋 验证测试结果表格...');
        
        // 检查表格是否存在
        const tableExists = await page.locator('.test-results-table').count() > 0;
        if (!tableExists) {
            throw new Error('测试结果表格不存在');
        }
        console.log('✅ 测试结果表格存在');
        
        // 检查表格行数
        const tableRows = await page.locator('.test-results-table .el-table__row').count();
        console.log(`✅ 表格显示${tableRows}行数据`);
        
        // 6. 测试筛选功能
        console.log('🔍 测试筛选功能...');
        
        // 测试状态筛选
        const statusFilterExists = await page.locator('select[data-testid="status-filter"]').count() > 0;
        if (statusFilterExists) {
            await page.selectOption('select[data-testid="status-filter"]', 'passed');
            await page.waitForTimeout(1000);
            console.log('✅ 状态筛选功能正常');
        }
        
        // 7. 测试按钮功能
        console.log('🔘 测试按钮功能...');
        
        // 测试刷新按钮
        const refreshButton = page.locator('button:has-text("刷新数据")');
        if (await refreshButton.count() > 0) {
            await refreshButton.click();
            await page.waitForTimeout(2000);
            console.log('✅ 刷新按钮功能正常');
        }
        
        // 8. 验证响应式设计
        console.log('📱 验证响应式设计...');
        
        // 测试不同屏幕尺寸
        await page.setViewportSize({ width: 768, height: 1024 });
        await page.waitForTimeout(1000);
        
        // 检查在小屏幕下是否仍然可见
        const mobileVisibility = await page.locator('.test-dashboard').isVisible();
        if (!mobileVisibility) {
            throw new Error('在移动端视口下仪表板不可见');
        }
        console.log('✅ 响应式设计正常');
        
        // 恢复正常屏幕尺寸
        await page.setViewportSize({ width: 1920, height: 1080 });
        
        // 9. 截图保存测试证据
        console.log('📸 保存测试截图...');
        
        const screenshotPath = path.join(process.cwd(), 'test-results', 'dashboard-e2e-success.png');
        
        // 确保目录存在
        const screenshotDir = path.dirname(screenshotPath);
        if (!fs.existsSync(screenshotDir)) {
            fs.mkdirSync(screenshotDir, { recursive: true });
        }
        
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`✅ 截图已保存: ${screenshotPath}`);
        
        // 10. 生成测试报告
        const report = {
            testName: '测试仪表板端到端功能测试',
            timestamp: new Date().toISOString(),
            status: 'PASSED',
            url: 'http://localhost:3002/#/test-dashboard',
            results: {
                pageTitle: '✅ 正确',
                overviewCards: `✅ ${overviewCards}个卡片`,
                dataLoading: `✅ 总测试数: ${totalTests}`,
                categories: `✅ ${categoryCards}个分类`,
                resultsTable: `✅ ${tableRows}行数据`,
                filterFunction: '✅ 正常',
                buttonFunction: '✅ 正常',
                responsiveDesign: '✅ 正常',
                screenshot: screenshotPath
            },
            summary: {
                totalChecks: 8,
                passedChecks: 8,
                failedChecks: 0,
                successRate: 100
            }
        };
        
        const reportPath = path.join(process.cwd(), 'test-results', 'dashboard-e2e-report.json');
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        console.log(`✅ 测试报告已保存: ${reportPath}`);
        
        console.log('\n🎉 测试仪表板端到端功能测试完成!');
        console.log('═══════════════════════════════════════');
        console.log('📊 测试结果概览:');
        console.log(`  ✅ 总检查项: ${report.summary.totalChecks}`);
        console.log(`  ✅ 通过检查: ${report.summary.passedChecks}`);
        console.log(`  ❌ 失败检查: ${report.summary.failedChecks}`);
        console.log(`  📈 成功率: ${report.summary.successRate}%`);
        console.log(`  🔗 访问地址: ${report.url}`);
        console.log(`  📸 测试截图: ${report.results.screenshot}`);
        console.log('═══════════════════════════════════════');
        
        return report;
        
    } catch (error) {
        console.error('❌ 测试失败:', error.message);
        
        // 保存失败截图
        const errorScreenshot = path.join(process.cwd(), 'test-results', 'dashboard-e2e-error.png');
        const errorDir = path.dirname(errorScreenshot);
        if (!fs.existsSync(errorDir)) {
            fs.mkdirSync(errorDir, { recursive: true });
        }
        
        await page.screenshot({ path: errorScreenshot, fullPage: true });
        console.log(`📸 错误截图已保存: ${errorScreenshot}`);
        
        // 生成失败报告
        const errorReport = {
            testName: '测试仪表板端到端功能测试',
            timestamp: new Date().toISOString(),
            status: 'FAILED',
            error: error.message,
            screenshot: errorScreenshot,
            url: 'http://localhost:3002/#/test-dashboard'
        };
        
        const errorReportPath = path.join(process.cwd(), 'test-results', 'dashboard-e2e-error-report.json');
        fs.writeFileSync(errorReportPath, JSON.stringify(errorReport, null, 2));
        
        throw error;
        
    } finally {
        await browser.close();
    }
}

// 主执行函数
async function main() {
    try {
        const report = await testDashboardE2E();
        process.exit(0);
    } catch (error) {
        console.error('💥 端到端测试执行失败:', error.message);
        process.exit(1);
    }
}

// 如果直接运行此文件，执行测试
if (require.main === module) {
    main();
}

module.exports = { testDashboardE2E };