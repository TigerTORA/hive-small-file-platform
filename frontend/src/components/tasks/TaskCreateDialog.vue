<template>
  <el-dialog v-model="visible" title="创建合并任务" width="600px">
    <el-form
      :model="taskForm"
      :rules="taskRules"
      ref="formRef"
      label-width="120px"
    >
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
          @blur="$emit('checkPartitions')"
        />
      </el-form-item>

      <!-- 表信息显示 -->
      <el-form-item v-if="tableInfo" label="表信息">
        <el-tag :type="tableInfo.is_partitioned ? 'success' : 'info'" size="small">
          {{ tableInfo.is_partitioned ? '分区表' : '普通表' }}
        </el-tag>
        <span v-if="tableInfo.is_partitioned" style="margin-left: 8px; color: #606266">
          共 {{ tableInfo.partition_count }} 个分区
        </span>
      </el-form-item>

      <!-- 分区选择 -->
      <el-form-item v-if="tableInfo?.is_partitioned" label="分区选择">
        <el-button
          size="small"
          @click="$emit('loadPartitions')"
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
          style="margin-top: 8px"
        />
      </el-form-item>

      <!-- 非分区表的分区过滤器输入 -->
      <el-form-item v-else label="分区过滤">
        <el-input
          v-model="taskForm.partition_filter"
          placeholder="如: dt='2023-12-01' (可选)"
        />
      </el-form-item>

      <el-form-item label="合并策略">
        <el-tag type="success" size="large">统一安全合并 (UNIFIED_SAFE_MERGE)</el-tag>
        <div style="margin-top: 4px; font-size: 12px; color: #909399">
          系统统一使用安全合并策略，确保零停机时间
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
          <span v-if="disableFormatSelection" style="margin-left: 8px"
            >仅在安全合并且整表模式下支持修改</span
          >
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
          <span v-if="disableCompressionSelection" style="margin-left: 8px"
            >仅在安全合并且整表模式下支持修改</span
          >
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
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="$emit('create')">创建</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import type { MergeTaskCreate } from '@/api/tasks'
import type { Cluster } from '@/api/clusters'

defineProps<{
  taskForm: MergeTaskCreate
  taskRules: any
  clusters: Cluster[]
  tableInfo: any
  partitions: any[]
  selectedPartitions: string[]
  partitionsLoading: boolean
  storageFormatOptions: Array<{ label: string; value: any }>
  compressionOptions: Array<{ label: string; value: string }>
  disableFormatSelection: boolean
  disableCompressionSelection: boolean
  tableFormatLabel: string
  tableCompressionLabel: string
}>()

defineEmits<{
  (e: 'checkPartitions'): void
  (e: 'loadPartitions'): void
  (e: 'create'): void
}>()

const visible = defineModel<boolean>()
const formRef = defineModel<any>('formRef')
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
