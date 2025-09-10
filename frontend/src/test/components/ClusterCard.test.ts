import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ClusterCard from '@/components/cards/ClusterCard.vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useMonitoringStore } from '@/stores/monitoring'

// Mock Element Plus components
const mockElementPlusComponents = {
  ElCard: { template: '<div class="el-card"><slot></slot><template #header><slot name="header"></slot></template></div>' },
  ElIcon: { template: '<i><slot></slot></i>' },
  ElTag: { template: '<span class="el-tag"><slot></slot></span>', props: ['type', 'size'] },
  ElProgress: { template: '<div class="el-progress"></div>', props: ['percentage', 'color', 'showText', 'strokeWidth'] },
  ElSelect: { template: '<select class="el-select"><slot></slot></select>', props: ['modelValue', 'placeholder', 'style', 'size'] },
  ElOption: { template: '<option class="el-option"></option>', props: ['key', 'label', 'value'] }
}

describe('ClusterCard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  const createWrapper = (props = {}) => {
    return mount(ClusterCard, {
      props,
      global: {
        components: mockElementPlusComponents,
        stubs: {
          'el-card': mockElementPlusComponents.ElCard,
          'el-icon': mockElementPlusComponents.ElIcon,
          'el-tag': mockElementPlusComponents.ElTag,
          'el-progress': mockElementPlusComponents.ElProgress,
          'el-select': mockElementPlusComponents.ElSelect,
          'el-option': mockElementPlusComponents.ElOption,
          'Connection': { template: '<span>Connection</span>' },
          'Clock': { template: '<span>Clock</span>' }
        }
      }
    })
  }

  it('renders correctly with default props', () => {
    const wrapper = createWrapper()
    
    expect(wrapper.find('.cluster-card').exists()).toBe(true)
    expect(wrapper.text()).toContain('集群统计')
  })

  it('displays cluster statistics', () => {
    const dashboardStore = useDashboardStore()
    dashboardStore.summary = {
      total_clusters: 5,
      active_clusters: 4,
      total_tables: 0,
      monitored_tables: 0,
      total_files: 0,
      total_small_files: 0,
      small_file_ratio: 0,
      total_size_gb: 0,
      small_file_size_gb: 0
    }

    const wrapper = createWrapper()
    
    expect(wrapper.text()).toContain('5')
    expect(wrapper.text()).toContain('4')
    expect(wrapper.text()).toContain('总集群数')
    expect(wrapper.text()).toContain('活跃集群')
  })

  it('calculates active rate correctly', () => {
    const dashboardStore = useDashboardStore()
    dashboardStore.summary = {
      total_clusters: 5,
      active_clusters: 4,
      total_tables: 0,
      monitored_tables: 0,
      total_files: 0,
      total_small_files: 0,
      small_file_ratio: 0,
      total_size_gb: 0,
      small_file_size_gb: 0
    }

    const wrapper = createWrapper()
    
    // Active rate should be 80% (4/5 * 100)
    expect(wrapper.text()).toContain('80%')
  })

  it('shows correct status based on active rate', () => {
    const dashboardStore = useDashboardStore()
    
    // Test high active rate (should show "良好")
    dashboardStore.summary = {
      total_clusters: 5,
      active_clusters: 5,
      total_tables: 0,
      monitored_tables: 0,
      total_files: 0,
      total_small_files: 0,
      small_file_ratio: 0,
      total_size_gb: 0,
      small_file_size_gb: 0
    }

    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('良好')
  })

  it('displays cluster selector when showSelector is true', () => {
    const wrapper = createWrapper({ showSelector: true })
    
    expect(wrapper.find('.cluster-selector').exists()).toBe(true)
    expect(wrapper.find('.el-select').exists()).toBe(true)
  })

  it('hides cluster selector when showSelector is false', () => {
    const wrapper = createWrapper({ showSelector: false })
    
    expect(wrapper.find('.cluster-selector').exists()).toBe(false)
  })

  it('displays footer when showFooter is true', () => {
    const wrapper = createWrapper({ showFooter: true })
    
    expect(wrapper.find('.card-footer').exists()).toBe(true)
    expect(wrapper.text()).toContain('最后更新')
  })

  it('hides footer when showFooter is false', () => {
    const wrapper = createWrapper({ showFooter: false })
    
    expect(wrapper.find('.card-footer').exists()).toBe(false)
  })

  it('emits cluster-change event when cluster selection changes', async () => {
    const wrapper = createWrapper()
    
    // Simulate cluster change
    await wrapper.vm.handleClusterChange(2)
    
    expect(wrapper.emitted('clusterChange')).toBeTruthy()
    expect(wrapper.emitted('clusterChange')?.[0]).toEqual([2])
  })

  it('handles zero clusters gracefully', () => {
    const dashboardStore = useDashboardStore()
    dashboardStore.summary = {
      total_clusters: 0,
      active_clusters: 0,
      total_tables: 0,
      monitored_tables: 0,
      total_files: 0,
      total_small_files: 0,
      small_file_ratio: 0,
      total_size_gb: 0,
      small_file_size_gb: 0
    }

    const wrapper = createWrapper()
    
    expect(wrapper.text()).toContain('0%') // Active rate should be 0%
    expect(wrapper.text()).toContain('正常') // Status should be "正常" for 0%
  })

  it('formats numbers using monitoring store formatter', () => {
    const monitoringStore = useMonitoringStore()
    const formatSpy = vi.spyOn(monitoringStore, 'formatNumber')
    
    const wrapper = createWrapper()
    
    // The formatNumber method should be called for displaying numbers
    expect(formatSpy).toHaveBeenCalled()
  })

  it('applies hover effects', () => {
    const wrapper = createWrapper()
    const card = wrapper.find('.cluster-card')
    
    expect(card.classes()).toContain('cluster-card')
    
    // Test CSS class is applied (hover effects are CSS-based)
    expect(wrapper.html()).toContain('cluster-card')
  })
})