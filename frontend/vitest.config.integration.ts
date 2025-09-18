/**
 * Vitest集成测试配置
 * 专门用于集成测试的配置，优化性能和测试环境
 */

import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '~': resolve(__dirname, './src')
    }
  },

  test: {
    // 测试环境配置
    environment: 'happy-dom',

    // 全局设置
    globals: true,

    // 包含的测试文件
    include: [
      'src/test/integration/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}',
      'src/test/e2e/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
    ],

    // 排除的文件
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/cypress/**',
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build}.config.*'
    ],

    // 测试超时配置
    testTimeout: 30000, // 30秒
    hookTimeout: 30000,

    // 并发配置
    threads: true,
    minThreads: 1,
    maxThreads: 4,

    // 覆盖率配置
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage/integration',
      include: [
        'src/**/*.{js,ts,vue}',
        '!src/test/**',
        '!src/**/*.d.ts',
        '!src/**/*.test.*',
        '!src/**/*.spec.*'
      ],
      exclude: ['src/test/**', 'src/**/*.d.ts', 'src/main.ts', 'src/env.d.ts'],
      thresholds: {
        global: {
          branches: 70,
          functions: 75,
          lines: 80,
          statements: 80
        },
        // 对关键模块要求更高的覆盖率
        'src/utils/feature-flags.ts': {
          branches: 90,
          functions: 95,
          lines: 95,
          statements: 95
        },
        'src/stores/**': {
          branches: 80,
          functions: 85,
          lines: 85,
          statements: 85
        }
      }
    },

    // 设置文件
    setupFiles: ['./src/test/setup/integration.setup.ts'],

    // 环境变量
    env: {
      NODE_ENV: 'test',
      VITE_APP_TITLE: 'Hive小文件治理平台-测试',
      VITE_API_BASE_URL: 'http://localhost:8000',
      VITE_FEATURE_DEMO_MODE: 'true',
      // 启用所有特性进行测试
      VITE_FEATURE_REALTIME_MONITORING: 'true',
      VITE_FEATURE_ADVANCED_CHARTS: 'true',
      VITE_FEATURE_EXPORT_REPORTS: 'true',
      VITE_FEATURE_FULLSCREEN_MODE: 'true',
      VITE_FEATURE_DARK_THEME: 'true',
      VITE_FEATURE_PERFORMANCE_MONITORING: 'true',
      VITE_FEATURE_SMART_RECOMMENDATIONS: 'true',
      VITE_FEATURE_BATCH_OPERATIONS: 'true',
      VITE_FEATURE_WEBSOCKET_UPDATES: 'true'
    },

    // 报告器配置
    reporter: ['default', 'json', 'html'],

    // 输出目录
    outputFile: {
      json: './test-results/integration-results.json',
      html: './test-results/integration-report.html'
    },

    // 监听文件变化（开发模式）
    watch: false,

    // 失败时的行为
    bail: 0, // 不在第一个失败时停止

    // 重试配置
    retry: 1, // 失败的测试重试1次

    // 性能相关配置
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false,
        isolate: true,
        minThreads: 1,
        maxThreads: 4
      }
    },

    // 日志级别
    logLevel: 'info',

    // 清理模拟
    clearMocks: true,
    restoreMocks: true,

    // 快照配置
    resolveSnapshotPath: (testPath, snapExtension) => {
      return testPath.replace('/src/test/', '/src/test/__snapshots__/') + snapExtension
    }
  },

  // 构建优化
  esbuild: {
    target: 'node14'
  },

  // 定义全局变量
  define: {
    __VUE_OPTIONS_API__: true,
    __VUE_PROD_DEVTOOLS__: false,
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false
  }
})
