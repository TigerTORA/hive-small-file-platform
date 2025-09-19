/**
 * 监控系统集成测试
 * 测试监控设置、自动刷新、主题切换等核心功能
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMonitoringStore } from '../../stores/monitoring'

describe('Monitoring Store Integration Tests', () => {
  let store: ReturnType<typeof useMonitoringStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useMonitoringStore()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllTimers()
  })

  describe('监控设置管理', () => {
    it('应该有正确的默认设置', () => {
      expect(store.settings.autoRefresh).toBe(true)
      expect(store.settings.refreshInterval).toBe(60)
      expect(store.settings.selectedCluster).toBe(null) // 默认为null，因为没有localStorage数据
      expect(store.settings.theme).toBe('light')
      expect(store.settings.chartColors).toHaveLength(8)
    })

    it('应该能够更新刷新间隔', () => {
      store.setRefreshInterval(120)
      expect(store.settings.refreshInterval).toBe(120)
    })

    it('应该能够切换自动刷新状态', () => {
      expect(store.settings.autoRefresh).toBe(true)
      store.toggleAutoRefresh()
      expect(store.settings.autoRefresh).toBe(false)
      store.toggleAutoRefresh()
      expect(store.settings.autoRefresh).toBe(true)
    })

    it('应该能够选择不同的集群', () => {
      store.setSelectedCluster(2)
      expect(store.settings.selectedCluster).toBe(2)

      store.setSelectedCluster(null)
      expect(store.settings.selectedCluster).toBe(null)
    })

    it('应该能够批量更新设置', () => {
      store.updateSettings({
        refreshInterval: 300,
        theme: 'dark',
        selectedCluster: 3
      })

      expect(store.settings.refreshInterval).toBe(300)
      expect(store.settings.theme).toBe('dark')
      expect(store.settings.selectedCluster).toBe(3)
    })
  })

  describe('主题管理', () => {
    it('应该能够切换主题', () => {
      expect(store.settings.theme).toBe('light')
      store.setTheme('dark')
      expect(store.settings.theme).toBe('dark')
      store.setTheme('light')
      expect(store.settings.theme).toBe('light')
    })

    it('应该能够获取图表主题配置', () => {
      const lightTheme = store.getChartTheme()
      expect(lightTheme.backgroundColor).toBe('#ffffff')
      expect(lightTheme.textStyle.color).toBe('#333333')

      store.setTheme('dark')
      const darkTheme = store.getChartTheme()
      expect(darkTheme.backgroundColor).toBe('#1f1f1f')
      expect(darkTheme.textStyle.color).toBe('#ffffff')
    })

    it('应该能够获取图表颜色', () => {
      const firstColor = store.getChartColor(0)
      expect(firstColor).toBe('#409EFF')

      const secondColor = store.getChartColor(1)
      expect(secondColor).toBe('#67C23A')

      // 测试循环
      const ninthColor = store.getChartColor(8)
      expect(ninthColor).toBe(firstColor)
    })
  })

  describe('计算属性验证', () => {
    it('应该正确计算刷新间隔选项', () => {
      const options = store.refreshIntervalOptions
      expect(options).toHaveLength(5)
      expect(options[0]).toEqual({ label: '30秒', value: 30 })
      expect(options[4]).toEqual({ label: '10分钟', value: 600 })
    })

    it('应该正确反映自动刷新状态', () => {
      expect(store.isAutoRefreshEnabled).toBe(true)
      store.toggleAutoRefresh()
      expect(store.isAutoRefreshEnabled).toBe(false)
    })

    it('应该计算距离下次刷新的时间', () => {
      // 设置上次刷新时间
      store.triggerRefresh()

      // 前进30秒
      vi.advanceTimersByTime(30000)

      const timeUntilNext = store.timeUntilNextRefresh
      expect(timeUntilNext).toBe(30) // 60 - 30 = 30秒
    })

    it('自动刷新禁用时距离下次刷新时间应为0', () => {
      store.toggleAutoRefresh() // 禁用自动刷新
      const timeUntilNext = store.timeUntilNextRefresh
      expect(timeUntilNext).toBe(0)
    })
  })

  describe('自动刷新功能', () => {
    it('应该能够设置自动刷新', () => {
      const mockCallback = vi.fn()

      store.setupAutoRefresh(mockCallback)

      // 模拟时间流逝
      vi.advanceTimersByTime(60000)

      expect(mockCallback).toHaveBeenCalled()
    })

    it('应该能够清除自动刷新', () => {
      const mockCallback = vi.fn()

      store.setupAutoRefresh(mockCallback)
      store.clearAutoRefresh()

      // 模拟时间流逝
      vi.advanceTimersByTime(60000)

      // 因为已清除，不应该被调用
      expect(mockCallback).not.toHaveBeenCalled()
    })

    it('应该能够手动触发刷新', () => {
      const mockCallback = vi.fn()

      store.triggerRefresh(mockCallback)

      expect(mockCallback).toHaveBeenCalled()
      expect(store.lastRefreshTime).not.toBe(null)
    })

    it('禁用自动刷新时不应启动定时器', () => {
      store.toggleAutoRefresh() // 禁用自动刷新

      const mockCallback = vi.fn()
      store.setupAutoRefresh(mockCallback)

      // 模拟时间流逝
      vi.advanceTimersByTime(60000)

      // 因为自动刷新被禁用，不应该被调用
      expect(mockCallback).not.toHaveBeenCalled()
    })
  })

  describe('格式化工具', () => {
    it('应该正确格式化文件大小', () => {
      expect(store.formatFileSize(0)).toBe('0 B')
      expect(store.formatFileSize(1024)).toBe('1 KB')
      expect(store.formatFileSize(1024 * 1024)).toBe('1 MB')
      expect(store.formatFileSize(1024 * 1024 * 1024)).toBe('1 GB')
      expect(store.formatFileSize(1536)).toBe('1.5 KB')
    })

    it('应该正确格式化数字', () => {
      expect(store.formatNumber(999)).toBe('999')
      expect(store.formatNumber(1000)).toBe('1.0K')
      expect(store.formatNumber(1500)).toBe('1.5K')
      expect(store.formatNumber(1000000)).toBe('1.0M')
      expect(store.formatNumber(1500000)).toBe('1.5M')
    })

    it('应该正确格式化日期', () => {
      const testDate = new Date('2023-12-25T15:30:00')
      const formatted = store.formatDate(testDate)

      // 验证格式符合中文日期格式
      expect(formatted).toMatch(/\d{2}\/\d{2}\s+\d{2}:\d{2}/)
    })
  })

  describe('设置持久化', () => {
    it('应该支持从localStorage加载设置', () => {
      const savedSettings = {
        autoRefresh: false,
        refreshInterval: 300,
        selectedCluster: 3, // 与单独存储的selectedCluster保持一致
        theme: 'dark',
        chartColors: ['#FF0000']
      }

      // 使用 vi.stubGlobal 来mock localStorage
      const mockLocalStorage = {
        getItem: vi.fn((key: string) => {
          if (key === 'monitoring-settings') {
            return JSON.stringify(savedSettings)
          }
          if (key === 'selectedCluster') {
            return '3'
          }
          return null
        }),
        setItem: vi.fn(),
        removeItem: vi.fn()
      }

      vi.stubGlobal('localStorage', mockLocalStorage)

      // 创建新的pinia实例
      setActivePinia(createPinia())

      // 重新创建store，这样在初始化时就会使用mock的localStorage
      const newStore = useMonitoringStore()

      // 手动调用loadSettings来从localStorage加载设置
      newStore.loadSettings()

      expect(newStore.settings.autoRefresh).toBe(false)
      expect(newStore.settings.refreshInterval).toBe(300)
      expect(newStore.settings.selectedCluster).toBe(3)
      expect(newStore.settings.theme).toBe('dark')
      expect(newStore.settings.chartColors).toEqual(['#FF0000'])

      // 清理mock
      vi.unstubAllGlobals()
    })
  })

  describe('集成场景测试', () => {
    it('应该支持完整的监控设置工作流', () => {
      // 1. 初始化设置
      expect(store.settings.autoRefresh).toBe(true)

      // 2. 用户选择集群
      store.setSelectedCluster(2)

      // 3. 调整刷新间隔
      store.setRefreshInterval(120)

      // 4. 切换主题
      store.setTheme('dark')

      // 5. 启动自动刷新
      const mockCallback = vi.fn()
      store.setupAutoRefresh(mockCallback)

      // 6. 验证设置
      expect(store.settings.selectedCluster).toBe(2)
      expect(store.settings.refreshInterval).toBe(120)
      expect(store.settings.theme).toBe('dark')

      // 7. 停止自动刷新
      store.clearAutoRefresh()
    })

    it('应该能够重新配置监控参数', () => {
      const mockCallback = vi.fn()

      // 启动监控
      store.setupAutoRefresh(mockCallback)

      // 切换集群并重新配置
      store.setSelectedCluster(3)
      store.setRefreshInterval(300)
      store.setupAutoRefresh(mockCallback)

      expect(store.settings.selectedCluster).toBe(3)
      expect(store.settings.refreshInterval).toBe(300)
    })

    it('应该支持主题切换并影响图表样式', () => {
      // 验证浅色主题
      expect(store.settings.theme).toBe('light')
      const lightTheme = store.getChartTheme()
      expect(lightTheme.backgroundColor).toBe('#ffffff')

      // 切换到深色主题
      store.setTheme('dark')
      const darkTheme = store.getChartTheme()
      expect(darkTheme.backgroundColor).toBe('#1f1f1f')
      expect(darkTheme.textStyle.color).toBe('#ffffff')
    })
  })

  describe('生命周期管理', () => {
    it('应该能够正确初始化', () => {
      store.initialize()

      expect(store.lastRefreshTime).not.toBe(null)
      expect(store.settings.theme).toBeDefined()
    })

    it('应该能够正确清理资源', () => {
      const mockCallback = vi.fn()

      // 设置一些需要清理的资源
      store.setupAutoRefresh(mockCallback)

      // 清理
      store.cleanup()

      // 验证定时器已被清理
      vi.advanceTimersByTime(60000)
      expect(mockCallback).not.toHaveBeenCalled()
    })
  })

  describe('错误处理和边界情况', () => {
    it('应该优雅处理存储错误', () => {
      const mockConsoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {})

      // 这应该不会抛出错误，即使localStorage失败
      expect(() => store.saveSettings()).not.toThrow()
    })

    it('应该正确处理时间计算', () => {
      // 没有上次刷新时间时
      expect(store.timeUntilNextRefresh).toBe(0)

      // 设置上次刷新时间
      store.triggerRefresh()
      expect(store.timeUntilNextRefresh).toBeGreaterThan(0)
    })

    it('应该处理图表颜色索引越界', () => {
      const color = store.getChartColor(100) // 远超数组长度
      expect(store.settings.chartColors).toContain(color) // 应该是有效的颜色
    })
  })
})
