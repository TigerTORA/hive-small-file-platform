<template>
  <div class="tasks">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>任务管理</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            创建任务
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="合并任务" name="merge">
          <el-table :data="tasks" stripe v-loading="loading">
            <el-table-column prop="task_name" label="任务名称" width="200" />
            <el-table-column prop="database_name" label="数据库" width="120" />
            <el-table-column prop="table_name" label="表名" width="200" />
            <el-table-column prop="merge_strategy" label="合并策略" width="120">
              <template #default="{ row }">
                <el-tag :type="row.merge_strategy === 'concatenate' ? 'success' : 'warning'" size="small">
                  {{ row.merge_strategy === 'concatenate' ? '文件合并' : '重写插入' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <div class="status-column">
                  <el-tag :type="getStatusType(row.status)" size="small">
                    {{ getStatusText(row.status) }}
                  </el-tag>
                  <div v-if="row.status === 'running'" class="execution-phase">
                    <span class="phase-text">{{ getExecutionPhase(row) }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="执行进度" width="180" v-if="hasRunningTasks">
              <template #default="{ row }">
                <div v-if="row.status === 'running'" class="progress-column">
                  <el-progress 
                    :percentage="getTaskProgress(row)" 
                    :status="row.status === 'failed' ? 'exception' : undefined"
                    :stroke-width="6"
                  />
                  <div class="progress-details">
                    <span class="progress-text">{{ getProgressText(row) }}</span>
                  </div>
                </div>
                <div v-else-if="row.status === 'success'" class="completed-info">
                  <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
                  <span>已完成</span>
                </div>
                <div v-else-if="row.status === 'failed'" class="failed-info">
                  <el-icon color="#f56c6c"><CircleCloseFilled /></el-icon>
                  <span>执行失败</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="处理前文件数" width="140">
              <template #default="{ row }">
                {{ displayFiles(row.files_before) }}
              </template>
            </el-table-column>
            <el-table-column label="处理后文件数" width="140">
              <template #default="{ row }">
                {{ displayFiles(row.files_after) }}
              </template>
            </el-table-column>
            <el-table-column prop="created_time" label="创建时间" width="160">
              <template #default="{ row }">
                {{ formatTime(row.created_time) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="250">
              <template #default="{ row }">
                <el-button v-if="row.status === 'pending'" type="success" size="small" @click="showPreview(row)">预览</el-button>
                <el-button v-if="row.status === 'pending'" type="primary" size="small" @click="executeTask(row)">执行</el-button>
                <el-button v-if="row.status === 'running'" type="warning" size="small" @click="cancelTask(row)">取消</el-button>
                <el-button type="info" size="small" @click="viewLogs(row)">日志</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="扫描任务" name="scan">
          <el-table :data="scanTasks" stripe v-loading="loadingScan">
            <el-table-column prop="task_id" label="任务ID" width="260" />
            <el-table-column prop="task_name" label="任务名称" min-width="200" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" width="180">
              <template #default="{ row }">
                <el-progress :percentage="row.progress_percentage || 0" :status="row.status === 'failed' ? 'exception' : undefined" />
              </template>
            </el-table-column>
            <el-table-column prop="start_time" label="开始时间" width="160">
              <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button size="small" @click="openScanLogs(row.task_id)">查看日志</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 创建任务对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建合并任务" width="600px">
      <el-form :model="taskForm" :rules="taskRules" ref="taskFormRef" label-width="120px">
        <el-form-item label="集群" prop="cluster_id">
          <el-select v-model="taskForm.cluster_id" placeholder="选择集群">
            <el-option
              v-for="cluster in clusters"
              :key="cluster.id"
              :label="cluster.name"
              :value="cluster.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="taskForm.task_name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="数据库" prop="database_name">
          <el-input v-model="taskForm.database_name" placeholder="请输入数据库名" />
        </el-form-item>
        <el-form-item label="表名" prop="table_name">
          <el-input 
            v-model="taskForm.table_name" 
            placeholder="请输入表名" 
            @blur="checkTablePartitions"
          />
        </el-form-item>
        
        <!-- 表信息显示 -->
        <el-form-item v-if="tableInfo" label="表信息">
          <el-tag :type="tableInfo.is_partitioned ? 'success' : 'info'" size="small">
            {{ tableInfo.is_partitioned ? '分区表' : '普通表' }}
          </el-tag>
          <span v-if="tableInfo.is_partitioned" style="margin-left: 8px; color: #606266;">
            共 {{ tableInfo.partition_count }} 个分区
          </span>
        </el-form-item>
        
        <!-- 分区选择 -->
        <el-form-item v-if="tableInfo?.is_partitioned" label="分区选择">
          <el-button 
            size="small" 
            @click="loadPartitions"
            :loading="partitionsLoading"
            style="margin-bottom: 8px;"
          >
            加载分区列表
          </el-button>
          
          <div v-if="partitions.length > 0" style="max-height: 200px; overflow-y: auto; border: 1px solid #dcdfe6; border-radius: 4px; padding: 8px;">
            <el-checkbox-group v-model="selectedPartitions">
              <div v-for="partition in partitions" :key="partition.partition_spec">
                <el-checkbox :label="partition.partition_spec">
                  {{ partition.partition_spec }}
                </el-checkbox>
              </div>
            </el-checkbox-group>
          </div>
          
          <el-input 
            v-if="!tableInfo?.is_partitioned" 
            v-model="taskForm.partition_filter" 
            placeholder="手动输入分区过滤器，如: dt='2023-12-01'"
            style="margin-top: 8px;"
          />
        </el-form-item>
        
        <!-- 非分区表的分区过滤器输入 -->
        <el-form-item v-else label="分区过滤">
          <el-input v-model="taskForm.partition_filter" placeholder="如: dt='2023-12-01' (可选)" />
        </el-form-item>
        
        <el-form-item label="合并策略">
          <el-radio-group v-model="taskForm.merge_strategy">
            <el-radio label="safe_merge">安全合并 (推荐)</el-radio>
            <el-radio label="concatenate">文件合并 (CONCATENATE)</el-radio>
            <el-radio label="insert_overwrite">重写插入 (INSERT OVERWRITE)</el-radio>
          </el-radio-group>
          <div style="margin-top: 4px; font-size: 12px; color: #909399;">
            安全合并使用临时表+重命名策略，确保零停机时间
          </div>
        </el-form-item>
        <el-form-item label="目标文件大小">
          <el-input-number
            v-model="taskForm.target_file_size"
            :min="1024 * 1024"
            :step="64 * 1024 * 1024"
            placeholder="字节"
          />
          <span style="margin-left: 8px; color: #909399;">字节（可选）</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" @click="createTask">创建</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 日志查看对话框 -->
    <el-dialog v-model="showLogsDialog" title="任务日志" width="800px">
      <div class="logs-container">
        <div v-if="taskLogs.length === 0" class="no-logs">
          暂无日志记录
        </div>
        <div v-else>
          <div
            v-for="log in taskLogs"
            :key="log.id"
            :class="['log-entry', `log-${log.log_level.toLowerCase()}`]"
          >
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
            <span class="log-level">{{ log.log_level }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 预览对话框 -->
    <el-dialog v-model="showPreviewDialog" title="合并预览" width="700px">
      <div v-if="previewLoading" style="text-align: center; padding: 20px;">
        <el-icon class="is-loading"><Loading /></el-icon>
        <div style="margin-top: 10px;">正在生成预览...</div>
      </div>
      
      <div v-else-if="previewData" class="preview-container">
        <div class="preview-section">
          <h3>任务信息</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="任务名称">{{ previewData.task_name }}</el-descriptions-item>
            <el-descriptions-item label="目标表">{{ previewData.table }}</el-descriptions-item>
            <el-descriptions-item label="合并策略">
              <el-tag :type="previewData.merge_strategy === 'safe_merge' ? 'success' : 'warning'">
                {{ getStrategyName(previewData.merge_strategy) }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="preview-section">
          <h3>预期效果</h3>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic title="合并前文件数" :value="previewData.preview.estimated_files_before" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="合并后文件数" :value="previewData.preview.estimated_files_after" />
            </el-col>
            <el-col :span="6">
              <el-statistic 
                title="预计节省空间" 
                :value="formatBytes(previewData.preview.estimated_size_reduction)" 
                suffix="B" 
              />
            </el-col>
            <el-col :span="6">
              <el-statistic 
                title="预计耗时" 
                :value="previewData.preview.estimated_duration" 
                suffix="秒" 
              />
            </el-col>
          </el-row>
        </div>

        <div v-if="previewData.preview.warnings && previewData.preview.warnings.length > 0" class="preview-section">
          <h3>注意事项</h3>
          <el-alert 
            v-for="(warning, index) in previewData.preview.warnings" 
            :key="index"
            :title="warning" 
            type="warning" 
            show-icon 
            style="margin-bottom: 10px;"
          />
        </div>

        <div v-if="previewData.preview.is_partitioned" class="preview-section">
          <h3>分区信息</h3>
          <p>
            <el-tag type="info">分区表</el-tag>
            <span style="margin-left: 10px;">共 {{ previewData.preview.partitions?.length || 0 }} 个分区</span>
          </p>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showPreviewDialog = false">关闭</el-button>
          <el-button v-if="previewData && !previewLoading" type="primary" @click="executeTaskFromPreview">
            确认执行
          </el-button>
        </div>
      </template>
    </el-dialog>
    <ScanProgressDialog v-model="showScanDialog" :task-id="selectedScanTaskId" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { tasksApi, type MergeTask, type MergeTaskCreate } from '@/api/tasks'
import { clustersApi, type Cluster } from '@/api/clusters'
import { scanTasksApi, type ScanTask } from '@/api/scanTasks'
import ScanProgressDialog from '@/components/ScanProgressDialog.vue'
import dayjs from 'dayjs'

// 数据
const activeTab = ref('merge')
const tasks = ref<MergeTask[]>([])
const scanTasks = ref<ScanTask[]>([])
const clusters = ref<Cluster[]>([])
const loading = ref(false)
const loadingScan = ref(false)
const showCreateDialog = ref(false)
const showLogsDialog = ref(false)
const showPreviewDialog = ref(false)
const showScanDialog = ref(false)
const taskLogs = ref<any[]>([])
const previewData = ref<any>(null)
const previewLoading = ref(false)
const previewingTask = ref<MergeTask | null>(null)
const selectedScanTaskId = ref<string | null>(null)

// 分区相关数据
const tableInfo = ref<any>(null)
const partitions = ref<any[]>([])
const selectedPartitions = ref<string[]>([])
const partitionsLoading = ref(false)

// 表单数据
const taskForm = ref<MergeTaskCreate>({
  cluster_id: 0,
  task_name: '',
  table_name: '',
  database_name: '',
  partition_filter: '',
  merge_strategy: 'safe_merge'
})

const taskRules = {
  cluster_id: [{ required: true, message: '请选择集群', trigger: 'change' }],
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  database_name: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
  table_name: [{ required: true, message: '请输入表名', trigger: 'blur' }]
}

const taskFormRef = ref()

// 方法
const loadTasks = async () => {
  loading.value = true
  try {
    tasks.value = await tasksApi.list()
  } catch (error) {
    console.error('Failed to load tasks:', error)
  } finally {
    loading.value = false
  }
}

const loadScanTasks = async () => {
  loadingScan.value = true
  try {
    scanTasks.value = await scanTasksApi.list()
  } catch (error) {
    console.error('Failed to load scan tasks:', error)
  } finally {
    loadingScan.value = false
  }
}

const loadClusters = async () => {
  try {
    clusters.value = await clustersApi.list()
  } catch (error) {
    console.error('Failed to load clusters:', error)
  }
}

const createTask = async () => {
  try {
    await taskFormRef.value.validate()
    
    // 准备任务数据
    const taskData = { ...taskForm.value }
    
    // 处理分区选择
    if (tableInfo.value?.is_partitioned && selectedPartitions.value.length > 0) {
      // 构建分区过滤器：多个分区用OR连接
      const partitionFilters = selectedPartitions.value.map(partition => `(${partition})`)
      taskData.partition_filter = partitionFilters.join(' OR ')
    }
    
    await tasksApi.create(taskData)
    
    ElMessage.success('任务创建成功')
    showCreateDialog.value = false
    resetTaskForm()
    loadTasks()
  } catch (error) {
    console.error('Failed to create task:', error)
    ElMessage.error('创建任务失败')
  }
}

const executeTask = async (task: MergeTask) => {
  try {
    await tasksApi.execute(task.id)
    ElMessage.success('任务执行已启动')
    loadTasks()
  } catch (error) {
    console.error('Failed to execute task:', error)
  }
}

const cancelTask = async (task: MergeTask) => {
  try {
    await ElMessageBox.confirm(
      `确定要取消任务 "${task.task_name}" 吗？`,
      '确认取消',
      {
        confirmButtonText: '取消任务',
        cancelButtonText: '不取消',
        type: 'warning'
      }
    )
    
    await tasksApi.cancel(task.id)
    ElMessage.success('任务已取消')
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to cancel task:', error)
    }
  }
}

const viewLogs = async (task: MergeTask) => {
  try {
    taskLogs.value = await tasksApi.getLogs(task.id)
    showLogsDialog.value = true
  } catch (error) {
    console.error('Failed to load task logs:', error)
  }
}

const openScanLogs = (taskId: string) => {
  selectedScanTaskId.value = taskId
  showScanDialog.value = true
}

const resetTaskForm = () => {
  taskForm.value = {
    cluster_id: 0,
    task_name: '',
    table_name: '',
    database_name: '',
    partition_filter: '',
    merge_strategy: 'safe_merge'
  }
  // 清空分区相关数据
  tableInfo.value = null
  partitions.value = []
  selectedPartitions.value = []
}

const getStatusType = (status: string): string => {
  const statusMap: Record<string, string> = {
    'pending': 'info',
    'running': 'warning',
    'success': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    'pending': '等待中',
    'running': '运行中',
    'success': '成功',
    'failed': '失败'
  }
  return statusMap[status] || status
}

const formatTime = (time: string): string => {
  return dayjs(time).format('MM-DD HH:mm:ss')
}

// 显示文件数：统计失败或为空时显示 NaN
const displayFiles = (value: number | null | undefined) => {
  if (value === null || value === undefined) return 'NaN'
  return value
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const getStrategyName = (strategy: string): string => {
  const strategyMap: Record<string, string> = {
    'safe_merge': '安全合并',
    'concatenate': '文件合并',
    'insert_overwrite': '重写插入'
  }
  return strategyMap[strategy] || strategy
}

// 显示任务预览
const showPreview = async (task: MergeTask) => {
  try {
    previewingTask.value = task
    previewData.value = null
    showPreviewDialog.value = true
    previewLoading.value = true
    
    const preview = await tasksApi.getTaskPreview(task.id)
    previewData.value = preview
  } catch (error) {
    console.error('Failed to load task preview:', error)
    ElMessage.error('获取预览信息失败')
  } finally {
    previewLoading.value = false
  }
}

// 从预览对话框执行任务
const executeTaskFromPreview = async () => {
  if (previewingTask.value) {
    showPreviewDialog.value = false
    await executeTask(previewingTask.value)
  }
}

// 检查表分区信息
const checkTablePartitions = async () => {
  if (!taskForm.value.cluster_id || !taskForm.value.database_name || !taskForm.value.table_name) {
    return
  }
  
  try {
    tableInfo.value = await tasksApi.getTableInfo(
      taskForm.value.cluster_id,
      taskForm.value.database_name,
      taskForm.value.table_name
    )
    // 清空之前的分区数据
    partitions.value = []
    selectedPartitions.value = []
  } catch (error) {
    console.error('Failed to get table info:', error)
    tableInfo.value = null
  }
}

// 加载分区列表
const loadPartitions = async () => {
  if (!taskForm.value.cluster_id || !taskForm.value.database_name || !taskForm.value.table_name) {
    ElMessage.warning('请先选择集群、数据库和表名')
    return
  }
  
  partitionsLoading.value = true
  try {
    const response = await tasksApi.getTablePartitions(
      taskForm.value.cluster_id,
      taskForm.value.database_name,
      taskForm.value.table_name
    )
    partitions.value = response.partitions || []
    selectedPartitions.value = []
  } catch (error) {
    console.error('Failed to load partitions:', error)
    ElMessage.error('加载分区列表失败')
  } finally {
    partitionsLoading.value = false
  }
}

// 任务进度监控相关
const pollingInterval = ref<NodeJS.Timeout | null>(null)

// 获取任务执行阶段
const getExecutionPhase = (row: MergeTask): string => {
  if (row.status !== 'running') return ''
  
  // 基于任务的详细信息判断当前执行阶段
  if (row.execution_phase) {
    const phaseMap: Record<string, string> = {
      'initialization': '初始化中',
      'connection_test': '连接测试',
      'pre_validation': '预验证',
      'file_analysis': '文件分析',
      'temp_table_creation': '创建临时表',
      'data_validation': '数据验证',
      'atomic_swap': '原子切换',
      'post_validation': '后验证',
      'cleanup': '清理中',
      'completion': '完成中'
    }
    return phaseMap[row.execution_phase] || row.execution_phase
  }
  
  // 默认基于状态返回阶段
  return '执行中'
}

// 获取任务进度百分比
const getTaskProgress = (row: MergeTask): number => {
  if (row.status === 'success') return 100
  if (row.status === 'failed') return 0
  
  // 基于执行阶段计算进度
  if (row.execution_phase) {
    const progressMap: Record<string, number> = {
      'initialization': 5,
      'connection_test': 10,
      'pre_validation': 15,
      'file_analysis': 25,
      'temp_table_creation': 45,
      'data_validation': 65,
      'atomic_swap': 80,
      'post_validation': 90,
      'cleanup': 95,
      'completion': 98
    }
    return progressMap[row.execution_phase] || 50
  }
  
  // 如果有具体进度信息，使用具体值
  if (row.progress_percentage !== undefined && row.progress_percentage !== null) {
    return row.progress_percentage
  }
  
  return 50 // 默认进度
}

// 获取进度文本
const getProgressText = (row: MergeTask): string => {
  if (row.status !== 'running') return ''
  
  const phase = getExecutionPhase(row)
  const progress = getTaskProgress(row)
  
  // 如果有估计剩余时间，显示剩余时间
  if (row.estimated_remaining_time) {
    return `${phase} - ${progress}% (预计剩余 ${formatDuration(row.estimated_remaining_time)})`
  }
  
  // 如果有处理的文件数信息
  if (row.processed_files_count && row.total_files_count) {
    return `${phase} - ${row.processed_files_count}/${row.total_files_count} 文件`
  }
  
  return `${phase} - ${progress}%`
}

// 检查是否有运行中的任务
const hasRunningTasks = computed(() => {
  return tasks.value.some(task => task.status === 'running')
})

// 格式化持续时间
const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${Math.round(seconds)}秒`
  if (seconds < 3600) return `${Math.round(seconds / 60)}分钟`
  return `${Math.round(seconds / 3600)}小时`
}

// 启动任务状态轮询
const startPolling = () => {
  if (pollingInterval.value) return
  
  pollingInterval.value = setInterval(() => {
    // 只有在有运行中任务时才轮询
    if (hasRunningTasks.value) {
      loadTasks()
    } else {
      stopPolling() // 没有运行中的任务时停止轮询
    }
  }, 3000) // 每3秒轮询一次
}

// 停止任务状态轮询
const stopPolling = () => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
  }
}

// 监听任务状态变化，自动启动/停止轮询
watch(
  () => hasRunningTasks.value,
  (hasRunning) => {
    if (hasRunning) {
      startPolling()
    } else {
      stopPolling()
    }
  }
)

onMounted(() => {
  loadTasks()
  loadClusters()
  loadScanTasks()
  
  // 如果有运行中的任务，启动轮询
  if (hasRunningTasks.value) {
    startPolling()
  }
})

// 组件卸载时清理轮询
onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logs-container {
  max-height: 400px;
  overflow-y: auto;
  background-color: #f5f5f5;
  padding: 16px;
  border-radius: 4px;
}

.no-logs {
  text-align: center;
  color: #909399;
  padding: 20px;
}

.log-entry {
  margin-bottom: 8px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.4;
}

.log-time {
  color: #909399;
  margin-right: 8px;
}

.log-level {
  display: inline-block;
  width: 60px;
  text-align: center;
  margin-right: 8px;
  font-weight: 600;
}

.log-info .log-level {
  color: #409eff;
}

.log-warning .log-level {
  color: #e6a23c;
}

.log-error .log-level {
  color: #f56c6c;
}

.log-message {
  color: #2c3e50;
}

.preview-container {
  padding: 16px 0;
}

.preview-section {
  margin-bottom: 24px;
}

.preview-section:last-child {
  margin-bottom: 0;
}

.preview-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #2c3e50;
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

/* 任务执行进度样式 */
.status-column {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.execution-phase {
  margin-top: 4px;
}

.phase-text {
  font-size: 11px;
  color: #909399;
  font-style: italic;
}

.progress-column {
  width: 100%;
}

.progress-details {
  margin-top: 4px;
  text-align: center;
}

.progress-text {
  font-size: 11px;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
  display: inline-block;
}

.completed-info,
.failed-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
  color: #606266;
}

.completed-info {
  color: #67c23a;
}

.failed-info {
  color: #f56c6c;
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .progress-text {
    max-width: 120px;
  }
}
</style>
