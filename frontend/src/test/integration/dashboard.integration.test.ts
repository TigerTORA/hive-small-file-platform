/**
 * Dashboard Store集成测试
 * 测试Dashboard数据加载、状态管理、错误处理等核心功能
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDashboardStore } from '../../stores/dashboard'

// Mock the dashboard API
vi.mock('@/api/dashboard', () => ({
  dashboardApi: {
    getSummary: vi.fn(),
    getTrends: vi.fn(),
    getFileDistribution: vi.fn(),
    getTopTables: vi.fn(),
    getRecentTasks: vi.fn(),
    getClusterStats: vi.fn()
  }
}))

// Mock Element Plus messages
vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn()
  }
}))

describe('Dashboard Store Integration Tests', () => {
  let store: ReturnType<typeof useDashboardStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDashboardStore()
    vi.clearAllMocks()
  })

  describe('初始状态验证', () => {
    it('应该有正确的初始状态', () => {
      expect(store.summary.total_clusters).toBe(0)
      expect(store.summary.active_clusters).toBe(0)
      expect(store.summary.total_tables).toBe(0)
      expect(store.summary.monitored_tables).toBe(0)
      expect(store.summary.total_files).toBe(0)
      expect(store.summary.total_small_files).toBe(0)
      expect(store.summary.small_file_ratio).toBe(0)
      expect(store.summary.total_size_gb).toBe(0)
      expect(store.summary.small_file_size_gb).toBe(0)

      expect(store.trends).toEqual([])
      expect(store.fileDistribution).toEqual([])
      expect(store.topTables).toEqual([])
      expect(store.recentTasks).toEqual([])
      expect(store.clusterStats).toEqual([])
    })

    it('应该有正确的初始加载和错误状态', () => {
      expect(store.loading.summary).toBe(false)
      expect(store.loading.trends).toBe(false)
      expect(store.loading.fileDistribution).toBe(false)
      expect(store.loading.topTables).toBe(false)
      expect(store.loading.recentTasks).toBe(false)
      expect(store.loading.clusterStats).toBe(false)

      expect(store.errors.summary).toBe(null)
      expect(store.errors.trends).toBe(null)
      expect(store.errors.fileDistribution).toBe(null)
      expect(store.errors.topTables).toBe(null)
      expect(store.errors.recentTasks).toBe(null)
      expect(store.errors.clusterStats).toBe(null)
    })
  })

  describe('计算属性验证', () => {
    it('应该正确计算isLoading状态', () => {
      expect(store.isLoading).toBe(false)

      store.loading.summary = true
      expect(store.isLoading).toBe(true)

      store.loading.summary = false
      store.loading.trends = true
      expect(store.isLoading).toBe(true)

      store.loading.trends = false
      expect(store.isLoading).toBe(false)
    })

    it('应该正确计算hasErrors状态', () => {
      expect(store.hasErrors).toBe(false)

      store.errors.summary = 'Test error'
      expect(store.hasErrors).toBe(true)

      store.errors.summary = null
      store.errors.trends = 'Another error'
      expect(store.hasErrors).toBe(true)

      store.errors.trends = null
      expect(store.hasErrors).toBe(false)
    })

    it('应该正确计算小文件比率', () => {
      // 总文件为0时
      expect(store.smallFileRatio).toBe(0)

      // 设置文件数据
      store.summary.total_files = 1000
      store.summary.total_small_files = 300
      expect(store.smallFileRatio).toBe(30)

      // 所有文件都是小文件
      store.summary.total_small_files = 1000
      expect(store.smallFileRatio).toBe(100)

      // 没有小文件
      store.summary.total_small_files = 0
      expect(store.smallFileRatio).toBe(0)
    })
  })

  describe('数据加载功能', () => {
    it('应该能够加载概要数据', async () => {
      const mockSummary = {
        total_clusters: 5,
        active_clusters: 3,
        total_tables: 100,
        monitored_tables: 80,
        total_files: 50000,
        total_small_files: 15000,
        small_file_ratio: 30,
        total_size_gb: 1000,
        small_file_size_gb: 50
      }

      const { dashboardApi } = await import('@/api/dashboard')
      ;(dashboardApi.getSummary as any).mockResolvedValue(mockSummary)

      await store.loadSummary()

      expect(store.summary).toEqual(mockSummary)
      expect(store.loading.summary).toBe(false)
      expect(store.errors.summary).toBe(null)
    })

    it('应该能够加载趋势数据', async () => {
      const mockTrends = [
        { date: '2023-12-01', small_files: 1000, total_size: 100 },
        { date: '2023-12-02', small_files: 1100, total_size: 110 }
      ]

      const { dashboardApi } = await import('@/api/dashboard')
      ;(dashboardApi.getTrends as any).mockResolvedValue(mockTrends)

      await store.loadTrends(1, 7)

      expect(store.trends).toEqual(mockTrends)
      expect(store.loading.trends).toBe(false)
      expect(store.errors.trends).toBe(null)
      expect(dashboardApi.getTrends).toHaveBeenCalledWith(1, 7)
    })

    it('应该能够加载文件分布数据', async () => {
      const mockDistribution = [
        { range: '0-10MB', count: 5000, percentage: 50 },
        { range: '10-100MB', count: 3000, percentage: 30 }
      ]

      const { dashboardApi } = await import('@/api/dashboard')
      ;(dashboardApi.getFileDistribution as any).mockResolvedValue(mockDistribution)

      await store.loadFileDistribution(1)

      expect(store.fileDistribution).toEqual(mockDistribution)
      expect(store.loading.fileDistribution).toBe(false)
      expect(store.errors.fileDistribution).toBe(null)
    })

    it('应该能够加载TOP表数据', async () => {
      const mockTopTables = [
        { table: 'db1.table1', small_files: 5000, total_files: 10000, cluster: 'cluster1' },
        { table: 'db2.table2', small_files: 3000, total_files: 8000, cluster: 'cluster1' }
      ]

      const { dashboardApi } = await import('@/api/dashboard')
      ;(dashboardApi.getTopTables as any).mockResolvedValue(mockTopTables)

      await store.loadTopTables(1, 10)

      expect(store.topTables).toEqual(mockTopTables)
      expect(store.loading.topTables).toBe(false)
      expect(store.errors.topTables).toBe(null)
      expect(dashboardApi.getTopTables).toHaveBeenCalledWith(1, 10)
    })

    it('应该能够加载最近任务数据', async () => {
      const mockRecentTasks = [
        { task_id: 1, task_name: 'merge_task_1', status: 'completed', created_at: '2023-12-01' },
        { task_id: 2, task_name: 'merge_task_2', status: 'running', created_at: '2023-12-02' }
      ]

      const { dashboardApi } = await import('@/api/dashboard')
      ;(dashboardApi.getRecentTasks as any).mockResolvedValue(mockRecentTasks)

      await store.loadRecentTasks(20, 'completed')

      expect(store.recentTasks).toEqual(mockRecentTasks)
      expect(store.loading.recentTasks).toBe(false)
      expect(store.errors.recentTasks).toBe(null)
      expect(dashboardApi.getRecentTasks).toHaveBeenCalledWith(20, 'completed')
    })

    it('应该能够加载集群统计数据', async () => {
      const mockClusterStats = {
        clusters: [
          { cluster_id: 1, cluster_name: 'cluster1', table_count: 50, file_count: 25000 },
          { cluster_id: 2, cluster_name: 'cluster2', table_count: 30, file_count: 15000 }
        ]
      }

      const { dashboardApi } = await import('@/api/dashboard')
      ;(dashboardApi.getClusterStats as any).mockResolvedValue(mockClusterStats)

      await store.loadClusterStats()

      expect(store.clusterStats).toEqual(mockClusterStats.clusters)
      expect(store.loading.clusterStats).toBe(false)
      expect(store.errors.clusterStats).toBe(null)
    })
  })

  describe('错误处理', () => {
    it('应该正确处理加载概要数据的错误', async () => {
      const errorMessage = 'Network error'
      const { dashboardApi } = await import('@/api/dashboard')
      ;(dashboardApi.getSummary as any).mockRejectedValue(new Error(errorMessage))

      await store.loadSummary()

      expect(store.errors.summary).toBe(errorMessage)
      expect(store.loading.summary).toBe(false)
    })

    it('应该正确处理加载趋势数据的错误', async () => {
      const { dashboardApi } = await import('@/api/dashboard')
      ;(dashboardApi.getTrends as any).mockRejectedValue(new Error('API Error'))

      await store.loadTrends()

      expect(store.errors.trends).toBe('API Error')
      expect(store.loading.trends).toBe(false)
    })

    it('应该处理未知错误对象', async () => {
      const { dashboardApi } = await import('@/api/dashboard')
      ;(dashboardApi.getSummary as any).mockRejectedValue({ unknown: 'error' })

      await store.loadSummary()

      expect(store.errors.summary).toBe('加载概要数据失败')
      expect(store.loading.summary).toBe(false)
    })
  })

  describe('批量操作', () => {
    it('应该能够加载所有数据', async () => {
      const { dashboardApi } = await import('@/api/dashboard')

      // Mock所有API调用
      ;(dashboardApi.getSummary as any).mockResolvedValue({})
      ;(dashboardApi.getTrends as any).mockResolvedValue([])
      ;(dashboardApi.getFileDistribution as any).mockResolvedValue([])
      ;(dashboardApi.getTopTables as any).mockResolvedValue([])
      ;(dashboardApi.getRecentTasks as any).mockResolvedValue([])
      ;(dashboardApi.getClusterStats as any).mockResolvedValue({ clusters: [] })

      await store.loadAllData(1)

      // 验证所有API都被调用
      expect(dashboardApi.getSummary).toHaveBeenCalled()
      expect(dashboardApi.getTrends).toHaveBeenCalledWith(1, 7)
      expect(dashboardApi.getFileDistribution).toHaveBeenCalledWith(1)
      expect(dashboardApi.getTopTables).toHaveBeenCalledWith(1, 10)
      expect(dashboardApi.getRecentTasks).toHaveBeenCalledWith(10, undefined)
      expect(dashboardApi.getClusterStats).toHaveBeenCalled()
    })

    it('应该能够刷新数据', async () => {
      const { dashboardApi } = await import('@/api/dashboard')

      // Mock所有API调用
      ;(dashboardApi.getSummary as any).mockResolvedValue({})
      ;(dashboardApi.getTrends as any).mockResolvedValue([])
      ;(dashboardApi.getFileDistribution as any).mockResolvedValue([])
      ;(dashboardApi.getTopTables as any).mockResolvedValue([])
      ;(dashboardApi.getRecentTasks as any).mockResolvedValue([])
      ;(dashboardApi.getClusterStats as any).mockResolvedValue({ clusters: [] })

      await store.refresh(2)

      // 验证refresh调用了loadAllData
      expect(dashboardApi.getTrends).toHaveBeenCalledWith(2, 7)
      expect(dashboardApi.getFileDistribution).toHaveBeenCalledWith(2)
      expect(dashboardApi.getTopTables).toHaveBeenCalledWith(2, 10)
    })
  })

  describe('状态管理', () => {
    it('应该能够清空错误状态', () => {
      // 设置一些错误
      store.errors.summary = 'Error 1'
      store.errors.trends = 'Error 2'
      store.errors.fileDistribution = 'Error 3'

      store.clearErrors()

      expect(store.errors.summary).toBe(null)
      expect(store.errors.trends).toBe(null)
      expect(store.errors.fileDistribution).toBe(null)
      expect(store.errors.topTables).toBe(null)
      expect(store.errors.recentTasks).toBe(null)
      expect(store.errors.clusterStats).toBe(null)
    })

    it('应该能够重置所有状态', () => {
      // 设置一些数据和错误
      store.summary.total_clusters = 10
      store.trends = [{ date: '2023-12-01', small_files: 1000, total_size: 100 }]
      store.fileDistribution = [{ range: '0-10MB', count: 5000, percentage: 50 }]
      store.topTables = [{ table: 'test.table', small_files: 100, total_files: 200, cluster: 'test' }]
      store.recentTasks = [{ task_id: 1, task_name: 'test', status: 'completed', created_at: '2023-12-01' }]
      store.clusterStats = [{ cluster_id: 1, cluster_name: 'test', table_count: 10, file_count: 1000 }]
      store.errors.summary = 'Test error'

      store.reset()

      // 验证所有状态都被重置
      expect(store.summary.total_clusters).toBe(0)
      expect(store.trends).toEqual([])
      expect(store.fileDistribution).toEqual([])
      expect(store.topTables).toEqual([])
      expect(store.recentTasks).toEqual([])
      expect(store.clusterStats).toEqual([])
      expect(store.errors.summary).toBe(null)
    })
  })

  describe('集成场景测试', () => {
    it('应该支持完整的数据加载工作流', async () => {
      const { dashboardApi } = await import('@/api/dashboard')

      // 模拟一个完整的数据加载场景
      const mockData = {
        summary: { total_clusters: 5, active_clusters: 3, total_tables: 100, monitored_tables: 80, total_files: 10000, total_small_files: 3000, small_file_ratio: 30, total_size_gb: 500, small_file_size_gb: 50 },
        trends: [{ date: '2023-12-01', small_files: 1000, total_size: 100 }],
        distribution: [{ range: '0-10MB', count: 5000, percentage: 50 }],
        topTables: [{ table: 'db1.table1', small_files: 500, total_files: 1000, cluster: 'cluster1' }],
        recentTasks: [{ task_id: 1, task_name: 'merge_task', status: 'completed', created_at: '2023-12-01' }],
        clusterStats: { clusters: [{ cluster_id: 1, cluster_name: 'cluster1', table_count: 50, file_count: 5000 }] }
      }

      ;(dashboardApi.getSummary as any).mockResolvedValue(mockData.summary)
      ;(dashboardApi.getTrends as any).mockResolvedValue(mockData.trends)
      ;(dashboardApi.getFileDistribution as any).mockResolvedValue(mockData.distribution)
      ;(dashboardApi.getTopTables as any).mockResolvedValue(mockData.topTables)
      ;(dashboardApi.getRecentTasks as any).mockResolvedValue(mockData.recentTasks)
      ;(dashboardApi.getClusterStats as any).mockResolvedValue(mockData.clusterStats)

      // 执行完整加载
      await store.loadAllData(1)

      // 验证所有数据都被正确加载
      expect(store.summary).toEqual(mockData.summary)
      expect(store.trends).toEqual(mockData.trends)
      expect(store.fileDistribution).toEqual(mockData.distribution)
      expect(store.topTables).toEqual(mockData.topTables)
      expect(store.recentTasks).toEqual(mockData.recentTasks)
      expect(store.clusterStats).toEqual(mockData.clusterStats.clusters)

      // 验证没有加载状态和错误
      expect(store.isLoading).toBe(false)
      expect(store.hasErrors).toBe(false)

      // 验证计算属性工作正常
      expect(store.smallFileRatio).toBe(30)
    })

    it('应该能够处理混合成功失败的加载场景', async () => {
      const { dashboardApi } = await import('@/api/dashboard')

      // 部分成功，部分失败
      ;(dashboardApi.getSummary as any).mockResolvedValue({ total_clusters: 5, active_clusters: 3, total_tables: 100, monitored_tables: 80, total_files: 10000, total_small_files: 3000, small_file_ratio: 30, total_size_gb: 500, small_file_size_gb: 50 })
      ;(dashboardApi.getTrends as any).mockRejectedValue(new Error('Trends API failed'))
      ;(dashboardApi.getFileDistribution as any).mockResolvedValue([])
      ;(dashboardApi.getTopTables as any).mockRejectedValue(new Error('TopTables API failed'))
      ;(dashboardApi.getRecentTasks as any).mockResolvedValue([])
      ;(dashboardApi.getClusterStats as any).mockResolvedValue({ clusters: [] })

      await store.loadAllData()

      // 验证成功的数据被加载
      expect(store.summary.total_clusters).toBe(5)
      expect(store.fileDistribution).toEqual([])
      expect(store.recentTasks).toEqual([])

      // 验证失败的API产生了错误
      expect(store.errors.trends).toBe('Trends API failed')
      expect(store.errors.topTables).toBe('TopTables API failed')

      // 验证混合状态
      expect(store.hasErrors).toBe(true)
      expect(store.isLoading).toBe(false)
    })
  })
})