import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface GridItemLayout {
  i: string // 唯一标识
  x: number // X坐标（网格单位）
  y: number // Y坐标（网格单位）
  w: number // 宽度（网格单位）
  h: number // 高度（网格单位）
  static?: boolean // 是否静态（不可拖拽和调整）
  minW?: number // 最小宽度
  minH?: number // 最小高度
  maxW?: number // 最大宽度
  maxH?: number // 最大高度
}

export interface CardConfig {
  id: string
  title: string
  defaultLayout: Omit<GridItemLayout, 'i'>
  minW?: number
  minH?: number
  maxW?: number
  maxH?: number
}

export interface LayoutPreset {
  id: string
  name: string
  description: string
  layout: GridItemLayout[]
}

const STORAGE_KEY = 'dashboard-layout-config'

export const useDashboardLayoutStore = defineStore('dashboardLayout', () => {
  // 状态
  const isEditMode = ref(false)
  const currentLayout = ref<GridItemLayout[]>([])
  const customLayouts = ref<Record<string, GridItemLayout[]>>({})
  const activePreset = ref<string | null>(null)

  // 默认卡片配置 - 精简版，只保留核心功能卡片
  const defaultCards: CardConfig[] = [
    {
      id: 'cluster',
      title: '集群概览',
      defaultLayout: { x: 0, y: 0, w: 4, h: 5 },
      minW: 3,
      minH: 4,
      maxW: 8,
      maxH: 7
    },
    {
      id: 'smallFile',
      title: '小文件监控',
      defaultLayout: { x: 4, y: 0, w: 8, h: 5 },
      minW: 6,
      minH: 4,
      maxW: 12,
      maxH: 8
    }
  ]

  // 预设布局 - 精简版，适应2个卡片的布局
  const layoutPresets: LayoutPreset[] = [
    {
      id: 'default',
      name: '默认布局',
      description: '左右分布的标准布局',
      layout: defaultCards.map(card => ({
        i: card.id,
        ...card.defaultLayout,
        minW: card.minW,
        minH: card.minH,
        maxW: card.maxW,
        maxH: card.maxH
      }))
    },
    {
      id: 'focused',
      name: '重点关注',
      description: '突出小文件监控',
      layout: [
        { i: 'smallFile', x: 0, y: 0, w: 9, h: 6, minW: 6, minH: 4, maxW: 12, maxH: 8 },
        { i: 'cluster', x: 9, y: 0, w: 3, h: 6, minW: 3, minH: 4, maxW: 6, maxH: 7 }
      ]
    },
    {
      id: 'compact',
      name: '紧凑布局',
      description: '节省空间的上下排列',
      layout: [
        { i: 'cluster', x: 0, y: 0, w: 12, h: 4, minW: 8, minH: 3, maxW: 12, maxH: 5 },
        { i: 'smallFile', x: 0, y: 4, w: 12, h: 4, minW: 8, minH: 3, maxW: 12, maxH: 6 }
      ]
    },
    {
      id: 'balanced',
      name: '均衡布局',
      description: '两个卡片等宽排列',
      layout: [
        { i: 'cluster', x: 0, y: 0, w: 6, h: 5, minW: 4, minH: 4, maxW: 8, maxH: 7 },
        { i: 'smallFile', x: 6, y: 0, w: 6, h: 5, minW: 4, minH: 4, maxW: 8, maxH: 7 }
      ]
    }
  ]

  // 计算属性
  const cards = computed(() => defaultCards)
  const presets = computed(() => layoutPresets)
  const hasCustomLayout = computed(() => {
    const defaultLayoutStr = JSON.stringify(getPresetLayout('default'))
    const currentLayoutStr = JSON.stringify(currentLayout.value)
    return defaultLayoutStr !== currentLayoutStr
  })

  // 获取当前布局
  const getCurrentLayout = computed(() => currentLayout.value)

  // 工具函数
  function getPresetLayout(presetId: string): GridItemLayout[] {
    const preset = layoutPresets.find(p => p.id === presetId)
    return preset ? [...preset.layout] : [...layoutPresets[0].layout]
  }

  function generateLayoutId(): string {
    return `layout_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  // Actions
  function setEditMode(mode: boolean) {
    isEditMode.value = mode
  }

  function updateLayout(newLayout: GridItemLayout[]) {
    currentLayout.value = [...newLayout]
    saveLayoutToStorage()
  }

  function applyPreset(presetId: string) {
    const presetLayout = getPresetLayout(presetId)
    if (presetLayout.length > 0) {
      currentLayout.value = [...presetLayout]
      activePreset.value = presetId
      saveLayoutToStorage()
    }
  }

  function resetToDefault() {
    applyPreset('default')
  }

  function saveAsCustomLayout(name: string, description?: string): string {
    const layoutId = generateLayoutId()
    const layoutCopy = [...currentLayout.value]

    customLayouts.value[layoutId] = layoutCopy

    // 也可以扩展为保存带名称和描述的自定义预设
    const customPreset: LayoutPreset = {
      id: layoutId,
      name,
      description: description || '用户自定义布局',
      layout: layoutCopy
    }

    // 这里可以扩展为支持动态添加到 layoutPresets
    saveLayoutToStorage()
    return layoutId
  }

  function deleteCustomLayout(layoutId: string) {
    if (customLayouts.value[layoutId]) {
      delete customLayouts.value[layoutId]
      if (activePreset.value === layoutId) {
        activePreset.value = null
      }
      saveLayoutToStorage()
    }
  }

  function saveLayoutToStorage() {
    const layoutData = {
      currentLayout: currentLayout.value,
      activePreset: activePreset.value,
      customLayouts: customLayouts.value,
      timestamp: Date.now()
    }

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(layoutData))
    } catch (error) {
      console.warn('Failed to save layout to localStorage:', error)
    }
  }

  function loadLayoutFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const layoutData = JSON.parse(stored)

        if (layoutData.currentLayout && Array.isArray(layoutData.currentLayout)) {
          currentLayout.value = layoutData.currentLayout
        } else {
          // 如果没有有效的存储布局，使用默认布局
          currentLayout.value = getPresetLayout('default')
        }

        if (layoutData.activePreset) {
          activePreset.value = layoutData.activePreset
        }

        if (layoutData.customLayouts && typeof layoutData.customLayouts === 'object') {
          customLayouts.value = layoutData.customLayouts
        }

        return true
      }
    } catch (error) {
      console.warn('Failed to load layout from localStorage:', error)
    }

    // 如果加载失败，使用默认布局
    currentLayout.value = getPresetLayout('default')
    activePreset.value = 'default'
    return false
  }

  function clearLayoutStorage() {
    try {
      localStorage.removeItem(STORAGE_KEY)
      currentLayout.value = getPresetLayout('default')
      activePreset.value = 'default'
      customLayouts.value = {}
    } catch (error) {
      console.warn('Failed to clear layout storage:', error)
    }
  }

  function exportLayout(): string {
    const exportData = {
      layout: currentLayout.value,
      preset: activePreset.value,
      timestamp: Date.now(),
      version: '1.0'
    }
    return JSON.stringify(exportData, null, 2)
  }

  function importLayout(jsonData: string): boolean {
    try {
      const importData = JSON.parse(jsonData)

      if (importData.layout && Array.isArray(importData.layout)) {
        currentLayout.value = importData.layout
        activePreset.value = importData.preset || null
        saveLayoutToStorage()
        return true
      }
    } catch (error) {
      console.error('Failed to import layout:', error)
    }
    return false
  }

  // 初始化
  function initialize() {
    const loaded = loadLayoutFromStorage()
    if (!loaded) {
      console.log('Using default layout configuration')
    }
  }

  return {
    // 状态
    isEditMode,
    currentLayout: getCurrentLayout,
    activePreset,
    customLayouts,

    // 计算属性
    cards,
    presets,
    hasCustomLayout,

    // Actions
    setEditMode,
    updateLayout,
    applyPreset,
    resetToDefault,
    saveAsCustomLayout,
    deleteCustomLayout,
    saveLayoutToStorage,
    loadLayoutFromStorage,
    clearLayoutStorage,
    exportLayout,
    importLayout,
    initialize
  }
})
