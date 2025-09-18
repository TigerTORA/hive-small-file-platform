const { chromium } = require('playwright')

async function testClusterInterface() {
  console.log('开始测试新的集群界面...')

  const browser = await chromium.launch({ headless: false })
  const context = await browser.newContext()
  const page = await context.newPage()

  try {
    // 1. 测试首页重定向到集群管理
    console.log('1. 测试首页重定向...')
    await page.goto('http://localhost:3002/')
    await page.waitForLoadState('networkidle')

    const url = page.url()
    console.log('当前URL:', url)

    if (url.includes('/clusters')) {
      console.log('✅ 首页成功重定向到集群管理页面')
    } else {
      console.log('❌ 首页重定向失败')
      return
    }

    // 2. 测试集群管理页面加载
    console.log('2. 测试集群管理页面...')
    await page.waitForSelector('.clusters-management', { timeout: 10000 })
    console.log('✅ 集群管理页面加载成功')

    // 3. 检查页面基本元素
    const hasHeader = (await page.locator('h2:has-text("集群管理")').count()) > 0
    console.log(hasHeader ? '✅ 页面标题正确' : '❌ 页面标题缺失')

    const hasStats = (await page.locator('.stats-overview').count()) > 0
    console.log(hasStats ? '✅ 统计卡片显示正常' : '❌ 统计卡片缺失')

    const hasSearch = (await page.locator('input[placeholder*="搜索"]').count()) > 0
    console.log(hasSearch ? '✅ 搜索框显示正常' : '❌ 搜索框缺失')

    // 4. 测试集群卡片点击
    console.log('4. 测试集群详情导航...')
    const clusterCards = await page.locator('.cluster-card').count()
    console.log(`发现 ${clusterCards} 个集群卡片`)

    if (clusterCards > 0) {
      // 点击第一个集群卡片
      await page.locator('.cluster-card .card-actions button:has-text("详情")').first().click()
      await page.waitForLoadState('networkidle', { timeout: 5000 })

      const detailUrl = page.url()
      console.log('详情页URL:', detailUrl)

      if (detailUrl.includes('/clusters/') && detailUrl.split('/').length >= 5) {
        console.log('✅ 成功导航到集群详情页面')

        // 检查集群详情页面元素
        await page.waitForSelector('.cluster-detail', { timeout: 5000 })

        const hasBackButton = (await page.locator('button:has-text("返回集群列表")').count()) > 0
        console.log(hasBackButton ? '✅ 返回按钮显示正常' : '❌ 返回按钮缺失')

        const hasTabs = (await page.locator('.el-tabs').count()) > 0
        console.log(hasTabs ? '✅ 标签页显示正常' : '❌ 标签页缺失')

        // 测试返回功能
        if (hasBackButton) {
          await page.locator('button:has-text("返回集群列表")').click()
          await page.waitForLoadState('networkidle')

          const backUrl = page.url()
          if (backUrl.includes('/clusters') && !backUrl.includes('/clusters/')) {
            console.log('✅ 返回集群列表功能正常')
          } else {
            console.log('❌ 返回功能异常')
          }
        }
      } else {
        console.log('❌ 集群详情页面导航失败')
      }
    } else {
      console.log('⚠️  没有找到集群卡片，可能需要先添加集群数据')
    }

    console.log('\n🎉 新集群界面测试完成！')
  } catch (error) {
    console.error('❌ 测试过程中出现错误:', error.message)
  } finally {
    await browser.close()
  }
}

// 运行测试
testClusterInterface().catch(console.error)
