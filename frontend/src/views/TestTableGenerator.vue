<template>
  <div class="test-table-generator">
    <el-card class="header-card">
      <template #header>
        <div class="card-header">
          <h2>
            <el-icon><Tools /></el-icon>
            测试表生成器
          </h2>
          <p>为小文件治理平台生成测试用的外部表</p>
        </div>
      </template>

      <!-- 场景选择 -->
      <div class="scenario-section">
        <h3>选择测试场景</h3>
        <el-row :gutter="16">
          <el-col v-for="(scenario, key) in scenarios" :key="key" :span="6">
            <el-card
              class="scenario-card"
              :class="{ active: selectedScenario === key }"
              @click="selectScenario(key, scenario)"
              shadow="hover"
            >
              <div class="scenario-content">
                <h4>{{ scenario.name_cn }}</h4>
                <p>{{ scenario.description }}</p>
                <div class="scenario-stats">
                  <el-tag size="small">{{ scenario.estimated_files }} 文件</el-tag>
                  <el-tag size="small" type="info">{{ scenario.estimated_size_mb.toFixed(1) }}MB</el-tag>
                  <el-tag size="small" type="warning">~{{ scenario.estimated_duration_minutes }}分钟</el-tag>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>

    <!-- 配置表单 -->
    <el-card class="config-card">
      <template #header>
        <h3>配置参数</h3>
      </template>

      <el-form :model="config" :rules="rules" ref="configForm" label-width="150px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="集群" prop="cluster_id" required>
              <el-select v-model="config.cluster_id" placeholder="请选择目标集群" style="width: 100%">
                <el-option
                  v-for="cluster in clusters"
                  :key="cluster.id"
                  :label="cluster.name"
                  :value="cluster.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="表名" prop="table_name">
              <el-input v-model="config.table_name" placeholder="test_small_files_table" />
            </el-form-item>

            <el-form-item label="数据库名" prop="database_name">
              <el-input v-model="config.database_name" placeholder="test_db" />
            </el-form-item>

            <el-form-item label="HDFS路径" prop="hdfs_base_path">
              <el-input v-model="config.hdfs_base_path" placeholder="/user/test/small_files_test" />
              <div class="form-tip">注意：请确保路径不会影响生产数据</div>
            </el-form-item>

            <el-form-item label="写入方式" prop="data_generation_mode">
              <el-select
                v-model="config.data_generation_mode"
                placeholder="请选择写入方式"
                style="width: 100%"
              >
                <el-option label="Beeline (LOAD DATA)" value="beeline" />
                <el-option label="WebHDFS 客户端" value="webhdfs" />
              </el-select>
              <div class="form-tip">Beeline 通过 Hive 加载本地文件，WebHDFS 直接写入 HDFS</div>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="分区数量" prop="partition_count">
              <el-input-number
                v-model="config.partition_count"
                :min="1"
                :max="1000"
                style="width: 100%"
                @change="updateEstimation"
              />
            </el-form-item>

            <el-form-item label="每分区文件数" prop="files_per_partition">
              <el-input-number
                v-model="config.files_per_partition"
                :min="1"
                :max="1000"
                style="width: 100%"
                @change="updateEstimation"
              />
            </el-form-item>

            <el-form-item label="单文件大小(KB)" prop="file_size_kb">
              <el-input-number
                v-model="config.file_size_kb"
                :min="1"
                :max="1024"
                style="width: 100%"
                @change="updateEstimation"
              />
            </el-form-item>

            <el-form-item>
              <el-checkbox v-model="config.force_recreate">
                强制重新创建（删除已存在的表和数据）
              </el-checkbox>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 预估信息 -->
        <el-alert
          v-if="estimation"
          :type="getEstimationType()"
          :title="`预估：${estimation.total_files} 个文件，${estimation.total_size_mb.toFixed(1)}MB，约需 ${estimation.duration_minutes} 分钟`"
          show-icon
          :closable="false"
        >
          <template v-if="estimation.warnings?.length">
            <div class="warnings">
              <p v-for="warning in estimation.warnings" :key="warning" class="warning">
                {{ warning }}
              </p>
            </div>
          </template>
        </el-alert>
      </el-form>

      <div class="action-buttons">
        <el-button @click="resetForm">重置</el-button>
        <el-button @click="validateConfig" type="info">验证配置</el-button>
        <el-button
          type="primary"
          :loading="creating"
          @click="createTestTable"
          :disabled="!isConfigValid"
        >
          <el-icon><Plus /></el-icon>
          创建测试表
        </el-button>
      </div>
    </el-card>

    <!-- 任务进度 -->
    <el-card v-if="currentTask" class="progress-card">
      <template #header>
        <div class="progress-header">
          <h3>创建进度</h3>
          <el-tag :type="getStatusType(currentTask.status)">{{ getStatusText(currentTask.status) }}</el-tag>
        </div>
      </template>

      <div class="progress-content">
        <el-progress
          :percentage="currentTask.progress_percentage"
          :status="currentTask.status === 'failed' ? 'exception' : undefined"
        />

        <div class="progress-details">
          <p><strong>当前阶段：</strong>{{ getPhaseText(currentTask.current_phase) }}</p>
          <p><strong>当前操作：</strong>{{ currentTask.current_operation }}</p>
          <p v-if="currentTask.error_message" class="error-message">
            <strong>错误信息：</strong>{{ currentTask.error_message }}
          </p>
        </div>

        <!-- 实时日志 -->
        <el-collapse v-if="taskLogs.length" v-model="logsCollapsed">
          <el-collapse-item title="执行日志" name="logs">
            <div class="logs-container">
              <div
                v-for="log in taskLogs"
                :key="log.id"
                class="log-entry"
                :class="log.level"
              >
                <span class="log-time">{{ formatTime(log.timestamp) }}</span>
                <span class="log-level">{{ log.level }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>

        <!-- 完成信息 -->
        <div v-if="currentTask.status === 'success'" class="success-info">
          <el-alert type="success" title="测试表创建成功！" show-icon :closable="false">
            <template #default>
              <div class="success-details">
                <p>📊 <strong>HDFS文件：</strong>{{ currentTask.hdfs_files_created }} 个</p>
                <p>📂 <strong>Hive分区：</strong>{{ currentTask.hive_partitions_added }} 个</p>
                <p>💾 <strong>总大小：</strong>{{ currentTask.total_size_mb?.toFixed(1) }}MB</p>
              </div>

              <div class="next-steps">
                <h4>下一步操作：</h4>
                <ol>
                  <li>在 <router-link to="/">监控中心</router-link> 查看小文件统计</li>
                  <li>在 <router-link to="/tables">表管理</router-link> 中扫描新创建的测试表</li>
                  <li>在 <router-link to="/tasks">任务管理</router-link> 中创建合并任务测试治理效果</li>
                </ol>
              </div>
            </template>
          </el-alert>
        </div>
      </div>
    </el-card>

    <!-- 历史任务 -->
    <el-card class="history-card">
      <template #header>
        <div class="flex justify-between items-center">
          <h3>历史任务</h3>
          <el-button size="small" @click="refreshTasks">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-table :data="historyTasks" style="width: 100%" max-height="300">
        <el-table-column prop="id" label="任务ID" width="100" />
        <el-table-column prop="config.table_name" label="表名" width="200" />
        <el-table-column prop="config.database_name" label="数据库" width="150" />
        <el-table-column label="文件数" width="100">
          <template #default="scope">
            {{ scope.row.config.partition_count * scope.row.config.files_per_partition }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150">
          <template #default="scope">
            <el-progress
              :percentage="scope.row.progress_percentage"
              :stroke-width="8"
              :show-text="false"
            />
            <span class="progress-text">{{ scope.row.progress_percentage.toFixed(1) }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_time" label="创建时间" width="160">
          <template #default="scope">
            {{ formatDateTime(scope.row.created_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button
              v-if="scope.row.status === 'running'"
              size="small"
              type="info"
              @click="watchTask(scope.row.id)"
            >
              查看
            </el-button>
            <el-button
              v-if="scope.row.status === 'success'"
              size="small"
              type="success"
              @click="verifyTable(scope.row)"
            >
              验证
            </el-button>
            <el-popconfirm
              v-if="scope.row.status === 'success'"
              title="确定要删除这个测试表吗？"
              @confirm="deleteTestTable(scope.row)"
            >
              <template #reference>
                <el-button size="small" type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, reactive, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { Tools, Plus, Refresh } from '@element-plus/icons-vue'
import { useTestTableApi } from '@/api/testTables'
import { useClustersApi } from '@/api/clusters'
import { useWebSocket } from '@/composables/useWebSocket'

const testTableApi = useTestTableApi()
const clustersApi = useClustersApi()

// 响应式数据
const scenarios = ref({})
const selectedScenario = ref('default')
const clusters = ref([])
const creating = ref(false)
const currentTask = ref(null)
const taskLogs = ref([])
const logsCollapsed = ref(['logs'])
const historyTasks = ref([])
const configForm = ref(null)

// 配置表单
const config = reactive({
  cluster_id: null,
  table_name: 'test_small_files_table',
  database_name: 'test_db',
  hdfs_base_path: '/user/test/small_files_test',
  partition_count: 10,
  files_per_partition: 100,
  file_size_kb: 50,
  scenario: 'default',
  data_generation_mode: 'beeline',
  force_recreate: false
})

// 预估信息
const estimation = ref(null)

// 表单验证规则
const rules = {
  cluster_id: [{ required: true, message: '请选择集群', trigger: 'change' }],
  table_name: [{ required: true, message: '请输入表名', trigger: 'blur' }],
  database_name: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
  hdfs_base_path: [{ required: true, message: '请输入HDFS路径', trigger: 'blur' }],
  data_generation_mode: [{ required: true, message: '请选择写入方式', trigger: 'change' }]
}

// WebSocket连接
const { connect, subscribe, disconnect } = useWebSocket()

// 计算属性
const isConfigValid = computed(() => {
  return (
    config.cluster_id &&
    config.table_name &&
    config.database_name &&
    config.hdfs_base_path &&
    config.data_generation_mode
  )
})

// 场景数据映射
const scenarioNameMap = {
  light: '轻量测试',
  default: '默认测试',
  heavy: '重度测试',
  extreme: '极限测试',
  custom: '自定义'
}

// 生命周期
onMounted(async () => {
  await loadInitialData()
  setupWebSocket()
})

// 方法定义
const loadInitialData = async () => {
  try {
    // 加载场景配置
    const scenarioData = await testTableApi.getScenarios()
    scenarios.value = Object.fromEntries(
      Object.entries(scenarioData.scenarios).map(([key, value]: [string, any]) => [
        key,
        {
          ...value,
          name_cn: scenarioNameMap[key] || value.name
        }
      ])
    )

    // 加载集群列表
    clusters.value = await clustersApi.list()

    // 加载历史任务
    await refreshTasks()

    // 选择默认场景
    if (scenarios.value.default) {
      selectScenario('default', scenarios.value.default)
    }
  } catch (error) {
    ElMessage.error('加载初始数据失败: ' + error.message)
  }
}

const setupWebSocket = () => {
  connect()
  subscribe(['test_table_tasks'])

  // 监听WebSocket消息
  window.addEventListener('websocket-message', handleWebSocketMessage)
}

const handleWebSocketMessage = (event) => {
  const message = event.detail
  if (message.type === 'test_table_task_update') {
    const taskData = message.data
    if (currentTask.value && currentTask.value.id === taskData.id) {
      currentTask.value = taskData

      // 如果任务完成，显示通知
      if (taskData.status === 'success') {
        ElNotification({
          title: '测试表创建成功',
          message: `表 ${taskData.config.database_name}.${taskData.config.table_name} 创建完成`,
          type: 'success',
          duration: 5000
        })
      } else if (taskData.status === 'failed') {
        ElNotification({
          title: '测试表创建失败',
          message: taskData.error_message,
          type: 'error',
          duration: 10000
        })
      }
    }

    // 更新历史任务列表
    const index = historyTasks.value.findIndex(task => task.id === taskData.id)
    if (index >= 0) {
      historyTasks.value[index] = taskData
    }
  }
}

const selectScenario = (key, scenario) => {
  selectedScenario.value = key
  if (key !== 'custom') {
    config.partition_count = scenario.config.partition_count
    config.files_per_partition = scenario.config.files_per_partition
    config.file_size_kb = scenario.config.file_size_kb
    config.data_generation_mode = scenario.config.data_generation_mode || 'beeline'
    config.scenario = key
  }
  updateEstimation()
}

// 监听配置参数的手动修改,自动切换到自定义场景
watch(
  () => [config.partition_count, config.files_per_partition, config.file_size_kb],
  (newValues, oldValues) => {
    // 仅当选中非自定义场景且参数被手动修改时切换
    if (selectedScenario.value !== 'custom' && scenarios.value[selectedScenario.value]) {
      const currentScenario = scenarios.value[selectedScenario.value]
      const scenarioConfig = currentScenario.config

      // 检查是否任一参数与当前场景配置不匹配
      const [newPartition, newFiles, newSize] = newValues
      if (
        newPartition !== scenarioConfig.partition_count ||
        newFiles !== scenarioConfig.files_per_partition ||
        newSize !== scenarioConfig.file_size_kb
      ) {
        selectedScenario.value = 'custom'
        config.scenario = 'custom'
        console.log('检测到手动修改配置参数,已切换至自定义场景')
      }
    }
  }
)

const updateEstimation = async () => {
  try {
    const response = await testTableApi.validateConfig({
      table_name: config.table_name,
      database_name: config.database_name,
      hdfs_base_path: config.hdfs_base_path,
      partition_count: config.partition_count,
      files_per_partition: config.files_per_partition,
      file_size_kb: config.file_size_kb
    })

    if (response.valid) {
      estimation.value = {
        total_files: response.estimated_files,
        total_size_mb: response.estimated_size_mb,
        duration_minutes: response.estimated_duration_minutes,
        warnings: response.warnings || []
      }
    }
  } catch (error) {
    console.error('更新预估信息失败:', error)
  }
}

const validateConfig = async () => {
  try {
    if (!configForm.value) {
      ElMessage.error('表单未初始化')
      return
    }
    await configForm.value.validate()
    await updateEstimation()
    ElMessage.success('配置验证通过')
  } catch (error) {
    ElMessage.error('配置验证失败')
  }
}

const createTestTable = async () => {
  try {
    if (!configForm.value) {
      ElMessage.error('表单未初始化')
      return
    }
    await configForm.value.validate()

    creating.value = true

    const request = {
      cluster_id: config.cluster_id,
      config: { ...config },
      force_recreate: config.force_recreate
    }

    const task = await testTableApi.createTestTable(request)
    currentTask.value = task

    // 订阅任务进度
    subscribe([`test_table_task_${task.id}`])

    ElMessage.success('测试表创建任务已启动')

    // 滚动到进度区域
    await nextTick()
    document.querySelector('.progress-card')?.scrollIntoView({ behavior: 'smooth' })

  } catch (error) {
    ElMessage.error('创建测试表失败: ' + error.message)
  } finally {
    creating.value = false
  }
}

const resetForm = () => {
  config.table_name = 'test_small_files_table'
  config.database_name = 'test_db'
  config.hdfs_base_path = '/user/test/small_files_test'
  config.partition_count = 10
  config.files_per_partition = 100
  config.file_size_kb = 50
  config.data_generation_mode = 'beeline'
  config.force_recreate = false
  selectedScenario.value = 'default'
  estimation.value = null
  currentTask.value = null
  configForm.value?.clearValidate()
}

const refreshTasks = async () => {
  try {
    historyTasks.value = await testTableApi.listTasks()
  } catch (error) {
    ElMessage.error('获取历史任务失败: ' + error.message)
  }
}

const watchTask = (taskId) => {
  // 切换到对应任务的监控
  subscribe([`test_table_task_${taskId}`])
  ElMessage.info('已切换到任务监控')
}

const verifyTable = async (task) => {
  try {
    const result = await testTableApi.verifyTestTable({
      cluster_id: task.cluster_id,
      database_name: task.config.database_name,
      table_name: task.config.table_name
    })

    if (result.verification_passed) {
      ElNotification({
        title: '验证通过',
        message: `表存在且数据完整，包含 ${result.partitions_count} 个分区，${result.hdfs_files_count} 个文件`,
        type: 'success'
      })
    } else {
      ElNotification({
        title: '验证失败',
        message: `发现问题：${result.issues.join(', ')}`,
        type: 'warning'
      })
    }
  } catch (error) {
    ElMessage.error('验证失败: ' + error.message)
  }
}

const deleteTestTable = async (task) => {
  try {
    await testTableApi.deleteTestTable({
      cluster_id: task.cluster_id,
      database_name: task.config.database_name,
      table_name: task.config.table_name,
      delete_hdfs_data: true
    })

    ElMessage.success('测试表删除成功')
    await refreshTasks()
  } catch (error) {
    ElMessage.error('删除测试表失败: ' + error.message)
  }
}

// 工具方法
const getEstimationType = () => {
  if (!estimation.value) return 'info'
  const totalFiles = estimation.value.total_files
  if (totalFiles > 10000) return 'error'
  if (totalFiles > 2000) return 'warning'
  return 'info'
}

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '等待中',
    running: '执行中',
    success: '成功',
    failed: '失败'
  }
  return texts[status] || status
}

const getPhaseText = (phase) => {
  const texts = {
    preparation: '准备阶段',
    hdfs_setup: 'HDFS设置',
    data_generation: '数据生成',
    hive_table_creation: 'Hive建表',
    verification: '验证阶段',
    completed: '完成',
    error: '出错'
  }
  return texts[phase] || phase
}

const formatTime = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString()
}

const formatDateTime = (timestamp) => {
  return new Date(timestamp).toLocaleString()
}

// 监听配置变化
// watch([() => config.partition_count, () => config.files_per_partition, () => config.file_size_kb],
//   updateEstimation,
//   { deep: true }
// )

// 清理
onBeforeUnmount(() => {
  disconnect()
  window.removeEventListener('websocket-message', handleWebSocketMessage)
})
</script>

<style scoped>
.test-table-generator {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.header-card .card-header h2 {
  margin: 0 0 8px 0;
  color: #409eff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-card .card-header p {
  margin: 0;
  color: #909399;
}

.scenario-section {
  margin-top: 20px;
}

.scenario-section h3 {
  margin: 0 0 16px 0;
  color: #303133;
}

.scenario-card {
  cursor: pointer;
  transition: all 0.3s;
  height: 120px;
}

.scenario-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.scenario-card.active {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.scenario-content h4 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 16px;
}

.scenario-content p {
  margin: 0 0 12px 0;
  color: #606266;
  font-size: 12px;
  line-height: 1.4;
}

.scenario-stats {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.config-card {
  margin-top: 20px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.warnings {
  margin-top: 8px;
}

.warning {
  margin: 4px 0;
  color: #e6a23c;
  font-size: 12px;
}

.action-buttons {
  text-align: right;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.progress-card {
  margin-top: 20px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-content {
  space-y: 16px;
}

.progress-details {
  margin: 16px 0;
}

.progress-details p {
  margin: 8px 0;
  color: #606266;
}

.error-message {
  color: #f56c6c;
}

.logs-container {
  max-height: 200px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
}

.log-entry {
  margin: 4px 0;
  display: flex;
  gap: 8px;
}

.log-time {
  color: #909399;
  min-width: 80px;
}

.log-level {
  min-width: 60px;
  font-weight: bold;
}

.log-level.ERROR {
  color: #f56c6c;
}

.log-level.WARNING {
  color: #e6a23c;
}

.log-level.INFO {
  color: #409eff;
}

.log-message {
  flex: 1;
}

.success-info {
  margin-top: 16px;
}

.success-details p {
  margin: 8px 0;
}

.next-steps {
  margin-top: 16px;
}

.next-steps h4 {
  margin: 0 0 8px 0;
  color: #303133;
}

.next-steps ol {
  margin: 8px 0;
  padding-left: 24px;
}

.next-steps li {
  margin: 4px 0;
}

.history-card {
  margin-top: 20px;
}

.progress-text {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.flex {
  display: flex;
}

.justify-between {
  justify-content: space-between;
}

.items-center {
  align-items: center;
}
</style>
