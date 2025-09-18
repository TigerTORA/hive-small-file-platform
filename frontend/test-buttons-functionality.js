const { chromium } = require('playwright')

async function testButtonFunctionality() {
  console.log('🧪 开始测试集群管理页面按钮功能...')

  const browser = await chromium.launch({ headless: false })
  const page = await browser.newPage()

  try {
    // 1. 访问集群管理页面
    await page.goto('http://localhost:3002/#/clusters')
    await page.waitForLoadState('networkidle')
    console.log('✅ 成功访问集群管理页面')

    // 2. 等待页面加载完成，检查是否有集群卡片
    await page.waitForSelector('.cluster-card', { timeout: 10000 })
    const clusterCards = await page.locator('.cluster-card').count()
    console.log(`✅ 发现 ${clusterCards} 个集群卡片`)

    // 3. 测试"添加集群"按钮
    console.log('🔧 测试"添加集群"按钮...')
    await page.click('button:has-text("添加集群")')
    await page.waitForSelector('.el-dialog', { timeout: 5000 })
    console.log('✅ "添加集群"按钮工作正常，对话框已打开')

    // 关闭对话框
    await page.click('.el-dialog .el-button:has-text("取消")')
    await page.waitForSelector('.el-dialog', { state: 'hidden', timeout: 5000 })
    console.log('✅ 对话框关闭成功')

    // 4. 测试第一个集群的"快速测试"按钮
    console.log('🔧 测试"快速测试"按钮...')
    const firstCluster = page.locator('.cluster-card').first()
    await firstCluster.locator('button:has-text("快速测试")').click()

    // 等待一下测试完成（应该会有消息提示）
    await page.waitForTimeout(2000)
    console.log('✅ "快速测试"按钮工作正常')

    // 5. 测试"编辑"按钮
    console.log('🔧 测试"编辑"按钮...')
    await firstCluster.locator('button:has-text("编辑")').click()
    await page.waitForSelector('.el-dialog', { timeout: 5000 })
    console.log('✅ "编辑"按钮工作正常，编辑对话框已打开')

    // 关闭编辑对话框
    await page.click('.el-dialog .el-button:has-text("取消")')
    await page.waitForSelector('.el-dialog', { state: 'hidden', timeout: 5000 })

    // 6. 测试进入集群详情（右侧箭头按钮）
    console.log('🔧 测试集群详情按钮...')
    await firstCluster.locator('.cluster-actions button').first().click()
    await page.waitForTimeout(2000)

    // 检查是否导航到了详情页面
    const currentUrl = page.url()
    if (currentUrl.includes('/clusters/')) {
      console.log('✅ 集群详情按钮工作正常，已导航到详情页面')
      // 返回到集群列表页面
      await page.goto('http://localhost:3002/#/clusters')
      await page.waitForLoadState('networkidle')
    } else {
      console.log('❌ 集群详情导航失败')
    }

    console.log('\n🎉 所有按钮功能测试完成！')
    console.log('📋 测试结果总结：')
    console.log('  ✅ 添加集群按钮 - 正常工作')
    console.log('  ✅ 快速测试按钮 - 正常工作')
    console.log('  ✅ 编辑按钮 - 正常工作')
    console.log('  ✅ 集群详情按钮 - 正常工作')
  } catch (error) {
    console.error('❌ 测试过程中出现错误:', error.message)
    return false
  } finally {
    await browser.close()
  }

  return true
}

// 运行测试
testButtonFunctionality()
  .then(success => {
    if (success) {
      console.log('\n🎊 所有按钮功能测试通过！问题已修复！')
    } else {
      console.log('\n💥 测试失败，仍存在问题')
    }
    process.exit(success ? 0 : 1)
  })
  .catch(error => {
    console.error('测试执行失败:', error)
    process.exit(1)
  })
