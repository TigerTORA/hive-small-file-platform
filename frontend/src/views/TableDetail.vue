<template>
  <div class="table-detail">
    <div class="breadcrumb-container">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/dashboard' }">监控仪表板</el-breadcrumb-item>
        <el-breadcrumb-item :to="{ path: '/tables' }">表管理</el-breadcrumb-item>
        <el-breadcrumb-item>{{ clusterId }}.{{ database }}.{{ tableName }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div v-if="loading" class="loading-state">
      <el-card shadow="never">
        <div class="loading-container">
          <el-skeleton :rows="10" animated />
        </div>
      </el-card>
    </div>

    <template v-else-if="tableMetric">
      <div class="table-detail__layout">
        <!-- 表摘要卡片 -->
        <TableSummaryCard
          :table-qualified-name="tableQualifiedName"
          :summary-meta="summaryMeta"
          :table-type-tag="tableTypeTag"
          :storage-format-tag="storageFormatTag"
          :is-partitioned="tableMetric.is_partitioned"
          :small-files="tableMetric.small_files"
          :summary-stats="summaryStats"
          :merge-supported="mergeSupported"
          :unsupported-reason="unsupportedReason"
          :scanning="scanningTableStrict"
          @scan="handleScanTable"
          @open-merge="openMergeDialog"
        />

        <div class="table-detail__grid">
          <!-- 基础信息 -->
          <TableInfoSection
            :table-info-source="tableInfoSource"
            :table-type-tag="tableTypeTag"
            :archive-status-label="archiveStatusLabel"
            :is-archived="isArchived"
            :last-access-label="lastAccessLabel"
            :cold-data-label="coldDataLabel"
            :table-location-display="tableLocationDisplay"
            :table-location-raw="tableLocationRaw"
            :storage-format-tag="storageFormatTag"
            :compression-label="compressionLabel"
            :partition-columns-label="partitionColumnsLabel"
          />

          <!-- 分区详情表格 -->
          <PartitionMetricsTable
            v-if="tableMetric.is_partitioned"
            :loading="partitionLoading"
            :error="partitionError"
            :items="partitionItems"
            :total="partitionTotal"
            :page="partitionPage"
            :page-size="partitionPageSize"
            :concurrency="partitionConcurrency"
            @refresh="refreshPartitionMetrics"
            @size-change="handlePartitionSizeChange"
            @page-change="handlePartitionPageChange"
            @update:concurrency="partitionConcurrency = $event; loadPartitionMetrics()"
          />

          <!-- 优化建议列表 -->
          <RecommendationList
            :recommendations="recommendationList"
            :is-healthy="isTableHealthy"
          />
        </div>
      </div>
    </template>

    <div v-else class="no-data">
      <el-empty description="未找到表信息" />
    </div>

    <!-- 治理对话框 -->
    <GovernanceDialog
      v-model="showMergeDialog"
      :table-qualified-name="tableQualifiedName"
      :cluster-id="clusterId"
      :database="database"
      :table-name="tableName"
      :is-partitioned="tableMetric?.is_partitioned || false"
      :partition-options="partitionOptions"
      :creating="creating"
      @create="handleCreateMergeTask"
    />

    <TaskRunDialog
      v-model="showRunDialog"
      :type="'archive'"
      :scan-task-id="runScanTaskId || undefined"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { tasksApi, type MergeTaskCreate } from '@/api/tasks'
import { specToFilter } from '@/utils/tableHelpers'

import TaskRunDialog from '@/components/TaskRunDialog.vue'
import TableSummaryCard from '@/components/TableDetail/TableSummaryCard.vue'
import TableInfoSection from '@/components/TableDetail/TableInfoSection.vue'
import PartitionMetricsTable from '@/components/TableDetail/PartitionMetricsTable.vue'
import RecommendationList from '@/components/TableDetail/RecommendationList.vue'
import GovernanceDialog from '@/components/TableDetail/GovernanceDialog.vue'

import { useTableDetail } from '@/composables/useTableDetail'
import { useTableActions } from '@/composables/useTableActions'
import { usePartitionManagement } from '@/composables/usePartitionManagement'
import { useTableMetrics } from '@/composables/useTableMetrics'

const route = useRoute()
const router = useRouter()

const clusterId = computed(() => Number(route.params.clusterId))
const database = computed(() => String(route.params.database))
const tableName = computed(() => String(route.params.tableName))
const tableQualifiedName = computed(() => `${database.value}.${tableName.value}`)

const {
  loading,
  tableMetric,
  tableInfoExtra,
  mergeSupported,
  unsupportedReason,
  loadTableInfo
} = useTableDetail(clusterId, database, tableName)

const {
  tableInfoSource,
  storageFormatTag,
  compressionLabel,
  tableTypeTag,
  tableLocationRaw,
  tableLocationDisplay,
  partitionColumnsLabel,
  archiveStatusLabel,
  isArchived,
  lastAccessLabel,
  coldDataLabel,
  summaryMeta,
  summaryStats,
  recommendationList,
  isTableHealthy
} = useTableMetrics(tableMetric, tableInfoExtra)

const {
  scanningTableStrict,
  creating,
  scanCurrentTable,
  createMergeTask
} = useTableActions(clusterId, database, tableName, tableLocationRaw)

const {
  partitionLoading,
  partitionError,
  partitionItems,
  partitionTotal,
  partitionPage,
  partitionPageSize,
  partitionConcurrency,
  partitionOptions,
  selectedPartitions,
  loadPartitionMetrics,
  refreshPartitionMetrics,
  handlePartitionSizeChange,
  handlePartitionPageChange,
  resetPartitionSelection
} = usePartitionManagement(clusterId, database, tableName)

const showMergeDialog = ref(false)
const showRunDialog = ref(false)
const runScanTaskId = ref<string | null>(null)
const mergeScope = ref<'table' | 'partition'>('table')

const handleScanTable = () => {
  scanCurrentTable(true, () => {
    loadTableInfo({ skipLoading: true })
  })
}

const openMergeDialog = async () => {
  if (tableMetric.value?.is_partitioned && partitionOptions.value.length === 0) {
    try {
      const resp = await tasksApi.getTablePartitions(
        clusterId.value,
        database.value,
        tableName.value
      )
      partitionOptions.value = (resp?.partitions || resp || []) as string[]
    } catch (error) {
      partitionOptions.value = []
    }
  }
  mergeScope.value = tableMetric.value?.is_partitioned ? 'partition' : 'table'
  resetPartitionSelection()
  showMergeDialog.value = true
}

const handleCreateMergeTask = async (payload: {
  mergeForm: MergeTaskCreate & {
    storagePolicy?: boolean
    policy?: string
    recursive?: boolean
    runMover?: boolean
    ec?: boolean
    ecPolicy?: string
    ecRecursive?: boolean
    setReplication?: boolean
    replicationFactor?: number
    replicationRecursive?: boolean
  }
  mergeScope: 'table' | 'partition'
  selectedPartitions: string[]
}) => {
  try {
    const { taskId, additionalTasks } = await createMergeTask(
      payload.mergeForm,
      payload.mergeScope,
      payload.selectedPartitions,
      specToFilter
    )

    ElMessage.success(`治理任务已创建并启动${additionalTasks.length > 0 ? `，包含 ${additionalTasks.length + 1} 个子任务` : ''}`)
    showMergeDialog.value = false

    if (additionalTasks.length > 0) {
      runScanTaskId.value = additionalTasks[additionalTasks.length - 1]
      showRunDialog.value = true
    } else {
      router.push('/tasks')
    }
  } catch (error: any) {
    console.error('Failed to create merge task:', error)
    ElMessage.error(error?.message || '创建合并任务失败')
  }
}

onMounted(async () => {
  await loadTableInfo()
  if (tableMetric.value?.is_partitioned) {
    await loadPartitionMetrics()
  }
  if (tableMetric.value?.is_partitioned) {
    try {
      const resp = await tasksApi.getTablePartitions(
        clusterId.value,
        database.value,
        tableName.value
      )
      partitionOptions.value = (resp?.partitions || resp || []) as string[]
    } catch (error) {
      partitionOptions.value = []
    }
  }
})
</script>

<style scoped>
.table-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.table-detail .breadcrumb-container {
  margin-bottom: 8px;
}

.table-detail__layout {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.table-detail__grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 6px;
  align-items: stretch;
  grid-auto-flow: row dense;
}

@media (max-width: 1280px) {
  .table-detail__grid {
    grid-template-columns: 1fr;
  }
}

.loading-state {
  margin-bottom: 12px;
}

.loading-container {
  padding: 16px;
}

.no-data {
  padding: 24px;
  text-align: center;
}
</style>
