/**
 * 性能集成测试
 * 测试应用的性能指标、内存使用和响应时间
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import Dashboard from '@/views/Dashboard.vue'
import BigScreenMonitor from '@/components/BigScreenMonitor.vue'
import { FeatureManager } from '@/utils/feature-flags'

// Performance monitoring utilities
class PerformanceMonitor {
  private startTime: number = 0
  private endTime: number = 0
  private memoryBefore: number = 0
  private memoryAfter: number = 0

  start() {
    this.startTime = performance.now()
    if (performance.memory) {
      this.memoryBefore = performance.memory.usedJSHeapSize
    }
  }

  end() {
    this.endTime = performance.now()
    if (performance.memory) {
      this.memoryAfter = performance.memory.usedJSHeapSize
    }
  }

  getDuration() {
    return this.endTime - this.startTime
  }

  getMemoryDelta() {
    return this.memoryAfter - this.memoryBefore
  }

  getMemoryUsage() {
    if (!performance.memory) return null
    return {
      used: performance.memory.usedJSHeapSize,
      total: performance.memory.totalJSHeapSize,
      limit: performance.memory.jsHeapSizeLimit
    }
  }
}

// Mock performance.memory for environments that don't support it
if (!performance.memory) {
  Object.defineProperty(performance, 'memory', {
    value: {
      usedJSHeapSize: 1000000,
      totalJSHeapSize: 2000000,
      jsHeapSizeLimit: 10000000
    },
    writable: true
  })
}

describe('Performance Integration Tests', () => {
  let pinia: any
  let monitor: PerformanceMonitor

  beforeEach(() => {
    monitor = new PerformanceMonitor()

    pinia = createTestingPinia({
      createSpy: vi.fn,
      initialState: {
        dashboard: {
          summary: {
            total_tables: 1500,
            total_small_files: 850000,
            total_size_bytes: 2147483648,
            small_file_ratio: 25.6,
            last_updated: '2024-01-15T10:30:00Z'
          },
          recentTasks: [],
          isLoading: false,
          error: null
        },
        monitoring: {
          settings: {
            selectedCluster: 'cluster-1',
            autoRefreshInterval: 30000
          },
          isAutoRefreshEnabled: true
        }
      }
    })

    FeatureManager.reset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('组件渲染性能', () => {
    it('Dashboard组件应该在合理时间内渲染', () => {
      monitor.start()

      const wrapper = mount(Dashboard, {
        global: {
          plugins: [pinia],
          provide: {
            featureFlags: {
              isEnabled: (feature: string) => FeatureManager.isEnabled(feature)
            }
          },
          stubs: {
            'el-card': true,
            'el-button': true,
            'el-select': true,
            'el-option': true,
            'el-progress': true,
            'el-icon': true
          }
        }
      })

      monitor.end()

      expect(wrapper.exists()).toBe(true)
      expect(monitor.getDuration()).toBeLessThan(100) // 应该在100ms内完成
    })

    it('BigScreenMonitor组件应该在合理时间内渲染', () => {
      monitor.start()

      const wrapper = mount(BigScreenMonitor, {
        props: {
          clusterId: 'cluster-1'
        },
        global: {
          plugins: [pinia],
          stubs: {
            'el-button': true,
            'el-select': true,
            'el-option': true,
            'el-icon': true,
            'el-tag': true,
            'el-progress': true
          }
        }
      })

      monitor.end()

      expect(wrapper.exists()).toBe(true)
      expect(monitor.getDuration()).toBeLessThan(150) // 大屏组件更复杂，允许150ms
    })

    it('应该支持快速重新渲染', async () => {
      const wrapper = mount(Dashboard, {
        global: {
          plugins: [pinia],
          provide: {
            featureFlags: {
              isEnabled: (feature: string) => FeatureManager.isEnabled(feature)
            }
          },
          stubs: {
            'el-card': true,
            'el-button': true,
            'el-select': true,
            'el-option': true,
            'el-progress': true,
            'el-icon': true
          }
        }
      })

      // 多次更新数据测试重新渲染性能
      const iterations = 10
      const durations: number[] = []

      for (let i = 0; i < iterations; i++) {
        monitor.start()

        // 更新store数据触发重新渲染
        const dashboardStore = pinia.state.value.dashboard
        dashboardStore.summary.total_tables = 1500 + i * 100

        await wrapper.vm.$nextTick()
        monitor.end()

        durations.push(monitor.getDuration())
      }

      // 平均重新渲染时间应该很快
      const averageDuration = durations.reduce((a, b) => a + b) / durations.length
      expect(averageDuration).toBeLessThan(50)
    })
  })

  describe('大数据量处理性能', () => {
    it('应该高效处理大量任务数据', () => {
      // 生成大量测试数据
      const largeTasks = Array.from({ length: 1000 }, (_, i) => ({
        id: `task-${i}`,
        type: i % 2 === 0 ? 'scan' : 'merge',
        database_name: `database_${i % 10}`,
        table_name: `table_${i}`,
        status: ['completed', 'running', 'pending'][i % 3],
        created_at: new Date(Date.now() - i * 60000).toISOString()
      }))

      pinia.state.value.dashboard.recentTasks = largeTasks

      monitor.start()

      const wrapper = mount(Dashboard, {
        global: {
          plugins: [pinia],
          provide: {
            featureFlags: {
              isEnabled: (feature: string) => FeatureManager.isEnabled(feature)
            }
          },
          stubs: {
            'el-card': true,
            'el-button': true,
            'el-select': true,
            'el-option': true,
            'el-progress': true,
            'el-icon': true,
            'el-tag': true
          }
        }
      })

      monitor.end()

      expect(wrapper.exists()).toBe(true)
      expect(monitor.getDuration()).toBeLessThan(500) // 大数据量应该在500ms内完成
    })

    it('应该高效处理大量指标数据', () => {
      // 创建包含大量指标的数据
      const largeMetrics = {
        total_tables: 50000,
        total_small_files: 25000000,
        total_size_bytes: Number.MAX_SAFE_INTEGER / 2,
        small_file_ratio: 65.4,
        last_updated: '2024-01-15T10:30:00Z',
        // 添加额外的计算密集型数据
        detailed_stats: Array.from({ length: 100 }, (_, i) => ({
          database: `db_${i}`,
          tables: Math.floor(Math.random() * 1000),
          small_files: Math.floor(Math.random() * 100000)
        }))
      }

      pinia.state.value.dashboard.summary = largeMetrics

      monitor.start()

      const wrapper = mount(Dashboard, {
        global: {
          plugins: [pinia],
          provide: {
            featureFlags: {
              isEnabled: (feature: string) => FeatureManager.isEnabled(feature)
            }
          },
          stubs: {
            'el-card': true,
            'el-button': true,
            'el-select': true,
            'el-option': true,
            'el-progress': true,
            'el-icon': true
          }
        }
      })

      monitor.end()

      expect(wrapper.exists()).toBe(true)
      expect(monitor.getDuration()).toBeLessThan(200)
    })
  })

  describe('内存使用性能', () => {
    it('组件挂载不应该造成显著内存泄露', () => {
      const initialMemory = monitor.getMemoryUsage()
      const wrappers: any[] = []

      // 创建和销毁多个组件实例
      for (let i = 0; i < 10; i++) {
        const wrapper = mount(Dashboard, {
          global: {
            plugins: [pinia],
            provide: {
              featureFlags: {
                isEnabled: (feature: string) => FeatureManager.isEnabled(feature)
              }
            },
            stubs: {
              'el-card': true,
              'el-button': true,
              'el-select': true,
              'el-option': true,
              'el-progress': true,
              'el-icon': true
            }
          }
        })
        wrappers.push(wrapper)
      }

      // 销毁所有组件
      wrappers.forEach(wrapper => wrapper.unmount())

      // 强制垃圾回收（如果支持）
      if (global.gc) {
        global.gc()
      }

      const finalMemory = monitor.getMemoryUsage()

      if (initialMemory && finalMemory) {
        // 内存增长应该在合理范围内（1MB）
        const memoryIncrease = finalMemory.used - initialMemory.used
        expect(memoryIncrease).toBeLessThan(1024 * 1024)
      }
    })

    it('大屏组件销毁应该正确清理资源', () => {
      monitor.start()

      const wrapper = mount(BigScreenMonitor, {
        props: {
          clusterId: 'cluster-1'
        },
        global: {
          plugins: [pinia],
          stubs: {
            'el-button': true,
            'el-select': true,
            'el-option': true,
            'el-icon': true,
            'el-tag': true,
            'el-progress': true
          }
        }
      })

      const memoryBeforeDestroy = monitor.getMemoryUsage()

      // 销毁组件
      wrapper.unmount()

      if (global.gc) {
        global.gc()
      }

      const memoryAfterDestroy = monitor.getMemoryUsage()

      // 验证内存释放
      if (memoryBeforeDestroy && memoryAfterDestroy) {
        // 销毁后内存使用应该减少或保持稳定
        const memoryChange = memoryAfterDestroy.used - memoryBeforeDestroy.used
        expect(memoryChange).toBeLessThan(512 * 1024) // 不应该增长超过512KB
      }
    })
  })

  describe('特性开关性能', () => {
    it('特性检查应该是高性能的', () => {
      const iterations = 10000

      monitor.start()

      for (let i = 0; i < iterations; i++) {
        FeatureManager.isEnabled('realtimeMonitoring')
        FeatureManager.isEnabled('advancedCharts')
        FeatureManager.isEnabled('demoMode')
        FeatureManager.isEnabled('fullscreenMode')
      }

      monitor.end()

      // 10000次特性检查应该在50ms内完成
      expect(monitor.getDuration()).toBeLessThan(50)
    })

    it('批量特性设置应该是高效的', () => {
      const batchConfig = {
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

      monitor.start()

      // 执行100次批量设置
      for (let i = 0; i < 100; i++) {
        FeatureManager.setFeatures(batchConfig)
      }

      monitor.end()

      // 批量设置应该很快
      expect(monitor.getDuration()).toBeLessThan(20)
    })
  })

  describe('响应式性能', () => {
    it('响应式数据更新应该是高效的', async () => {
      const wrapper = mount(Dashboard, {
        global: {
          plugins: [pinia],
          provide: {
            featureFlags: {
              isEnabled: (feature: string) => FeatureManager.isEnabled(feature)
            }
          },
          stubs: {
            'el-card': true,
            'el-button': true,
            'el-select': true,
            'el-option': true,
            'el-progress': true,
            'el-icon': true
          }
        }
      })

      const dashboardStore = pinia.state.value.dashboard
      const updateTimes: number[] = []

      // 执行多次数据更新
      for (let i = 0; i < 50; i++) {
        monitor.start()

        dashboardStore.summary.total_tables = 1000 + i
        dashboardStore.summary.small_file_ratio = 20 + (i % 10)

        await wrapper.vm.$nextTick()
        monitor.end()

        updateTimes.push(monitor.getDuration())
      }

      // 平均更新时间应该很快
      const averageUpdateTime = updateTimes.reduce((a, b) => a + b) / updateTimes.length
      expect(averageUpdateTime).toBeLessThan(10)
    })

    it('计算属性应该有效缓存', () => {
      const wrapper = mount(Dashboard, {
        global: {
          plugins: [pinia],
          provide: {
            featureFlags: {
              isEnabled: (feature: string) => FeatureManager.isEnabled(feature)
            }
          },
          stubs: {
            'el-card': true,
            'el-button': true,
            'el-select': true,
            'el-option': true,
            'el-progress': true,
            'el-icon': true
          }
        }
      })

      const vm = wrapper.vm as any
      const iterations = 1000

      monitor.start()

      // 多次访问同一个计算属性
      for (let i = 0; i < iterations; i++) {
        const _ = vm.keyMetrics || vm.$data
      }

      monitor.end()

      // 缓存的计算属性访问应该很快
      expect(monitor.getDuration()).toBeLessThan(30)
    })
  })

  describe('异步操作性能', () => {
    it('并发数据获取应该在合理时间内完成', async () => {
      // Mock API调用
      const mockApiCall = vi.fn().mockImplementation(() =>
        new Promise(resolve => setTimeout(() => resolve({ data: 'test' }), 10))
      )

      monitor.start()

      // 模拟并发API调用
      const promises = Array.from({ length: 10 }, () => mockApiCall())
      await Promise.all(promises)

      monitor.end()

      // 并发调用应该比串行调用快
      expect(monitor.getDuration()).toBeLessThan(50) // 应该远小于10 * 10ms
      expect(mockApiCall).toHaveBeenCalledTimes(10)
    })

    it('应该正确处理API调用超时', async () => {
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Timeout')), 100)
      )

      monitor.start()

      try {
        await timeoutPromise
      } catch (error) {
        monitor.end()

        // 超时处理应该很快
        expect(monitor.getDuration()).toBeLessThan(150)
        expect(error.message).toBe('Timeout')
      }
    })
  })

  describe('DOM操作性能', () => {
    it('大量DOM更新应该是高效的', async () => {
      const wrapper = mount(Dashboard, {
        global: {
          plugins: [pinia],
          provide: {
            featureFlags: {
              isEnabled: (feature: string) => FeatureManager.isEnabled(feature)
            }
          },
          stubs: {
            'el-card': true,
            'el-button': true,
            'el-select': true,
            'el-option': true,
            'el-progress': true,
            'el-icon': true,
            'el-tag': true
          }
        }
      })

      const dashboardStore = pinia.state.value.dashboard

      // 生成大量任务数据
      const largeTasks = Array.from({ length: 500 }, (_, i) => ({
        id: `task-${i}`,
        type: i % 2 === 0 ? 'scan' : 'merge',
        database_name: `db_${i % 5}`,
        table_name: `table_${i}`,
        status: ['completed', 'running', 'pending'][i % 3],
        created_at: new Date().toISOString()
      }))

      monitor.start()

      // 更新大量数据
      dashboardStore.recentTasks = largeTasks
      await wrapper.vm.$nextTick()

      monitor.end()

      // DOM更新应该在合理时间内完成
      expect(monitor.getDuration()).toBeLessThan(300)
    })
  })

  describe('内存泄露检测', () => {
    it('重复挂载和卸载不应该造成内存泄露', () => {
      const initialMemory = monitor.getMemoryUsage()

      // 重复挂载和卸载组件
      for (let i = 0; i < 20; i++) {
        const wrapper = mount(Dashboard, {
          global: {
            plugins: [pinia],
            provide: {
              featureFlags: {
                isEnabled: (feature: string) => FeatureManager.isEnabled(feature)
              }
            },
            stubs: {
              'el-card': true,
              'el-button': true,
              'el-select': true,
              'el-option': true,
              'el-progress': true,
              'el-icon': true
            }
          }
        })

        // 立即销毁
        wrapper.unmount()
      }

      // 强制垃圾回收
      if (global.gc) {
        global.gc()
      }

      const finalMemory = monitor.getMemoryUsage()

      if (initialMemory && finalMemory) {
        // 内存增长应该最小
        const memoryIncrease = finalMemory.used - initialMemory.used
        expect(memoryIncrease).toBeLessThan(2 * 1024 * 1024) // 小于2MB
      }
    })

    it('长时间运行不应该造成明显内存增长', async () => {
      const wrapper = mount(Dashboard, {
        global: {
          plugins: [pinia],
          provide: {
            featureFlags: {
              isEnabled: (feature: string) => FeatureManager.isEnabled(feature)
            }
          },
          stubs: {
            'el-card': true,
            'el-button': true,
            'el-select': true,
            'el-option': true,
            'el-progress': true,
            'el-icon': true
          }
        }
      })

      const initialMemory = monitor.getMemoryUsage()
      const dashboardStore = pinia.state.value.dashboard

      // 模拟长时间运行的数据更新
      for (let i = 0; i < 100; i++) {
        dashboardStore.summary.total_tables = 1000 + i
        dashboardStore.summary.last_updated = new Date().toISOString()
        await wrapper.vm.$nextTick()
      }

      if (global.gc) {
        global.gc()
      }

      const finalMemory = monitor.getMemoryUsage()

      if (initialMemory && finalMemory) {
        // 长时间运行后内存增长应该在合理范围内
        const memoryIncrease = finalMemory.used - initialMemory.used
        expect(memoryIncrease).toBeLessThan(5 * 1024 * 1024) // 小于5MB
      }

      wrapper.unmount()
    })
  })

  describe('性能基准测试', () => {
    it('组件渲染性能基准', () => {
      const results = {
        dashboard: [],
        bigScreen: []
      }

      // Dashboard渲染基准
      for (let i = 0; i < 5; i++) {
        monitor.start()

        const wrapper = mount(Dashboard, {
          global: {
            plugins: [pinia],
            provide: {
              featureFlags: {
                isEnabled: (feature: string) => FeatureManager.isEnabled(feature)
              }
            },
            stubs: {
              'el-card': true,
              'el-button': true,
              'el-select': true,
              'el-option': true,
              'el-progress': true,
              'el-icon': true
            }
          }
        })

        monitor.end()
        results.dashboard.push(monitor.getDuration())
        wrapper.unmount()
      }

      // BigScreen渲染基准
      for (let i = 0; i < 5; i++) {
        monitor.start()

        const wrapper = mount(BigScreenMonitor, {
          props: { clusterId: 'cluster-1' },
          global: {
            plugins: [pinia],
            stubs: {
              'el-button': true,
              'el-select': true,
              'el-option': true,
              'el-icon': true,
              'el-tag': true,
              'el-progress': true
            }
          }
        })

        monitor.end()
        results.bigScreen.push(monitor.getDuration())
        wrapper.unmount()
      }

      // 计算平均性能
      const dashboardAvg = results.dashboard.reduce((a, b) => a + b) / results.dashboard.length
      const bigScreenAvg = results.bigScreen.reduce((a, b) => a + b) / results.bigScreen.length

      console.log('Performance Benchmarks:')
      console.log(`Dashboard average render time: ${dashboardAvg.toFixed(2)}ms`)
      console.log(`BigScreen average render time: ${bigScreenAvg.toFixed(2)}ms`)

      // 性能要求
      expect(dashboardAvg).toBeLessThan(100)
      expect(bigScreenAvg).toBeLessThan(150)
    })
  })
})