import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import TrendChart from '@/components/charts/TrendChart.vue'
import type { TrendPoint } from '@/api/dashboard'

// Mock vue-echarts
vi.mock('vue-echarts', () => ({
  default: {
    name: 'VChart',
    template: '<div data-testid="mock-chart" class="trend-echarts" @click="$emit(\'click\', $event)"></div>',
    props: ['option', 'loading', 'autoresize'],
    emits: ['click']
  }
}))

// Mock Element Plus components
const mockElementPlusComponents = {
  ElSkeleton: { template: '<div class="el-skeleton"><slot></slot><template #template><slot name="template"></slot></template></div>', props: ['animated'] },
  ElSkeletonItem: { template: '<div class="el-skeleton-item"></div>', props: ['variant', 'style'] },
  ElEmpty: { template: '<div class="el-empty"><slot></slot><slot name="image"></slot><slot name="description"></slot></div>', props: ['description'] },
  ElButton: { template: '<button class="el-button" @click="$emit(\'click\')"><slot></slot></button>', props: ['type', 'loading'] },
  ElButtonGroup: { template: '<div class="el-button-group"><slot></slot></div>', props: ['size'] },
  ElRadioGroup: { template: '<div class="el-radio-group" @change="$emit(\'change\', $event.target.value)"><slot></slot></div>', props: ['modelValue', 'size'] },
  ElRadioButton: { template: '<label class="el-radio-button"><input type="radio" /><slot></slot></label>', props: ['value'] }
}

describe('TrendChart', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  const mockTrendData: TrendPoint[] = [
    {
      date: '2023-12-01',
      total_files: 1000,
      small_files: 300,
      ratio: 30.0
    },
    {
      date: '2023-12-02',
      total_files: 1200,
      small_files: 400,
      ratio: 33.3
    },
    {
      date: '2023-12-03',
      total_files: 1100,
      small_files: 350,
      ratio: 31.8
    }
  ]

  const createWrapper = (props = {}) => {
    return mount(TrendChart, {
      props: {
        data: mockTrendData,
        title: '小文件趋势分析',
        subtitle: '显示文件数量和小文件占比的变化趋势',
        height: 400,
        showHeader: true,
        showFooter: true,
        loading: false,
        error: null,
        refreshing: false,
        exporting: false,
        theme: 'light',
        ...props
      },
      global: {
        components: mockElementPlusComponents,
        stubs: {
          'el-skeleton': mockElementPlusComponents.ElSkeleton,
          'el-skeleton-item': mockElementPlusComponents.ElSkeletonItem,
          'el-empty': mockElementPlusComponents.ElEmpty,
          'el-button': mockElementPlusComponents.ElButton,
          'el-button-group': mockElementPlusComponents.ElButtonGroup,
          'el-radio-group': mockElementPlusComponents.ElRadioGroup,
          'el-radio-button': mockElementPlusComponents.ElRadioButton,
          'v-chart': {
            template: '<div data-testid="mock-chart" class="trend-echarts" @click="$emit(\'click\', $event)"></div>',
            props: ['option', 'loading', 'autoresize'],
            emits: ['click']
          },
          'Download': { template: '<span>Download</span>' },
          'FullScreen': { template: '<span>FullScreen</span>' },
          'Refresh': { template: '<span>Refresh</span>' }
        }
      }
    })
  }

  it('renders correctly with default props', () => {
    const wrapper = createWrapper()
    
    expect(wrapper.find('.trend-chart').exists()).toBe(true)
    expect(wrapper.text()).toContain('小文件趋势分析')
    expect(wrapper.text()).toContain('显示文件数量和小文件占比的变化趋势')
  })

  it('displays chart header when showHeader is true', () => {
    const wrapper = createWrapper({ showHeader: true })
    
    expect(wrapper.find('.chart-header').exists()).toBe(true)
    expect(wrapper.text()).toContain('小文件趋势分析')
    expect(wrapper.find('.el-radio-group').exists()).toBe(true)
  })

  it('hides chart header when showHeader is false', () => {
    const wrapper = createWrapper({ showHeader: false })
    
    expect(wrapper.find('.chart-header').exists()).toBe(false)
  })

  it('displays chart footer when showFooter is true', () => {
    const wrapper = createWrapper({ showFooter: true })
    
    expect(wrapper.find('.chart-footer').exists()).toBe(true)
    expect(wrapper.find('.chart-legend').exists()).toBe(true)
    expect(wrapper.find('.chart-actions').exists()).toBe(true)
  })

  it('hides chart footer when showFooter is false', () => {
    const wrapper = createWrapper({ showFooter: false })
    
    expect(wrapper.find('.chart-footer').exists()).toBe(false)
  })

  it('shows loading skeleton when loading is true', () => {
    const wrapper = createWrapper({ loading: true })
    
    expect(wrapper.find('.chart-loading').exists()).toBe(true)
    expect(wrapper.find('.el-skeleton').exists()).toBe(true)
    expect(wrapper.find('.trend-echarts').exists()).toBe(false)
  })

  it('shows error message when error is present', () => {
    const wrapper = createWrapper({ error: 'Failed to load data' })
    
    expect(wrapper.find('.chart-error').exists()).toBe(true)
    expect(wrapper.find('.el-empty').exists()).toBe(true)
    expect(wrapper.find('.trend-echarts').exists()).toBe(false)
  })

  it('displays chart when data is available', () => {
    const wrapper = createWrapper()
    
    expect(wrapper.find('[data-testid="mock-chart"]').exists()).toBe(true)
    expect(wrapper.find('.chart-loading').exists()).toBe(false)
    expect(wrapper.find('.chart-error').exists()).toBe(false)
  })

  it('shows empty data message when no data', () => {
    const wrapper = createWrapper({ data: [] })
    
    // With empty data, the chart should still render but show "暂无数据" in the chart
    expect(wrapper.find('[data-testid="mock-chart"]').exists()).toBe(true)
  })

  it('displays correct legend items based on data', () => {
    const wrapper = createWrapper()
    
    expect(wrapper.find('.chart-legend').exists()).toBe(true)
    expect(wrapper.text()).toContain('总文件数')
    expect(wrapper.text()).toContain('小文件数')
    expect(wrapper.text()).toContain('小文件占比')
  })

  it('emits refresh event when refresh button is clicked', async () => {
    const wrapper = createWrapper()
    
    const refreshButton = wrapper.findAll('.el-button').find(button =>
      button.html().includes('Refresh')
    )
    
    await refreshButton?.trigger('click')
    
    expect(wrapper.emitted('refresh')).toBeTruthy()
  })

  it('emits export event when export button is clicked', async () => {
    const wrapper = createWrapper()
    
    const exportButton = wrapper.findAll('.el-button').find(button =>
      button.html().includes('Download')
    )
    
    await exportButton?.trigger('click')
    
    expect(wrapper.emitted('export')).toBeTruthy()
  })

  it('emits fullscreen event when fullscreen button is clicked', async () => {
    const wrapper = createWrapper()
    
    const fullscreenButton = wrapper.findAll('.el-button').find(button =>
      button.html().includes('FullScreen')
    )
    
    await fullscreenButton?.trigger('click')
    
    expect(wrapper.emitted('fullscreen')).toBeTruthy()
  })

  it('emits period-change event when period selection changes', async () => {
    const wrapper = createWrapper()
    
    const radioGroup = wrapper.find('.el-radio-group')
    await radioGroup.trigger('change')
    
    expect(wrapper.emitted('period-change')).toBeTruthy()
  })

  it('emits chart-click event when chart is clicked', async () => {
    const wrapper = createWrapper()
    
    const chart = wrapper.find('[data-testid="mock-chart"]')
    const mockParams = { seriesName: '总文件数', value: 1000 }
    await chart.trigger('click', mockParams)
    
    expect(wrapper.emitted('chart-click')).toBeTruthy()
  })

  it('applies correct container style based on height prop', () => {
    const wrapper = createWrapper({ height: 500 })
    
    const container = wrapper.find('.chart-container')
    expect(container.attributes('style')).toContain('height: 500px')
  })

  it('shows loading state on action buttons', () => {
    const wrapper = createWrapper({ 
      refreshing: true, 
      exporting: true 
    })
    
    const refreshButton = wrapper.findAll('.el-button').find(button =>
      button.html().includes('Refresh')
    )
    const exportButton = wrapper.findAll('.el-button').find(button =>
      button.html().includes('Download')
    )
    
    expect(refreshButton?.attributes('loading')).toBeDefined()
    expect(exportButton?.attributes('loading')).toBeDefined()
  })

  it('formats legend values correctly', () => {
    const wrapper = createWrapper()
    
    // The legend should show formatted values from the last data point
    const legendItems = wrapper.findAll('.legend-item')
    expect(legendItems.length).toBeGreaterThan(0)
    
    // Should contain the formatted numbers and percentage
    const footerText = wrapper.find('.chart-footer').text()
    expect(footerText).toContain('1.1K') // 1100 formatted
    expect(footerText).toContain('31.8%') // ratio from last data point
  })

  it('handles custom title and subtitle', () => {
    const customTitle = 'Custom Chart Title'
    const customSubtitle = 'Custom chart subtitle'
    
    const wrapper = createWrapper({
      title: customTitle,
      subtitle: customSubtitle
    })
    
    expect(wrapper.text()).toContain(customTitle)
    expect(wrapper.text()).toContain(customSubtitle)
  })
})