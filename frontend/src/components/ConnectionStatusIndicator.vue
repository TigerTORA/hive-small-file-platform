<template>
  <div class="connection-status-indicator">
    <div class="service-indicators">
      <el-tooltip
        :content="getTooltipContent('hiveserver')"
        placement="top"
        :show-after="500"
      >
        <div
          class="service-indicator"
          :class="getStatusClass(hiveserverStatus)"
          @click="$emit('test-connection', 'hiveserver')"
        >
          <el-icon class="service-icon">
            <Grid />
          </el-icon>
          <span class="status-dot" :class="getStatusClass(hiveserverStatus)"></span>
        </div>
      </el-tooltip>

      <el-tooltip
        :content="getTooltipContent('hdfs')"
        placement="top"
        :show-after="500"
      >
        <div
          class="service-indicator"
          :class="getStatusClass(hdfsStatus)"
          @click="$emit('test-connection', 'hdfs')"
        >
          <el-icon class="service-icon">
            <Files />
          </el-icon>
          <span class="status-dot" :class="getStatusClass(hdfsStatus)"></span>
        </div>
      </el-tooltip>

      <el-tooltip
        :content="getTooltipContent('metastore')"
        placement="top"
        :show-after="500"
      >
        <div
          class="service-indicator"
          :class="getStatusClass(metastoreStatus)"
          @click="$emit('test-connection', 'metastore')"
        >
          <el-icon class="service-icon">
            <Connection />
          </el-icon>
          <span class="status-dot" :class="getStatusClass(metastoreStatus)"></span>
        </div>
      </el-tooltip>
    </div>

    <div v-if="loading" class="loading-indicator">
      <el-icon class="rotating">
        <Loading />
      </el-icon>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Grid, Files, Connection, Loading } from '@element-plus/icons-vue'

export interface ConnectionStatus {
  status: 'success' | 'error' | 'unknown' | 'testing'
  message?: string
  mode?: string
}

interface Props {
  hiveserverStatus?: ConnectionStatus
  hdfsStatus?: ConnectionStatus
  metastoreStatus?: ConnectionStatus
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  hiveserverStatus: () => ({ status: 'unknown' }),
  hdfsStatus: () => ({ status: 'unknown' }),
  metastoreStatus: () => ({ status: 'unknown' }),
  loading: false
})

const emit = defineEmits<{
  'test-connection': [service: string]
}>()

const getStatusClass = (status?: ConnectionStatus) => {
  if (!status) return 'status-unknown'

  switch (status.status) {
    case 'success':
      return 'status-success'
    case 'error':
      return 'status-error'
    case 'testing':
      return 'status-testing'
    default:
      return 'status-unknown'
  }
}

const getTooltipContent = (service: string) => {
  let status: ConnectionStatus | undefined
  let serviceName: string

  switch (service) {
    case 'hiveserver':
      status = props.hiveserverStatus
      serviceName = 'HiveServer2'
      break
    case 'hdfs':
      status = props.hdfsStatus
      serviceName = 'HDFS WebHDFS'
      break
    case 'metastore':
      status = props.metastoreStatus
      serviceName = 'MetaStore'
      break
    default:
      return '未知服务'
  }

  if (!status) return `${serviceName}: 未知状态`

  const statusText = status.status === 'success' ? '连接正常' :
                    status.status === 'error' ? '连接异常' :
                    status.status === 'testing' ? '正在测试' : '未测试'

  const message = status.message ? `\n${status.message}` : ''
  const mode = status.mode ? `\n模式: ${status.mode}` : ''

  return `${serviceName}: ${statusText}${message}${mode}\n\n点击重新测试`
}
</script>

<style scoped>
.connection-status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.service-indicators {
  display: flex;
  gap: 8px;
  align-items: center;
}

.service-indicator {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--gray-100);
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid var(--gray-200);
}

.service-indicator:hover {
  transform: scale(1.1);
  background: var(--gray-150);
}

.service-icon {
  font-size: 12px;
  color: var(--gray-500);
  z-index: 1;
}

.status-dot {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 2px solid white;
  z-index: 2;
}

.status-success .status-dot {
  background: #22c55e;
  box-shadow: 0 0 4px rgba(34, 197, 94, 0.5);
}

.status-error .status-dot {
  background: #ef4444;
  box-shadow: 0 0 4px rgba(239, 68, 68, 0.5);
}

.status-testing .status-dot {
  background: #f59e0b;
  box-shadow: 0 0 4px rgba(245, 158, 11, 0.5);
  animation: pulse 1.5s infinite;
}

.status-unknown .status-dot {
  background: var(--gray-400);
}

.loading-indicator {
  display: flex;
  align-items: center;
  color: var(--gray-500);
}

.rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.2);
  }
}
</style>