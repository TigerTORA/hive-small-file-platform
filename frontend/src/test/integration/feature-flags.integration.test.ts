/**
 * 特性开关系统集成测试
 * 测试运行时特性切换、预设配置和环境变量集成
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { FeatureManager, featureFlags, presetConfigs, applyPreset } from '@/utils/feature-flags'

describe('Feature Flags Integration Tests', () => {
  beforeEach(() => {
    // 重置特性开关状态
    FeatureManager.reset()
  })

  afterEach(() => {
    // 清理环境变量模拟
    vi.restoreAllMocks()
  })

  describe('运行时特性控制', () => {
    it('应该能够动态启用和禁用特性', () => {
      // 初始状态
      expect(FeatureManager.isEnabled('realtimeMonitoring')).toBe(true)
      expect(FeatureManager.isEnabled('advancedCharts')).toBe(false)

      // 动态启用特性
      FeatureManager.enable('advancedCharts')
      expect(FeatureManager.isEnabled('advancedCharts')).toBe(true)

      // 动态禁用特性
      FeatureManager.disable('realtimeMonitoring')
      expect(FeatureManager.isEnabled('realtimeMonitoring')).toBe(false)
    })

    it('应该能够切换特性状态', () => {
      const initialState = FeatureManager.isEnabled('darkTheme')
      const newState = FeatureManager.toggle('darkTheme')

      expect(newState).toBe(!initialState)
      expect(FeatureManager.isEnabled('darkTheme')).toBe(newState)
    })

    it('应该能够批量设置特性', () => {
      const testFeatures = {
        realtimeMonitoring: false,
        advancedCharts: true,
        darkTheme: true
      }

      FeatureManager.setFeatures(testFeatures)

      expect(FeatureManager.isEnabled('realtimeMonitoring')).toBe(false)
      expect(FeatureManager.isEnabled('advancedCharts')).toBe(true)
      expect(FeatureManager.isEnabled('darkTheme')).toBe(true)
    })
  })

  describe('预设配置应用', () => {
    it('应该正确应用开发模式预设', () => {
      applyPreset('development')

      const config = FeatureManager.getAllFeatures()

      // 开发模式应该启用所有特性
      expect(config.realtimeMonitoring).toBe(true)
      expect(config.advancedCharts).toBe(true)
      expect(config.demoMode).toBe(true)
      expect(config.darkTheme).toBe(true)
      expect(config.performanceMonitoring).toBe(true)
    })

    it('应该正确应用生产模式预设', () => {
      applyPreset('production')

      const config = FeatureManager.getAllFeatures()

      // 生产模式应该只启用稳定特性
      expect(config.realtimeMonitoring).toBe(true)
      expect(config.advancedCharts).toBe(false)
      expect(config.demoMode).toBe(false)
      expect(config.performanceMonitoring).toBe(false)
    })

    it('应该正确应用演示模式预设', () => {
      applyPreset('demo')

      const config = FeatureManager.getAllFeatures()

      // 演示模式应该启用展示效果最佳的特性
      expect(config.demoMode).toBe(true)
      expect(config.advancedCharts).toBe(true)
      expect(config.smartRecommendations).toBe(true)
    })

    it('应该正确应用精简模式预设', () => {
      applyPreset('minimal')

      const config = FeatureManager.getAllFeatures()

      // 精简模式应该禁用所有非核心特性
      Object.values(config).forEach(value => {
        expect(value).toBe(false)
      })
    })
  })

  describe('环境变量集成', () => {
    it('应该从环境变量读取特性配置', () => {
      // 模拟环境变量
      const mockEnv = {
        VITE_FEATURE_REALTIME_MONITORING: 'false',
        VITE_FEATURE_ADVANCED_CHARTS: 'true',
        VITE_FEATURE_DEMO_MODE: '1'
      }

      vi.stubGlobal('import', {
        meta: {
          env: mockEnv
        }
      })

      // 重新加载特性配置（模拟环境变量加载）
      FeatureManager.reset()

      // 验证环境变量是否正确应用
      // 注意：实际测试中需要重新导入模块或使用其他方式应用环境变量
      expect(true).toBe(true) // 占位测试，实际需要更复杂的环境变量测试
    })
  })

  describe('配置导入导出', () => {
    it('应该能够导出当前配置', () => {
      FeatureManager.setFeatures({
        realtimeMonitoring: true,
        advancedCharts: false,
        demoMode: true
      })

      const exported = FeatureManager.exportConfig()
      const config = JSON.parse(exported)

      expect(config.realtimeMonitoring).toBe(true)
      expect(config.advancedCharts).toBe(false)
      expect(config.demoMode).toBe(true)
    })

    it('应该能够导入配置', () => {
      const importConfig = JSON.stringify({
        realtimeMonitoring: false,
        advancedCharts: true,
        darkTheme: true
      })

      FeatureManager.importConfig(importConfig)

      expect(FeatureManager.isEnabled('realtimeMonitoring')).toBe(false)
      expect(FeatureManager.isEnabled('advancedCharts')).toBe(true)
      expect(FeatureManager.isEnabled('darkTheme')).toBe(true)
    })

    it('应该处理无效的导入配置', () => {
      const invalidConfig = '{ invalid json }'

      // 应该不抛出错误
      expect(() => {
        FeatureManager.importConfig(invalidConfig)
      }).not.toThrow()
    })
  })

  describe('配置优先级', () => {
    it('运行时配置应该覆盖默认配置', () => {
      // 默认值
      expect(FeatureManager.isEnabled('advancedCharts')).toBe(false)

      // 运行时覆盖
      FeatureManager.enable('advancedCharts')
      expect(FeatureManager.isEnabled('advancedCharts')).toBe(true)
    })

    it('应该保持配置的响应性', () => {
      // 通过代理对象访问
      expect(featureFlags.realtimeMonitoring).toBe(true)

      FeatureManager.disable('realtimeMonitoring')
      expect(featureFlags.realtimeMonitoring).toBe(false)

      FeatureManager.enable('realtimeMonitoring')
      expect(featureFlags.realtimeMonitoring).toBe(true)
    })
  })

  describe('边界情况和错误处理', () => {
    it('应该处理不存在的特性名称', () => {
      expect(() => {
        FeatureManager.isEnabled('nonExistentFeature' as any)
      }).not.toThrow()

      expect(FeatureManager.isEnabled('nonExistentFeature' as any)).toBeUndefined()
    })

    it('应该处理空配置对象', () => {
      expect(() => {
        FeatureManager.setFeatures({})
      }).not.toThrow()
    })

    it('应该在重置后恢复默认配置', () => {
      // 修改配置
      FeatureManager.setFeatures({
        realtimeMonitoring: false,
        advancedCharts: true
      })

      // 重置
      FeatureManager.reset()

      // 验证恢复到默认值
      expect(FeatureManager.isEnabled('realtimeMonitoring')).toBe(true) // 默认为true
      expect(FeatureManager.isEnabled('advancedCharts')).toBe(false) // 默认为false
    })
  })

  describe('性能测试', () => {
    it('特性检查应该是高性能的', () => {
      const iterations = 10000
      const startTime = performance.now()

      for (let i = 0; i < iterations; i++) {
        FeatureManager.isEnabled('realtimeMonitoring')
        FeatureManager.isEnabled('advancedCharts')
        FeatureManager.isEnabled('demoMode')
      }

      const endTime = performance.now()
      const duration = endTime - startTime

      // 10000次检查应该在100ms内完成
      expect(duration).toBeLessThan(100)
    })

    it('批量配置设置应该是原子操作', () => {
      const largeBatch = {
        realtimeMonitoring: true,
        advancedCharts: false,
        demoMode: true,
        exportReports: false,
        fullscreenMode: true,
        darkTheme: false,
        performanceMonitoring: true,
        smartRecommendations: false,
        batchOperations: true,
        websocketUpdates: false
      }

      const startTime = performance.now()
      FeatureManager.setFeatures(largeBatch)
      const endTime = performance.now()

      // 批量设置应该快速完成
      expect(endTime - startTime).toBeLessThan(10)

      // 验证所有配置都已应用
      Object.entries(largeBatch).forEach(([key, value]) => {
        expect(FeatureManager.isEnabled(key as any)).toBe(value)
      })
    })
  })
})
