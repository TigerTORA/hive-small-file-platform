/**
 * 详细日志测试 - 验证数据库扫描进度日志改进效果
 * 测试我们对 ScanService, HybridTableScanner, MySQLHiveMetastoreConnector 的日志增强
 */
const { chromium } = require('playwright');

async function testDetailedLogging() {
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext();
    const page = await context.newPage();

    console.log('🚀 开始详细日志测试...');
    
    try {
        // 1. 导航到集群管理页面
        console.log('📂 导航到集群管理页面');
        await page.goto('http://localhost:3000');
        await page.waitForTimeout(2000);
        
        // 2. 检查现有集群或创建测试集群
        const clusterExists = await page.locator('text=测试集群').isVisible().catch(() => false);
        let clusterId = 1;
        
        if (!clusterExists) {
            console.log('➕ 创建测试集群');
            await page.click('button:has-text("添加集群")');
            await page.waitForSelector('input[placeholder*="集群名称"]');
            
            await page.fill('input[placeholder*="集群名称"]', '详细日志测试集群');
            await page.fill('input[placeholder*="HDFS"]', 'http://test-hdfs:50070');
            await page.fill('input[placeholder*="HiveServer2"]', 'jdbc:hive2://test-hive:10000');
            await page.fill('input[placeholder*="MetaStore"]', 'mysql://test:pass@test-mysql:3306/hive');
            
            await page.click('button:has-text("保存")');
            await page.waitForTimeout(1000);
            
            // 获取新创建的集群ID
            const clusterRow = await page.locator('tr').filter({ hasText: '详细日志测试集群' }).first();
            if (await clusterRow.isVisible()) {
                clusterId = await clusterRow.getAttribute('data-cluster-id') || '1';
            }
        }
        
        // 3. 进入集群详情页面
        console.log('🔍 进入集群详情页面');
        await page.click(`tr:has-text("详细日志测试集群"), tr:has-text("测试集群")`);
        await page.waitForTimeout(2000);
        
        // 4. 启动全量数据库扫描
        console.log('🔄 启动全量数据库扫描');
        await page.click('button:has-text("扫描所有数据库")');
        
        // 等待扫描开始
        await page.waitForTimeout(2000);
        
        // 5. 实时监控日志输出 - 这是关键测试点
        console.log('📋 监控扫描进度日志...');
        
        let logCheckCount = 0;
        let detailedLogsFound = false;
        let logMessages = [];
        
        // 检查20次，每次间隔3秒
        while (logCheckCount < 20 && !detailedLogsFound) {
            try {
                // 查找进度对话框或日志区域
                const progressDialog = page.locator('.el-dialog:has-text("扫描进度")');
                const isProgressVisible = await progressDialog.isVisible().catch(() => false);
                
                if (isProgressVisible) {
                    // 提取所有日志消息
                    const logs = await page.locator('.log-item, .scan-log, .progress-log').allTextContents();
                    logMessages.push(...logs);
                    
                    console.log(`第${logCheckCount + 1}次检查 - 发现${logs.length}条日志`);
                    
                    // 检查是否包含我们增强的详细日志特征
                    const hasDetailedLogs = logs.some(log => 
                        log.includes('🚀 开始扫描集群') ||
                        log.includes('🔗 正在连接MetaStore') ||
                        log.includes('📊 正在获取数据库列表') ||
                        log.includes('📈 扫描统计') ||
                        log.includes('MetaStore连接成功，MySQL') ||
                        log.includes('connect_time') ||
                        log.includes('database_query_time') ||
                        log.includes('耗时') && log.includes('秒') ||
                        log.includes('成功率') ||
                        log.includes('个表')
                    );
                    
                    if (hasDetailedLogs) {
                        detailedLogsFound = true;
                        console.log('✅ 发现详细日志特征！');
                        logs.forEach((log, index) => {
                            console.log(`   日志${index + 1}: ${log}`);
                        });
                        break;
                    }
                    
                    // 显示当前日志内容
                    if (logs.length > 0) {
                        console.log('当前日志内容:');
                        logs.slice(-5).forEach(log => console.log(`   - ${log}`));
                    }
                }
                
                logCheckCount++;
                await page.waitForTimeout(3000);
                
            } catch (error) {
                console.log(`日志检查出错: ${error.message}`);
                logCheckCount++;
                await page.waitForTimeout(3000);
            }
        }
        
        // 6. 检查任务日志页面
        console.log('📋 检查任务日志页面');
        await page.click('button:has-text("查看任务"), a:has-text("任务"), .nav-link:has-text("任务")').catch(() => {
            console.log('未找到任务按钮，尝试直接访问任务页面');
        });
        
        // 尝试直接导航到任务页面
        await page.goto('http://localhost:3000/#/tasks');
        await page.waitForTimeout(2000);
        
        // 查找最新的扫描任务
        const taskRows = await page.locator('tr').all();
        for (let row of taskRows.slice(0, 3)) { // 检查前3行
            const rowText = await row.textContent();
            if (rowText && rowText.includes('扫描')) {
                console.log('🔍 检查任务详情');
                await row.click();
                await page.waitForTimeout(1000);
                
                // 查看任务日志
                const taskLogs = await page.locator('.task-log, .log-content, .log-detail').allTextContents();
                if (taskLogs.length > 0) {
                    console.log('任务日志内容:');
                    taskLogs.forEach((log, index) => {
                        console.log(`   任务日志${index + 1}: ${log}`);
                    });
                    
                    // 检查任务日志是否包含详细信息
                    const hasDetailedTaskLogs = taskLogs.some(log => 
                        log.includes('连接时间') ||
                        log.includes('查询时间') ||
                        log.includes('扫描统计') ||
                        log.includes('成功率') ||
                        log.includes('MySQL') ||
                        log.includes('🚀') || log.includes('🔗') || log.includes('📊')
                    );
                    
                    if (hasDetailedTaskLogs) {
                        detailedLogsFound = true;
                        console.log('✅ 在任务日志中发现详细日志！');
                    }
                }
                break;
            }
        }
        
        // 7. 生成测试报告
        console.log('\n' + '='.repeat(50));
        console.log('📊 详细日志测试结果报告');
        console.log('='.repeat(50));
        console.log(`✨ 日志检查次数: ${logCheckCount}`);
        console.log(`📝 收集到的日志总数: ${logMessages.length}`);
        console.log(`🎯 发现详细日志特征: ${detailedLogsFound ? '是' : '否'}`);
        
        if (detailedLogsFound) {
            console.log('\n✅ 测试成功！日志改进已生效');
            console.log('🔥 改进特征包括:');
            console.log('   - emoji 图标增强视觉效果');
            console.log('   - 连接时间和性能指标');
            console.log('   - 详细的扫描统计信息');
            console.log('   - 具体的错误诊断和建议');
        } else {
            console.log('\n⚠️ 注意：未检测到明显的详细日志特征');
            console.log('可能原因:');
            console.log('   - 连接失败导致日志较少');
            console.log('   - 日志显示组件尚未更新');
            console.log('   - 需要检查后端日志输出');
        }
        
        if (logMessages.length > 0) {
            console.log('\n📄 完整日志记录:');
            logMessages.forEach((msg, index) => {
                console.log(`   ${index + 1}. ${msg}`);
            });
        }
        
        // 截图保存证据
        await page.screenshot({ path: 'detailed-logging-test.png' });
        console.log('\n📷 测试截图已保存为: detailed-logging-test.png');
        
        return detailedLogsFound;
        
    } catch (error) {
        console.error('❌ 测试过程中发生错误:', error);
        return false;
    } finally {
        await page.waitForTimeout(2000);
        await browser.close();
    }
}

// 运行测试
testDetailedLogging().then(success => {
    if (success) {
        console.log('\n🎉 详细日志功能测试通过！');
        console.log('🔗 验证链接: http://localhost:3000 (集群详情页面)');
        console.log('🔗 任务日志页面: http://localhost:3000/#/tasks');
    } else {
        console.log('\n🔧 需要进一步检查日志实现');
    }
    process.exit(success ? 0 : 1);
}).catch(error => {
    console.error('测试启动失败:', error);
    process.exit(1);
});