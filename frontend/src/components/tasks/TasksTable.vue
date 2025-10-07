<template>
  <div class="list-scroll">
    <div class="cloudera-table">
      <div class="table-header">
        <h3>任务列表</h3>
        <div class="table-actions">
          <el-text type="info">共 {{ tasks.length }} 条</el-text>
        </div>
      </div>
      <el-table :data="tasks" stripe class="cloudera-data-table">
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
                {{
                  row.type === 'merge'
                    ? '合并'
                    : row.type === 'scan'
                    ? '扫描'
                    : row.type === 'test-table-generation'
                    ? '测试表生成'
                    : row.type
                }}
              </el-tag>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="对象" min-width="220">
          <template #default="{ row }">
            {{
              row.database_name && row.table_name
                ? `${row.database_name}.${row.table_name}`
                : '-'
            }}
          </template>
        </el-table-column>
        <el-table-column v-if="showArchiveSummary" label="归档详情" min-width="360">
          <template #default="{ row }">
            <template v-if="row.type === 'archive' && row.subtype === 'archive-table'">
              <span class="mono">moved={{ archiveSummaries[row.task_id]?.files_moved ?? '-' }}</span>
              <span class="mono" style="margin-left: 8px"
                >loc={{ shortPath(archiveSummaries[row.task_id]?.archive_location) }}</span
              >
            </template>
            <template v-else-if="row.type === 'archive' && row.subtype === 'archive-table-policy'">
              <span class="mono">ok={{ archiveSummaries[row.task_id]?.paths_success ?? '-' }}</span>
              <span class="mono" style="margin-left: 8px"
                >fail={{ archiveSummaries[row.task_id]?.paths_failed ?? '-' }}</span
              >
              <span class="mono" style="margin-left: 8px"
                >policy={{ archiveSummaries[row.task_id]?.effective ?? 'COLD' }}</span
              >
            </template>
            <template v-else-if="row.type === 'archive' && row.subtype === 'restore-table'">
              <span class="mono"
                >restored={{ archiveSummaries[row.task_id]?.files_restored ?? '-' }}</span
              >
              <span class="mono" style="margin-left: 8px"
                >loc={{ shortPath(archiveSummaries[row.task_id]?.restored_location) }}</span
              >
            </template>
            <template v-else-if="row.type === 'archive' && row.subtype === 'restore-table-policy'">
              <span class="mono">ok={{ archiveSummaries[row.task_id]?.paths_success ?? '-' }}</span>
              <span class="mono" style="margin-left: 8px"
                >fail={{ archiveSummaries[row.task_id]?.paths_failed ?? '-' }}</span
              >
              <span class="mono" style="margin-left: 8px"
                >policy={{ archiveSummaries[row.task_id]?.effective ?? 'HOT' }}</span
              >
            </template>
            <template v-else>
              <span>-</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="200">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{
              getStatusText(row.status)
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="200">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress || 0"
              :status="row.status === 'failed' ? 'exception' : undefined"
            />
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="160">
          <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
        </el-table-column>
        <el-table-column label="最近更新" width="160">
          <template #default="{ row }">{{
            formatTime(row.last_update || row.start_time)
          }}</template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button size="small" class="cloudera-btn secondary" @click="$emit('viewLogs', row)"
              >查看日志</el-button
            >
            <el-button
              v-if="row.type === 'merge' && (row.status === 'failed' || row.status === 'cancelled')"
              size="small"
              class="cloudera-btn primary"
              style="margin-left: 6px"
              @click="$emit('retry', row)"
              >重试</el-button
            >
            <el-button
              v-if="row.type === 'archive'"
              size="small"
              class="cloudera-btn primary"
              style="margin-left: 6px"
              @click="$emit('restore', row)"
              >恢复</el-button
            >
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { archiveTypeLabel, archiveTypeTag, getStatusType, getStatusText } from '@/utils/tasks/taskHelpers'
import { formatTime, shortPath } from '@/utils/tasks/taskFormatters'

defineProps<{
  tasks: any[]
  archiveSummaries: Record<string, any>
  showArchiveSummary?: boolean
}>()

defineEmits<{
  (e: 'viewLogs', row: any): void
  (e: 'retry', row: any): void
  (e: 'restore', row: any): void
}>()
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

.mono {
  font-family: Menlo, Monaco, monospace;
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

@media (max-width: 992px) {
  .cloudera-data-table :deep(.el-table__header th:nth-child(4)),
  .cloudera-data-table :deep(.el-table__body td:nth-child(4)) {
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
