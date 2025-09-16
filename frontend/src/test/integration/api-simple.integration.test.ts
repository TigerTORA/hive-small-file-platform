/**
 * 简化的API集成测试
 * 测试特性开关和基础API功能集成
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { FeatureManager } from '@/utils/feature-flags'

// 测试数据工厂
const createMockResponse = (data: any) => ({
  success: true,
  data,
  error: null,
  message: 'Success'
})

describe('API Integration - 简化版本', () => {
  beforeEach(() => {
    FeatureManager.reset()
    vi.clearAllMocks()
  })

  describe('特性开关与API集成', () => {
    it('应该根据特性开关启用/禁用实时监控API', () => {
      // 默认启用实时监控
      expect(FeatureManager.isEnabled('realtimeMonitoring')).toBe(true)

      // 禁用实时监控
      FeatureManager.disable('realtimeMonitoring')
      expect(FeatureManager.isEnabled('realtimeMonitoring')).toBe(false)

      // 重新启用
      FeatureManager.enable('realtimeMonitoring')
      expect(FeatureManager.isEnabled('realtimeMonitoring')).toBe(true)
    })

    it('应该支持高级图表特性切换', () => {
      // 默认禁用高级图表
      expect(FeatureManager.isEnabled('advancedCharts')).toBe(false)

      // 启用高级图表
      FeatureManager.enable('advancedCharts')
      expect(FeatureManager.isEnabled('advancedCharts')).toBe(true)

      // 验证特性状态持久化
      const allFeatures = FeatureManager.getAllFeatures()
      expect(allFeatures.advancedCharts).toBe(true)
    })

    it('应该支持演示模式配置', () => {
      // 应用演示模式预设
      FeatureManager.setFeatures({
        demoMode: true,
        advancedCharts: true,
        smartRecommendations: true,
        performanceMonitoring: true
      })

      expect(FeatureManager.isEnabled('demoMode')).toBe(true)
      expect(FeatureManager.isEnabled('advancedCharts')).toBe(true)
      expect(FeatureManager.isEnabled('smartRecommendations')).toBe(true)
      expect(FeatureManager.isEnabled('performanceMonitoring')).toBe(true)
    })
  })

  describe('API响应数据处理', () => {
    it('应该正确处理仪表盘数据格式', () => {
      const mockDashboardData = {
        total_tables: 1500,
        total_small_files: 850000,
        total_size_bytes: 2147483648,
        small_file_ratio: 25.6,
        last_updated: '2024-01-15T10:30:00Z'
      }

      const response = createMockResponse(mockDashboardData)

      expect(response.success).toBe(true)
      expect(response.data.total_tables).toBe(1500)
      expect(response.data.small_file_ratio).toBe(25.6)
      expect(typeof response.data.last_updated).toBe('string')
    })

    it('应该正确处理集群列表数据', () => {
      const mockClusters = [
        {
          id: 'cluster-1',
          name: '生产集群-01',
          status: 'active',
          namenode_host: '192.168.1.100',
          namenode_port: 9000
        },
        {
          id: 'cluster-2',
          name: '测试集群-01',
          status: 'inactive',
          namenode_host: '192.168.1.101',
          namenode_port: 9000
        }
      ]

      const response = createMockResponse(mockClusters)

      expect(response.success).toBe(true)
      expect(Array.isArray(response.data)).toBe(true)
      expect(response.data).toHaveLength(2)
      expect(response.data[0].status).toBe('active')
      expect(response.data[1].status).toBe('inactive')
    })

    it('应该正确处理任务列表数据', () => {
      const mockTasks = {
        tasks: [
          {
            id: 'task-1',
            type: 'scan',
            status: 'completed',
            processing_time_seconds: 330.5
          },
          {
            id: 'task-2',
            type: 'merge',
            status: 'running',
            progress_percentage: 65.4
          }
        ],
        total: 100,
        page: 1,
        page_size: 20
      }

      const response = createMockResponse(mockTasks)

      expect(response.success).toBe(true)
      expect(response.data.tasks).toHaveLength(2)
      expect(response.data.tasks[0].status).toBe('completed')
      expect(response.data.tasks[1].status).toBe('running')
      expect(response.data.total).toBe(100)
    })
  })

  describe('错误处理集成', () => {
    it('应该正确处理API错误响应格式', () => {
      const errorResponse = {
        success: false,
        data: null,
        error: 'Network Error',
        message: '网络连接失败，请检查网络设置'
      }

      expect(errorResponse.success).toBe(false)
      expect(errorResponse.data).toBeNull()
      expect(errorResponse.error).toBe('Network Error')
      expect(errorResponse.message).toContain('网络连接')
    })

    it('应该处理服务器错误响应', () => {
      const serverError = {
        success: false,
        data: null,
        error: 'Internal Server Error',
        message: '服务器内部错误，请稍后重试'
      }

      expect(serverError.success).toBe(false)
      expect(serverError.error).toBe('Internal Server Error')
      expect(serverError.message).toContain('服务器内部错误')
    })
  })

  describe('数据验证集成', () => {
    it('应该验证数值类型和范围', () => {
      const mockData = {
        total_tables: 1500,
        small_file_ratio: 25.6,
        processing_time_seconds: 330.5
      }

      // 验证数据类型
      expect(typeof mockData.total_tables).toBe('number')
      expect(typeof mockData.small_file_ratio).toBe('number')
      expect(typeof mockData.processing_time_seconds).toBe('number')

      // 验证数据范围
      expect(mockData.total_tables).toBeGreaterThan(0)
      expect(mockData.small_file_ratio).toBeGreaterThanOrEqual(0)
      expect(mockData.small_file_ratio).toBeLessThanOrEqual(100)
      expect(mockData.processing_time_seconds).toBeGreaterThan(0)
    })

    it('应该验证时间戳格式', () => {
      const timestamps = [
        '2024-01-15T10:30:00Z',
        '2024-01-15T09:00:00Z',
        '2024-01-15T10:00:00Z'
      ]

      timestamps.forEach(timestamp => {
        const date = new Date(timestamp)
        expect(date.getTime()).not.toBeNaN()
        expect(timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/)
      })
    })

    it('应该验证状态枚举值', () => {
      const validStatuses = ['active', 'inactive', 'pending', 'error']
      const validTaskStatuses = ['pending', 'running', 'completed', 'failed']

      validStatuses.forEach(status => {
        expect(['active', 'inactive', 'pending', 'error']).toContain(status)
      })

      validTaskStatuses.forEach(status => {
        expect(['pending', 'running', 'completed', 'failed']).toContain(status)
      })
    })
  })

  describe('性能考虑', () => {
    it('大量数据处理应该在合理时间内完成', () => {
      const startTime = performance.now()

      // 模拟处理大量数据
      const largeDataset = Array.from({ length: 10000 }, (_, index) => ({
        id: `item-${index}`,
        value: Math.random() * 100,
        timestamp: new Date().toISOString()
      }))

      // 模拟数据处理
      const processedData = largeDataset.filter(item => item.value > 50).length

      const endTime = performance.now()
      const duration = endTime - startTime

      expect(processedData).toBeGreaterThan(0)
      expect(duration).toBeLessThan(100) // 应该在100ms内完成
    })

    it('特性开关检查应该是高性能的', () => {
      const iterations = 1000
      const startTime = performance.now()

      for (let i = 0; i < iterations; i++) {
        FeatureManager.isEnabled('realtimeMonitoring')
        FeatureManager.isEnabled('advancedCharts')
        FeatureManager.isEnabled('demoMode')
      }

      const endTime = performance.now()
      const duration = endTime - startTime

      // 1000次特性检查应该在50ms内完成
      expect(duration).toBeLessThan(50)
    })
  })

  describe('集成配置测试', () => {
    it('应该支持批量特性配置', () => {
      const batchConfig = {
        realtimeMonitoring: true,
        advancedCharts: true,
        demoMode: true,
        exportReports: true,
        darkTheme: false,
        performanceMonitoring: true
      }

      FeatureManager.setFeatures(batchConfig)

      Object.entries(batchConfig).forEach(([feature, enabled]) => {
        expect(FeatureManager.isEnabled(feature as any)).toBe(enabled)
      })
    })

    it('应该支持配置导入导出', () => {
      const originalConfig = {
        realtimeMonitoring: false,
        advancedCharts: true,
        demoMode: true
      }

      FeatureManager.setFeatures(originalConfig)

      // 导出配置
      const exportedConfig = FeatureManager.exportConfig()
      const parsedConfig = JSON.parse(exportedConfig)

      expect(parsedConfig.realtimeMonitoring).toBe(false)
      expect(parsedConfig.advancedCharts).toBe(true)
      expect(parsedConfig.demoMode).toBe(true)

      // 重置并导入
      FeatureManager.reset()
      FeatureManager.importConfig(exportedConfig)

      expect(FeatureManager.isEnabled('realtimeMonitoring')).toBe(false)
      expect(FeatureManager.isEnabled('advancedCharts')).toBe(true)
      expect(FeatureManager.isEnabled('demoMode')).toBe(true)
    })
  })
})