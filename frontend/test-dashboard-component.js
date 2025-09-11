const { chromium } = require('playwright')

async function testDashboardComponent() {
  console.log('🔍 开始诊断 TestDashboard.vue 组件加载问题...')
  
  const browser = await chromium.launch({ 
    headless: false,
    devtools: true 
  })
  
  const context = await browser.newContext()
  const page = await context.newPage()
  
  // 监听所有console消息
  page.on('console', (msg) => {
    console.log(`🖥️  浏览器控制台 [${msg.type()}]:`, msg.text())
  })
  
  // 监听页面错误
  page.on('pageerror', (error) => {
    console.error('❌ 页面错误:', error.message)
  })
  
  // 监听网络请求错误
  page.on('response', (response) => {
    if (!response.ok()) {
      console.error(`🌐 网络请求失败: ${response.url()} - ${response.status()}`)
    }
  })
  
  try {
    console.log('📱 访问测试仪表板页面...')
    await page.goto('http://localhost:3002/#/test-dashboard', { 
      waitUntil: 'networkidle',
      timeout: 10000 
    })
    
    // 等待页面完全加载
    await page.waitForTimeout(3000)
    
    // 检查页面基本结构
    console.log('\n🔍 检查页面基本结构...')
    
    // 检查是否有路由视图
    const routerView = await page.locator('router-view, .test-dashboard').count()
    console.log(`✅ Router View 存在: ${routerView > 0 ? '是' : '否'}`)
    
    // 检查测试仪表板根元素
    const dashboardRoot = await page.locator('.test-dashboard').count()
    console.log(`✅ TestDashboard 根元素存在: ${dashboardRoot > 0 ? '是' : '否'}`)
    
    // 检查页面标题
    const pageTitle = await page.locator('.page-title').textContent().catch(() => null)
    console.log(`✅ 页面标题: ${pageTitle || '未找到'}`)
    
    // 检查概览卡片
    const overviewCards = await page.locator('.overview-card').count()
    console.log(`✅ 概览卡片数量: ${overviewCards}`)
    
    // 检查测试分类
    const categoryCards = await page.locator('.category-card').count()
    console.log(`✅ 测试分类卡片数量: ${categoryCards}`)
    
    // 检查表格
    const tableRows = await page.locator('.el-table__row').count()
    console.log(`✅ 测试结果表格行数: ${tableRows}`)
    
    // 检查是否有加载状态
    const isLoading = await page.locator('.el-loading-mask').count()
    console.log(`✅ 加载状态: ${isLoading > 0 ? '显示' : '未显示'}`)
    
    // 检查API调用情况
    console.log('\n🌐 检查API调用情况...')
    
    // 尝试手动触发API调用
    const refreshButton = await page.locator('button:has-text("刷新数据")').first()
    if (await refreshButton.count() > 0) {
      console.log('🔄 点击刷新按钮测试API调用...')
      await refreshButton.click()
      await page.waitForTimeout(2000)
    }
    
    // 检查数据内容
    console.log('\n📊 检查数据内容...')
    
    const totalTests = await page.locator('.overview-card h3').first().textContent().catch(() => '0')
    console.log(`📈 总测试数: ${totalTests}`)
    
    // 检查控制台是否有Vue相关错误
    console.log('\n🔍 检查Vue组件状态...')
    
    const vueAppExists = await page.evaluate(() => {
      return window.__VUE__ !== undefined || document.querySelector('#app').__vue__ !== undefined
    }).catch(() => false)
    console.log(`✅ Vue应用状态: ${vueAppExists ? '正常' : '异常'}`)
    
    // 检查Element Plus组件是否正常加载
    const elementPlusLoaded = await page.evaluate(() => {
      return window.ElementPlus !== undefined
    }).catch(() => false)
    console.log(`✅ Element Plus加载状态: ${elementPlusLoaded ? '正常' : '异常'}`)
    
    // 检查路由状态
    const currentRoute = await page.evaluate(() => {
      return window.location.hash
    })
    console.log(`🛣️  当前路由: ${currentRoute}`)
    
    // 截图保存
    await page.screenshot({ 
      path: '/Users/luohu/new_project/hive-small-file-platform/frontend/test-dashboard-debug.png',
      fullPage: true
    })
    console.log('📸 已保存页面截图: test-dashboard-debug.png')
    
    // 检查组件内部状态
    const componentState = await page.evaluate(() => {
      const app = document.querySelector('#app')
      if (app && app.__vue_app__) {
        return {
          appExists: true,
          routerExists: !!app.__vue_app__.config.globalProperties.$router,
          routeExists: !!app.__vue_app__.config.globalProperties.$route
        }
      }
      return { appExists: false }
    }).catch(() => ({ appExists: false }))
    
    console.log('🔧 Vue应用内部状态:', componentState)
    
    console.log('\n✅ 诊断完成!')
    
  } catch (error) {
    console.error('❌ 测试过程中出现错误:', error.message)
  } finally {
    await browser.close()
  }
}

testDashboardComponent().catch(console.error)