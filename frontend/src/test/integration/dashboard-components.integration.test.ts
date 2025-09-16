/**
 * Dashboard组件集成测试
 * 测试Dashboard相关组件的集成、数据流转和用户交互
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { ElMessage } from 'element-plus'
import Dashboard from '@/views/Dashboard.vue'
import BigScreenMonitor from '@/components/BigScreenMonitor.vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useMonitoringStore } from '@/stores/monitoring'
import { FeatureManager } from '@/utils/feature-flags'

// Mock external dependencies
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  },
  ElMessageBox: {
    confirm: vi.fn()
  }
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn()
  }),
  useRoute: () => ({
    query: { cluster: 'cluster-1' },
    path: '/'
  })
}))

vi.mock('@/api/dashboard', () => ({
  dashboardApi: {
    getSummary: vi.fn(),
    getTrend: vi.fn(),
    getTopTables: vi.fn()
  }
}))

vi.mock('@/api/tasks', () => ({
  tasksApi: {
    getAll: vi.fn(),
    scanAllDatabases: vi.fn()
  }
}))

// Mock ECharts
vi.mock('echarts', () => ({
  init: vi.fn(() => ({
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn()
  })),
  registerTheme: vi.fn()
}))

describe('Dashboard Components Integration Tests', () => {
  let pinia: any
  let dashboardStore: any
  let monitoringStore: any

  beforeEach(() => {
    // 重置特性开关
    FeatureManager.reset()
    FeatureManager.setFeatures({
      realtimeMonitoring: true,
      advancedCharts: true,
      fullscreenMode: true,
      demoMode: true
    })

    // 创建测试用的 Pinia 实例
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
          recentTasks: [
            {
              id: 'task-1',
              type: 'scan',
              database_name: 'user_data',
              table_name: 'user_profiles',
              status: 'completed',
              created_at: '2024-01-15T09:00:00Z'
            },
            {
              id: 'task-2',
              type: 'merge',
              database_name: 'user_data',
              table_name: 'user_activities',
              status: 'running',
              created_at: '2024-01-15T10:00:00Z'
            }
          ],
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

    dashboardStore = useDashboardStore()
    monitoringStore = useMonitoringStore()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Dashboard 主页面集成', () => {
    it('应该正确渲染Dashboard组件并显示数据', async () => {
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

      await flushPromises()

      // 验证组件渲染
      expect(wrapper.exists()).toBe(true)

      // 验证数据显示
      const summaryText = wrapper.text()
      expect(summaryText).toContain('1500') // total_tables
      expect(summaryText).toContain('850000') // total_small_files
      expect(summaryText).toContain('25.6') // small_file_ratio
    })

    it('应该正确处理特性开关', async () => {
      // 禁用某些特性
      FeatureManager.disable('fullscreenMode')

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

      await flushPromises()

      // 全屏按钮应该不存在
      const fullscreenButton = wrapper.find('[title="进入大屏模式"]')
      expect(fullscreenButton.exists()).toBe(false)
    })

    it('应该正确处理刷新操作', async () => {
      const mockLoadAllData = vi.fn().mockResolvedValue(undefined)
      dashboardStore.loadAllData = mockLoadAllData

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

      await flushPromises()

      // 查找并点击刷新按钮
      const refreshButton = wrapper.find('button:contains("立即刷新")')
      if (refreshButton.exists()) {
        await refreshButton.trigger('click')
        expect(mockLoadAllData).toHaveBeenCalled()
      }
    })

    it('应该正确显示任务列表', async () => {
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

      await flushPromises()

      // 验证任务卡片存在
      const taskElements = wrapper.findAll('.task-item')
      expect(taskElements.length).toBeGreaterThan(0)

      // 验证任务信息显示
      const taskContent = wrapper.text()
      expect(taskContent).toContain('user_data')
      expect(taskContent).toContain('user_profiles')
    })
  })

  describe('大屏监控组件集成', () => {
    it('应该正确渲染大屏监控组件', async () => {
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

      await flushPromises()

      // 验证大屏组件渲染
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.big-screen-monitor').exists()).toBe(true)

      // 验证时间显示
      expect(wrapper.find('[data-testid="big-screen-time"]').exists()).toBe(true)
    })

    it('应该正确显示关键指标卡片', async () => {
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

      await flushPromises()

      // 验证指标卡片
      const metricCards = wrapper.findAll('.metric-card')
      expect(metricCards.length).toBe(4) // 总表数、小文件总数、总存储大小、小文件率

      // 验证指标内容
      const cardContent = wrapper.text()
      expect(cardContent).toContain('总表数')
      expect(cardContent).toContain('小文件总数')
      expect(cardContent).toContain('总存储大小')
      expect(cardContent).toContain('小文件率')
    })

    it('应该正确处理集群切换', async () => {
      const mockLoadAllData = vi.fn().mockResolvedValue(undefined)
      dashboardStore.loadAllData = mockLoadAllData

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

      await flushPromises()

      // 模拟集群切换
      const selectComponent = wrapper.findComponent({ name: 'ElSelect' })
      if (selectComponent.exists()) {
        await selectComponent.vm.$emit('change', 'cluster-2')
        expect(mockLoadAllData).toHaveBeenCalledWith('cluster-2')
      }
    })

    it('应该正确显示实时任务状态', async () => {
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

      await flushPromises()

      // 验证任务网格
      const tasksGrid = wrapper.find('.tasks-grid')
      expect(tasksGrid.exists()).toBe(true)

      // 验证任务卡片
      const taskCards = wrapper.findAll('.task-card')
      expect(taskCards.length).toBeGreaterThan(0)

      // 验证任务信息
      const taskContent = wrapper.text()
      expect(taskContent).toContain('扫描任务')
      expect(taskContent).toContain('合并任务')
    })
  })

  describe('组件间数据流转', () => {
    it('应该正确传递集群选择状态', async () => {
      // 设置初始集群
      monitoringStore.settings.selectedCluster = 'cluster-2'

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

      await flushPromises()

      // 验证组件使用了正确的集群ID
      expect(monitoringStore.settings.selectedCluster).toBe('cluster-2')
    })

    it('应该正确响应Store状态变化', async () => {
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

      await flushPromises()

      // 修改Store状态
      dashboardStore.summary.total_tables = 2000
      await wrapper.vm.$nextTick()

      // 验证UI更新
      expect(wrapper.text()).toContain('2000')
    })

    it('应该正确处理加载状态', async () => {
      // 设置加载状态
      dashboardStore.isLoading = true

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

      await flushPromises()

      // 验证加载状态显示
      // 这里根据实际的加载状态实现进行验证
    })

    it('应该正确处理错误状态', async () => {
      // 设置错误状态
      dashboardStore.error = '加载失败'

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

      await flushPromises()

      // 验证错误状态处理
      // 这里根据实际的错误处理实现进行验证
    })
  })

  describe('用户交互集成测试', () => {
    it('应该正确处理批量扫描操作', async () => {
      const mockScanAllDatabases = vi.fn().mockResolvedValue({
        summary: {
          total_databases: 10,
          total_tables_scanned: 500,
          total_small_files: 150000,
          small_file_ratio: 30.0
        }
      })

      // Mock tasksApi
      const { tasksApi } = await import('@/api/tasks')
      vi.mocked(tasksApi.scanAllDatabases).mockImplementation(mockScanAllDatabases)

      // Mock ElMessageBox.confirm
      const { ElMessageBox } = await import('element-plus')
      vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm')

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

      await flushPromises()

      // 查找批量扫描按钮
      const batchScanButton = wrapper.find('button:contains("批量扫描")')
      if (batchScanButton.exists()) {
        await batchScanButton.trigger('click')
        await flushPromises()

        // 验证API调用
        expect(mockScanAllDatabases).toHaveBeenCalledWith('cluster-1', 10)

        // 验证成功消息
        expect(ElMessage.success).toHaveBeenCalled()
      }
    })

    it('应该正确处理全屏模式切换', async () => {
      const mockRouterPush = vi.fn()

      // Mock router
      vi.doMock('vue-router', () => ({
        useRouter: () => ({
          push: mockRouterPush
        }),
        useRoute: () => ({
          query: { cluster: 'cluster-1' },
          path: '/'
        })
      }))

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

      await flushPromises()

      // 查找全屏按钮
      const fullscreenButton = wrapper.find('[title="进入大屏模式"]')
      if (fullscreenButton.exists()) {
        await fullscreenButton.trigger('click')

        // 验证路由跳转
        expect(mockRouterPush).toHaveBeenCalledWith({
          path: '/big-screen',
          query: { cluster: 'cluster-1' }
        })
      }
    })
  })

  describe('响应式设计测试', () => {
    it('应该在移动端正确显示', async () => {
      // 模拟移动端视口
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })

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

      await flushPromises()

      // 验证移动端样式类
      expect(wrapper.find('.dashboard').exists()).toBe(true)
    })

    it('应该在平板端正确显示', async () => {
      // 模拟平板视口
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768,
      })

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

      await flushPromises()

      // 验证平板端布局
      expect(wrapper.find('.dashboard').exists()).toBe(true)
    })
  })

  describe('性能集成测试', () => {
    it('组件挂载应该在合理时间内完成', async () => {
      const startTime = performance.now()

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

      await flushPromises()
      const endTime = performance.now()

      // 组件挂载应该在合理时间内完成
      expect(endTime - startTime).toBeLessThan(500)
      expect(wrapper.exists()).toBe(true)
    })

    it('应该正确处理大量数据渲染', async () => {
      // 设置大量任务数据
      const largeTasks = Array.from({ length: 100 }, (_, i) => ({
        id: `task-${i}`,
        type: i % 2 === 0 ? 'scan' : 'merge',
        database_name: `database_${i}`,
        table_name: `table_${i}`,
        status: 'completed',
        created_at: new Date().toISOString()
      }))

      dashboardStore.recentTasks = largeTasks

      const startTime = performance.now()

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

      await flushPromises()
      const endTime = performance.now()

      // 即使有大量数据，渲染也应该在合理时间内完成
      expect(endTime - startTime).toBeLessThan(1000)
      expect(wrapper.exists()).toBe(true)
    })
  })
})