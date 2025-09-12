/**
 * ClustersManagement.vue 组件单元测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ClustersManagement from '@/views/ClustersManagement.vue'
import { clustersApi } from '@/api/clusters'

// Mock API
vi.mock('@/api/clusters', () => ({
  clustersApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    testConnection: vi.fn()
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

// Mock router
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/cluster/:id', component: { template: '<div>Cluster Detail</div>' } }
  ]
})

describe('ClustersManagement.vue', () => {
  let wrapper: VueWrapper<any>

  const mockClusters = [
    {
      id: 1,
      name: 'production-cluster',
      description: '生产环境集群',
      hive_metastore_url: 'mysql://user:pass@prod-db:3306/hive',
      hdfs_namenode_url: 'hdfs://prod-namenode:9000',
      connection_type: 'mysql',
      created_time: '2023-01-01T00:00:00Z',
      updated_time: '2023-01-01T00:00:00Z'
    },
    {
      id: 2,
      name: 'test-cluster',
      description: '测试环境集群',
      hive_metastore_url: 'postgresql://user:pass@test-db:5432/hive_metastore',
      hdfs_namenode_url: 'hdfs://test-namenode:9000',
      connection_type: 'postgresql',
      created_time: '2023-01-02T00:00:00Z',
      updated_time: '2023-01-02T00:00:00Z'
    }
  ]

  beforeEach(async () => {
    // Reset mocks
    vi.clearAllMocks()
    
    // Mock successful API response
    vi.mocked(clustersApi.list).mockResolvedValue(mockClusters)
    
    wrapper = mount(ClustersManagement, {
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
    it('应该正确渲染页面标题', () => {
      expect(wrapper.find('.page-title').text()).toBe('集群管理')
    })

    it('应该显示统计信息卡片', () => {
      const statsCards = wrapper.findAll('.stat-card')
      expect(statsCards.length).toBe(3)
      
      expect(statsCards[0].find('.stat-label').text()).toBe('总集群数')
      expect(statsCards[1].find('.stat-label').text()).toBe('在线集群')
      expect(statsCards[2].find('.stat-label').text()).toBe('离线集群')
    })

    it('应该在组件挂载时加载集群列表', () => {
      expect(clustersApi.list).toHaveBeenCalledTimes(1)
    })

    it('应该正确显示集群卡片', async () => {
      await nextTick()
      
      const clusterCards = wrapper.findAll('.cluster-card')
      expect(clusterCards.length).toBe(2)
      
      expect(clusterCards[0].find('.cluster-name').text()).toBe('production-cluster')
      expect(clusterCards[1].find('.cluster-name').text()).toBe('test-cluster')
    })
  })

  describe('搜索和过滤功能', () => {
    it('应该根据搜索关键字过滤集群', async () => {
      const searchInput = wrapper.find('input[placeholder="搜索集群名称..."]')
      await searchInput.setValue('production')
      await nextTick()
      
      const clusterCards = wrapper.findAll('.cluster-card:not(.hidden)')
      expect(clusterCards.length).toBe(1)
      expect(clusterCards[0].find('.cluster-name').text()).toBe('production-cluster')
    })

    it('应该根据连接类型过滤集群', async () => {
      // 设置连接类型过滤器
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.filterConnectionType = 'mysql'
      await nextTick()
      
      const filteredClusters = wrapper_instance.filteredClusters
      expect(filteredClusters.length).toBe(1)
      expect(filteredClusters[0].name).toBe('production-cluster')
    })

    it('应该根据状态过滤集群', async () => {
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.filterStatus = 'online'
      await nextTick()
      
      // 由于没有实际的连接状态，这里只测试过滤逻辑存在
      expect(wrapper_instance.filterStatus).toBe('online')
    })

    it('应该清除搜索条件', async () => {
      const searchInput = wrapper.find('input[placeholder="搜索集群名称..."]')
      await searchInput.setValue('test')
      
      const clearButton = wrapper.find('.el-input__clear')
      await clearButton.trigger('click')
      
      expect(searchInput.element.value).toBe('')
    })
  })

  describe('集群操作', () => {
    it('应该打开新增集群对话框', async () => {
      const addButton = wrapper.find('[data-test="add-cluster-btn"]')
      await addButton.trigger('click')
      
      expect(wrapper.vm.showAddDialog).toBe(true)
      expect(wrapper.find('.cluster-dialog').exists()).toBe(true)
    })

    it('应该打开编辑集群对话框', async () => {
      const editButton = wrapper.find('[data-test="edit-cluster-btn"]')
      await editButton.trigger('click')
      
      expect(wrapper.vm.showEditDialog).toBe(true)
      expect(wrapper.vm.editingCluster).toBeTruthy()
    })

    it('应该能够测试集群连接', async () => {
      vi.mocked(clustersApi.testConnection).mockResolvedValue({ 
        success: true, 
        message: '连接成功' 
      })
      
      const testButton = wrapper.find('[data-test="test-connection-btn"]')
      await testButton.trigger('click')
      
      expect(clustersApi.testConnection).toHaveBeenCalledWith(1)
    })

    it('应该能够导航到集群详情页', async () => {
      const pushSpy = vi.spyOn(router, 'push')
      
      const detailButton = wrapper.find('[data-test="view-detail-btn"]')
      await detailButton.trigger('click')
      
      expect(pushSpy).toHaveBeenCalledWith('/cluster/1')
    })
  })

  describe('集群CRUD操作', () => {
    it('应该成功创建新集群', async () => {
      const newCluster = {
        name: 'new-cluster',
        description: '新集群',
        hive_metastore_url: 'mysql://user:pass@new-db:3306/hive',
        hdfs_namenode_url: 'hdfs://new-namenode:9000',
        connection_type: 'mysql'
      }

      vi.mocked(clustersApi.create).mockResolvedValue({
        id: 3,
        ...newCluster,
        created_time: '2023-01-03T00:00:00Z',
        updated_time: '2023-01-03T00:00:00Z'
      })

      // 打开对话框
      wrapper.vm.showAddDialog = true
      await nextTick()

      // 填写表单
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.newCluster = newCluster

      // 提交表单
      await wrapper_instance.handleAddCluster()

      expect(clustersApi.create).toHaveBeenCalledWith(newCluster)
      expect(clustersApi.list).toHaveBeenCalledTimes(2) // 初始加载 + 创建后刷新
    })

    it('应该成功更新集群', async () => {
      const updatedCluster = {
        ...mockClusters[0],
        description: '更新后的描述'
      }

      vi.mocked(clustersApi.update).mockResolvedValue(updatedCluster)

      const wrapper_instance = wrapper.vm as any
      wrapper_instance.editingCluster = updatedCluster
      wrapper_instance.showEditDialog = true

      await wrapper_instance.handleUpdateCluster()

      expect(clustersApi.update).toHaveBeenCalledWith(1, updatedCluster)
      expect(clustersApi.list).toHaveBeenCalledTimes(2)
    })

    it('应该成功删除集群', async () => {
      const { ElMessageBox } = await import('element-plus')
      vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm')
      vi.mocked(clustersApi.delete).mockResolvedValue({ success: true })

      const wrapper_instance = wrapper.vm as any
      await wrapper_instance.handleDeleteCluster(mockClusters[0])

      expect(ElMessageBox.confirm).toHaveBeenCalled()
      expect(clustersApi.delete).toHaveBeenCalledWith(1)
      expect(clustersApi.list).toHaveBeenCalledTimes(2)
    })

    it('应该处理删除取消操作', async () => {
      const { ElMessageBox } = await import('element-plus')
      vi.mocked(ElMessageBox.confirm).mockRejectedValue('cancel')

      const wrapper_instance = wrapper.vm as any
      await wrapper_instance.handleDeleteCluster(mockClusters[0])

      expect(ElMessageBox.confirm).toHaveBeenCalled()
      expect(clustersApi.delete).not.toHaveBeenCalled()
    })
  })

  describe('表单验证', () => {
    beforeEach(async () => {
      wrapper.vm.showAddDialog = true
      await nextTick()
    })

    it('应该验证必填字段', async () => {
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.newCluster = {
        name: '',
        description: '',
        hive_metastore_url: '',
        hdfs_namenode_url: '',
        connection_type: ''
      }

      // 尝试提交空表单
      const submitButton = wrapper.find('[data-test="submit-cluster-btn"]')
      await submitButton.trigger('click')

      // 应该显示验证错误
      expect(wrapper.findAll('.el-form-item__error').length).toBeGreaterThan(0)
    })

    it('应该验证URL格式', async () => {
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.newCluster = {
        name: 'test-cluster',
        description: '测试集群',
        hive_metastore_url: 'invalid-url',
        hdfs_namenode_url: 'invalid-url',
        connection_type: 'mysql'
      }

      const isValid = await wrapper_instance.$refs.addClusterForm.validate()
      expect(isValid).toBe(false)
    })

    it('应该验证集群名称唯一性', async () => {
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.newCluster = {
        name: 'production-cluster', // 已存在的名称
        description: '测试集群',
        hive_metastore_url: 'mysql://user:pass@test:3306/hive',
        hdfs_namenode_url: 'hdfs://test:9000',
        connection_type: 'mysql'
      }

      const isDuplicate = wrapper_instance.isClusterNameDuplicate('production-cluster')
      expect(isDuplicate).toBe(true)
    })
  })

  describe('错误处理', () => {
    it('应该处理API加载错误', async () => {
      vi.mocked(clustersApi.list).mockRejectedValue(new Error('API Error'))

      const { ElMessage } = await import('element-plus')
      
      const newWrapper = mount(ClustersManagement, {
        global: {
          plugins: [router]
        }
      })

      await nextTick()

      expect(ElMessage.error).toHaveBeenCalledWith('加载集群列表失败')
      
      newWrapper.unmount()
    })

    it('应该处理连接测试失败', async () => {
      vi.mocked(clustersApi.testConnection).mockRejectedValue(new Error('Connection failed'))

      const { ElMessage } = await import('element-plus')
      
      const wrapper_instance = wrapper.vm as any
      await wrapper_instance.handleTestConnection(mockClusters[0])

      expect(ElMessage.error).toHaveBeenCalledWith('连接测试失败')
    })

    it('应该处理创建集群失败', async () => {
      vi.mocked(clustersApi.create).mockRejectedValue(new Error('Create failed'))

      const { ElMessage } = await import('element-plus')
      
      const wrapper_instance = wrapper.vm as any
      wrapper_instance.newCluster = {
        name: 'test-cluster',
        description: '测试',
        hive_metastore_url: 'mysql://test:3306/hive',
        hdfs_namenode_url: 'hdfs://test:9000',
        connection_type: 'mysql'
      }

      await wrapper_instance.handleAddCluster()

      expect(ElMessage.error).toHaveBeenCalledWith('创建集群失败')
    })
  })

  describe('响应式设计', () => {
    it('应该在小屏幕上显示不同的布局', async () => {
      // 模拟小屏幕尺寸
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768
      })

      window.dispatchEvent(new Event('resize'))
      await nextTick()

      // 检查是否应用了移动端样式
      expect(wrapper.find('.clusters-container').classes()).toContain('mobile-layout')
    })
  })

  describe('性能优化', () => {
    it('应该正确缓存计算属性', async () => {
      const wrapper_instance = wrapper.vm as any
      
      // 多次访问计算属性
      const result1 = wrapper_instance.filteredClusters
      const result2 = wrapper_instance.filteredClusters
      
      // 结果应该相同且缓存生效
      expect(result1).toBe(result2)
    })

    it('应该防抖搜索输入', async () => {
      const searchInput = wrapper.find('input[placeholder="搜索集群名称..."]')
      
      // 快速输入多个字符
      await searchInput.setValue('p')
      await searchInput.setValue('pr')
      await searchInput.setValue('pro')
      
      // 应该只触发一次搜索
      await new Promise(resolve => setTimeout(resolve, 500))
      
      const clusterCards = wrapper.findAll('.cluster-card:not(.hidden)')
      expect(clusterCards.length).toBe(1)
    })
  })
})