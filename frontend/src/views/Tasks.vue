<template>
  <div class="tasks-management">
    <!-- Cloudera风格页面头部 -->
    <div class="header-section">
      <div class="title-section">
        <h1>任务管理</h1>
        <p>统一管理与监控扫描任务、合并任务、归档任务</p>
      </div>
      <div class="actions-section">
        <el-button
          @click="loadTasks"
          :loading="loading"
          class="cloudera-btn secondary"
        >
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button
          @click="showCreateDialog = true"
          class="cloudera-btn primary"
        >
          <el-icon><Plus /></el-icon>
          创建任务
        </el-button>
      </div>
    </div>

    <!-- 主体：筛选器 + 内容 -->
    <div class="main-layout">
      <!-- 筛选器（左侧） -->
      <el-card class="filters-pane" shadow="never">
        <div class="filters-title">筛选器</div>
        <el-input v-model="globalSearch" placeholder="搜索任务名/表名/数据库" clearable size="small" class="filters-search" />
        <div class="filter-section">
          <div class="filter-header">状态</div>
          <div class="filter-list">
            <div v-for="s in statusOptions" :key="s.value" :class="['filter-item', { active: selectedStatuses.has(s.value) }]" @click="toggleStatus(s.value)">
              <span class="name">{{ s.label }}</span>
              <span class="count">{{ statusCounts[s.value] || 0 }}</span>
            </div>
          </div>
        </div>
        <div class="filter-section">
          <div class="filter-header">类型</div>
          <div class="filter-list">
            <div v-for="t in typeOptions" :key="t.value" :class="['filter-item', { active: selectedTypes.has(t.value) }]" @click="toggleType(t.value)">
              <span class="name">{{ t.label }}</span>
              <span class="count">{{ typeCounts[t.value] || 0 }}</span>
            </div>
          </div>
        </div>
        <div class="filter-section">
          <div class="filter-header">归档子类型</div>
          <div class="filter-list">
            <div v-for="t in archiveSubtypeOptions" :key="t.value" :class="['filter-item', { active: selectedArchiveSubtypes.has(t.value) }]" @click="toggleArchiveSubtype(t.value)">
              <span class="name">{{ t.label }}</span>
              <span class="count">{{ archiveSubtypeCounts[t.value] || 0 }}</span>
            </div>
          </div>
        </div>
        
        <div class="filter-actions">
          <el-button text size="small" @click="resetFilters">清除筛选</el-button>
        </div>
      </el-card>

      <!-- 内容（右侧） -->
      <div class="content-pane">
        <!-- 统一任务列表（单表）占满可用高度，在容器内部滚动 -->
        <div class="list-scroll">
        <div class="cloudera-table">
          <div class="table-header">
            <h3>任务列表</h3>
            <div class="table-actions">
              <el-text type="info">共 {{ filteredAllTasks.length }} 条</el-text>
            </div>
          </div>
          <el-table :data="filteredAllTasks" stripe class="cloudera-data-table">
            <el-table-column prop="task_name" label="任务名称" min-width="240" />
            <el-table-column label="类型" width="120">
              <template #default="{ row }">
                <template v-if="row.type === 'archive'">
                  <el-tag size="small" :type="archiveTypeTag(row.subtype)">
                    {{ archiveTypeLabel(row.subtype) }}
                  </el-tag>
                </template>
                <template v-else>
                  <el-tag size="small" type="info">{{ row.type === 'merge' ? '合并' : '扫描' }}</el-tag>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="对象" min-width="220">
              <template #default="{ row }">
                {{ row.database_name && row.table_name ? `${row.database_name}.${row.table_name}` : '-' }}
              </template>
            </el-table-column>
            <el-table-column v-if="showArchiveSummaryColumn" label="归档详情" min-width="360">
              <template #default="{ row }">
                <template v-if="row.type === 'archive' && row.subtype === 'archive-table'">
                  <span class="mono">moved={{ archiveSummaries[row.task_id]?.files_moved ?? '-' }}</span>
                  <span class="mono" style="margin-left:8px">loc={{ shortPath(archiveSummaries[row.task_id]?.archive_location) }}</span>
                </template>
                <template v-else-if="row.type === 'archive' && row.subtype === 'archive-table-policy'">
                  <span class="mono">ok={{ archiveSummaries[row.task_id]?.paths_success ?? '-' }}</span>
                  <span class="mono" style="margin-left:8px">fail={{ archiveSummaries[row.task_id]?.paths_failed ?? '-' }}</span>
                  <span class="mono" style="margin-left:8px">policy={{ archiveSummaries[row.task_id]?.effective ?? 'COLD' }}</span>
                </template>
                <template v-else-if="row.type === 'archive' && row.subtype === 'restore-table'">
                  <span class="mono">restored={{ archiveSummaries[row.task_id]?.files_restored ?? '-' }}</span>
                  <span class="mono" style="margin-left:8px">loc={{ shortPath(archiveSummaries[row.task_id]?.restored_location) }}</span>
                </template>
                <template v-else-if="row.type === 'archive' && row.subtype === 'restore-table-policy'">
                  <span class="mono">ok={{ archiveSummaries[row.task_id]?.paths_success ?? '-' }}</span>
                  <span class="mono" style="margin-left:8px">fail={{ archiveSummaries[row.task_id]?.paths_failed ?? '-' }}</span>
                  <span class="mono" style="margin-left:8px">policy={{ archiveSummaries[row.task_id]?.effective ?? 'HOT' }}</span>
                </template>
                <template v-else>
                  <span>-</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="状态" min-width="200">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusText(row.status) }}</el-tag>
                <!-- 移除行级“无新日志”提示 -->
              </template>
            </el-table-column>
            <el-table-column label="进度" width="200">
              <template #default="{ row }">
                <el-progress :percentage="row.progress || 0" :status="row.status === 'failed' ? 'exception' : undefined" />
              </template>
            </el-table-column>
            <el-table-column label="开始时间" width="160">
              <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
            </el-table-column>
            <el-table-column label="最近更新" width="160">
              <template #default="{ row }">{{ formatTime(row.last_update || row.start_time) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="320" fixed="right">
              <template #default="{ row }">
                <el-button size="small" class="cloudera-btn secondary" @click="openRunRow(row)">查看日志</el-button>
                <el-button
                  v-if="row.type === 'merge' && (row.status === 'failed' || row.status === 'cancelled')"
                  size="small"
                  class="cloudera-btn primary"
                  style="margin-left:6px"
                  @click="retryMergeRow(row)"
                >重试</el-button>
                <el-button
                  v-if="row.type === 'archive'"
                  size="small"
                  class="cloudera-btn primary"
                  style="margin-left:6px"
                  @click="restoreArchiveRow(row)"
                >恢复</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        </div>
      </div>
    </div>

    <!-- 创建任务对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="创建合并任务"
      width="600px"
    >
      <el-form
        :model="taskForm"
        :rules="taskRules"
        ref="taskFormRef"
        label-width="120px"
      >
        <el-form-item
          label="集群"
          prop="cluster_id"
        >
          <el-select
            v-model="taskForm.cluster_id"
            placeholder="选择集群"
          >
            <el-option
              v-for="cluster in clusters"
              :key="cluster.id"
              :label="cluster.name"
              :value="cluster.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          label="任务名称"
          prop="task_name"
        >
          <el-input
            v-model="taskForm.task_name"
            placeholder="请输入任务名称"
          />
        </el-form-item>
        <el-form-item
          label="数据库"
          prop="database_name"
        >
          <el-input
            v-model="taskForm.database_name"
            placeholder="请输入数据库名"
          />
        </el-form-item>
        <el-form-item
          label="表名"
          prop="table_name"
        >
          <el-input
            v-model="taskForm.table_name"
            placeholder="请输入表名"
            @blur="checkTablePartitions"
          />
        </el-form-item>

        <!-- 表信息显示 -->
        <el-form-item
          v-if="tableInfo"
          label="表信息"
        >
          <el-tag
            :type="tableInfo.is_partitioned ? 'success' : 'info'"
            size="small"
          >
            {{ tableInfo.is_partitioned ? '分区表' : '普通表' }}
          </el-tag>
          <span
            v-if="tableInfo.is_partitioned"
            style="margin-left: 8px; color: #606266"
          >
            共 {{ tableInfo.partition_count }} 个分区
          </span>
        </el-form-item>

        <!-- 分区选择 -->
        <el-form-item
          v-if="tableInfo?.is_partitioned"
          label="分区选择"
        >
          <el-button
            size="small"
            @click="loadPartitions"
            :loading="partitionsLoading"
            style="margin-bottom: 8px"
          >
            加载分区列表
          </el-button>

          <div
            v-if="partitions.length > 0"
            style="
              max-height: 200px;
              overflow-y: auto;
              border: 1px solid #dcdfe6;
              border-radius: 4px;
              padding: 8px;
            "
          >
            <el-checkbox-group v-model="selectedPartitions">
              <div
                v-for="partition in partitions"
                :key="partition.partition_spec"
              >
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
            style="margin-top: 8px"
          />
        </el-form-item>

        <!-- 非分区表的分区过滤器输入 -->
        <el-form-item
          v-else
          label="分区过滤"
        >
          <el-input
            v-model="taskForm.partition_filter"
            placeholder="如: dt='2023-12-01' (可选)"
          />
        </el-form-item>

        <el-form-item label="合并策略">
          <el-radio-group v-model="taskForm.merge_strategy">
            <el-radio label="safe_merge">安全合并 (推荐)</el-radio>
            <el-radio label="concatenate">文件合并 (CONCATENATE)</el-radio>
            <el-radio label="insert_overwrite">重写插入 (INSERT OVERWRITE)</el-radio>
          </el-radio-group>
          <div style="margin-top: 4px; font-size: 12px; color: #909399">
            安全合并使用临时表+重命名策略，确保零停机时间
          </div>
        </el-form-item>
        <el-form-item label="输出文件格式">
          <el-select
            v-model="taskForm.target_storage_format"
            placeholder="保持与原表一致"
            :disabled="disableFormatSelection"
            style="width: 220px"
            clearable
          >
            <el-option
              v-for="opt in storageFormatOptions"
              :key="opt.label"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <div style="margin-left: 12px; color: #909399; font-size: 12px">
            当前格式：{{ tableFormatLabel }}
            <span v-if="disableFormatSelection" style="margin-left: 8px">仅在安全合并且整表模式下支持修改</span>
          </div>
        </el-form-item>
        <el-form-item label="压缩算法">
          <el-select
            v-model="taskForm.target_compression"
            placeholder="保持与原表一致"
            :disabled="disableCompressionSelection"
            style="width: 220px"
          >
            <el-option
              v-for="opt in compressionOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <div style="margin-left: 12px; color: #909399; font-size: 12px">
            当前压缩：{{ tableCompressionLabel }}
            <span v-if="disableCompressionSelection" style="margin-left: 8px">仅在安全合并且整表模式下支持修改</span>
          </div>
        </el-form-item>
        <el-form-item label="目标文件大小">
          <el-input-number
            v-model="taskForm.target_file_size"
            :min="1024 * 1024"
            :step="64 * 1024 * 1024"
            placeholder="字节"
          />
          <span style="margin-left: 8px; color: #909399">字节（可选）</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button
            type="primary"
            @click="createTask"
            >创建</el-button
          >
        </div>
      </template>
    </el-dialog>

    <!-- 日志查看对话框 -->
    <el-dialog
      v-model="showLogsDialog"
      title="任务日志"
      width="800px"
    >
      <div class="logs-container">
        <div
          v-if="taskLogs.length === 0"
          class="no-logs"
        >
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
    <el-dialog
      v-model="showPreviewDialog"
      title="合并预览"
      width="700px"
    >
      <div
        v-if="previewLoading"
        style="text-align: center; padding: 20px"
      >
        <el-icon class="is-loading"><Loading /></el-icon>
        <div style="margin-top: 10px">正在生成预览...</div>
      </div>

      <div
        v-else-if="previewData"
        class="preview-container"
      >
        <div class="preview-section">
          <h3>任务信息</h3>
          <el-descriptions
            :column="2"
            border
          >
            <el-descriptions-item label="任务名称">{{
              previewData.task_name
            }}</el-descriptions-item>
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
              <el-statistic
                title="合并前文件数"
                :value="previewData.preview.estimated_files_before"
              />
            </el-col>
            <el-col :span="6">
              <el-statistic
                title="合并后文件数"
                :value="previewData.preview.estimated_files_after"
              />
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

        <div
          v-if="previewData.preview.warnings && previewData.preview.warnings.length > 0"
          class="preview-section"
        >
          <h3>注意事项</h3>
          <el-alert
            v-for="(warning, index) in previewData.preview.warnings"
            :key="index"
            :title="warning"
            type="warning"
            show-icon
            style="margin-bottom: 10px"
          />
        </div>

        <div
          v-if="previewData.preview.is_partitioned"
          class="preview-section"
        >
          <h3>分区信息</h3>
          <p>
            <el-tag type="info">分区表</el-tag>
            <span style="margin-left: 10px"
              >共 {{ previewData.preview.partitions?.length || 0 }} 个分区</span
            >
          </p>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showPreviewDialog = false">关闭</el-button>
          <el-button
            v-if="previewData && !previewLoading"
            type="primary"
            @click="executeTaskFromPreview"
          >
            确认执行
          </el-button>
        </div>
      </template>
    </el-dialog>
    <TaskRunDialog
      v-model="showRunDialog"
      :type="runDialogType"
      :scan-task-id="runScanTaskId || undefined"
      :merge-task-id="runMergeTaskId || undefined"
    />
  </div>
</template>

<script setup lang="ts">
  import { ref, onMounted, computed, watch, onBeforeUnmount } from 'vue'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { Plus, Refresh, Loading } from '@element-plus/icons-vue'
  import { tasksApi, type MergeTask, type MergeTaskCreate } from '@/api/tasks'
  import { clustersApi, type Cluster } from '@/api/clusters'
  import { scanTasksApi, type ScanTask } from '@/api/scanTasks'
  import { tablesApi } from '@/api/tables'
  import { useMonitoringStore } from '@/stores/monitoring'
  import TaskRunDialog from '@/components/TaskRunDialog.vue'
  import dayjs from 'dayjs'

  // 数据
  const taskSearchText = ref('')
  const globalSearch = ref('')
  // 归档任务（统一纳入单列表）所需状态
  const monitoringStore = useMonitoringStore()
  const selectedClusterId = computed(() => monitoringStore.settings.selectedCluster)
  const archiveTasks = ref<any[]>([])

  const tasks = ref<MergeTask[]>([])
  const scanTasks = ref<ScanTask[]>([])
  const clusters = ref<Cluster[]>([])
  const loading = ref(false)
  const loadingScan = ref(false)
  const loadingArchiveTables = ref(false)
  const loadingArchivePartitions = ref(false)
  const showCreateDialog = ref(false)
  const showLogsDialog = ref(false)
  const showPreviewDialog = ref(false)
  const showRunDialog = ref(false)
  const taskLogs = ref<any[]>([])
  const previewData = ref<any>(null)
  const previewLoading = ref(false)
  const previewingTask = ref<MergeTask | null>(null)
  const runDialogType = ref<'scan' | 'merge' | 'archive'>('scan')
  const runScanTaskId = ref<string | null>(null)
  const runMergeTaskId = ref<number | null>(null)
  // 归档任务数据（已移除界面，保留为将来扩展占位）
  // 扫描任务筛选与刷新
  const scanClusterFilter = ref<number | null>(null)
  const scanStatusFilter = ref<string>('')
  const scanAutoRefresh = ref<number>(0)
  let scanRefreshTimer: NodeJS.Timeout | null = null

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
    merge_strategy: 'safe_merge',
    target_storage_format: null,
    target_compression: 'KEEP'
  })

  const taskRules = {
    cluster_id: [{ required: true, message: '请选择集群', trigger: 'change' }],
    task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
    database_name: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
    table_name: [{ required: true, message: '请输入表名', trigger: 'blur' }]
  }

  const taskFormRef = ref()

  const storageFormatOptions = [
    { label: '保持原格式', value: null },
    { label: 'Parquet', value: 'PARQUET' },
    { label: 'ORC', value: 'ORC' },
    { label: 'TextFile', value: 'TEXTFILE' },
    { label: 'RCFile', value: 'RCFILE' },
    { label: 'Avro', value: 'AVRO' }
  ]

  const compressionOptions = [
    { label: '保持原压缩', value: 'KEEP' },
    { label: 'Snappy', value: 'SNAPPY' },
    { label: 'Gzip', value: 'GZIP' },
    { label: 'LZ4', value: 'LZ4' },
    { label: '不压缩', value: 'NONE' }
  ]

  const disableFormatSelection = computed(() => {
    const hasPartitionFilter = !!taskForm.value.partition_filter || selectedPartitions.value.length > 0
    return taskForm.value.merge_strategy !== 'safe_merge' || hasPartitionFilter
  })
  const disableCompressionSelection = computed(() => disableFormatSelection.value)

  const tableFormatLabel = computed(() => {
    if (!tableInfo.value) return '未知'
    return tableInfo.value.storage_format || '未知'
  })

  const tableCompressionLabel = computed(() => {
    if (!tableInfo.value) return '默认'
    const raw = (tableInfo.value.current_compression || '').toUpperCase()
    if (!raw || raw === 'DEFAULT') return '默认'
    return raw
  })

  watch(
    () => monitoringStore.settings.selectedCluster,
    clusterId => {
      taskForm.value.cluster_id = clusterId || 0
    }
  )

  watch(
    () => taskForm.value.merge_strategy,
    strategy => {
      if (strategy !== 'safe_merge') {
        taskForm.value.target_storage_format = null
        taskForm.value.target_compression = 'KEEP'
      }
    }
  )

  watch(
    () => [taskForm.value.partition_filter, selectedPartitions.value.length],
    () => {
      if (disableFormatSelection.value) {
        taskForm.value.target_storage_format = null
        taskForm.value.target_compression = 'KEEP'
      }
    }
  )

  // 计算属性
  // 统计卡片已移除，这些总计已不再使用

  // 统一筛选器
  const statusOptions = [
    { label: '失败', value: 'failed' },
    { label: '已成功', value: 'success' },
    { label: '正在执行', value: 'running' },
    { label: '已取消', value: 'cancelled' },
    { label: '排队中', value: 'pending' }
  ]
  const typeOptions = [
    { label: '合并任务', value: 'merge' },
    { label: '扫描任务', value: 'scan' },
    { label: '归档任务', value: 'archive' }
  ]
  const selectedStatuses = ref<Set<string>>(new Set())
  const selectedTypes = ref<Set<string>>(new Set())
  const toggleStatus = (s: string) => { const set = selectedStatuses.value; set.has(s) ? set.delete(s) : set.add(s) }
  const toggleType = (t: string) => { const set = selectedTypes.value; set.has(t) ? set.delete(t) : set.add(t) }
  const resetFilters = () => { selectedStatuses.value.clear(); selectedTypes.value.clear(); globalSearch.value = ''; taskSearchText.value = '' }

  // 归档子类型筛选（仅对归档类scan任务生效）
  const archiveSubtypeOptions = [
    { label: '表归档', value: 'archive-table' },
    { label: '表恢复', value: 'restore-table' },
    { label: '策略归档', value: 'archive-table-policy' },
    { label: '策略恢复', value: 'restore-table-policy' },
  ]
  const selectedArchiveSubtypes = ref<Set<string>>(new Set())
  const toggleArchiveSubtype = (v: string) => { const set = selectedArchiveSubtypes.value; set.has(v) ? set.delete(v) : set.add(v) }

  const normalizeStatus = (s: string) => (s === 'completed' ? 'success' : s)
  const statusCounts = computed<Record<string, number>>(() => {
    const map: Record<string, number> = {}
    for (const r of tasks.value) { const s = normalizeStatus(r.status); map[s] = (map[s] || 0) + 1 }
    for (const r of scanTasks.value) { const s = normalizeStatus(r.status); map[s] = (map[s] || 0) + 1 }
    for (const r of archiveTasks.value) { const s = 'success'; map[s] = (map[s] || 0) + 1 }
    return map
  })
  const typeCounts = computed<Record<string, number>>(() => ({
    merge: tasks.value.length,
    scan: scanTasks.value.length,
    archive: archiveTasks.value.length
  }))

  const archiveSubtypeCounts = computed<Record<string, number>>(() => {
    const m: Record<string, number> = {}
    for (const r of scanTasks.value) {
      const sub = String((r as any).task_type)
      if (sub.startsWith('archive') || sub.startsWith('restore')) m[sub] = (m[sub] || 0) + 1
    }
    return m
  })

  const matchSearch = (text: string) => {
    const q = (globalSearch.value || taskSearchText.value || '').trim().toLowerCase()
    if (!q) return true
    return (text || '').toLowerCase().includes(q)
  }

  const filteredTasks = computed(() => {
    if (selectedTypes.value.size && !selectedTypes.value.has('merge')) return []
    return tasks.value.filter(task => {
      const s = normalizeStatus(task.status)
      if (selectedStatuses.value.size && !selectedStatuses.value.has(s)) return false
      const text = `${task.task_name} ${task.database_name}.${task.table_name}`
      return matchSearch(text)
    })
  })

  // 统计卡片：根据筛选器后结果统计
  // 统计卡片已移除：相关按筛选的统计也不再需要

  const filteredScanTasks = computed(() => {
    if (selectedTypes.value.size && !selectedTypes.value.has('scan')) return []
    return scanTasks.value.filter(task => {
      const s = normalizeStatus(task.status)
      if (selectedStatuses.value.size && !selectedStatuses.value.has(s)) return false
      // 归档子类型筛选
      const tt = String((task as any).task_type || '')
      if (tt.startsWith('archive')) {
        if (selectedArchiveSubtypes.value.size && !selectedArchiveSubtypes.value.has(tt)) return false
      } else {
        // 如果选择了归档子类型，非归档scan任务应被排除
        if (selectedArchiveSubtypes.value.size) return false
      }
      const text = `${task.task_name || ''}`
      return matchSearch(text)
    })
  })

  // 单列表数据：统一合并/扫描任务
  const filteredAllTasks = computed(() => {
    const mergeRows = filteredTasks.value.map(row => ({
      type: 'merge',
      raw: row,
      task_name: row.task_name,
      database_name: row.database_name,
      table_name: row.table_name,
      status: row.status,
      progress: getTaskProgress(row),
      start_time: row.created_time,
      last_update: (row as any).updated_time || row.created_time
    }))
    const scanRows = filteredScanTasks.value.map(r => ({
      type: (r as any).task_type && (String((r as any).task_type).startsWith('archive') || String((r as any).task_type).startsWith('restore')) ? 'archive' : 'scan',
      raw: r,
      task_name: r.task_name || '扫描任务',
      database_name: null as any,
      table_name: null as any,
      status: normalizeStatus(r.status),
      progress: r.progress_percentage || 0,
      start_time: r.start_time,
      last_update: (r as any).last_update || r.end_time || r.start_time,
      task_id: r.task_id,
      subtype: (r as any).task_type
    }))
    const archiveRows = (selectedTypes.value.size && !selectedTypes.value.has('archive'))
      ? []
      : archiveTasks.value.map(r => ({
          type: 'archive',
          raw: r,
          task_name: r.task_name || `归档 ${r.database_name}.${r.table_name}`,
          database_name: r.database_name,
          table_name: r.table_name,
          status: 'success',
          progress: 100,
          start_time: r.archived_at,
          last_update: r.archived_at
        }))
    return [...mergeRows, ...scanRows, ...archiveRows].sort((a,b) => new Date(b.last_update || b.start_time).getTime() - new Date(a.last_update || a.start_time).getTime())
  })

  const openRunRow = (row: any) => {
    if (row.type === 'scan') {
      runDialogType.value = 'scan'
      runScanTaskId.value = row.task_id || row.raw?.task_id
      runMergeTaskId.value = null
      showRunDialog.value = true
    } else if (row.type === 'merge') {
      runDialogType.value = 'merge'
      runMergeTaskId.value = row.raw?.id
      runScanTaskId.value = null
      showRunDialog.value = true
    } else if (row.type === 'archive') {
      runDialogType.value = 'archive'
      runScanTaskId.value = row.task_id || row.raw?.task_id || null
      runMergeTaskId.value = null
      showRunDialog.value = true
    }
  }

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
      const cid = scanClusterFilter.value || undefined
      const status = scanStatusFilter.value || undefined
      scanTasks.value = await scanTasksApi.list(cid as any, status)
      // 仅为归档与恢复任务异步加载概要
      await refreshArchiveSummaries()
    } catch (error) {
      console.error('Failed to load scan tasks:', error)
    } finally {
      loadingScan.value = false
    }
  }

  // 加载归档任务（基于已归档表列表示例映射）
  const loadArchiveTasks = async () => {
    try {
      archiveTasks.value = []
      const cid = selectedClusterId.value
      if (!cid) return
      const res: any = await tablesApi.getArchivedTables(cid, 200)
      const list = res?.archived_tables || res?.items || []
      archiveTasks.value = list.map((t: any) => ({
        cluster_id: cid,
        database_name: t.database_name,
        table_name: t.table_name,
        archived_at: t.archived_at,
        archive_location: t.archive_location,
        task_name: `归档 ${t.database_name}.${t.table_name}`
      }))
    } catch (e) {
      console.error('Failed to load archive tasks:', e)
    }
  }

  const loadClusters = async () => {
    try {
      clusters.value = await clustersApi.list()
    } catch (error) {
      console.error('Failed to load clusters:', error)
    }
  }

  // 归档相关功能已从该界面移除

  const createTask = async () => {
    try {
      await taskFormRef.value.validate()

      // 准备任务数据
      const taskData = { ...taskForm.value }

      if (!taskData.target_storage_format) {
        delete taskData.target_storage_format
      } else {
        taskData.target_storage_format = taskData.target_storage_format.toUpperCase() as MergeTaskCreate['target_storage_format']
      }
      if (taskData.target_compression) {
        taskData.target_compression = taskData.target_compression.toUpperCase() as MergeTaskCreate['target_compression']
      }

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

  const retryMergeRow = async (row: any) => {
    try {
      const id = row.raw?.id || row.id
      if (!id) return
      await tasksApi.retry(id)
      ElMessage.success('已触发重试')
      // 打开执行详情并开始轮询
      runDialogType.value = 'merge'
      runMergeTaskId.value = id
      runScanTaskId.value = null
      showRunDialog.value = true
      await loadTasks()
    } catch (e: any) {
      console.error('Retry failed', e)
      ElMessage.error(e?.message || '重试失败')
    }
  }

  const cancelTask = async (task: MergeTask) => {
    try {
      await ElMessageBox.confirm(`确定要取消任务 "${task.task_name}" 吗？`, '确认取消', {
        confirmButtonText: '取消任务',
        cancelButtonText: '不取消',
        type: 'warning'
      })

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
    runDialogType.value = 'merge'
    runMergeTaskId.value = task.id
    runScanTaskId.value = null
    showRunDialog.value = true
  }

  const openScanLogs = (taskId: string) => {
    runDialogType.value = 'scan'
    runScanTaskId.value = taskId
    runMergeTaskId.value = null
    showRunDialog.value = true
  }

  const restoreArchiveRow = async (row: any) => {
    try {
      const cid = selectedClusterId.value
      if (!cid) {
        ElMessage.warning('请先选择集群')
        return
      }
      await ElMessageBox.confirm(`确定要恢复 ${row.database_name}.${row.table_name} 吗？`, '确认恢复', {
        confirmButtonText: '恢复（后台任务）',
        cancelButtonText: '取消',
        type: 'warning'
      })
      const resp = await tablesApi.restoreTableWithProgress(cid as number, row.database_name, row.table_name)
      const taskId = (resp as any)?.task_id
      if (taskId) {
        // 打开归档任务运行对话框
        runDialogType.value = 'archive'
        runScanTaskId.value = taskId
        runMergeTaskId.value = null
        showRunDialog.value = true
        ElMessage.success('已提交恢复任务')
      } else {
        ElMessage.success('恢复任务已提交')
      }
      await loadArchiveTasks()
    } catch (e: any) {
      if (e !== 'cancel') {
        console.error('Restore archive failed:', e)
        ElMessage.error(e?.message || '恢复失败')
      }
    }
  }

  const resetTaskForm = () => {
    taskForm.value = {
      cluster_id: selectedClusterId.value || 0,
      task_name: '',
      table_name: '',
      database_name: '',
      partition_filter: '',
      merge_strategy: 'safe_merge',
      target_storage_format: null,
      target_compression: 'KEEP'
    }
    // 清空分区相关数据
    tableInfo.value = null
    partitions.value = []
    selectedPartitions.value = []
  }

  const getStatusType = (status: string): string => {
    const statusMap: Record<string, string> = {
      pending: 'info',
      running: 'warning',
      success: 'success',
      failed: 'danger'
    }
    return statusMap[status] || 'info'
  }

  const getStatusText = (status: string): string => {
    const statusMap: Record<string, string> = {
      pending: '排队中',
      running: '正在执行',
      success: '已成功',
      failed: '失败',
      cancelled: '已取消'
    }
    return statusMap[status] || status
  }

  // 行停滞检测：根据 last_update 或 start_time 估算“无新日志”时长
  const nowTs = ref(Date.now())
  setInterval(() => { nowTs.value = Date.now() }, 60_000)
  const staleSeconds = (row: any): number => {
    const base = row.last_update || row.start_time
    if (!base) return 0
    const t = new Date(base).getTime() || 0
    if (!t) return 0
    return Math.max(0, Math.floor((nowTs.value - t) / 1000))
  }
  const humanizeDuration = (sec: number): string => {
    const m = Math.floor(sec / 60)
    const s = sec % 60
    if (m <= 0) return `${s}s`
    return `${m}m${s.toString().padStart(2, '0')}s`
  }

  // 归档/恢复任务：行高亮与概要
  const archiveTypeLabel = (sub: string) => {
    if (sub === 'archive-table') return '表归档'
    if (sub === 'restore-table') return '表恢复'
    if (sub === 'archive-table-policy') return '策略归档'
    if (sub === 'restore-table-policy') return '策略恢复'
    if (sub && sub.startsWith('archive')) return '归档'
    return '扫描'
  }
  const archiveTypeTag = (sub: string) => {
    if (sub === 'archive-table') return 'warning'
    if (sub === 'restore-table') return 'success'
    if (sub === 'archive-table-policy') return 'primary'
    if (sub === 'restore-table-policy') return 'success'
    return 'info'
  }
  const showArchiveSummaryColumn = true
  const archiveSummaries = ref<Record<string, any>>({})
  const shortPath = (p?: string) => {
    if (!p) return '-'
    if (p.length <= 36) return p
    const parts = p.split('/')
    if (parts.length > 4) return `${parts.slice(0,3).join('/')}/…/${parts.slice(-2).join('/')}`
    return p.slice(0, 16) + '…' + p.slice(-12)
  }
  const parseStructured = (msg: string): { code?: string; ctx?: Record<string,string> } => {
    // 形如: "[ARCHIVE] A150 数据移动完成 files_moved=10 archive_location=/..."
    const m = msg.match(/\]\s*(\w+)\s+/)
    const code = m ? m[1] : undefined
    const ctx: Record<string, string> = {}
    const kvRe = /(\w+)=([^\s]+)/g
    let mm
    while ((mm = kvRe.exec(msg)) !== null) {
      ctx[mm[1]] = mm[2]
    }
    return { code, ctx }
  }
  const refreshArchiveSummaries = async () => {
    // 挑选 archive/restore 表任务
    const candidates = (scanTasks.value || []).filter((t: any) => ['archive-table', 'restore-table', 'archive-table-policy', 'restore-table-policy'].includes(String(t.task_type)))
    for (const t of candidates) {
      const tid = t.task_id
      if (!tid) continue
      // 若已缓存且任务已完成，不再重复加载
      if (archiveSummaries.value[tid] && (t.status === 'completed' || t.status === 'failed')) continue
      try {
        const logs = await scanTasksApi.getLogs(tid)
        const acc: any = {}
        for (const l of logs || []) {
          const { code, ctx } = parseStructured(String(l.message || ''))
          if (!code || !ctx) continue
          if (code === 'A150') {
            if (ctx.files_moved) acc.files_moved = Number(ctx.files_moved)
            if (ctx.archive_location) acc.archive_location = ctx.archive_location
          }
          if (code === 'PL120') {
            if (ctx.paths_success) acc.paths_success = Number(ctx.paths_success)
            if (ctx.paths_failed) acc.paths_failed = Number(ctx.paths_failed)
            if (ctx.effective) acc.effective = ctx.effective
          }
          if (code === 'AR190') {
            if (ctx.files_restored) acc.files_restored = Number(ctx.files_restored)
            if (ctx.restored_location) acc.restored_location = ctx.restored_location
          }
        }
        if (Object.keys(acc).length) {
          archiveSummaries.value[tid] = { ...(archiveSummaries.value[tid] || {}), ...acc }
        }
      } catch (e) {
        // 忽略日志加载失败
      }
    }
  }

  const formatTime = (time: string): string => {
    return dayjs(time).format('MM-DD HH:mm:ss')
  }

  // 归档操作
  // 归档恢复操作已移除

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

  const copyId = async (id: string) => {
    try {
      await navigator.clipboard.writeText(id)
    } catch {}
    ElMessage.success('任务ID已复制')
  }

  const shortId = (id: string) => {
    if (!id) return '-'
    return id.slice(0, 10) + '…' + id.slice(-6)
  }

  const getStrategyName = (strategy: string): string => {
    const strategyMap: Record<string, string> = {
      safe_merge: '安全合并',
      concatenate: '文件合并',
      insert_overwrite: '重写插入'
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
        initialization: '初始化中',
        connection_test: '连接测试',
        pre_validation: '预验证',
        file_analysis: '文件分析',
        temp_table_creation: '创建临时表',
        data_validation: '数据验证',
        atomic_swap: '原子切换',
        post_validation: '后验证',
        cleanup: '清理中',
        completion: '完成中'
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
        initialization: 5,
        connection_test: 10,
        pre_validation: 15,
        file_analysis: 25,
        temp_table_creation: 45,
        data_validation: 65,
        atomic_swap: 80,
        post_validation: 90,
        cleanup: 95,
        completion: 98
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
    hasRunning => {
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
    loadArchiveTasks()

    // 如果有运行中的任务，启动轮询
    if (hasRunningTasks.value) {
      startPolling()
    }
    setupScanAutoRefresh()
  })

  watch(selectedClusterId, () => {
    loadArchiveTasks()
  })

  // 组件卸载时清理轮询
  onBeforeUnmount(() => {
    stopPolling()
    if (scanRefreshTimer) {
      clearInterval(scanRefreshTimer)
      scanRefreshTimer = null
    }
  })

  const setupScanAutoRefresh = () => {
    if (scanRefreshTimer) {
      clearInterval(scanRefreshTimer)
      scanRefreshTimer = null
    }
    if (scanAutoRefresh.value > 0) {
      scanRefreshTimer = setInterval(() => {
        loadScanTasks()
      }, scanAutoRefresh.value * 1000)
    }
  }

  watch(scanAutoRefresh, setupScanAutoRefresh)

  // 归档相关已移除
  watch([scanClusterFilter, scanStatusFilter], () => loadScanTasks())
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

  .header-section {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--space-8);
    padding: var(--space-6);
    background: var(--bg-primary);
    border-radius: var(--radius-xl);
    border: 1px solid var(--gray-200);
    box-shadow: var(--elevation-1);
  }

  .title-section h1 {
    margin: 0 0 var(--space-2) 0;
    font-size: var(--text-3xl);
    font-weight: var(--font-bold);
    color: var(--gray-900);
  }

  .title-section p {
    margin: 0;
    color: var(--gray-600);
    font-size: var(--text-lg);
  }

  .actions-section {
    display: flex;
    gap: var(--space-4);
    align-items: center;
  }

  /* 主布局与筛选器 */
  .main-layout {
    display: grid; grid-template-columns: 260px 1fr; gap: 16px;
    flex: 1 1 auto; min-height: 0; overflow: hidden;
  }
  .content-pane { min-width: 0; display: flex; flex-direction: column; min-height: 0; }
  .list-scroll { flex: 1 1 auto; min-height: 0; overflow: auto; }
  /* 筛选保持 sticky，跟随 page-content 内滚动 */
  .filters-pane { position: sticky; top: var(--space-2); align-self: start; max-height: calc(100vh - 96px); overflow: auto; }
  .filters-title { font-weight: 600; color: var(--gray-900); margin-bottom: 8px; }
  .filters-search { margin-bottom: 8px; }
  .filter-section { margin-top: 12px; }
  .filter-header { font-size: 13px; color: #606266; margin-bottom: 6px; }
  .filter-list { display: flex; flex-direction: column; border: 1px solid #ebeef5; border-radius: 6px; }
  .filter-item { display: flex; justify-content: space-between; padding: 6px 10px; cursor: pointer; }
  .filter-item:hover { background: #f5f7fa; }
  .filter-item.active { background: #ecf5ff; }
  .filter-item .name { color: #303133; }
  .filter-item .count { color: #909399; }
  .filter-actions { margin-top: 12px; text-align: right; }

  /* Cloudera风格标签页 */
  .cloudera-tabs {
    background: var(--bg-primary);
    border-radius: var(--radius-xl);
    border: 1px solid var(--gray-200);
    box-shadow: var(--elevation-1);
    overflow: hidden;
  }

  /* 防止表格在小屏横向撑爆，允许内部区域滚动 */
  .cloudera-data-table { width: 100%; }
  .cloudera-data-table :deep(.el-table__header-wrapper),
  .cloudera-data-table :deep(.el-table__body-wrapper) { overflow-x: auto; }
  /* 表头吸顶（相对于 .list-scroll） */
  .cloudera-data-table :deep(.el-table__header-wrapper) {
    position: sticky;
    top: 0;
    z-index: 5;
    background: var(--bg-primary);
    box-shadow: 0 1px 0 var(--gray-200);
  }

  @media (max-width: 1280px) {
    .main-layout {
      grid-template-columns: 1fr;
    }

    .filters-pane {
      position: static;
      order: -1;
    }
  }

  /* 更小屏幕时隐藏次要列，提升自适应性 */
  @media (max-width: 992px) {
    .cloudera-data-table :deep(.el-table__header th:nth-child(4)),
    .cloudera-data-table :deep(.el-table__body td:nth-child(4)) { /* 归档详情/对象等较宽列按需裁剪 */
      display: none;
    }
  }

  .tab-nav {
    display: flex;
    background: var(--gray-50);
    border-bottom: 1px solid var(--gray-200);
  }

  .tab-item {
    flex: 1;
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-4) var(--space-6);
    cursor: pointer;
    transition: all var(--transition-fast);
    font-weight: var(--font-medium);
    color: var(--gray-600);
    border-right: 1px solid var(--gray-200);
  }

  .tab-item:last-child {
    border-right: none;
  }

  .tab-item:hover {
    background: var(--gray-100);
    color: var(--gray-900);
  }

  .tab-item.active {
    background: var(--primary-50);
    color: var(--primary-600);
    border-bottom: 3px solid var(--primary-500);
  }

  .tab-content {
    padding: var(--space-6);
  }

  .tab-pane {
    animation: fadeIn 0.3s ease-in-out;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  /* 表格样式调整 */
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

  .search-input {
    min-width: 250px;
  }

  /* 依次出现动画 */
  /* 统计卡片相关动画已移除 */

  .mono {
    font-family: Menlo, Monaco, monospace;
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

    /* 统计卡片已移除 */
  }

  @media (max-width: 768px) {
    .tasks-management {
      padding: var(--space-4);
    }

    .header-section {
      flex-direction: column;
      gap: var(--space-4);
      text-align: center;
    }

    /* 统计卡片已移除 */

    .tab-nav {
      flex-direction: column;
    }

    .tab-item {
      border-right: none;
      border-bottom: 1px solid var(--gray-200);
    }

    .tab-item:last-child {
      border-bottom: none;
    }

    .table-header {
      flex-direction: column;
      gap: var(--space-3);
      align-items: stretch;
    }

    .search-input {
      min-width: auto;
    }
  }
</style>
