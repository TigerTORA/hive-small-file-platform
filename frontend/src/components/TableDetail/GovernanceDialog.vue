<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="数据治理"
    width="900px"
    class="governance-dialog"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <template #header>
      <div class="dialog-header">
        <div class="dialog-header__icon">
          <el-icon><Operation /></el-icon>
        </div>
        <div class="dialog-header__content">
          <h3 class="dialog-header__title">数据治理</h3>
          <p class="dialog-header__subtitle">{{ tableQualifiedName }} - 统一治理配置</p>
        </div>
      </div>
    </template>

    <div class="governance-form-container">
      <el-form
        :model="mergeForm"
        :rules="mergeRules"
        ref="mergeFormRef"
        label-width="130px"
        class="governance-form"
      >
        <div class="form-section">
          <div class="form-section__header">
            <el-icon class="form-section__icon"><Setting /></el-icon>
            <h4 class="form-section__title">基础配置</h4>
          </div>
          <div class="form-section__content">
            <el-form-item label="任务名称" prop="task_name">
              <el-input
                v-model="mergeForm.task_name"
                placeholder="自动生成任务名称"
                :prefix-icon="Edit"
              />
            </el-form-item>
            <template v-if="isPartitioned">
              <el-form-item label="合并范围">
                <el-radio-group v-model="mergeScope" class="scope-radio-group">
                  <el-radio label="table" class="scope-radio">
                    <div class="radio-option">
                      <el-icon><CollectionTag /></el-icon>
                      <span>整表</span>
                    </div>
                  </el-radio>
                  <el-radio label="partition" class="scope-radio">
                    <div class="radio-option">
                      <el-icon><Grid /></el-icon>
                      <span>指定分区</span>
                    </div>
                  </el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="分区选择" v-if="mergeScope === 'partition'">
                <PartitionSelector
                  v-model="selectedPartitions"
                  v-model:select-mode="partitionSelectMode"
                  v-model:range-mode="timeRangeMode"
                  v-model:recent-days="recentDays"
                  v-model:date-range="dateRange"
                  v-model:exclude-weekends="excludeWeekends"
                  v-model:partition-pattern="partitionPattern"
                  v-model:search-text="partitionSearchText"
                  :predicted-recent-count="predictedRecentCount"
                  :predicted-range-count="predictedRangeCount"
                  :predicted-pattern-count="predictedPatternCount"
                  :filtered-count="filteredPartitions.length"
                  :paginated-partitions="paginatedPartitions"
                  :has-more="hasMorePartitions"
                  :remaining="remainingPartitions"
                  :total-count="partitionOptions.length"
                  @mode-change="onPartitionModeChange"
                  @time-range-mode-change="onTimeRangeModeChange"
                  @recent-days-change="onRecentDaysChange"
                  @select-recent="selectRecentPartitions"
                  @date-range-change="onDateRangeChange"
                  @select-date-range="selectDateRangePartitions"
                  @pattern-change="onPatternChange"
                  @select-pattern="selectPatternPartitions"
                  @preview-pattern="previewPattern"
                  @partition-search="onPartitionSearch"
                  @select-all-filtered="selectAllFiltered"
                  @clear-selection="clearSelectedPartitions"
                  @load-more="loadMorePartitions"
                  @show-details="showSelectedDetails"
                />
              </el-form-item>
            </template>
            <el-form-item label="目标文件大小">
              <el-input-number
                v-model="mergeForm.target_file_size"
                :min="1024 * 1024"
                :step="64 * 1024 * 1024"
                placeholder="字节"
                style="width: 200px"
              />
              <span class="form-hint-inline">字节（可选，建议 64MB-256MB）</span>
            </el-form-item>
          </div>
        </div>

        <div class="form-section">
          <div class="form-section__header">
            <el-icon class="form-section__icon"><DataAnalysis /></el-icon>
            <h4 class="form-section__title">格式优化</h4>
            <span class="form-section__badge">可选</span>
          </div>
          <div class="form-section__content">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="存储格式">
                  <el-select
                    v-model="mergeForm.target_storage_format"
                    placeholder="保持原格式"
                    style="width: 100%"
                    clearable
                  >
                    <el-option label="ORC" value="ORC" />
                    <el-option label="PARQUET" value="PARQUET" />
                    <el-option label="TEXTFILE" value="TEXTFILE" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="压缩格式">
                  <el-select
                    v-model="mergeForm.target_compression"
                    style="width: 100%"
                  >
                    <el-option label="保持原样" value="KEEP" />
                    <el-option label="GZIP" value="GZIP" />
                    <el-option label="SNAPPY" value="SNAPPY" />
                    <el-option label="LZ4" value="LZ4" />
                    <el-option label="ZSTD" value="ZSTD" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
          </div>
        </div>
      </el-form>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <div class="footer-info">
          <el-icon><InfoFilled /></el-icon>
          <span>治理任务将在后台执行，可在任务管理中查看进度</span>
        </div>
        <div class="footer-actions">
          <el-button @click="$emit('update:modelValue', false)" size="large">
            <el-icon><Close /></el-icon>
            取消
          </el-button>
          <el-button
            type="primary"
            @click="handleCreate"
            :loading="creating"
            :disabled="mergeScope === 'partition' && selectedPartitions.length === 0"
            size="large"
          >
            <el-icon v-if="!creating"><Check /></el-icon>
            <span>{{ creating ? '正在创建...' : '创建并执行' }}</span>
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Operation, Setting, Edit, CollectionTag, Grid, DataAnalysis, InfoFilled, Close, Check } from '@element-plus/icons-vue'
import type { MergeTaskCreate } from '@/api/tasks'
import PartitionSelector from './PartitionSelector.vue'
import { usePartitionManagement } from '@/composables/usePartitionManagement'

interface Props {
  modelValue: boolean
  tableQualifiedName: string
  clusterId: number
  database: string
  tableName: string
  isPartitioned: boolean
  partitionOptions: string[]
  creating: boolean
}

const props = defineProps<Props>()
const emit = defineEmits(['update:modelValue', 'create'])

const mergeFormRef = ref()
const mergeScope = ref<'table' | 'partition'>('table')

const mergeForm = ref<MergeTaskCreate & {
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
}>({
  cluster_id: props.clusterId,
  task_name: `merge_${props.database}_${props.tableName}_${Date.now()}`,
  table_name: props.tableName,
  database_name: props.database,
  partition_filter: '',
  merge_strategy: 'safe_merge',
  target_storage_format: null,
  target_compression: 'KEEP',
  use_ec: false
})

const mergeRules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }]
}

const clusterId = computed(() => props.clusterId)
const database = computed(() => props.database)
const tableName = computed(() => props.tableName)

const {
  selectedPartitions,
  partitionSelectMode,
  timeRangeMode,
  recentDays,
  predictedRecentCount,
  dateRange,
  excludeWeekends,
  predictedRangeCount,
  partitionPattern,
  predictedPatternCount,
  partitionSearchText,
  filteredPartitions,
  paginatedPartitions,
  hasMorePartitions,
  remainingPartitions,
  onPartitionModeChange,
  onTimeRangeModeChange,
  onRecentDaysChange,
  selectRecentPartitions,
  onDateRangeChange,
  selectDateRangePartitions,
  onPatternChange,
  selectPatternPartitions,
  previewPattern,
  onPartitionSearch,
  selectAllFiltered,
  loadMorePartitions,
  clearSelectedPartitions,
  showSelectedDetails,
  updatePredictions,
  updateFilteredPartitions,
  updatePaginatedPartitions
} = usePartitionManagement(clusterId, database, tableName)

watch(() => props.modelValue, (val) => {
  if (val) {
    mergeScope.value = props.isPartitioned ? 'partition' : 'table'
    mergeForm.value.task_name = `merge_${props.database}_${props.tableName}_${Date.now()}`
    selectedPartitions.value = []
    if (props.isPartitioned) {
      updatePredictions()
      updateFilteredPartitions()
      updatePaginatedPartitions()
    }
  }
})

const handleCreate = async () => {
  try {
    await mergeFormRef.value?.validate()
    emit('create', {
      mergeForm: mergeForm.value,
      mergeScope: mergeScope.value,
      selectedPartitions: selectedPartitions.value
    })
  } catch (error) {
    console.error('Validation failed:', error)
  }
}
</script>

<style scoped>
.governance-dialog :deep(.el-dialog) {
  border-radius: 16px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.1);
}

.dialog-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 16px 16px 0 0;
}

.dialog-header__icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.dialog-header__title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.dialog-header__subtitle {
  font-size: 14px;
  opacity: 0.9;
  margin: 4px 0 0 0;
}

.governance-form-container {
  background: #fafbfc;
  border-radius: 12px;
  margin: -8px;
  padding: 8px;
}

.governance-form {
  background: white;
  border-radius: 8px;
  padding: 16px;
}

.form-section {
  margin-bottom: 16px;
  border: 1px solid #e8eaec;
  border-radius: 12px;
  overflow: hidden;
  background: white;
}

.form-section__header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(90deg, #f8f9fa 0%, #ffffff 100%);
  border-bottom: 1px solid #e8eaec;
}

.form-section__icon {
  color: #409eff;
  font-size: 18px;
}

.form-section__title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2d3d;
  margin: 0;
  flex: 1;
}

.form-section__badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 500;
  background: #e1f3d8;
  color: #529b2e;
}

.form-section__content {
  padding: 16px;
}

.scope-radio-group {
  display: flex;
  gap: 16px;
  width: 100%;
}

.scope-radio {
  flex: 1;
}

.scope-radio :deep(.el-radio__input) {
  display: none;
}

.scope-radio :deep(.el-radio__label) {
  padding: 0;
  width: 100%;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
  justify-content: center;
}

.scope-radio.is-checked .radio-option {
  border-color: #409eff;
  background: #ecf5ff;
  color: #409eff;
}

.form-hint-inline {
  margin-left: 8px;
  font-size: 11px;
  color: #909399;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
}

.footer-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 12px;
  flex: 1;
}

.footer-actions {
  display: flex;
  gap: 12px;
}
</style>
