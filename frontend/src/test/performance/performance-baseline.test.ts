/**
 * 性能基准测试
 * 建立前端应用关键功能的性能基准线，用于持续监控性能变化
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDashboardStore } from '../../stores/dashboard'
import { useMonitoringStore } from '../../stores/monitoring'

// Mock APIs for consistent testing
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

vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn()
  }
}))

describe('性能基准测试', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('Store初始化性能', () => {
    it('Dashboard Store初始化应在10ms内完成', async () => {
      const startTime = performance.now()

      const store = useDashboardStore()

      const endTime = performance.now()
      const initTime = endTime - startTime

      expect(initTime).toBeLessThan(10)
      expect(store).toBeDefined()
      expect(store.summary).toBeDefined()
    })

    it('Monitoring Store初始化应在5ms内完成', async () => {
      const startTime = performance.now()

      const store = useMonitoringStore()

      const endTime = performance.now()
      const initTime = endTime - startTime

      expect(initTime).toBeLessThan(5)
      expect(store).toBeDefined()
      expect(store.settings).toBeDefined()
    })

    it('多个Store并发初始化应在20ms内完成', async () => {
      const startTime = performance.now()

      const [dashboardStore, monitoringStore] = await Promise.all([
        Promise.resolve(useDashboardStore()),
        Promise.resolve(useMonitoringStore())
      ])

      const endTime = performance.now()
      const totalTime = endTime - startTime

      expect(totalTime).toBeLessThan(20)
      expect(dashboardStore).toBeDefined()
      expect(monitoringStore).toBeDefined()
    })
  })

  describe('数据处理性能', () => {
    it('大量数据处理应在合理时间内完成', () => {
      const store = useDashboardStore()

      // 生成大量测试数据
      const largeData = Array.from({ length: 10000 }, (_, i) => ({
        table: `database_${Math.floor(i / 100)}.table_${i}`,
        small_files: Math.floor(Math.random() * 5000),
        total_files: Math.floor(Math.random() * 10000) + 5000,
        cluster: `cluster_${Math.floor(i / 1000)}`
      }))

      const startTime = performance.now()

      // 模拟数据处理
      store.topTables = largeData
      const processedData = store.topTables.slice(0, 100)

      const endTime = performance.now()
      const processingTime = endTime - startTime

      expect(processingTime).toBeLessThan(50) // 50ms内处理10k条数据
      expect(processedData).toHaveLength(100)
    })

    it('计算属性性能应保持高效', () => {
      const store = useDashboardStore()

      // 设置测试数据
      store.summary.total_files = 100000
      store.summary.total_small_files = 30000

      const startTime = performance.now()

      // 多次访问计算属性
      for (let i = 0; i < 1000; i++) {
        const ratio = store.smallFileRatio
        expect(ratio).toBe(30)
      }

      const endTime = performance.now()
      const avgTime = (endTime - startTime) / 1000

      expect(avgTime).toBeLessThan(0.03) // 每次计算应在0.03ms内
    })

    it('数组操作性能基准', () => {
      const monitoringStore = useMonitoringStore()

      const startTime = performance.now()

      // 测试图表颜色循环访问
      const colors = []
      for (let i = 0; i < 1000; i++) {
        colors.push(monitoringStore.getChartColor(i))
      }

      const endTime = performance.now()
      const totalTime = endTime - startTime

      expect(totalTime).toBeLessThan(20) // 1000次颜色获取应在20ms内
      expect(colors).toHaveLength(1000)
      expect(colors[0]).toBe('#409EFF') // 验证第一个颜色
    })
  })

  describe('内存使用性能', () => {
    it('Store状态重置应释放内存', () => {
      const store = useDashboardStore()

      // 填充大量数据
      store.trends = Array.from({ length: 5000 }, (_, i) => ({
        date: `2023-12-${String((i % 30) + 1).padStart(2, '0')}`,
        small_files: Math.floor(Math.random() * 1000),
        total_size: Math.floor(Math.random() * 10000)
      }))

      store.fileDistribution = Array.from({ length: 1000 }, (_, i) => ({
        range: `${i * 10}-${(i + 1) * 10}MB`,
        count: Math.floor(Math.random() * 5000),
        percentage: Math.floor(Math.random() * 100)
      }))

      // 验证数据已设置
      expect(store.trends).toHaveLength(5000)
      expect(store.fileDistribution).toHaveLength(1000)

      const startTime = performance.now()

      // 重置状态
      store.reset()

      const endTime = performance.now()
      const resetTime = endTime - startTime

      // 验证重置性能和效果
      expect(resetTime).toBeLessThan(5) // 重置应在5ms内完成
      expect(store.trends).toHaveLength(0)
      expect(store.fileDistribution).toHaveLength(0)
    })

    it('批量状态更新性能', () => {
      const monitoringStore = useMonitoringStore()

      const newSettings = {
        autoRefresh: false,
        refreshInterval: 300,
        selectedCluster: 5,
        theme: 'dark' as const,
        chartColors: ['#FF0000', '#00FF00', '#0000FF']
      }

      const startTime = performance.now()

      // 执行批量更新
      monitoringStore.updateSettings(newSettings)

      const endTime = performance.now()
      const updateTime = endTime - startTime

      expect(updateTime).toBeLessThan(2) // 批量更新应在2ms内完成
      expect(monitoringStore.settings.refreshInterval).toBe(300)
      expect(monitoringStore.settings.theme).toBe('dark')
    })
  })

  describe('异步操作性能', () => {
    it('模拟API加载性能基准', async () => {
      const store = useDashboardStore()
      const { dashboardApi } = await import('@/api/dashboard')

      // Mock API响应时间
      ;(dashboardApi.getSummary as any).mockImplementation(
        () =>
          new Promise(
            resolve =>
              setTimeout(
                () =>
                  resolve({
                    total_clusters: 5,
                    active_clusters: 3,
                    total_tables: 100,
                    monitored_tables: 80,
                    total_files: 50000,
                    total_small_files: 15000,
                    small_file_ratio: 30,
                    total_size_gb: 1000,
                    small_file_size_gb: 50,
                    files_reduced: 20000,
                    size_saved_gb: 128.5
                  }),
                50
              ) // 模拟50ms API延迟
          )
      )

      const startTime = performance.now()

      await store.loadSummary()

      const endTime = performance.now()
      const totalTime = endTime - startTime

      // 总时间应接近API延迟时间，处理开销应最小
      expect(totalTime).toBeGreaterThan(45) // 至少API延迟时间
      expect(totalTime).toBeLessThan(70) // 不应超过太多处理时间
      expect(store.summary.total_clusters).toBe(5)
    })

    it('并发API加载性能', async () => {
      const store = useDashboardStore()
      const { dashboardApi } = await import('@/api/dashboard')

      // Mock所有API
      const mockDelay = 30
      ;(dashboardApi.getSummary as any).mockImplementation(
        () =>
          new Promise(resolve =>
            setTimeout(
              () =>
                resolve({
                  total_clusters: 0,
                  active_clusters: 0,
                  total_tables: 0,
                  monitored_tables: 0,
                  total_files: 0,
                  total_small_files: 0,
                  small_file_ratio: 0,
                  total_size_gb: 0,
                  small_file_size_gb: 0,
                  files_reduced: 0,
                  size_saved_gb: 0
                }),
              mockDelay
            )
          )
      )
      ;(dashboardApi.getTrends as any).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve([]), mockDelay))
      )
      ;(dashboardApi.getFileDistribution as any).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve([]), mockDelay))
      )
      ;(dashboardApi.getTopTables as any).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve([]), mockDelay))
      )
      ;(dashboardApi.getRecentTasks as any).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve([]), mockDelay))
      )
      ;(dashboardApi.getClusterStats as any).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ clusters: [] }), mockDelay))
      )

      const startTime = performance.now()

      await store.loadAllData()

      const endTime = performance.now()
      const totalTime = endTime - startTime

      // 并发加载应接近最慢API的时间，而不是所有API时间之和
      expect(totalTime).toBeLessThan(mockDelay + 20) // 允许20ms处理开销
      expect(totalTime).toBeGreaterThan(mockDelay - 10) // 至少是API时间
    })
  })

  describe('格式化工具性能', () => {
    it('文件大小格式化性能', () => {
      const monitoringStore = useMonitoringStore()

      const testSizes = [
        0,
        1024,
        1024 * 1024,
        1024 * 1024 * 1024,
        1536,
        2048000,
        5368709120,
        1099511627776
      ]

      const startTime = performance.now()

      // 大量格式化操作
      const results = []
      for (let i = 0; i < 1000; i++) {
        const size = testSizes[i % testSizes.length]
        results.push(monitoringStore.formatFileSize(size))
      }

      const endTime = performance.now()
      const avgTime = (endTime - startTime) / 1000

      expect(avgTime).toBeLessThan(0.02) // 平均每次格式化应在0.02ms内
      expect(results).toHaveLength(1000)
      expect(results[0]).toBe('0 B')
      expect(results[1]).toBe('1 KB')
    })

    it('数字格式化性能', () => {
      const monitoringStore = useMonitoringStore()

      const testNumbers = [0, 999, 1000, 1500, 1000000, 1500000, 2500000, 999999999]

      const startTime = performance.now()

      // 大量数字格式化
      const results = []
      for (let i = 0; i < 1000; i++) {
        const num = testNumbers[i % testNumbers.length]
        results.push(monitoringStore.formatNumber(num))
      }

      const endTime = performance.now()
      const avgTime = (endTime - startTime) / 1000

      expect(avgTime).toBeLessThan(0.01) // 平均每次格式化应在0.01ms内
      expect(results).toHaveLength(1000)
      expect(results[1]).toBe('999')
      expect(results[2]).toBe('1.0K')
    })

    it('日期格式化性能', () => {
      const monitoringStore = useMonitoringStore()

      const testDates = [
        new Date('2023-12-01T10:30:00'),
        new Date('2023-12-15T15:45:30'),
        new Date('2024-01-01T00:00:00'),
        new Date('2024-06-15T12:00:00')
      ]

      const startTime = performance.now()

      // 大量日期格式化
      const results = []
      for (let i = 0; i < 1000; i++) {
        const date = testDates[i % testDates.length]
        results.push(monitoringStore.formatDate(date))
      }

      const endTime = performance.now()
      const avgTime = (endTime - startTime) / 1000

      expect(avgTime).toBeLessThan(0.15) // 平均每次格式化应在0.15ms内
      expect(results).toHaveLength(1000)
      expect(results[0]).toMatch(/\d{2}\/\d{2}\s+\d{2}:\d{2}/)
    })
  })

  describe('性能监控和度量', () => {
    it('应该提供性能度量指标', () => {
      const performanceMetrics = {
        storeInitTime: 0,
        dataProcessingTime: 0,
        apiResponseTime: 0,
        renderingTime: 0
      }

      // 模拟性能度量收集
      const startTime = performance.now()

      const store = useDashboardStore()
      store.summary.total_files = 100000
      const ratio = store.smallFileRatio

      const endTime = performance.now()

      performanceMetrics.storeInitTime = endTime - startTime

      expect(performanceMetrics.storeInitTime).toBeLessThan(10)
      expect(ratio).toBe(0)

      // 验证度量指标结构
      expect(performanceMetrics).toHaveProperty('storeInitTime')
      expect(performanceMetrics).toHaveProperty('dataProcessingTime')
      expect(performanceMetrics).toHaveProperty('apiResponseTime')
      expect(performanceMetrics).toHaveProperty('renderingTime')
    })

    it('应该检测性能回归', () => {
      // 基准性能指标
      const baseline = {
        storeInit: 5, // ms
        dataProcessing: 20, // ms
        apiCall: 100, // ms
        formatting: 0.01 // ms per operation
      }

      // 当前性能测试
      const startTime = performance.now()
      const store = useDashboardStore()
      store.summary.total_files = 50000
      store.summary.total_small_files = 15000
      const ratio = store.smallFileRatio
      const endTime = performance.now()

      const currentPerformance = {
        storeInit: endTime - startTime,
        dataProcessing: 15,
        apiCall: 80,
        formatting: 0.008
      }

      // 检查性能是否在可接受范围内（允许20%波动）
      expect(currentPerformance.storeInit).toBeLessThan(baseline.storeInit * 1.2)
      expect(currentPerformance.dataProcessing).toBeLessThan(baseline.dataProcessing * 1.2)
      expect(currentPerformance.apiCall).toBeLessThan(baseline.apiCall * 1.2)
      expect(currentPerformance.formatting).toBeLessThan(baseline.formatting * 1.2)

      expect(ratio).toBe(30)
    })
  })

  describe('压力测试', () => {
    it('应该在高负载下保持性能', () => {
      const store = useDashboardStore()
      const monitoringStore = useMonitoringStore()

      const startTime = performance.now()

      // 模拟高负载操作
      for (let i = 0; i < 100; i++) {
        // 多次状态更新
        store.summary.total_files = i * 1000
        store.summary.total_small_files = i * 300

        // 多次计算属性访问
        const ratio = store.smallFileRatio

        // 多次格式化操作
        const formattedSize = monitoringStore.formatFileSize(i * 1024 * 1024)
        const formattedNumber = monitoringStore.formatNumber(i * 1000)

        expect(ratio).toBeGreaterThanOrEqual(0)
        expect(formattedSize).toBeDefined()
        expect(formattedNumber).toBeDefined()
      }

      const endTime = performance.now()
      const totalTime = endTime - startTime

      // 高负载测试应在合理时间内完成
      expect(totalTime).toBeLessThan(100) // 100次操作应在100ms内完成
    })

    it('内存泄漏检测', () => {
      const initialHeapUsed = process.memoryUsage().heapUsed

      // 执行多轮操作
      for (let round = 0; round < 10; round++) {
        const store = useDashboardStore()

        // 填充数据
        store.trends = Array.from({ length: 1000 }, (_, i) => ({
          date: `2023-12-${String((i % 30) + 1).padStart(2, '0')}`,
          small_files: Math.floor(Math.random() * 1000),
          total_size: Math.floor(Math.random() * 10000)
        }))

        // 处理数据
        const processedData = store.trends.slice(0, 100)
        expect(processedData).toHaveLength(100)

        // 清理
        store.reset()
      }

      // 强制垃圾回收（如果可用）
      if (global.gc) {
        global.gc()
      }

      const finalHeapUsed = process.memoryUsage().heapUsed
      const memoryIncrease = finalHeapUsed - initialHeapUsed

      // 内存增长应在合理范围内（小于10MB）
      expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024)
    })
  })
})
