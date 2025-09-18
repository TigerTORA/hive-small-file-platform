<template>
  <el-dialog
    v-model="dialogVisible"
    title="集群连接测试"
    width="800px"
    :before-close="handleClose"
  >
    <div class="connection-test-dialog">
      <!-- 测试状态概览 -->
      <div class="status-overview">
        <el-tag
          :type="getStatusType(testResult?.overall_status)"
          size="large"
          class="status-tag"
        >
          {{ getStatusText(testResult?.overall_status) }}
        </el-tag>
        <span
          class="test-time"
          v-if="testResult?.test_time"
        >
          测试时间: {{ formatTime(testResult.test_time) }}
        </span>
      </div>

      <!-- 加载状态 -->
      <div
        v-if="testing"
        class="testing-status"
      >
        <el-icon class="rotating"><Loading /></el-icon>
        <span>正在测试连接...</span>
      </div>

      <!-- 连接测试结果 -->
      <div
        v-if="testResult && !testing"
        class="test-results"
      >
        <!-- 各组件测试结果 -->
        <div
          class="component-tests"
          v-if="testResult.tests"
        >
          <h4>组件连接状态</h4>
          <el-row :gutter="16">
            <el-col
              :span="8"
              v-if="testResult.tests.metastore"
            >
              <el-card class="test-card">
                <template #header>
                  <div class="card-header">
                    <el-icon><Coin /></el-icon>
                    <span>Hive MetaStore</span>
                    <el-tag
                      :type="getStatusType(testResult.tests.metastore?.status)"
                      size="small"
                    >
                      {{ testResult.tests.metastore?.status || 'unknown' }}
                    </el-tag>
                  </div>
                </template>
                <div class="test-details">
                  <p v-if="testResult.tests.metastore?.mode">
                    <strong>模式:</strong> {{ testResult.tests.metastore?.mode }}
                  </p>
                  <p v-if="testResult.tests.metastore?.message">
                    <strong>消息:</strong> {{ testResult.tests.metastore?.message }}
                  </p>
                  <p v-if="testResult.tests.metastore?.duration">
                    <strong>耗时:</strong> {{ testResult.tests.metastore?.duration }}ms
                  </p>
                </div>
              </el-card>
            </el-col>
            <el-col
              :span="8"
              v-if="testResult.tests.hdfs"
            >
              <el-card class="test-card">
                <template #header>
                  <div class="card-header">
                    <el-icon><FolderOpened /></el-icon>
                    <span>HDFS</span>
                    <el-tag
                      :type="getStatusType(testResult.tests.hdfs?.status)"
                      size="small"
                    >
                      {{ testResult.tests.hdfs?.status }}
                    </el-tag>
                  </div>
                </template>
                <div class="test-details">
                  <p v-if="testResult.tests.hdfs?.mode">
                    <strong>模式:</strong> {{ testResult.tests.hdfs?.mode }}
                  </p>
                  <p v-if="testResult.tests.hdfs?.message">
                    <strong>消息:</strong> {{ testResult.tests.hdfs?.message }}
                  </p>
                  <p v-if="testResult.tests.hdfs?.duration">
                    <strong>耗时:</strong> {{ testResult.tests.hdfs?.duration }}ms
                  </p>
                </div>
              </el-card>
            </el-col>
            <el-col
              :span="8"
              v-if="testResult.tests.beeline"
            >
              <el-card class="test-card">
                <template #header>
                  <div class="card-header">
                    <el-icon><Connection /></el-icon>
                    <span>Beeline/JDBC</span>
                    <el-tag
                      :type="getStatusType(testResult.tests.beeline?.status)"
                      size="small"
                    >
                      {{ testResult.tests.beeline?.status }}
                    </el-tag>
                  </div>
                </template>
                <div class="test-details">
                  <p v-if="testResult.tests.beeline.connection_type">
                    <strong>连接类型:</strong> {{ testResult.tests.beeline.connection_type }}
                  </p>
                  <p v-if="testResult.tests.beeline.driver">
                    <strong>驱动:</strong> {{ testResult.tests.beeline.driver }}
                  </p>
                  <p v-if="testResult.tests.beeline.message">
                    <strong>消息:</strong> {{ testResult.tests.beeline.message }}
                  </p>
                  <p
                    v-if="
                      testResult.tests.beeline.details &&
                      testResult.tests.beeline.details.connection_info &&
                      testResult.tests.beeline.details.connection_info.response_time_ms
                    "
                  >
                    <strong>响应时间:</strong>
                    {{ testResult.tests.beeline.details.connection_info.response_time_ms }}ms
                  </p>
                  <!-- 显示建议 -->
                  <div
                    v-if="
                      testResult.tests.beeline.details &&
                      testResult.tests.beeline.details.suggestions
                    "
                    class="suggestions-inline"
                  >
                    <p><strong>建议:</strong></p>
                    <ul class="suggestion-list">
                      <li
                        v-for="suggestion in testResult.tests.beeline.details.suggestions.slice(
                          0,
                          2
                        )"
                        :key="suggestion"
                      >
                        {{ suggestion }}
                      </li>
                    </ul>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <!-- 详细日志 -->
        <div
          class="logs-section"
          v-if="testResult.logs && testResult.logs.length > 0"
        >
          <h4>详细日志</h4>
          <div class="logs-container">
            <div
              v-for="(log, index) in testResult.logs"
              :key="index"
              :class="['log-entry', `log-${log.level?.toLowerCase()}`]"
            >
              <el-tag
                :type="getLogTagType(log.level)"
                size="small"
                >{{ log.level }}</el-tag
              >
              <span class="log-message">{{ log.message }}</span>
              <span
                class="log-timestamp"
                v-if="log.timestamp"
                >{{ formatTime(log.timestamp) }}</span
              >
            </div>
          </div>
        </div>

        <!-- 建议 -->
        <div
          class="suggestions-section"
          v-if="testResult.suggestions && testResult.suggestions.length > 0"
        >
          <h4>诊断建议</h4>
          <el-alert
            v-for="(suggestion, index) in testResult.suggestions"
            :key="index"
            :title="suggestion"
            type="info"
            :closable="false"
            class="suggestion-alert"
          />
        </div>

        <!-- 警告信息 -->
        <div
          class="warning-section"
          v-if="testResult.warning"
        >
          <el-alert
            :title="testResult.warning"
            type="warning"
            :closable="false"
            show-icon
          />
        </div>
      </div>

      <!-- 错误信息 -->
      <div
        v-if="error && !testing"
        class="error-section"
      >
        <el-alert
          :title="error"
          type="error"
          :closable="false"
          show-icon
        />
      </div>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button
          type="primary"
          @click="retestConnection"
          :loading="testing"
          >重新测试</el-button
        >
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
  import { ref, computed } from 'vue'
  import { ElDialog, ElTag, ElIcon, ElRow, ElCol, ElCard, ElAlert, ElButton } from 'element-plus'
  import { Loading, Coin, FolderOpened, Connection } from '@element-plus/icons-vue'

  interface TestResult {
    overall_status: string
    test_time: string
    tests?: {
      metastore?: {
        status: string
        mode?: string
        message?: string
        duration?: number
      }
      hdfs?: {
        status: string
        mode?: string
        message?: string
        duration?: number
      }
      beeline?: {
        status: string
        connection_type?: string
        driver?: string
        message?: string
        details?: {
          port_connectivity?: any
          jdbc_test?: any
          connection_info?: {
            response_time_ms?: number
            auth_method?: string
            jdbc_url?: string
          }
          suggestions?: string[]
        }
      }
    }
    logs?: Array<{
      level: string
      message: string
      timestamp?: string
    }>
    suggestions?: string[]
    warning?: string
    error?: string
  }

  interface Props {
    visible: boolean
    clusterConfig?: any
    testResult?: TestResult | null
    testing?: boolean
    error?: string | null
  }

  const props = withDefaults(defineProps<Props>(), {
    visible: false,
    testResult: null,
    testing: false,
    error: null
  })

  const emit = defineEmits<{
    'update:visible': [value: boolean]
    retest: [clusterConfig: any]
  }>()

  const dialogVisible = computed({
    get: () => props.visible,
    set: value => emit('update:visible', value)
  })

  const handleClose = () => {
    emit('update:visible', false)
  }

  const retestConnection = () => {
    if (props.clusterConfig) {
      emit('retest', props.clusterConfig)
    }
  }

  const getStatusType = (status: string) => {
    switch (status) {
      case 'success':
        return 'success'
      case 'partial':
        return 'warning'
      case 'failed':
        return 'danger'
      default:
        return 'info'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'success':
        return '连接成功'
      case 'partial':
        return '部分成功'
      case 'failed':
        return '连接失败'
      default:
        return '状态未知'
    }
  }

  const getLogTagType = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'error':
        return 'danger'
      case 'warn':
      case 'warning':
        return 'warning'
      case 'info':
        return 'info'
      case 'debug':
        return ''
      default:
        return 'info'
    }
  }

  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString('zh-CN')
    } catch {
      return timestamp
    }
  }
</script>

<style scoped>
  .connection-test-dialog {
    max-height: 600px;
    overflow-y: auto;
  }

  .status-overview {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
    padding: 16px;
    background-color: var(--el-bg-color-page);
    border-radius: 8px;
  }

  .status-tag {
    font-size: 16px;
    padding: 8px 16px;
  }

  .test-time {
    color: var(--el-text-color-secondary);
    font-size: 14px;
  }

  .testing-status {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 40px 0;
    color: var(--el-color-primary);
  }

  .rotating {
    animation: rotate 2s linear infinite;
  }

  @keyframes rotate {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  .test-results h4 {
    margin: 24px 0 16px 0;
    color: var(--el-text-color-primary);
    font-size: 16px;
    font-weight: 600;
  }

  .component-tests h4:first-child {
    margin-top: 0;
  }

  .test-card {
    height: 100%;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .test-details p {
    margin: 8px 0;
    font-size: 14px;
    line-height: 1.5;
  }

  .test-details strong {
    color: var(--el-text-color-primary);
  }

  .logs-container {
    max-height: 200px;
    overflow-y: auto;
    border: 1px solid var(--el-border-color);
    border-radius: 4px;
    background-color: var(--el-fill-color-blank);
  }

  .log-entry {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--el-border-color-lighter);
    font-family: 'Courier New', monospace;
    font-size: 13px;
  }

  .log-entry:last-child {
    border-bottom: none;
  }

  .log-entry.log-error {
    background-color: var(--el-color-error-light-9);
  }

  .log-entry.log-warning,
  .log-entry.log-warn {
    background-color: var(--el-color-warning-light-9);
  }

  .log-message {
    flex: 1;
    word-break: break-word;
  }

  .log-timestamp {
    color: var(--el-text-color-secondary);
    font-size: 12px;
    white-space: nowrap;
  }

  .suggestion-alert {
    margin-bottom: 8px;
  }

  .suggestion-alert:last-child {
    margin-bottom: 0;
  }

  .error-section,
  .warning-section {
    margin-top: 16px;
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }

  .suggestions-inline {
    margin-top: 12px;
    padding-top: 8px;
    border-top: 1px solid var(--el-border-color-lighter);
  }

  .suggestion-list {
    margin: 4px 0;
    padding-left: 16px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  .suggestion-list li {
    margin: 2px 0;
    line-height: 1.4;
  }
</style>
