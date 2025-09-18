<template>
  <div class="tasks-view">
    <div class="tasks-header">
      <div class="filters">
        <el-select
          v-model="statusFilter"
          placeholder="任务状态"
          clearable
          style="width: 150px"
        >
          <el-option
            label="全部"
            value=""
          />
          <el-option
            label="等待中"
            value="pending"
          />
          <el-option
            label="运行中"
            value="running"
          />
          <el-option
            label="已完成"
            value="success"
          />
          <el-option
            label="失败"
            value="failed"
          />
        </el-select>
      </div>

      <div class="actions">
        <el-button @click="refreshTasks">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-tabs
      v-model="activeTab"
      type="border-card"
    >
      <el-tab-pane
        label="合并任务"
        name="merge"
      >
        <el-table
          :data="filteredMergeTasks"
          v-loading="loading"
          stripe
          style="width: 100%"
        >
          <el-table-column
            prop="id"
            label="任务ID"
            width="90"
          />
          <el-table-column
            label="表信息"
            min-width="200"
          >
            <template #default="{ row }"> {{ row.database_name }}.{{ row.table_name }} </template>
          </el-table-column>
          <el-table-column
            prop="merge_strategy"
            label="策略"
            width="140"
          />
          <el-table-column
            prop="status"
            label="状态"
            width="100"
          >
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="created_time"
            label="创建时间"
            width="180"
          >
            <template #default="{ row }">
              {{ formatTime(row.created_time) }}
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="150"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                size="small"
                @click="viewTaskDetail(row)"
                >详情</el-button
              >
              <el-button
                v-if="row.status === 'failed'"
                size="small"
                type="warning"
                @click="retryTask(row)"
                >重试</el-button
              >
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane
        label="扫描任务"
        name="scan"
      >
        <el-table
          :data="filteredScanTasks"
          v-loading="loadingScan"
          stripe
          style="width: 100%"
        >
          <el-table-column
            prop="task_id"
            label="任务ID"
            width="260"
          />
          <el-table-column
            prop="task_name"
            label="任务名称"
            min-width="200"
          />
          <el-table-column
            prop="status"
            label="状态"
            width="100"
          >
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="进度"
            width="180"
          >
            <template #default="{ row }">
              <el-progress
                :percentage="row.progress_percentage || 0"
                :status="row.status === 'failed' ? 'exception' : undefined"
              />
            </template>
          </el-table-column>
          <el-table-column
            prop="start_time"
            label="开始时间"
            width="180"
          >
            <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="160"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                size="small"
                @click="openScanLogs(row.task_id)"
                >查看日志</el-button
              >
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <ScanProgressDialog
      v-model="showScanDialog"
      :task-id="selectedScanTaskId"
      @completed="onScanCompleted"
    />
  </div>
</template>

<script setup lang="ts">
  import { ref, computed, onMounted } from 'vue'
  import { ElMessage } from 'element-plus'
  import { Refresh } from '@element-plus/icons-vue'
  import { tasksApi } from '@/api/tasks'
  import { scanTasksApi, type ScanTask } from '@/api/scanTasks'
  import ScanProgressDialog from '@/components/ScanProgressDialog.vue'
  import dayjs from 'dayjs'

  interface Props {
    clusterId: number
  }

  const props = defineProps<Props>()

  // Data
  const activeTab = ref('merge')
  const mergeTasks = ref<any[]>([])
  const scanTasks = ref<ScanTask[]>([])
  const loading = ref(false)
  const loadingScan = ref(false)
  const statusFilter = ref('')
  const showScanDialog = ref(false)
  const selectedScanTaskId = ref<string | null>(null)

  // Computed
  const filteredMergeTasks = computed(() => {
    if (!statusFilter.value) return mergeTasks.value
    return mergeTasks.value.filter(task => task.status === statusFilter.value)
  })

  const filteredScanTasks = computed(() => {
    if (!statusFilter.value) return scanTasks.value
    return scanTasks.value.filter(task => task.status === statusFilter.value)
  })

  // Methods
  const loadMergeTasks = async () => {
    loading.value = true
    try {
      mergeTasks.value = await tasksApi.getByCluster(props.clusterId)
    } catch (error) {
      console.error('Failed to load merge tasks:', error)
      ElMessage.error('加载合并任务列表失败')
    } finally {
      loading.value = false
    }
  }

  const loadScanTasks = async () => {
    loadingScan.value = true
    try {
      scanTasks.value = await scanTasksApi.list(props.clusterId)
    } catch (error) {
      console.error('Failed to load scan tasks:', error)
      ElMessage.error('加载扫描任务列表失败')
    } finally {
      loadingScan.value = false
    }
  }

  const refreshTasks = () => {
    loadMergeTasks()
    loadScanTasks()
  }

  const viewTaskDetail = (task: any) => {
    // TODO: Implement task detail view
    ElMessage.info('任务详情功能开发中')
  }

  const retryTask = async (task: any) => {
    try {
      await tasksApi.retry(task.id)
      ElMessage.success('任务重试成功')
      await loadMergeTasks()
    } catch (error) {
      console.error('Failed to retry task:', error)
      ElMessage.error('任务重试失败')
    }
  }

  const getStatusType = (status: string) => {
    const statusMap = {
      pending: '',
      running: 'warning',
      success: 'success',
      failed: 'danger'
    }
    return statusMap[status as keyof typeof statusMap] || ''
  }

  const getStatusText = (status: string) => {
    const statusMap = {
      pending: '等待中',
      running: '运行中',
      success: '已完成',
      failed: '失败'
    }
    return statusMap[status as keyof typeof statusMap] || status
  }

  const formatTime = (time: string): string => {
    return dayjs(time).format('MM-DD HH:mm:ss')
  }

  onMounted(() => {
    loadMergeTasks()
    loadScanTasks()
  })

  const openScanLogs = (taskId: string) => {
    selectedScanTaskId.value = taskId
    showScanDialog.value = true
  }

  const onScanCompleted = async () => {
    ElMessage.success('扫描任务已完成')
    await loadScanTasks()
  }
</script>

<style scoped>
  .tasks-view {
    height: 100%;
  }

  .tasks-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  .filters {
    display: flex;
    gap: 15px;
    align-items: center;
  }

  .actions {
    display: flex;
    gap: 10px;
  }
</style>
