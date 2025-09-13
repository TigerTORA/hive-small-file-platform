/**
 * 快速检查扫描按钮和日志显示
 */
const { chromium } = require('playwright');

async function checkScanInterface() {
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext();
    const page = await context.newPage();

    try {
        await page.goto('http://localhost:3000');
        await page.waitForTimeout(2000);
        
        // 检查集群列表
        console.log('📋 检查集群列表...');
        const clusters = await page.locator('tbody tr').allTextContents();
        console.log('发现集群:', clusters);
        
        // 点击第一个集群进入详情
        if (clusters.length > 0) {
            await page.locator('tbody tr').first().click();
            await page.waitForTimeout(2000);
            
            // 查找所有按钮
            console.log('🔍 检查集群详情页面按钮...');
            const buttons = await page.locator('button').allTextContents();
            console.log('页面按钮:', buttons);
            
            // 查找包含"扫描"的按钮
            const scanButtons = buttons.filter(btn => btn.includes('扫描'));
            console.log('扫描相关按钮:', scanButtons);
            
            // 尝试点击扫描按钮
            if (scanButtons.length > 0) {
                console.log(`点击扫描按钮: ${scanButtons[0]}`);
                await page.click(`button:has-text("${scanButtons[0]}")`);
                await page.waitForTimeout(3000);
                
                // 检查页面变化
                const dialogs = await page.locator('.el-dialog').count();
                console.log('对话框数量:', dialogs);
                
                if (dialogs > 0) {
                    const dialogText = await page.locator('.el-dialog').allTextContents();
                    console.log('对话框内容:', dialogText);
                }
            }
        }
        
        // 截图保存当前状态
        await page.screenshot({ path: 'scan-interface-check.png' });
        console.log('截图保存为: scan-interface-check.png');
        
    } catch (error) {
        console.error('检查出错:', error);
    } finally {
        await page.waitForTimeout(3000);
        await browser.close();
    }
}

checkScanInterface();