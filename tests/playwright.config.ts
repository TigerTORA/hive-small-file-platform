import { defineConfig, devices } from '@playwright/test'
import dotenv from 'dotenv'
import path from 'path'

// 加载环境变量
dotenv.config({ path: path.resolve(__dirname, '.env') })

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,  // E2E测试顺序执行
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,  // 单线程执行，避免并发问题

  reporter: [
    ['html', { outputFolder: 'reports/html', open: 'never' }],
    ['json', { outputFile: 'reports/results.json' }],
    ['list']
  ],

  use: {
    baseURL: process.env.FRONTEND_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: process.env.HEADLESS === 'true',
    slowMo: parseInt(process.env.SLOW_MO || '0'),
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
          args: ['--disable-dev-shm-usage']
        }
      },
    },
  ],

  timeout: parseInt(process.env.TIMEOUT || '30000'),
  expect: {
    timeout: 10000
  },

  webServer: process.env.AUTO_START_SERVERS === 'true' ? [
    {
      command: 'cd ../backend && python -m uvicorn app.main:app --host localhost --port 8000',
      port: 8000,
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'cd ../frontend && npm run dev',
      port: 3000,
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    }
  ] : undefined,
})
