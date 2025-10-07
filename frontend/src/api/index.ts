import axios from 'axios'
import { ElMessage } from 'element-plus'

// 本地开发与容器统一：默认使用相对路径 /api/v1，由 Vite 代理（开发）或反代（生产/容器）转发到后端
const baseURL = (import.meta as any).env?.VITE_API_BASE_URL || '/api/v1'
const api = axios.create({ baseURL, timeout: 30000 })

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 添加认证 token（从localStorage获取）
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
// 去重的错误提示（3 秒内相同文案仅提示一次）
let __lastToastMsg = ''
let __lastToastAt = 0

api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    const message = error?.response?.data?.detail || error?.message || '请求失败'
    const now = Date.now()
    if (!(message === __lastToastMsg && now - __lastToastAt < 3000)) {
      ElMessage.error(message)
      __lastToastMsg = message
      __lastToastAt = now
    }
    return Promise.reject(error)
  }
)

export default api
