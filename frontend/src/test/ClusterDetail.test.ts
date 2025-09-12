/**
 * ClusterDetail.vue 组件单元测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ClusterDetail from '@/views/ClusterDetail.vue'
import { clustersApi } from '@/api/clusters'
import { tablesApi } from '@/api/tables'
import { tasksApi } from '@/api/tasks'

// Mock APIs
vi.mock('@/api/clusters', () => ({
  clustersApi: {
    get: vi.fn()
  }
}))

vi.mock('@/api/tables', () => ({
  tablesApi: {
    getTableMetrics: vi.fn(),
    getDatabases: vi.fn(),
    scanAllDatabases: vi.fn()
  }
}))

vi.mock('@/api/tasks', () => ({
  tasksApi: {
    getByCluster: vi.fn(),
    createSmart: vi.fn()
  }
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn()
  },
  ElMessageBox: {
    confirm: vi.fn()
  }
}))

// Mock child components
vi.mock('@/components/TablesView.vue', () => ({
  default: {
    name: 'TablesView',
    template: '<div class="tables-view-mock">TablesView Component</div>',
    props: ['clusterId']
  }
}))

vi.mock('@/components/TasksView.vue', () => ({
  default: {
    name: 'TasksView', 
    template: '<div class="tasks-view-mock">TasksView Component</div>',
    props: ['clusterId']
  }
}))

// Mock router
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/clusters', component: { template: '<div>Clusters</div>' } },
    { path: '/cluster/:id', component: ClusterDetail }
  ]
})

describe('ClusterDetail.vue', () => {
  let wrapper: VueWrapper<any>

  const mockCluster = {
    id: 1,
    name: 'production-cluster',
    description: '生产环境集群',
    hive_metastore_url: 'mysql://user:pass@prod-db:3306/hive',
    hdfs_namenode_url: 'hdfs://prod-namenode:9000',
    connection_type: 'mysql',
    created_time: '2023-01-01T00:00:00Z',
    updated_time: '2023-01-01T00:00:00Z'
  }

  const mockTables = {
    items: [
      {
        id: 1,
        database_name: 'default',
        table_name: 'test_table',
        file_count: 100,
        small_file_count: 50,
        total_size: 1024 * 1024 * 1024,
        last_scan_time: '2023-01-01T12:00:00Z'
      }
    ],
    total: 1
  }

  const mockTasks = [
    {
      id: 1,
      cluster_id: 1,
      task_name: 'Smart merge for test_table',
      table_name: 'test_table',
      database_name: 'default',
      merge_strategy: 'safe_merge',
      status: 'pending',
      created_time: '2023-01-01T10:00:00Z'
    }
  ]

  beforeEach(async () => {
    // Reset mocks
    vi.clearAllMocks()
    
    // Mock successful API responses
    vi.mocked(clustersApi.get).mockResolvedValue(mockCluster)
    vi.mocked(tablesApi.getTableMetrics).mockResolvedValue(mockTables)
    vi.mocked(tablesApi.getDatabases).mockResolvedValue(['default', 'test_db'])
    vi.mocked(tasksApi.getByCluster).mockResolvedValue(mockTasks)
    
    // Set up router with cluster ID parameter
    await router.push('/cluster/1')
    
    wrapper = mount(ClusterDetail, {
      global: {
        plugins: [router]
      }
    })
    
    await nextTick()
  })

  afterEach(() => {
    wrapper.unmount()
  })

  describe('组件初始化', () => {
    it('应该正确渲染页面标题和导航', () => {
      expect(wrapper.find('.page-header h1').text()).toBe('production-cluster')
      expect(wrapper.find('.back-button').exists()).toBe(true)
    })

    it('应该显示集群基本信息', () => {
      const infoItems = wrapper.findAll('.cluster-info-item')
      expect(infoItems.length).toBeGreaterThan(0)
      
      const nameItem = infoItems.find(item => 
        item.find('.info-label').text() === '集群名称'
      )
      expect(nameItem?.find('.info-value').text()).toBe('production-cluster')
    })

    it('应该在组件挂载时加载集群数据', () => {
      expect(clustersApi.get).toHaveBeenCalledWith(1)
    })

    it('应该显示标签页导航', () => {
      const tabs = wrapper.findAll('.el-tabs__item')
      expect(tabs.length).toBe(4)
      
      const tabTexts = tabs.map(tab => tab.text())
      expect(tabTexts).toContain('表管理')
      expect(tabTexts).toContain('任务管理')  
      expect(tabTexts).toContain('小文件分析')
      expect(tabTexts).toContain('集群设置')
    })
  })

  describe('标签页切换', () => {
    it('应该正确切换到表管理标签页', async () => {
      const tablesTab = wrapper.find('[data-test="tables-tab"]')
      await tablesTab.trigger('click')
      
      expect(wrapper.vm.activeTab).toBe('tables')
      expect(wrapper.find('.tables-view-mock').exists()).toBe(true)
    })

    it('应该正确切换到任务管理标签页', async () => {
      const tasksTab = wrapper.find('[data-test="tasks-tab"]')
      await tasksTab.trigger('click')
      
      expect(wrapper.vm.activeTab).toBe('tasks')
      expect(wrapper.find('.tasks-view-mock').exists()).toBe(true)
    })

    it('应该正确切换到小文件分析标签页', async () => {
      const analysisTab = wrapper.find('[data-test="analysis-tab"]')
      await analysisTab.trigger('click')
      
      expect(wrapper.vm.activeTab).toBe('analysis')
    })

    it('应该正确切换到集群设置标签页', async () => {
      const settingsTab = wrapper.find('[data-test="settings-tab"]')
      await settingsTab.trigger('click')
      
      expect(wrapper.vm.activeTab).toBe('settings')
    })
  })

  describe('集群概览统计', () => {
    beforeEach(async () => {
      // 切换到概览标签页
      wrapper.vm.activeTab = 'overview'
      await nextTick()
    })

    it('应该显示表统计信息', () => {
      const statCards = wrapper.findAll('.stat-card')
      expect(statCards.length).toBeGreaterThan(0)
      
      const totalTablesCard = statCards.find(card => 
        card.find('.stat-label').text().includes('总表数')
      )
      expect(totalTablesCard).toBeTruthy()
    })

    it('应该显示小文件统计', () => {
      const smallFilesCard = wrapper.find('[data-test="small-files-stat"]')
      expect(smallFilesCard.exists()).toBe(true)
    })

    it('应该显示任务统计', () => {
      const tasksCard = wrapper.find('[data-test="tasks-stat"]')
      expect(tasksCard.exists()).toBe(true)
    })
  })

  describe('快速操作', () => {
    it('应该提供批量扫描功能', async () => {
      vi.mocked(tablesApi.scanAllDatabases).mockResolvedValue({
        success: true,
        message: '扫描已启动'
      })

      const scanButton = wrapper.find('[data-test="scan-all-btn"]')
      await scanButton.trigger('click')
      
      expect(tablesApi.scanAllDatabases).toHaveBeenCalledWith(1)
    })

    it('应该提供刷新数据功能', async () => {
      const refreshButton = wrapper.find('[data-test="refresh-btn"]')
      await refreshButton.trigger('click')
      
      expect(clustersApi.get).toHaveBeenCalledTimes(2) // 初始加载 + 刷新
    })

    it('应该能够创建智能任务', async () => {
      vi.mocked(tasksApi.createSmart).mockResolvedValue({
        task: {
          id: 2,
          task_name: 'Smart merge task',
          cluster_id: 1,
          status: 'pending'
        },
        strategy_info: {
          recommended_strategy: 'safe_merge',
          strategy_reason: '推荐安全合并策略',
          validation: { valid: true, warnings: [] }
        }
      })

      const smartTaskButton = wrapper.find('[data-test="create-smart-task-btn"]')
      await smartTaskButton.trigger('click')
      
      // 验证是否打开了智能任务对话框
      expect(wrapper.vm.showSmartTaskDialog).toBe(true)
    })
  })

  describe('返回导航', () => {
    it('应该能够返回集群列表', async () => {
      const pushSpy = vi.spyOn(router, 'push')
      
      const backButton = wrapper.find('.back-button')
      await backButton.trigger('click')
      
      expect(pushSpy).toHaveBeenCalledWith('/clusters')
    })

    it('应该显示面包屑导航', () => {
      const breadcrumb = wrapper.find('.breadcrumb')
      expect(breadcrumb.exists()).toBe(true)
      
      const links = breadcrumb.findAll('a')
      expect(links[0].text()).toBe('集群管理')
      expect(links[1].text()).toBe('production-cluster')
    })
  })

  describe('错误处理', () => {
    it('应该处理集群加载失败', async () => {
      vi.mocked(clustersApi.get).mockRejectedValue(new Error('Cluster not found'))

      const { ElMessage } = await import('element-plus')
      
      const newWrapper = mount(ClusterDetail, {
        global: {
          plugins: [router]
        }
      })

      await nextTick()

      expect(ElMessage.error).toHaveBeenCalledWith('加载集群信息失败')
      
      newWrapper.unmount()
    })

    it('应该处理扫描操作失败', async () => {
      vi.mocked(tablesApi.scanAllDatabases).mockRejectedValue(new Error('Scan failed'))

      const { ElMessage } = await import('element-plus')
      
      const wrapper_instance = wrapper.vm as any
      await wrapper_instance.handleScanAllDatabases()

      expect(ElMessage.error).toHaveBeenCalledWith('扫描启动失败')
    })

    it('应该显示集群不存在的错误', async () => {
      // 切换到不存在的集群ID
      await router.push('/cluster/999')
      
      vi.mocked(clustersApi.get).mockRejectedValue({
        response: { status: 404 }
      })

      const newWrapper = mount(ClusterDetail, {
        global: {
          plugins: [router]
        }
      })

      await nextTick()

      expect(newWrapper.find('.error-message').text()).toContain('集群不存在')
      
      newWrapper.unmount()
    })
  })

  describe('实时数据更新', () => {
    it('应该定期刷新数据', async () => {
      const wrapper_instance = wrapper.vm as any
      
      // 启动自动刷新
      wrapper_instance.startAutoRefresh()
      
      // 等待一个刷新周期
      await new Promise(resolve => setTimeout(resolve, 35000))
      
      expect(clustersApi.get).toHaveBeenCalledTimes(2) // 初始 + 自动刷新
      
      // 停止自动刷新
      wrapper_instance.stopAutoRefresh()
    })

    it('应该在组件卸载时停止自动刷新', () => {
      const wrapper_instance = wrapper.vm as any
      const stopRefreshSpy = vi.spyOn(wrapper_instance, 'stopAutoRefresh')
      
      wrapper.unmount()
      
      expect(stopRefreshSpy).toHaveBeenCalled()
    })
  })

  describe('权限控制', () => {
    it('应该根据权限显示或隐藏操作按钮', async () => {
      // 模拟只读权限用户
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.hasWritePermission = false
      await nextTick()
      
      const scanButton = wrapper.find('[data-test="scan-all-btn"]')
      expect(scanButton.element.disabled).toBe(true)
    })

    it('应该允许管理员执行所有操作', async () => {
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.hasAdminPermission = true
      await nextTick()
      
      const settingsTab = wrapper.find('[data-test="settings-tab"]')
      expect(settingsTab.exists()).toBe(true)
    })
  })

  describe('响应式设计', () => {
    it('应该在移动端使用紧凑布局', async () => {
      // 模拟移动端屏幕尺寸
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768
      })

      window.dispatchEvent(new Event('resize'))
      await nextTick()

      expect(wrapper.find('.cluster-detail').classes()).toContain('mobile-layout')
    })

    it('应该在移动端隐藏侧边栏', async () => {
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.isMobile = true
      await nextTick()
      
      const sidebar = wrapper.find('.cluster-sidebar')
      expect(sidebar.classes()).toContain('hidden-mobile')
    })
  })

  describe('性能优化', () => {
    it('应该缓存计算属性结果', async () => {
      const wrapper_instance = wrapper.vm as any
      
      // 多次访问计算属性
      const stats1 = wrapper_instance.clusterStats
      const stats2 = wrapper_instance.clusterStats
      
      expect(stats1).toBe(stats2)
    })

    it('应该懒加载标签页内容', async () => {
      // 初始状态下，非激活标签页内容不应该加载
      expect(wrapper.find('.tasks-view-mock').exists()).toBe(false)
      
      // 切换到任务标签页后才加载
      wrapper.vm.activeTab = 'tasks'
      await nextTick()
      
      expect(wrapper.find('.tasks-view-mock').exists()).toBe(true)
    })
  })

  describe('数据状态管理', () => {
    it('应该正确管理加载状态', async () => {
      expect(wrapper.vm.loading).toBe(false)
      
      // 触发数据加载
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.loadClusterData()
      
      expect(wrapper.vm.loading).toBe(true)
    })

    it('应该正确管理错误状态', async () => {
      vi.mocked(clustersApi.get).mockRejectedValue(new Error('API Error'))
      
      const wrapper_instance = wrapper.vm as any
      await wrapper_instance.loadClusterData()
      
      expect(wrapper.vm.error).toBeTruthy()
    })

    it('应该能够重置错误状态', async () => {
      wrapper.vm.error = 'Some error'
      
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.clearError()
      
      expect(wrapper.vm.error).toBeNull()
    })
  })
})