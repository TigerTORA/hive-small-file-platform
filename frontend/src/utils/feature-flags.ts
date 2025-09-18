/**
 * 特性开关管理系统
 * 支持环境变量和运行时配置
 */

export interface FeatureFlags {
  // 实时监控功能
  realtimeMonitoring: boolean

  // 高级图表功能
  advancedCharts: boolean

  // 演示模式
  demoMode: boolean

  // 导出报告功能
  exportReports: boolean

  // 大屏展示模式
  fullscreenMode: boolean

  // 深色主题
  darkTheme: boolean

  // 性能监控
  performanceMonitoring: boolean

  // 智能建议
  smartRecommendations: boolean

  // 批量操作
  batchOperations: boolean

  // WebSocket实时更新
  websocketUpdates: boolean
}

// 默认特性配置
const defaultFeatures: FeatureFlags = {
  realtimeMonitoring: true,
  advancedCharts: false,
  demoMode: false,
  exportReports: false,
  fullscreenMode: true,
  darkTheme: false,
  performanceMonitoring: false,
  smartRecommendations: false,
  batchOperations: true,
  websocketUpdates: false
}

// 环境变量覆盖配置
const envOverrides: Partial<FeatureFlags> = {
  realtimeMonitoring: getEnvBoolean('VITE_FEATURE_REALTIME_MONITORING'),
  advancedCharts: getEnvBoolean('VITE_FEATURE_ADVANCED_CHARTS'),
  demoMode: getEnvBoolean('VITE_FEATURE_DEMO_MODE'),
  exportReports: getEnvBoolean('VITE_FEATURE_EXPORT_REPORTS'),
  fullscreenMode: getEnvBoolean('VITE_FEATURE_FULLSCREEN_MODE'),
  darkTheme: getEnvBoolean('VITE_FEATURE_DARK_THEME'),
  performanceMonitoring: getEnvBoolean('VITE_FEATURE_PERFORMANCE_MONITORING'),
  smartRecommendations: getEnvBoolean('VITE_FEATURE_SMART_RECOMMENDATIONS'),
  batchOperations: getEnvBoolean('VITE_FEATURE_BATCH_OPERATIONS'),
  websocketUpdates: getEnvBoolean('VITE_FEATURE_WEBSOCKET_UPDATES')
}

function getEnvBoolean(key: string): boolean | undefined {
  const value = import.meta.env[key]
  if (value === undefined) return undefined
  return value === 'true' || value === '1'
}

// 运行时特性开关状态
let runtimeFeatures: Partial<FeatureFlags> = {}

// 合并配置的优先级：运行时 > 环境变量 > 默认值
function mergeFeatures(): FeatureFlags {
  return {
    ...defaultFeatures,
    ...Object.fromEntries(Object.entries(envOverrides).filter(([, value]) => value !== undefined)),
    ...runtimeFeatures
  }
}

// 导出当前特性配置
export const featureFlags: FeatureFlags = new Proxy({} as FeatureFlags, {
  get(target, prop: string) {
    const currentFeatures = mergeFeatures()
    return currentFeatures[prop as keyof FeatureFlags]
  }
})

// 特性开关管理器
export class FeatureManager {
  // 检查特性是否启用
  static isEnabled(feature: keyof FeatureFlags): boolean {
    return featureFlags[feature]
  }

  // 运行时启用特性
  static enable(feature: keyof FeatureFlags): void {
    runtimeFeatures[feature] = true
    console.log(`[FeatureFlags] Enabled feature: ${feature}`)
  }

  // 运行时禁用特性
  static disable(feature: keyof FeatureFlags): void {
    runtimeFeatures[feature] = false
    console.log(`[FeatureFlags] Disabled feature: ${feature}`)
  }

  // 切换特性状态
  static toggle(feature: keyof FeatureFlags): boolean {
    const currentState = this.isEnabled(feature)
    runtimeFeatures[feature] = !currentState
    console.log(`[FeatureFlags] Toggled feature ${feature}: ${!currentState}`)
    return !currentState
  }

  // 获取所有特性状态
  static getAllFeatures(): FeatureFlags {
    return mergeFeatures()
  }

  // 批量设置特性
  static setFeatures(features: Partial<FeatureFlags>): void {
    runtimeFeatures = { ...runtimeFeatures, ...features }
    console.log('[FeatureFlags] Updated features:', features)
  }

  // 重置到默认配置
  static reset(): void {
    runtimeFeatures = {}
    console.log('[FeatureFlags] Reset to default configuration')
  }

  // 导出当前配置
  static exportConfig(): string {
    return JSON.stringify(mergeFeatures(), null, 2)
  }

  // 导入配置
  static importConfig(config: string): void {
    try {
      const features = JSON.parse(config) as Partial<FeatureFlags>
      this.setFeatures(features)
    } catch (error) {
      console.error('[FeatureFlags] Failed to import config:', error)
    }
  }
}

// 预设配置
export const presetConfigs = {
  // 开发模式 - 所有功能开启
  development: {
    realtimeMonitoring: true,
    advancedCharts: true,
    demoMode: true,
    exportReports: true,
    fullscreenMode: true,
    darkTheme: true,
    performanceMonitoring: true,
    smartRecommendations: true,
    batchOperations: true,
    websocketUpdates: true
  },

  // 生产模式 - 稳定功能
  production: {
    realtimeMonitoring: true,
    advancedCharts: false,
    demoMode: false,
    exportReports: true,
    fullscreenMode: true,
    darkTheme: false,
    performanceMonitoring: false,
    smartRecommendations: false,
    batchOperations: true,
    websocketUpdates: false
  },

  // 演示模式 - 展示效果最佳
  demo: {
    realtimeMonitoring: true,
    advancedCharts: true,
    demoMode: true,
    exportReports: true,
    fullscreenMode: true,
    darkTheme: false,
    performanceMonitoring: true,
    smartRecommendations: true,
    batchOperations: true,
    websocketUpdates: true
  },

  // 精简模式 - 最小功能集
  minimal: {
    realtimeMonitoring: false,
    advancedCharts: false,
    demoMode: false,
    exportReports: false,
    fullscreenMode: false,
    darkTheme: false,
    performanceMonitoring: false,
    smartRecommendations: false,
    batchOperations: false,
    websocketUpdates: false
  }
} as const

// 应用预设配置
export function applyPreset(preset: keyof typeof presetConfigs): void {
  FeatureManager.setFeatures(presetConfigs[preset])
}

// 开发时的便捷方法
if (import.meta.env.DEV) {
  ;(window as any).featureFlags = featureFlags
  ;(window as any).FeatureManager = FeatureManager
  ;(window as any).applyPreset = applyPreset
  console.log('[FeatureFlags] Development mode: feature flags available in window object')
}
