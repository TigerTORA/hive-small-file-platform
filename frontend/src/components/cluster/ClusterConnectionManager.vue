<template>
  <div class="cluster-connection-manager">
    <!-- 连接测试对话框 -->
    <ConnectionTestDialog
      v-model:visible="showTestDialog"
      :cluster-config="currentTestConfig"
      :test-result="testResult"
      :testing="testingConnection"
      :error="testError"
      @retest="handleRetest"
    />
  </div>
</template>

<script setup lang="ts">
  import { ref, onMounted, onUnmounted } from 'vue'
  import { ElMessage } from 'element-plus'
  import { clustersApi, type Cluster } from '@/api/clusters'
  import ConnectionTestDialog from '@/components/ConnectionTestDialog.vue'

  interface Props {
    clusters: Cluster[]
  }

  interface Emits {
    (e: 'update-connection-status', status: Record<number, any>): void
  }

  const props = defineProps<Props>()
  const emit = defineEmits<Emits>()

  // 连接状态数据
  const connectionStatus = ref<
    Record<
      number,
      {
        hiveserver?: {
          status: 'success' | 'error' | 'unknown' | 'testing'
          message?: string
          mode?: string
        }
        hdfs?: {
          status: 'success' | 'error' | 'unknown' | 'testing'
          message?: string
          mode?: string
        }
        metastore?: {
          status: 'success' | 'error' | 'unknown' | 'testing'
          message?: string
          mode?: string
        }
        loading?: boolean
        lastChecked?: Date
      }
    >
  >({})

  // 状态检查定时器
  let statusCheckInterval: NodeJS.Timeout | null = null

  // 连接测试相关
  const showTestDialog = ref(false)
  const testingConnection = ref(false)
  const testResult = ref<any>(null)
  const testError = ref<string | null>(null)
  const currentTestConfig = ref<any>(null)

  // 增强连接测试
  const testConnectionEnhanced = async (
    cluster: Cluster,
    options?: {
      connectionTypes?: string[]
      forceRefresh?: boolean
    }
  ) => {
    currentTestConfig.value = cluster
    testResult.value = null
    testError.value = null
    testingConnection.value = true
    showTestDialog.value = true

    try {
      const result = await clustersApi.testConnectionEnhanced(cluster.id, options)
      testResult.value = result

      // 更新连接状态缓存
      if (result.tests) {
        updateConnectionStatusFromResult(cluster.id, result.tests)
      }
    } catch (error: any) {
      console.error('Failed to test connection:', error)
      testError.value = error.response?.data?.detail || error.message || '增强连接测试失败'
    } finally {
      testingConnection.value = false
    }
  }

  const testConnection = async (cluster: Cluster, mode: string = 'mock') => {
    if (mode === 'real') {
      await testConnectionEnhanced(cluster, { forceRefresh: true })
    } else if (mode === 'enhanced') {
      await testConnectionEnhanced(cluster, {
        connectionTypes: ['metastore', 'hdfs', 'hiveserver2'],
        forceRefresh: true
      })
    } else {
      // Mock测试 - 简单消息提示
      const loadingMessage = ElMessage({
        message: '正在测试连接...',
        type: 'info',
        duration: 0
      })

      try {
        const result = await clustersApi.testConnection(cluster.id, mode)
        loadingMessage.close()

        const tests = result.tests || result.connections
        const metastoreTest = tests?.metastore
        const hdfsTest = tests?.hdfs

        if (metastoreTest?.status === 'success') {
          const hdfsStatus = hdfsTest?.status
          const hdfsMode = hdfsTest?.mode

          if (hdfsStatus === 'success') {
            ElMessage.success(`✅ 连接测试成功！
          • MetaStore: ${metastoreTest.message || '连接正常'}
          • HDFS: ${hdfsTest.message || '连接正常'} (${hdfsMode}模式)`)
          } else {
            ElMessage.warning(`⚠️ 部分连接成功
          • MetaStore: ${metastoreTest.message || '连接正常'}
          • HDFS: ${hdfsTest?.message || '连接失败'} (${hdfsMode}模式)`)
          }
        } else {
          ElMessage.error(`❌ 连接测试失败
        • MetaStore: ${metastoreTest?.message || '连接失败'}
        ${hdfsTest ? `• HDFS: ${hdfsTest.message || '未测试'}` : ''}`)
        }
      } catch (error: any) {
        loadingMessage.close()
        console.error('Failed to test connection:', error)
        const errorMsg = error.response?.data?.detail || error.message || '网络连接失败'
        ElMessage.error(`❌ 测试失败: ${errorMsg}`)
      }
    }
  }

  const updateConnectionStatus = async (clusterId: number) => {
    if (!connectionStatus.value[clusterId]) {
      connectionStatus.value[clusterId] = {}
    }

    connectionStatus.value[clusterId].loading = true

    try {
      const result = await clustersApi.testConnection(clusterId, 'enhanced')
      const tests = result.tests || {}

      updateConnectionStatusFromResult(clusterId, tests)
    } catch (error) {
      console.error(`Failed to check connection status for cluster ${clusterId}:`, error)
      connectionStatus.value[clusterId] = {
        hiveserver: { status: 'error', message: '连接测试失败' },
        hdfs: { status: 'error', message: '连接测试失败' },
        metastore: { status: 'error', message: '连接测试失败' },
        loading: false,
        lastChecked: new Date()
      }
    }

    // 发送更新事件
    emit('update-connection-status', connectionStatus.value)
  }

  const updateConnectionStatusFromResult = (clusterId: number, tests: any) => {
    const mapStatus = (backendStatus: string) => {
      switch (backendStatus) {
        case 'success':
          return 'success'
        case 'failed':
          return 'error'
        case 'unknown':
          return 'unknown'
        default:
          return 'error'
      }
    }

    if (!connectionStatus.value[clusterId]) {
      connectionStatus.value[clusterId] = {}
    }

    for (const [service, serviceResult] of Object.entries(tests)) {
      const mappedServiceKey =
        service === 'metastore'
          ? 'metastore'
          : service === 'hdfs'
            ? 'hdfs'
            : service === 'hiveserver2'
              ? 'hiveserver'
              : service

      connectionStatus.value[clusterId][mappedServiceKey] = {
        status: mapStatus(serviceResult.status),
        message:
          serviceResult.error_message ||
          `响应时间: ${serviceResult.response_time_ms?.toFixed(0)}ms`,
        lastChecked: new Date(),
        responseTime: serviceResult.response_time_ms,
        failureType: serviceResult.failure_type,
        attemptCount: serviceResult.attempt_count
      }
    }

    connectionStatus.value[clusterId].loading = false
    connectionStatus.value[clusterId].lastChecked = new Date()

    emit('update-connection-status', connectionStatus.value)
  }

  const testSpecificConnection = async (clusterId: number, service: string) => {
    console.log(`Testing ${service} connection for cluster ${clusterId}`)

    if (!connectionStatus.value[clusterId]) {
      connectionStatus.value[clusterId] = {}
    }

    const currentStatus = connectionStatus.value[clusterId]
    const serviceKey = service === 'hiveserver' ? 'hiveserver2' : service

    currentStatus[serviceKey] = { status: 'testing', message: '正在测试连接...' }

    try {
      const result = await clustersApi.testConnectionEnhanced(clusterId, {
        connectionTypes: [serviceKey],
        forceRefresh: true
      })

      if (result.tests && result.tests[serviceKey]) {
        const serviceResult = result.tests[serviceKey]
        const mapStatus = (backendStatus: string) => {
          switch (backendStatus) {
            case 'success':
              return 'success'
            case 'failed':
              return 'error'
            case 'unknown':
              return 'unknown'
            default:
              return 'error'
          }
        }

        currentStatus[serviceKey] = {
          status: mapStatus(serviceResult.status),
          message:
            serviceResult.error_message ||
            `响应时间: ${serviceResult.response_time_ms?.toFixed(0)}ms`,
          lastChecked: new Date(),
          responseTime: serviceResult.response_time_ms,
          failureType: serviceResult.failure_type,
          attemptCount: serviceResult.attempt_count
        }

        if (serviceResult.status === 'success') {
          ElMessage({
            message: `${service} 连接测试成功 (${serviceResult.response_time_ms?.toFixed(0)}ms)`,
            type: 'success'
          })
        } else {
          ElMessage({
            message: `${service} 连接测试失败: ${serviceResult.error_message || '未知错误'}`,
            type: 'error',
            duration: 5000
          })
        }
      }
    } catch (error: any) {
      console.error(`Failed to test ${service} connection:`, error)
      currentStatus[serviceKey] = {
        status: 'error',
        message: error.message || '网络错误',
        lastChecked: new Date()
      }

      ElMessage({
        message: `${service} 连接测试失败: ${error.message || '网络错误'}`,
        type: 'error'
      })
    }

    emit('update-connection-status', connectionStatus.value)
  }

  const checkAllConnectionStatus = async () => {
    const promises = props.clusters.map(cluster => updateConnectionStatus(cluster.id))
    await Promise.allSettled(promises)
  }

  const startStatusCheckInterval = () => {
    statusCheckInterval = setInterval(() => {
      checkAllConnectionStatus()
    }, 30000)
  }

  const stopStatusCheckInterval = () => {
    if (statusCheckInterval) {
      clearInterval(statusCheckInterval)
      statusCheckInterval = null
    }
  }

  // 测试配置连接（创建前测试）
  const testConfigConnection = async (config: any) => {
    currentTestConfig.value = { ...config }
    testResult.value = null
    testError.value = null

    try {
      const result = await clustersApi.testConnectionConfig(config)
      testResult.value = result
      showTestDialog.value = true
    } catch (error: any) {
      console.error('Failed to test config connection:', error)
      testError.value = error.response?.data?.detail || error.message || '连接测试失败'
      showTestDialog.value = true
    }
  }

  // 重新测试连接
  const handleRetest = async (clusterConfig: any) => {
    testResult.value = null
    testError.value = null
    testingConnection.value = true

    try {
      let result
      if (clusterConfig.id) {
        result = await clustersApi.testConnection(clusterConfig.id, 'real')
      } else {
        result = await clustersApi.testConnectionConfig(clusterConfig)
      }
      testResult.value = result
    } catch (error: any) {
      console.error('Failed to retest connection:', error)
      testError.value = error.response?.data?.detail || error.message || '重新测试失败'
    } finally {
      testingConnection.value = false
    }
  }

  onMounted(async () => {
    await checkAllConnectionStatus()
    startStatusCheckInterval()
  })

  onUnmounted(() => {
    stopStatusCheckInterval()
  })

  defineExpose({
    testConnection,
    testConnectionEnhanced,
    testSpecificConnection,
    testConfigConnection,
    checkAllConnectionStatus,
    connectionStatus
  })
</script>

<style scoped>
  .cluster-connection-manager {
    /* 这个组件主要是逻辑容器，无需特殊样式 */
  }
</style>
