import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import * as Sentry from '@sentry/vue'

import App from './App.vue'
import router from './router'
import { useMonitoringStore } from '@/stores/monitoring'

const app = createApp(App)

// Initialize Sentry
const sentryDsn = import.meta.env.VITE_SENTRY_DSN
if (sentryDsn) {
  Sentry.init({
    app,
    dsn: sentryDsn,
    environment: import.meta.env.MODE,
    integrations: [Sentry.browserTracingIntegration({ router }), Sentry.replayIntegration()],
    tracesSampleRate: 1.0,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0
  })
}

// 注册 ElementPlus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// Setup Pinia and initialize global monitoring store early to avoid race conditions
const pinia = createPinia()
app.use(pinia)
try {
  const monitoringStore = useMonitoringStore(pinia)
  monitoringStore.initialize()
} catch (e) {
  // best-effort init; don't block app startup
  console.warn('Monitoring store init failed:', e)
}
app.use(router)
app.use(ElementPlus)

app.mount('#app')
