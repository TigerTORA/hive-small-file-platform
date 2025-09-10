import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface MonitoringSettings {
  autoRefresh: boolean
  refreshInterval: number // 秒
  selectedCluster: number | null
  theme: 'light' | 'dark'
  chartColors: string[]
}

export const useMonitoringStore = defineStore('monitoring', () => {
  // 状态
  const settings = ref<MonitoringSettings>({
    autoRefresh: true,
    refreshInterval: 60, // 默认60秒
    selectedCluster: 1, // 默认选择第一个集群
    theme: 'light',
    chartColors: [
      '#409EFF', // 蓝色
      '#67C23A', // 绿色  
      '#E6A23C', // 橙色
      '#F56C6C', // 红色
      '#909399', // 灰色
      '#5470C6', // 深蓝
      '#91CC75', // 浅绿
      '#EE6666'  // 浅红
    ]
  })

  const autoRefreshTimer = ref<NodeJS.Timeout | null>(null)
  const lastRefreshTime = ref<Date | null>(null)

  // 计算属性
  const refreshIntervalOptions = computed(() => [
    { label: '30秒', value: 30 },
    { label: '1分钟', value: 60 },
    { label: '2分钟', value: 120 },
    { label: '5分钟', value: 300 },
    { label: '10分钟', value: 600 }
  ])

  const isAutoRefreshEnabled = computed(() => settings.value.autoRefresh)

  const timeUntilNextRefresh = computed(() => {
    if (!lastRefreshTime.value || !settings.value.autoRefresh) return 0
    const elapsed = Math.floor((Date.now() - lastRefreshTime.value.getTime()) / 1000)
    return Math.max(0, settings.value.refreshInterval - elapsed)
  })

  // 操作方法
  function updateSettings(newSettings: Partial<MonitoringSettings>) {
    Object.assign(settings.value, newSettings)
    saveSettings()
    
    // 如果自动刷新设置改变，重新设置定时器
    if ('autoRefresh' in newSettings || 'refreshInterval' in newSettings) {
      setupAutoRefresh()
    }
  }

  function setSelectedCluster(clusterId: number | null) {
    settings.value.selectedCluster = clusterId
    saveSettings()
  }

  function toggleAutoRefresh() {
    settings.value.autoRefresh = !settings.value.autoRefresh
    saveSettings()
    setupAutoRefresh()
  }

  function setRefreshInterval(interval: number) {
    settings.value.refreshInterval = interval
    saveSettings()
    setupAutoRefresh()
  }

  function setTheme(theme: 'light' | 'dark') {
    settings.value.theme = theme
    saveSettings()
    
    // 应用主题到文档
    document.documentElement.className = theme
  }

  // 自动刷新相关
  function setupAutoRefresh(callback?: () => void) {
    clearAutoRefresh()
    
    if (!settings.value.autoRefresh || !callback) return
    
    autoRefreshTimer.value = setInterval(() => {
      callback()
      lastRefreshTime.value = new Date()
    }, settings.value.refreshInterval * 1000)
  }

  function clearAutoRefresh() {
    if (autoRefreshTimer.value) {
      clearInterval(autoRefreshTimer.value)
      autoRefreshTimer.value = null
    }
  }

  function triggerRefresh(callback?: () => void) {
    if (callback) {
      callback()
    }
    lastRefreshTime.value = new Date()
    
    // 重新设置定时器
    if (settings.value.autoRefresh) {
      setupAutoRefresh(callback)
    }
  }

  // 持久化
  function saveSettings() {
    try {
      localStorage.setItem('monitoring-settings', JSON.stringify(settings.value))
    } catch (error) {
      console.warn('Failed to save monitoring settings:', error)
    }
  }

  function loadSettings() {
    try {
      const saved = localStorage.getItem('monitoring-settings')
      if (saved) {
        const parsed = JSON.parse(saved)
        Object.assign(settings.value, parsed)
      }
    } catch (error) {
      console.warn('Failed to load monitoring settings:', error)
    }
  }

  // 图表主题相关
  function getChartTheme() {
    return {
      backgroundColor: settings.value.theme === 'dark' ? '#1f1f1f' : '#ffffff',
      textStyle: {
        color: settings.value.theme === 'dark' ? '#ffffff' : '#333333'
      },
      grid: {
        borderColor: settings.value.theme === 'dark' ? '#333333' : '#e0e6ed'
      }
    }
  }

  function getChartColor(index: number) {
    return settings.value.chartColors[index % settings.value.chartColors.length]
  }

  // 格式化工具
  function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B'
    
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  function formatNumber(num: number): string {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M'
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K'
    }
    return num.toString()
  }

  function formatDate(date: string | Date): string {
    const d = new Date(date)
    return d.toLocaleDateString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // 初始化
  function initialize() {
    loadSettings()
    setTheme(settings.value.theme)
    lastRefreshTime.value = new Date()
  }

  // 清理
  function cleanup() {
    clearAutoRefresh()
  }

  return {
    // 状态
    settings,
    lastRefreshTime,
    
    // 计算属性
    refreshIntervalOptions,
    isAutoRefreshEnabled,
    timeUntilNextRefresh,
    
    // 操作方法
    updateSettings,
    setSelectedCluster,
    toggleAutoRefresh,
    setRefreshInterval,
    setTheme,
    
    // 自动刷新
    setupAutoRefresh,
    clearAutoRefresh,
    triggerRefresh,
    
    // 持久化
    saveSettings,
    loadSettings,
    
    // 图表主题
    getChartTheme,
    getChartColor,
    
    // 格式化工具
    formatFileSize,
    formatNumber,
    formatDate,
    
    // 生命周期
    initialize,
    cleanup
  }
})