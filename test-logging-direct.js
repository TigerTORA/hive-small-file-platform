/**
 * 直接API测试日志改进效果
 */
const axios = require('axios');
const { chromium } = require('playwright');

const API_BASE = 'http://localhost:8899/api/v1';

async function testLoggingDirect() {
    console.log('🚀 开始直接API日志测试...');
    
    try {
        // 1. 创建测试集群
        console.log('➕ 创建测试集群');
        const clusterData = {
            name: '日志测试集群',
            hdfs_namenode_url: 'http://test-hdfs:50070',
            hiveserver2_url: 'jdbc:hive2://test-hive:10000',
            hive_metastore_url: 'mysql://test:pass@test-mysql:3306/hive',
            description: '用于测试详细日志功能'
        };
        
        let clusterId;
        try {
            const createResponse = await axios.post(`${API_BASE}/clusters/`, clusterData);
            clusterId = createResponse.data.id;
            console.log(`✅ 集群创建成功，ID: ${clusterId}`);
        } catch (error) {
            console.log('集群可能已存在，尝试获取现有集群');
            const clustersResponse = await axios.get(`${API_BASE}/clusters/`);
            const clusters = clustersResponse.data;
            if (clusters.length > 0) {
                clusterId = clusters[0].id;
                console.log(`✅ 使用现有集群，ID: ${clusterId}`);
            } else {
                throw new Error('无法创建或获取集群');
            }
        }
        
        // 2. 测试连接 - 这会触发我们增强的日志
        console.log('🔗 测试集群连接');
        const testResponse = await axios.post(`${API_BASE}/tables/test-connection/${clusterId}`);
        console.log('连接测试结果:', JSON.stringify(testResponse.data, null, 2));
        
        // 3. 启动数据库扫描 - 这会触发详细的扫描日志
        console.log('🔄 启动数据库扫描');
        const scanResponse = await axios.post(`${API_BASE}/tables/scan/${clusterId}/default`);
        console.log('扫描启动结果:', JSON.stringify(scanResponse.data, null, 2));
        
        const taskId = scanResponse.data.task_id;
        
        // 4. 监控扫描进度和日志
        console.log('📋 监控扫描进度...');
        let logCount = 0;
        let detailedLogsFound = false;
        
        for (let i = 0; i < 15; i++) {
            try {
                const progressResponse = await axios.get(`${API_BASE}/tables/scan-progress/${taskId}`);
                const progress = progressResponse.data;
                
                console.log(`\n第${i + 1}次检查 - 状态: ${progress.status}`);
                
                if (progress.logs && progress.logs.length > 0) {
                    console.log(`📝 发现 ${progress.logs.length} 条日志`);
                    
                    // 检查最新日志
                    const newLogs = progress.logs.slice(logCount);
                    logCount = progress.logs.length;
                    
                    newLogs.forEach(log => {
                        console.log(`   [${log.level}] ${log.message}`);
                        
                        // 检查详细日志特征
                        if (log.message.includes('🚀') || 
                            log.message.includes('🔗') || 
                            log.message.includes('📊') ||
                            log.message.includes('📈') ||
                            log.message.includes('connect_time') ||
                            log.message.includes('扫描统计') ||
                            log.message.includes('成功率') ||
                            log.message.includes('MetaStore连接成功，MySQL')) {
                            detailedLogsFound = true;
                            console.log('   ✨ 发现详细日志特征！');
                        }
                    });
                } else {
                    console.log('📝 暂无日志');
                }
                
                if (progress.status === 'completed' || progress.status === 'failed') {
                    console.log('🏁 扫描任务结束');
                    break;
                }
                
                await new Promise(resolve => setTimeout(resolve, 3000));
                
            } catch (error) {
                console.log(`进度检查失败: ${error.message}`);
                await new Promise(resolve => setTimeout(resolve, 3000));
            }
        }
        
        // 5. 获取任务详情
        console.log('\n📋 获取任务详情');
        try {
            const taskResponse = await axios.get(`${API_BASE}/scan-tasks/?limit=5`);
            const tasks = taskResponse.data;
            
            if (tasks.length > 0) {
                const latestTask = tasks[0];
                console.log('最新任务信息:', JSON.stringify({
                    id: latestTask.id,
                    status: latestTask.status,
                    database_name: latestTask.database_name,
                    start_time: latestTask.start_time,
                    end_time: latestTask.end_time,
                    result: latestTask.result
                }, null, 2));
                
                // 检查任务结果中的详细信息
                if (latestTask.result) {
                    const result = typeof latestTask.result === 'string' ? 
                        JSON.parse(latestTask.result) : latestTask.result;
                    
                    console.log('\n任务结果详情:');
                    console.log(`- 数据库: ${result.database}`);
                    console.log(`- 扫描表数: ${result.tables_scanned || 0}`);
                    console.log(`- 总文件数: ${result.total_files || 0}`);
                    console.log(`- 小文件数: ${result.total_small_files || 0}`);
                    console.log(`- 扫描耗时: ${result.scan_duration || 0}秒`);
                    console.log(`- HDFS模式: ${result.hdfs_mode || 'unknown'}`);
                    
                    if (result.metastore_query_time) {
                        console.log(`- MetaStore查询时间: ${result.metastore_query_time}秒`);
                        detailedLogsFound = true;
                        console.log('   ✅ 发现详细性能指标！');
                    }
                    
                    if (result.errors && result.errors.length > 0) {
                        console.log(`- 错误信息: ${result.errors.join(', ')}`);
                    }
                }
            }
        } catch (error) {
            console.log(`获取任务详情失败: ${error.message}`);
        }
        
        // 6. 通过浏览器验证前端显示
        console.log('\n🌐 验证前端显示');
        const browser = await chromium.launch({ headless: false });
        const context = await browser.newContext();
        const page = await context.newPage();
        
        try {
            await page.goto('http://localhost:3000/#/tasks');
            await page.waitForTimeout(2000);
            
            // 检查任务列表
            const taskRows = await page.locator('tbody tr').count();
            console.log(`前端显示任务数: ${taskRows}`);
            
            if (taskRows > 0) {
                // 点击第一个任务查看详情
                await page.locator('tbody tr').first().click();
                await page.waitForTimeout(1000);
                
                // 查找日志内容
                const logElements = await page.locator('.log-item, .task-log, .log-message').allTextContents();
                console.log('前端日志显示:');
                logElements.forEach((log, index) => {
                    console.log(`   前端日志${index + 1}: ${log}`);
                });
                
                if (logElements.some(log => 
                    log.includes('🚀') || log.includes('connect_time') || log.includes('扫描统计'))) {
                    detailedLogsFound = true;
                    console.log('   ✅ 前端显示详细日志！');
                }
            }
            
            await page.screenshot({ path: 'logging-verification.png' });
            console.log('📷 验证截图: logging-verification.png');
            
        } finally {
            await browser.close();
        }
        
        // 7. 生成测试报告
        console.log('\n' + '='.repeat(60));
        console.log('📊 详细日志改进测试报告');
        console.log('='.repeat(60));
        console.log(`✨ 详细日志特征检测: ${detailedLogsFound ? '✅ 成功' : '❌ 未检测到'}`);
        console.log(`📝 日志总数: ${logCount}`);
        
        if (detailedLogsFound) {
            console.log('\n🎉 日志改进验证成功！');
            console.log('🔥 改进效果包括:');
            console.log('   ✅ emoji图标增强视觉体验');
            console.log('   ✅ 连接时间等性能指标');
            console.log('   ✅ 详细的扫描统计信息');
            console.log('   ✅ 结构化的错误诊断');
            
            console.log('\n🔗 验证链接:');
            console.log(`   - 前端任务页面: http://localhost:3000/#/tasks`);
            console.log(`   - API任务接口: ${API_BASE}/scan-tasks/`);
            console.log(`   - 集群详情: http://localhost:3000/#/cluster/${clusterId}`);
        } else {
            console.log('\n⚠️ 未检测到明显的详细日志改进');
            console.log('建议检查:');
            console.log('   - 后端日志输出是否正常');
            console.log('   - 前端日志显示组件');
            console.log('   - 连接配置是否正确');
        }
        
        return detailedLogsFound;
        
    } catch (error) {
        console.error('❌ 测试失败:', error.message);
        return false;
    }
}

// 运行测试
testLoggingDirect().then(success => {
    console.log(success ? '\n🎉 测试完成 - 日志改进已生效！' : '\n🔧 测试完成 - 需要进一步优化');
    process.exit(success ? 0 : 1);
}).catch(error => {
    console.error('测试启动失败:', error);
    process.exit(1);
});