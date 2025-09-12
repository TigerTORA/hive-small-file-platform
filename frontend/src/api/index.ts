import axios from 'axios'
import { ElMessage } from 'element-plus'

const baseURL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const api = axios.create({ baseURL, timeout: 30000 })

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // TODO: 添加认证 token
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default api
