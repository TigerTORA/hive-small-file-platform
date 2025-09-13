import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    server: {
      port: parseInt(env.VITE_DEV_PORT || '3000'),
      proxy: {
        // 统一使用相对路径 /api/v1，开发态由 Vite 代理到本地后端 8000
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    preview: {
      port: parseInt(env.VITE_PREVIEW_PORT || '4173'),
    },
    build: {
      outDir: 'dist',
    },
  }
})
