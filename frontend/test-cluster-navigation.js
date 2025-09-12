const TestUtils = require('./test-utils.js');

async function testClusterNavigation() {
  const utils = new TestUtils();
  
  try {
    console.log('🧪 测试集群详情导航功能...\n');
    
    await utils.initBrowser();
    
    // 导航到集群管理页面
    console.log('📍 导航到集群管理页面');
    await utils.navigateToPage('clusters');
    await utils.waitForPageLoad();
    
    // 查找集群卡片
    console.log('🔍 查找集群卡片');
    const clusterCards = await utils.page.$$('.cluster-card');
    console.log(`找到 ${clusterCards.length} 个集群卡片`);
    
    if (clusterCards.length === 0) {
      console.log('❌ 没有找到集群卡片，可能页面结构不同');
      // 尝试查找其他可能的选择器
      const alternativeSelectors = [
        '.el-card',
        '.cluster-item',
        '[data-cluster-id]',
        'button:has-text("详情")',
        'button:has-text("进入")'
      ];
      
      for (const selector of alternativeSelectors) {
        const elements = await utils.page.$$(selector);
        console.log(`${selector}: ${elements.length} 个元素`);
      }
      
      // 截图查看页面状态
      await utils.takeScreenshot('cluster-page-debug');
      return;
    }
    
    // 测试第一个集群卡片的导航功能
    console.log('🎯 测试第一个集群的详情导航');
    const firstCard = clusterCards[0];
    
    // 方法1：测试圆形详情按钮（只有图标的按钮）
    console.log('🎯 方法1: 测试圆形详情按钮');
    const circleButton = await firstCard.$('button[circle]') || 
                        await firstCard.$('.cluster-actions button');
    
    let navigationSuccess = false;
    
    if (circleButton) {
      console.log('✅ 找到圆形详情按钮，点击测试');
      
      // 记录当前URL
      const beforeUrl = utils.page.url();
      console.log(`当前URL: ${beforeUrl}`);
      
      // 点击圆形按钮
      await circleButton.click();
      await utils.page.waitForTimeout(2000);
      
      // 检查是否跳转到详情页
      const afterUrl = utils.page.url();
      console.log(`点击后URL: ${afterUrl}`);
      
      if (afterUrl !== beforeUrl && afterUrl.includes('/clusters/')) {
        console.log('✅ 圆形按钮导航成功！');
        navigationSuccess = true;
      } else {
        console.log('❌ 圆形按钮导航失败');
      }
    } else {
      console.log('❌ 没有找到圆形详情按钮');
    }
    
    // 如果圆形按钮导航失败，尝试方法2：点击整个卡片
    if (!navigationSuccess) {
      console.log('🎯 方法2: 测试点击整个卡片');
      
      // 回到集群列表页
      await utils.navigateToPage('clusters');
      await utils.waitForPageLoad();
      
      const refreshedCards = await utils.page.$$('.cluster-card');
      if (refreshedCards.length > 0) {
        const testCard = refreshedCards[0];
        
        // 记录当前URL
        const beforeUrl = utils.page.url();
        console.log(`当前URL: ${beforeUrl}`);
        
        // 点击卡片的非按钮区域
        const cardContent = await testCard.$('.cluster-content') || testCard;
        await cardContent.click();
        await utils.page.waitForTimeout(2000);
        
        // 检查是否跳转到详情页
        const afterUrl = utils.page.url();
        console.log(`点击后URL: ${afterUrl}`);
        
        if (afterUrl !== beforeUrl && afterUrl.includes('/clusters/')) {
          console.log('✅ 卡片点击导航成功！');
          navigationSuccess = true;
        } else {
          console.log('❌ 卡片点击导航失败');
        }
      }
    }
    
    // 如果成功导航到详情页，验证页面内容
    if (navigationSuccess) {
      console.log('📋 验证集群详情页内容');
      await utils.waitForPageLoad();
      
      // 查找详情页特征元素
      const hasClusterHeader = await utils.elementExists('.cluster-header');
      const hasBackButton = await utils.elementExists('button:has-text("返回")');
      const hasClusterTitle = await utils.elementExists('h2');
      const hasStatsGrid = await utils.elementExists('.stats-grid');
      const hasTabsContent = await utils.elementExists('.el-tabs');
      
      console.log(`详情页内容验证：`);
      console.log(`- 集群头部: ${hasClusterHeader ? '✅' : '❌'}`);
      console.log(`- 返回按钮: ${hasBackButton ? '✅' : '❌'}`);
      console.log(`- 页面标题: ${hasClusterTitle ? '✅' : '❌'}`);
      console.log(`- 统计网格: ${hasStatsGrid ? '✅' : '❌'}`);
      console.log(`- 标签页内容: ${hasTabsContent ? '✅' : '❌'}`);
      
      // 测试返回功能
      if (hasBackButton) {
        console.log('🔙 测试返回功能');
        await utils.clickElement('button:has-text("返回")');
        await utils.page.waitForTimeout(2000);
        
        const returnUrl = utils.page.url();
        console.log(`返回后URL: ${returnUrl}`);
        
        if (returnUrl.includes('clusters') && !returnUrl.includes('/clusters/')) {
          console.log('✅ 返回功能正常');
        } else {
          console.log('❌ 返回功能异常');
        }
      }
    } else {
      console.log('❌ 所有导航方法都失败了');
      console.log('调试信息：查找卡片内的所有按钮');
      
      const buttons = await firstCard.$$('button');
      for (let i = 0; i < buttons.length; i++) {
        const buttonText = await buttons[i].textContent();
        const buttonClass = await buttons[i].getAttribute('class');
        console.log(`  按钮 ${i + 1}: "${buttonText}" (class: ${buttonClass})`);
      }
    }
    
    await utils.takeScreenshot('cluster-navigation-test');
    
  } catch (error) {
    console.error('💥 测试过程中出现错误:', error.message);
  } finally {
    await utils.closeBrowser();
  }
}

// 运行测试
if (require.main === module) {
  testClusterNavigation().catch(error => {
    console.error('测试运行失败:', error);
    process.exit(1);
  });
}

module.exports = testClusterNavigation;