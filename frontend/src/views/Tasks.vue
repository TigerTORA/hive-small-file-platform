<template>
  <div class="tasks-management">
    <!-- 页面头部 -->
    <TasksHeader :loading="loading" @refresh="handleRefresh" @create="showCreateDialog = true" />

    <!-- 主体：筛选器 + 内容 -->
    <div class="main-layout">
      <!-- 筛选器（左侧） -->
      <TasksFiltersPane
        v-model:globalSearch="filters.globalSearch.value"
        :selectedStatuses="filters.selectedStatuses.value"
        :selectedTypes="filters.selectedTypes.value"
        :selectedArchiveSubtypes="filters.selectedArchiveSubtypes.value"
        :statusOptions="filters.statusOptions"
        :typeOptions="filters.typeOptions"
        :archiveSubtypeOptions="filters.archiveSubtypeOptions"
        :statusCounts="filters.statusCounts.value"
        :typeCounts="filters.typeCounts.value"
        :archiveSubtypeCounts="filters.archiveSubtypeCounts.value"
        @toggleStatus="filters.toggleStatus"
        @toggleType="filters.toggleType"
        @toggleArchiveSubtype="filters.toggleArchiveSubtype"
        @reset="filters.resetFilters"
      />

      <!-- 内容（右侧） -->
      <div class="content-pane">
        <TasksTable
          :tasks="filters.filteredAllTasks.value"
          :archiveSummaries="tasksData.archiveSummaries.value"
          :showArchiveSummary="true"
          @viewLogs="handleViewLogs"
          @retry="handleRetry"
          @restore="handleRestore"
        />
      </div>
    </div>

    <!-- 创建任务对话框 -->
    <TaskCreateDialog
      v-model="showCreateDialog"
      v-model:formRef="taskFormRef"
      :taskForm="taskForm.taskForm.value"
      :taskRules="taskForm.taskRules"
      :clusters="tasksData.clusters.value"
      :tableInfo="taskForm.tableInfo.value"
      :partitions="taskForm.partitions.value"
      :selectedPartitions="taskForm.selectedPartitions.value"
      :partitionsLoading="taskForm.partitionsLoading.value"
      :storageFormatOptions="taskForm.storageFormatOptions"
      :compressionOptions="taskForm.compressionOptions"
      :disableFormatSelection="taskForm.disableFormatSelection.value"
      :disableCompressionSelection="taskForm.disableCompressionSelection.value"
      :tableFormatLabel="taskForm.tableFormatLabel.value"
      :tableCompressionLabel="taskForm.tableCompressionLabel.value"
      @checkPartitions="taskForm.checkTablePartitions"
      @loadPartitions="taskForm.loadPartitions"
      @create="handleCreateTask"
    />

    <!-- 任务运行对话框 -->
    <TaskRunDialog
      v-model="showRunDialog"
      :type="runDialogType"
      :scan-task-id="runScanTaskId || undefined"
      :merge-task-id="runMergeTaskId || undefined"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { tasksApi } from '@/api/tasks'
import { tablesApi } from '@/api/tables'
import { useMonitoringStore } from '@/stores/monitoring'
import TaskRunDialog from '@/components/TaskRunDialog.vue'
import TasksHeader from '@/components/tasks/TasksHeader.vue'
import TasksFiltersPane from '@/components/tasks/TasksFiltersPane.vue'
import TasksTable from '@/components/tasks/TasksTable.vue'
import TaskCreateDialog from '@/components/tasks/TaskCreateDialog.vue'
import { useTasksData } from '@/composables/tasks/useTasksData'
import { useTaskFilters } from '@/composables/tasks/useTaskFilters'
import { useTaskPolling, useScanAutoRefresh } from '@/composables/tasks/useTaskPolling'
import { useTaskForm } from '@/composables/tasks/useTaskForm'

const monitoringStore = useMonitoringStore()
const selectedClusterId = computed(() => monitoringStore.settings.selectedCluster)

// 使用组合式函数
const tasksData = useTasksData()
const filters = useTaskFilters(
  tasksData.tasks,
  tasksData.testTableTasks,
  tasksData.scanTasks,
  tasksData.archiveTasks
)
const polling = useTaskPolling(tasksData.tasks, tasksData.loadTasks)
const taskForm = useTaskForm()

// 扫描任务筛选和自动刷新
const scanClusterFilter = ref<number | null>(null)
const scanStatusFilter = ref<string>('')
const scanAutoRefresh = ref<number>(0)

const scanRefresh = useScanAutoRefresh(scanAutoRefresh, async () => {
  await tasksData.loadScanTasks(scanClusterFilter.value, scanStatusFilter.value)
  await tasksData.refreshArchiveSummaries()
})

// 对话框状态
const showRunDialog = ref(false)
const taskFormRef = ref()
const runDialogType = ref<'scan' | 'merge' | 'archive' | 'test-table'>('scan')
const runScanTaskId = ref<string | null>(null)
const runMergeTaskId = ref<number | string | null>(null)

// 解构数据
const { loading, showCreateDialog } = taskForm

/**
 * 刷新所有数据
 */
const handleRefresh = async () => {
  await tasksData.loadTasks()
  await tasksData.loadScanTasks(scanClusterFilter.value, scanStatusFilter.value)
  await tasksData.refreshArchiveSummaries()
}

/**
 * 查看日志
 */
const handleViewLogs = (row: any) => {
  if (row.type === 'scan') {
    runDialogType.value = 'scan'
    runScanTaskId.value = row.task_id || row.raw?.task_id
    runMergeTaskId.value = null
  } else if (row.type === 'merge') {
    runDialogType.value = 'merge'
    runMergeTaskId.value = row.raw?.id
    runScanTaskId.value = null
  } else if (row.type === 'archive') {
    runDialogType.value = 'archive'
    runScanTaskId.value = row.task_id || row.raw?.task_id || null
    runMergeTaskId.value = null
  } else if (row.type === 'test-table-generation') {
    runDialogType.value = 'test-table'
    runScanTaskId.value = null
    runMergeTaskId.value = row.id
  }
  showRunDialog.value = true
}

/**
 * 重试任务
 */
const handleRetry = async (row: any) => {
  try {
    const id = row.raw?.id || row.id
    if (!id) return
    await tasksApi.retry(id)
    ElMessage.success('已触发重试')
    runDialogType.value = 'merge'
    runMergeTaskId.value = id
    runScanTaskId.value = null
    showRunDialog.value = true
    await tasksData.loadTasks()
  } catch (e: any) {
    console.error('Retry failed', e)
    ElMessage.error(e?.message || '重试失败')
  }
}

/**
 * 恢复归档
 */
const handleRestore = async (row: any) => {
  try {
    const cid = selectedClusterId.value
    if (!cid) {
      ElMessage.warning('请先选择集群')
      return
    }
    await ElMessageBox.confirm(
      `确定要恢复 ${row.database_name}.${row.table_name} 吗？`,
      '确认恢复',
      {
        confirmButtonText: '恢复（后台任务）',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    const resp = await tablesApi.restoreTableWithProgress(
      cid as number,
      row.database_name,
      row.table_name
    )
    const taskId = (resp as any)?.task_id
    if (taskId) {
      runDialogType.value = 'archive'
      runScanTaskId.value = taskId
      runMergeTaskId.value = null
      showRunDialog.value = true
      ElMessage.success('已提交恢复任务')
    } else {
      ElMessage.success('恢复任务已提交')
    }
    await tasksData.loadArchiveTasks()
  } catch (e: any) {
    if (e !== 'cancel') {
      console.error('Restore archive failed:', e)
      ElMessage.error(e?.message || '恢复失败')
    }
  }
}

/**
 * 创建任务
 */
const handleCreateTask = async () => {
  await taskForm.createTask(tasksData.loadTasks)
}

// 初始化
onMounted(async () => {
  await tasksData.loadTasks()
  await tasksData.loadClusters()
  await tasksData.loadScanTasks(scanClusterFilter.value, scanStatusFilter.value)
  await tasksData.loadArchiveTasks()
  await tasksData.refreshArchiveSummaries()

  if (polling.hasRunningTasks.value) {
    polling.startPolling()
  }

  scanRefresh.setupScanAutoRefresh()
})

// 监听集群变化
watch(selectedClusterId, () => {
  tasksData.loadArchiveTasks()
})

// 监听扫描任务筛选器变化
watch([scanClusterFilter, scanStatusFilter], async () => {
  await tasksData.loadScanTasks(scanClusterFilter.value, scanStatusFilter.value)
  await tasksData.refreshArchiveSummaries()
})
</script>

<style scoped>
.tasks-management {
  padding: var(--space-3) var(--space-4) var(--space-8) var(--space-4);
  min-height: 100vh;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: visible;
  background: var(--bg-app);
}

.main-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.content-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

@media (max-width: 1280px) {
  .main-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .tasks-management {
    padding: var(--space-4);
  }
}
</style>
