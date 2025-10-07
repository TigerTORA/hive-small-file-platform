/**
 * WebSocket连接管理组合式API
 */
import { ref, onUnmounted } from 'vue'

interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
}

interface WebSocketState {
  connected: boolean
  reconnecting: boolean
  error: string | null
}

const state = ref<WebSocketState>({
  connected: false,
  reconnecting: false,
  error: null
})

let ws: WebSocket | null = null
let reconnectTimer: NodeJS.Timeout | null = null
let heartbeatTimer: NodeJS.Timeout | null = null
const subscriptions = new Set<string>()

export const useWebSocket = () => {
  const connect = (userId = 'anonymous') => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const wsUrl = `${protocol}//${host}/api/v1/ws?user_id=${userId}`

      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket连接已建立')
        state.value.connected = true
        state.value.reconnecting = false
        state.value.error = null

        // 重新订阅之前的主题
        if (subscriptions.size > 0) {
          subscribe(Array.from(subscriptions))
        }

        // 启动心跳
        startHeartbeat()
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)

          // 处理系统消息
          if (message.type === 'connection_established') {
            console.log('WebSocket连接确认:', message.data)
          } else if (message.type === 'pong') {
            // 心跳响应
            console.debug('心跳响应')
          } else {
            // 广播自定义事件给其他组件监听
            window.dispatchEvent(
              new CustomEvent('websocket-message', { detail: message })
            )
          }
        } catch (error) {
          console.error('WebSocket消息解析失败:', error)
        }
      }

      ws.onclose = (event) => {
        console.log('WebSocket连接已关闭:', event.code, event.reason)
        state.value.connected = false

        // 清理心跳
        stopHeartbeat()

        // 如果不是主动关闭，尝试重连
        if (event.code !== 1000 && !state.value.reconnecting) {
          reconnect()
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket连接错误:', error)
        state.value.error = 'WebSocket连接错误'
        state.value.connected = false
      }

    } catch (error) {
      console.error('创建WebSocket连接失败:', error)
      state.value.error = '创建WebSocket连接失败'
    }
  }

  const disconnect = () => {
    if (ws) {
      ws.close(1000, '主动断开')
      ws = null
    }

    stopHeartbeat()

    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    state.value.connected = false
    state.value.reconnecting = false
  }

  const reconnect = () => {
    if (state.value.reconnecting) {
      return
    }

    state.value.reconnecting = true
    console.log('尝试重新连接WebSocket...')

    reconnectTimer = setTimeout(() => {
      connect()
    }, 3000) // 3秒后重连
  }

  const subscribe = (topics: string[]) => {
    // 记录订阅
    topics.forEach(topic => subscriptions.add(topic))

    if (ws && ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'subscribe',
        data: { topics }
      }
      ws.send(JSON.stringify(message))
      console.log('订阅主题:', topics)
    }
  }

  const unsubscribe = (topics: string[]) => {
    // 移除订阅记录
    topics.forEach(topic => subscriptions.delete(topic))

    if (ws && ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'unsubscribe',
        data: { topics }
      }
      ws.send(JSON.stringify(message))
      console.log('取消订阅主题:', topics)
    }
  }

  const send = (message: any) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket未连接，无法发送消息')
    }
  }

  const startHeartbeat = () => {
    heartbeatTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        send({
          type: 'ping',
          data: { timestamp: Date.now() }
        })
      }
    }, 30000) // 30秒心跳
  }

  const stopHeartbeat = () => {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  return {
    state,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    send
  }
}

// 全局WebSocket实例
let globalWsInstance: ReturnType<typeof useWebSocket> | null = null

export const getGlobalWebSocket = () => {
  if (!globalWsInstance) {
    globalWsInstance = useWebSocket()
  }
  return globalWsInstance
}

// 自动清理
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    if (globalWsInstance) {
      globalWsInstance.disconnect()
    }
  })
}