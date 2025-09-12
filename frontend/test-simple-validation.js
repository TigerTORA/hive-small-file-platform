/**
 * 简化版验证测试 - 直接检查核心功能
 */

const puppeteer = require('playwright');
const https = require('https');
const http = require('http');

async function validateFixedIssues() {
    console.log('🔍 TDD Green阶段 - 验证所有问题已修复\n');
    
    let browser, page;
    let allTestsPassed = true;
    const issues = [];
    
    try {
        // 1. 后端API验证
        console.log('📡 测试1：后端API验证');
        try {
            const response = await fetch('http://localhost:8000/api/v1/clusters/');
            const clusters = await response.json();
            if (response.ok && Array.isArray(clusters) && clusters.length > 0) {
                console.log(`✅ 后端API正常，发现 ${clusters.length} 个集群`);
            } else {
                throw new Error('后端API异常');
            }
        } catch (error) {
            console.log(`❌ 后端API测试失败: ${error.message}`);
            issues.push('后端API不可用');
            allTestsPassed = false;
        }

        // 2. 前端代理验证  
        console.log('\n🌐 测试2：前端API代理验证');
        try {
            const response = await fetch('http://localhost:3001/api/v1/clusters/');
            const clusters = await response.json();
            if (response.ok && Array.isArray(clusters)) {
                console.log(`✅ 前端代理正常，数据传输成功`);
            } else {
                throw new Error('代理响应异常');
            }
        } catch (error) {
            console.log(`❌ 前端代理测试失败: ${error.message}`);
            issues.push('前端API代理异常');
            allTestsPassed = false;
        }

        // 3. 新增API端点验证
        console.log('\n🔧 测试3：新增API端点验证');
        
        // 测试集群连接测试端点
        try {
            const response = await fetch('http://localhost:8000/api/v1/clusters/1/test-connection?mode=mock');
            if (response.ok) {
                console.log('✅ 集群连接测试端点正常');
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.log(`❌ 集群连接测试端点失败: ${error.message}`);
            issues.push('集群连接测试API异常');
            allTestsPassed = false;
        }

        // 测试Mock扫描端点
        try {
            const response = await fetch('http://localhost:8000/api/v1/tables/scan-mock/1/default/test_table', {
                method: 'POST'
            });
            if (response.ok) {
                console.log('✅ Mock扫描端点正常');
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.log(`❌ Mock扫描端点失败: ${error.message}`);
            issues.push('Mock扫描API异常');  
            allTestsPassed = false;
        }

        // 4. 前端页面基础验证
        console.log('\n🖥️ 测试4：前端页面基础功能验证');
        
        browser = await puppeteer.chromium.launch({ headless: true });
        page = await browser.newPage();
        
        // 简单的错误监控
        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });
        
        // 访问集群管理页面
        await page.goto('http://localhost:3001/#/clusters', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        
        // 检查页面是否加载成功
        const title = await page.title();
        if (title && !title.includes('Error')) {
            console.log('✅ 集群管理页面加载成功');
        } else {
            console.log('❌ 页面标题异常:', title);
            allTestsPassed = false;
        }
        
        // 检查是否有严重的JavaScript错误
        const criticalErrors = errors.filter(err => 
            err.includes('Failed to load resource') && 
            err.includes('api')
        );
        
        if (criticalErrors.length === 0) {
            console.log('✅ 前端页面无严重API错误');
        } else {
            console.log('❌ 发现前端API错误:', criticalErrors.length);
            issues.push('前端页面API调用异常');
            allTestsPassed = false;
        }

    } catch (error) {
        console.log('❌ 验证测试执行异常:', error.message);
        allTestsPassed = false;
    } finally {
        if (browser) {
            await browser.close();
        }
    }
    
    // 生成最终报告
    console.log('\n📊 TDD验证报告');
    console.log('='.repeat(50));
    
    if (allTestsPassed) {
        console.log('🎉 所有测试通过！修复成功！');
        console.log('✅ 用户报告的问题已全部解决');
        console.log('✅ 进入TDD Green阶段 - 可以继续重构优化');
        return true;
    } else {
        console.log('❌ 仍有问题需要修复:');
        issues.forEach((issue, index) => {
            console.log(`${index + 1}. ${issue}`);
        });
        console.log('⚠️ 需要继续修复才能进入Green阶段');
        return false;
    }
}

// 执行验证
if (require.main === module) {
    validateFixedIssues().then(success => {
        process.exit(success ? 0 : 1);
    }).catch(error => {
        console.error('验证执行失败:', error);
        process.exit(2);
    });
}

module.exports = { validateFixedIssues };