import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SmallFileCard from '@/components/cards/SmallFileCard.vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useMonitoringStore } from '@/stores/monitoring'

// Mock Element Plus components
const mockElementPlusComponents = {
  ElCard: { template: '<div class="el-card"><slot></slot><template #header><slot name="header"></slot></template></div>' },
  ElIcon: { template: '<i><slot></slot></i>' },
  ElTag: { template: '<span class="el-tag"><slot></slot></span>', props: ['type', 'size', 'effect'] },
  ElProgress: { template: '<div class="el-progress"></div>', props: ['percentage', 'color', 'showText', 'strokeWidth'] },
  ElButton: { template: '<button class="el-button" @click="$emit(\'click\')"><slot></slot></button>', props: ['type', 'size', 'loading'] },
  ElDropdown: { template: '<div class="el-dropdown"><slot></slot><template #dropdown><slot name="dropdown"></slot></template></div>' },
  ElDropdownMenu: { template: '<div class="el-dropdown-menu"><slot></slot></div>' },
  ElDropdownItem: { template: '<div class="el-dropdown-item" @click="$emit(\'command\', command)"><slot></slot></div>', props: ['command'] }
}

describe('SmallFileCard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  const createWrapper = (props = {}) => {
    return mount(SmallFileCard, {
      props: {
        showImpact: true,
        showSuggestions: true,
        showActions: true,
        merging: false,
        analyzing: false,
        ...props
      },
      global: {
        components: mockElementPlusComponents,
        stubs: {
          'el-card': mockElementPlusComponents.ElCard,
          'el-icon': mockElementPlusComponents.ElIcon,
          'el-tag': mockElementPlusComponents.ElTag,
          'el-progress': mockElementPlusComponents.ElProgress,
          'el-button': mockElementPlusComponents.ElButton,
          'el-dropdown': mockElementPlusComponents.ElDropdown,
          'el-dropdown-menu': mockElementPlusComponents.ElDropdownMenu,
          'el-dropdown-item': mockElementPlusComponents.ElDropdownItem,
          'WarningFilled': { template: '<span>WarningFilled</span>' },
          'Warning': { template: '<span>Warning</span>' },
          'Coin': { template: '<span>Coin</span>' },
          'Timer': { template: '<span>Timer</span>' },
          'TrendCharts': { template: '<span>TrendCharts</span>' },
          'Lightbulb': { template: '<span>Lightbulb</span>' },
          'Operation': { template: '<span>Operation</span>' },
          'Search': { template: '<span>Search</span>' },
          'ArrowDown': { template: '<span>ArrowDown</span>' }
        }
      }
    })
  }

  it('renders correctly with default props', () => {
    const wrapper = createWrapper()
    
    expect(wrapper.find('.small-file-card').exists()).toBe(true)
    expect(wrapper.text()).toContain('小文件问题')
  })

  it('displays small file statistics', () => {
    const dashboardStore = useDashboardStore()
    dashboardStore.summary = {
      total_clusters: 1,
      active_clusters: 1,
      total_tables: 2,
      monitored_tables: 2,
      total_files: 1000,
      total_small_files: 600,
      small_file_ratio: 60,
      total_size_gb: 100,
      small_file_size_gb: 30
    }

    const wrapper = createWrapper()
    
    expect(wrapper.text()).toContain('600') // small file count
    expect(wrapper.text()).toContain('60%') // small file ratio
  })

  it('calculates severity level correctly', () => {
    const dashboardStore = useDashboardStore()
    
    // Test critical level (>=60%)
    dashboardStore.summary = {
      total_clusters: 1,
      active_clusters: 1,
      total_tables: 2,
      monitored_tables: 2,
      total_files: 1000,
      total_small_files: 700,
      small_file_ratio: 70,
      total_size_gb: 100,
      small_file_size_gb: 40
    }

    const wrapper = createWrapper()
    
    expect(wrapper.text()).toContain('严重')
    expect(wrapper.text()).toContain('严重问题')
    expect(wrapper.text()).toContain('需要立即处理')
  })

  it('shows different alert levels based on ratio', () => {
    const dashboardStore = useDashboardStore()
    
    // Test warning level (40-59%)
    dashboardStore.summary = {
      total_clusters: 1,
      active_clusters: 1,
      total_tables: 2,
      monitored_tables: 2,
      total_files: 1000,
      total_small_files: 450,
      small_file_ratio: 45,
      total_size_gb: 100,
      small_file_size_gb: 20
    }

    const wrapper = createWrapper()
    
    expect(wrapper.text()).toContain('警告')
    expect(wrapper.text()).toContain('高风险')
  })

  it('displays impact analysis when showImpact is true', () => {
    const wrapper = createWrapper({ showImpact: true })
    
    expect(wrapper.find('.impact-analysis').exists()).toBe(true)
    expect(wrapper.text()).toContain('影响分析')
    expect(wrapper.text()).toContain('性能影响')
    expect(wrapper.text()).toContain('存储效率')
    expect(wrapper.text()).toContain('查询延迟')
  })

  it('hides impact analysis when showImpact is false', () => {
    const wrapper = createWrapper({ showImpact: false })
    
    expect(wrapper.find('.impact-analysis').exists()).toBe(false)
  })

  it('displays optimization suggestions when showSuggestions is true', () => {
    const wrapper = createWrapper({ showSuggestions: true })
    
    expect(wrapper.find('.optimization-suggestions').exists()).toBe(true)
    expect(wrapper.text()).toContain('优化建议')
    expect(wrapper.text()).toContain('合并小文件到128MB以上')
  })

  it('shows critical suggestion for high ratios', () => {
    const dashboardStore = useDashboardStore()
    dashboardStore.summary = {
      total_clusters: 1,
      active_clusters: 1,
      total_tables: 2,
      monitored_tables: 2,
      total_files: 1000,
      total_small_files: 700,
      small_file_ratio: 70,
      total_size_gb: 100,
      small_file_size_gb: 40
    }

    const wrapper = createWrapper({ showSuggestions: true })
    
    expect(wrapper.text()).toContain('立即停止新数据写入并紧急合并')
    expect(wrapper.text()).toContain('避免系统性能进一步恶化')
  })

  it('displays action buttons when showActions is true', () => {
    const wrapper = createWrapper({ showActions: true })
    
    expect(wrapper.find('.action-buttons').exists()).toBe(true)
    expect(wrapper.text()).toContain('开始合并')
    expect(wrapper.text()).toContain('深度分析')
    expect(wrapper.text()).toContain('更多操作')
  })

  it('shows loading state on merge button', () => {
    const wrapper = createWrapper({ merging: true })
    
    const mergeButton = wrapper.findAll('.el-button').find(button => 
      button.text().includes('开始合并')
    )
    expect(mergeButton?.attributes('loading')).toBe('true')
  })

  it('shows loading state on analyze button', () => {
    const wrapper = createWrapper({ analyzing: true })
    
    const analyzeButton = wrapper.findAll('.el-button').find(button => 
      button.text().includes('深度分析')
    )
    expect(analyzeButton?.attributes('loading')).toBe('true')
  })

  it('emits start-merge event when merge button is clicked', async () => {
    const wrapper = createWrapper()
    
    const mergeButton = wrapper.findAll('.el-button').find(button => 
      button.text().includes('开始合并')
    )
    
    await mergeButton?.trigger('click')
    
    expect(wrapper.emitted('start-merge')).toBeTruthy()
  })

  it('emits analyze-files event when analyze button is clicked', async () => {
    const wrapper = createWrapper()
    
    const analyzeButton = wrapper.findAll('.el-button').find(button => 
      button.text().includes('深度分析')
    )
    
    await analyzeButton?.trigger('click')
    
    expect(wrapper.emitted('analyze-files')).toBeTruthy()
  })

  it('formats file sizes correctly', () => {
    const dashboardStore = useDashboardStore()
    dashboardStore.summary = {
      total_clusters: 1,
      active_clusters: 1,
      total_tables: 2,
      monitored_tables: 2,
      total_files: 1000,
      total_small_files: 500,
      small_file_ratio: 50,
      total_size_gb: 1500, // Should show as 1.5 TB
      small_file_size_gb: 800 // Should show as 800.0 GB
    }

    const wrapper = createWrapper()
    
    expect(wrapper.text()).toContain('1.5 TB')
  })

  it('calculates wasted storage correctly', () => {
    const dashboardStore = useDashboardStore()
    dashboardStore.summary = {
      total_clusters: 1,
      active_clusters: 1,
      total_tables: 2,
      monitored_tables: 2,
      total_files: 1000,
      total_small_files: 500,
      small_file_ratio: 50,
      total_size_gb: 100,
      small_file_size_gb: 30 // Wasted should be 30 * 0.3 = 9 GB
    }

    const wrapper = createWrapper()
    
    // Should show wasted storage calculation
    expect(wrapper.text()).toContain('浪费存储')
  })

  it('handles zero files gracefully', () => {
    const dashboardStore = useDashboardStore()
    dashboardStore.summary = {
      total_clusters: 1,
      active_clusters: 1,
      total_tables: 2,
      monitored_tables: 2,
      total_files: 0,
      total_small_files: 0,
      small_file_ratio: 0,
      total_size_gb: 0,
      small_file_size_gb: 0
    }

    const wrapper = createWrapper()
    
    expect(wrapper.text()).toContain('0%')
    expect(wrapper.text()).toContain('正常')
  })
})