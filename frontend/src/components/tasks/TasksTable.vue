<template>
  <div class="list-scroll">
    <div class="cloudera-table">
      <div class="table-header">
        <h3>任务列表</h3>
        <div class="table-actions">
          <el-text type="info">共 {{ tasks.length }} 条</el-text>
        </div>
      </div>
      <el-table :data="tasks" stripe class="cloudera-data-table" row-key="id">
        <el-table-column prop="task_name" label="任务名称" min-width="240" />
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <template v-if="row.type === 'archive'">
              <el-tag size="small" :type="archiveTypeTag(row.subtype)">
                {{ archiveTypeLabel(row.subtype) }}
              </el-tag>
            </template>
            <template v-else>
              <el-tag size="small" type="info">
                {{ typeLabel(row.type) }}
              </el-tag>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="集群" width="160">
          <template #default="{ row }">
            {{ row.cluster_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="对象" min-width="220">
          <template #default="{ row }">
            <span v-if="row.database_name && row.table_name">
              {{ row.database_name }}.{{ row.table_name }}
            </span>
            <span v-else-if="row.database_name">
              {{ row.database_name }}
            </span>
            <span v-else-if="row.table_name">
              {{ row.table_name }}
            </span>
            <span v-else>
              -
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="140">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="文件变化" min-width="210">
          <template #default="{ row }">
            <div v-if="row.type === 'merge' && hasFileStats(row)" class="file-change">
              <span class="before">{{ formatCount(row.files_before) }}</span>
              <span class="arrow">→</span>
              <span class="after">{{ formatCount(row.files_after) }}</span>
              <span v-if="fileDelta(row) !== null" :class="['delta', deltaClass(row)]">
                {{ formatDelta(row) }}
              </span>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="节省存储" width="140">
          <template #default="{ row }">
            <span v-if="row.type === 'merge' && row.size_saved !== null && row.size_saved !== undefined">
              {{ formatSizeSaved(row.size_saved) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="200">
          <template #default="{ row }">
            <template v-if="row.status === 'running'">
              <el-progress
                :percentage="row.progress || 0"
                :status="row.status === 'failed' ? 'exception' : undefined"
              />
            </template>
            <template v-else>
              <span>{{ row.status === 'success' ? '完成' : '-' }}</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="160">
          <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
        </el-table-column>
        <el-table-column label="最近更新" width="160">
          <template #default="{ row }">{{ formatTime(row.last_update || row.start_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" class="cloudera-btn secondary" @click="$emit('viewLogs', row)">
              查看日志
            </el-button>
            <el-button
              v-if="row.type === 'merge' && (row.status === 'failed' || row.status === 'cancelled')"
              size="small"
              class="cloudera-btn primary"
              style="margin-left: 6px"
              @click="$emit('retry', row)"
            >
              重试
            </el-button>
            <el-button
              v-if="row.type === 'archive' && row.subtype === 'archive-table'"
              size="small"
              class="cloudera-btn primary"
              style="margin-left: 6px"
              @click="$emit('restore', row)"
            >
              恢复
            </el-button>
            <el-tooltip
              v-if="showArchiveSummary && row.type === 'archive' && row.task_id && archiveSummaries[row.task_id]"
              placement="top"
            >
              <template #content>
                <div class="summary-popover">
                  <p v-for="(value, key) in archiveSummaries[row.task_id]" :key="key">
                    <strong>{{ key }}</strong>: {{ value }}
                  </p>
                </div>
              </template>
              <el-button text size="small" style="margin-left: 6px">详情</el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { archiveTypeLabel, archiveTypeTag, getStatusType, getStatusText } from '@/utils/tasks/taskHelpers'
import { formatTime, formatBytes } from '@/utils/tasks/taskFormatters'

const props = defineProps<{
  tasks: any[]
  archiveSummaries: Record<string, any>
  showArchiveSummary?: boolean
}>()

defineEmits<{
  (e: 'viewLogs', row: any): void
  (e: 'retry', row: any): void
  (e: 'restore', row: any): void
}>()

const typeLabel = (type: string) => {
  const map: Record<string, string> = {
    merge: '合并',
    scan: '扫描',
    archive: '归档',
    'test-table-generation': '测试表生成'
  }
  return map[type] || type
}

const hasFileStats = (row: any): boolean => row.files_before !== null && row.files_before !== undefined
  && row.files_after !== null && row.files_after !== undefined

const formatCount = (value: number | null | undefined): string => {
  if (value === null || value === undefined) {
    return '-'
  }
  return Number(value).toLocaleString()
}

const fileDelta = (row: any): number | null => {
  if (!hasFileStats(row)) return null
  return (row.files_before as number) - (row.files_after as number)
}

const deltaClass = (row: any): string => {
  const delta = fileDelta(row)
  if (delta === null || delta === 0) return ''
  return delta > 0 ? 'delta-positive' : 'delta-negative'
}

const formatDelta = (row: any): string => {
  const delta = fileDelta(row)
  if (delta === null || delta === 0) return '(0)'
  const sign = delta > 0 ? '-' : '+'
  return `(${sign}${Math.abs(delta).toLocaleString()})`
}

const formatSizeSaved = (value: number): string => {
  if (!Number.isFinite(value) || value <= 0) {
    return '0 B'
  }
  return formatBytes(value)
}
</script>

<style scoped>
.list-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--primary-500);
}

.table-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
}

.table-actions {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.summary-popover {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cloudera-data-table {
  width: 100%;
}

.cloudera-data-table :deep(.el-table__header-wrapper),
.cloudera-data-table :deep(.el-table__body-wrapper) {
  overflow-x: auto;
}

.cloudera-data-table :deep(.el-table__header-wrapper) {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--bg-primary);
  box-shadow: 0 1px 0 var(--gray-200);
}

.file-change {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-variant-numeric: tabular-nums;
}

.file-change .arrow {
  color: var(--gray-500);
}

.file-change .delta {
  margin-left: 4px;
  font-size: 12px;
}

.file-change .delta-positive {
  color: var(--green-600);
}

.file-change .delta-negative {
  color: var(--red-500);
}

@media (max-width: 992px) {
  .cloudera-data-table :deep(.el-table__header th:nth-child(4)),
  .cloudera-data-table :deep(.el-table__body td:nth-child(4)),
  .cloudera-data-table :deep(.el-table__header th:nth-child(6)),
  .cloudera-data-table :deep(.el-table__body td:nth-child(6)),
  .cloudera-data-table :deep(.el-table__header th:nth-child(7)),
  .cloudera-data-table :deep(.el-table__body td:nth-child(7)) {
    display: none;
  }
}

@media (max-width: 768px) {
  .table-header {
    flex-direction: column;
    gap: var(--space-3);
    align-items: stretch;
  }
}
</style>
