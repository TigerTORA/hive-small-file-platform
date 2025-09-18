/**
 * 集成测试环境设置
 * 配置测试环境、模拟全局对象和工具函数
 */

import { vi, beforeAll, afterAll, beforeEach, afterEach } from 'vitest'
import { config } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'

// 配置Vue Test Utils全局设置
config.global.plugins = [createTestingPinia({ createSpy: vi.fn })]

// 模拟全局对象
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}))

global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}))

// 模拟 matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
})

// 模拟 performance.memory（用于性能测试）
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

// 模拟 requestIdleCallback
global.requestIdleCallback = vi.fn().mockImplementation(callback => {
  return setTimeout(() => callback({ didTimeout: false, timeRemaining: () => 50 }), 0)
})

global.cancelIdleCallback = vi.fn()

// 模拟 requestAnimationFrame
global.requestAnimationFrame = vi.fn().mockImplementation(callback => {
  return setTimeout(callback, 16)
})

global.cancelAnimationFrame = vi.fn()

// 模拟 URL 和 URLSearchParams（如果需要）
if (typeof URL === 'undefined') {
  global.URL = class MockURL {
    constructor(public href: string) {}
    toString() {
      return this.href
    }
  } as any
}

// 模拟 Blob 和 File API（用于文件上传测试）
global.Blob = class MockBlob {
  constructor(
    public parts: any[],
    public options: any = {}
  ) {}
  get size() {
    return 0
  }
  get type() {
    return this.options.type || ''
  }
  slice() {
    return new MockBlob([], {})
  }
} as any

global.File = class MockFile extends global.Blob {
  constructor(
    public parts: any[],
    public name: string,
    options: any = {}
  ) {
    super(parts, options)
  }
  get lastModified() {
    return Date.now()
  }
} as any

// 模拟 localStorage 和 sessionStorage
const createStorageMock = () => {
  const storage = new Map()
  return {
    getItem: vi.fn((key: string) => storage.get(key) || null),
    setItem: vi.fn((key: string, value: string) => storage.set(key, value)),
    removeItem: vi.fn((key: string) => storage.delete(key)),
    clear: vi.fn(() => storage.clear()),
    get length() {
      return storage.size
    },
    key: vi.fn((index: number) => Array.from(storage.keys())[index] || null)
  }
}

Object.defineProperty(window, 'localStorage', {
  value: createStorageMock()
})

Object.defineProperty(window, 'sessionStorage', {
  value: createStorageMock()
})

// 模拟 console 方法（可选：用于测试时减少日志输出）
const originalConsoleError = console.error
const originalConsoleWarn = console.warn

// 模拟 fetch API（基础版本）
global.fetch = vi.fn().mockImplementation((url: string, options: any = {}) => {
  return Promise.resolve({
    ok: true,
    status: 200,
    statusText: 'OK',
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    blob: () => Promise.resolve(new Blob()),
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    headers: new Map(),
    url,
    clone: () => ({ json: () => Promise.resolve({}) })
  } as Response)
})

// 测试数据工厂
export const createMockCluster = (overrides: any = {}) => ({
  id: 'cluster-1',
  name: '测试集群',
  status: 'active',
  namenode_host: '192.168.1.100',
  namenode_port: 9000,
  created_at: '2024-01-01T00:00:00Z',
  ...overrides
})

export const createMockTable = (overrides: any = {}) => ({
  cluster_id: 'cluster-1',
  database_name: 'test_db',
  table_name: 'test_table',
  total_files: 1000,
  small_files: 500,
  small_file_ratio: 50.0,
  total_size_bytes: 1073741824,
  last_scan_time: '2024-01-15T10:00:00Z',
  ...overrides
})

export const createMockTask = (overrides: any = {}) => ({
  id: 'task-1',
  type: 'scan',
  cluster_id: 'cluster-1',
  database_name: 'test_db',
  table_name: 'test_table',
  status: 'completed',
  created_at: '2024-01-15T09:00:00Z',
  completed_at: '2024-01-15T09:05:00Z',
  processing_time_seconds: 300,
  ...overrides
})

export const createMockDashboardSummary = (overrides: any = {}) => ({
  total_tables: 1500,
  total_small_files: 850000,
  total_size_bytes: 2147483648,
  small_file_ratio: 25.6,
  last_updated: '2024-01-15T10:30:00Z',
  ...overrides
})

// API 模拟响应工厂
export const createApiResponse = (data: any, success = true) => ({
  success,
  data,
  error: success ? null : 'Test error',
  message: success ? 'Success' : 'Error occurred'
})

// 测试工具函数
export const waitFor = (condition: () => boolean, timeout = 5000) => {
  return new Promise<void>((resolve, reject) => {
    const startTime = Date.now()
    const checkCondition = () => {
      if (condition()) {
        resolve()
      } else if (Date.now() - startTime > timeout) {
        reject(new Error(`Condition not met within ${timeout}ms`))
      } else {
        setTimeout(checkCondition, 10)
      }
    }
    checkCondition()
  })
}

export const flushPromises = () => new Promise(resolve => setTimeout(resolve, 0))

// 性能测试工具
export class TestPerformanceMonitor {
  private marks: Map<string, number> = new Map()

  mark(name: string) {
    this.marks.set(name, performance.now())
  }

  measure(startMark: string, endMark?: string): number {
    const start = this.marks.get(startMark)
    if (!start) throw new Error(`Mark '${startMark}' not found`)

    const end = endMark ? this.marks.get(endMark) : performance.now()
    if (endMark && !end) throw new Error(`Mark '${endMark}' not found`)

    return (end as number) - start
  }

  clear() {
    this.marks.clear()
  }
}

// 全局钩子
beforeAll(() => {
  // 设置测试环境特定的配置
  vi.stubEnv('NODE_ENV', 'test')
  vi.stubEnv('VITE_FEATURE_DEMO_MODE', 'true')
})

afterAll(() => {
  // 清理全局设置
  vi.unstubAllEnvs()
})

beforeEach(() => {
  // 每个测试前重置模拟
  vi.clearAllMocks()

  // 重置 fetch 模拟
  vi.mocked(fetch).mockReset()

  // 重置存储
  window.localStorage.clear()
  window.sessionStorage.clear()

  // 重置时间
  vi.setSystemTime(new Date('2024-01-15T10:00:00Z'))
})

afterEach(() => {
  // 每个测试后清理
  vi.restoreAllMocks()
  vi.useRealTimers()

  // 恢复 console
  console.error = originalConsoleError
  console.warn = originalConsoleWarn
})

// 测试断言扩展
expect.extend({
  toBeWithinRange(received: number, floor: number, ceiling: number) {
    const pass = received >= floor && received <= ceiling
    if (pass) {
      return {
        message: () => `expected ${received} not to be within range ${floor} - ${ceiling}`,
        pass: true
      }
    } else {
      return {
        message: () => `expected ${received} to be within range ${floor} - ${ceiling}`,
        pass: false
      }
    }
  },

  toBeValidTimestamp(received: string) {
    const date = new Date(received)
    const pass = !isNaN(date.getTime())
    if (pass) {
      return {
        message: () => `expected ${received} not to be a valid timestamp`,
        pass: true
      }
    } else {
      return {
        message: () => `expected ${received} to be a valid timestamp`,
        pass: false
      }
    }
  },

  toHavePerformanceWithin(received: number, maxTime: number) {
    const pass = received <= maxTime
    if (pass) {
      return {
        message: () => `expected ${received}ms not to be within performance limit of ${maxTime}ms`,
        pass: true
      }
    } else {
      return {
        message: () => `expected ${received}ms to be within performance limit of ${maxTime}ms`,
        pass: false
      }
    }
  }
})

// 声明自定义匹配器类型
declare global {
  namespace Vi {
    interface Assertion {
      toBeWithinRange(floor: number, ceiling: number): void
      toBeValidTimestamp(): void
      toHavePerformanceWithin(maxTime: number): void
    }
  }
}

// 导出通用模拟和工具
export { createStorageMock, TestPerformanceMonitor, waitFor, flushPromises }

// 日志配置（可选）
if (process.env.VITEST_LOG_LEVEL === 'silent') {
  console.log = vi.fn()
  console.info = vi.fn()
  console.warn = vi.fn()
  console.error = vi.fn()
}
