import { vi } from 'vitest'

// Mock Element Plus message components only
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  },
  ElMessageBox: {
    confirm: vi.fn().mockResolvedValue(true),
    alert: vi.fn(),
    prompt: vi.fn()
  }
}))

// Mock Vue Router
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn(),
    back: vi.fn()
  }),
  useRoute: () => ({
    path: '/dashboard',
    params: {},
    query: {}
  })
}))

// Mock ECharts
vi.mock('vue-echarts', () => ({
  default: {
    name: 'VChart',
    template: '<div data-testid="mock-chart"></div>',
    props: ['option', 'loading', 'autoresize']
  }
}))

// Global test utilities
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}))

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})