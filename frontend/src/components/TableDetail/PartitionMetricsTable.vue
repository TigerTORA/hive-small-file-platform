<template>
  <el-card class="detail-card detail-card--span-12 partition-table" shadow="never">
    <div class="section-title">
      <el-icon><Grid /></el-icon>
      <span>分区详情</span>
    </div>
    <div class="partition-table__meta">
      <span>共 {{ total }} 个分区</span>
      <div class="partition-table__controls">
        <el-button size="small" :loading="loading" @click="$emit('refresh')">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <span>并发度</span>
        <el-input-number
          :model-value="concurrency"
          @update:model-value="$emit('update:concurrency', $event)"
          :min="1"
          :max="20"
          :step="1"
          size="small"
        />
      </div>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>
    <template v-else>
      <el-alert
        v-if="error"
        :title="error"
        type="error"
        :closable="false"
        style="margin-bottom: 12px"
      />

      <div v-if="items.length === 0" class="partition-table__empty">
        <el-empty description="暂无分区统计数据" />
      </div>
      <div v-else>
        <el-table :data="items" size="small" border>
          <el-table-column prop="partition_spec" label="分区" min-width="220" />
          <el-table-column prop="partition_path" label="路径" min-width="260">
            <template #default="scope">
              <el-tooltip :content="scope.row.partition_path" placement="top">
                <span class="mono-text">{{ scope.row.partition_path || '--' }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="file_count" label="文件数" width="100" />
          <el-table-column prop="small_file_count" label="小文件数" width="120">
            <template #default="scope">
              <span :style="{ color: scope.row.small_file_count > 0 ? '#F56C6C' : '#67C23A' }">
                {{ scope.row.small_file_count }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="小文件占比" width="160">
            <template #default="scope">
              <div class="ratio-bar">
                <div class="ratio-bar__track">
                  <div
                    class="ratio-bar__fill"
                    :style="{
                      width: calcSmallRatio(scope.row) + '%',
                      background: getProgressColor(calcSmallRatio(scope.row))
                    }"
                  ></div>
                </div>
                <span class="ratio-bar__label">{{ calcSmallRatio(scope.row) }}%</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="平均文件大小" width="140">
            <template #default="scope">
              {{ formatFileSize(scope.row.avg_file_size || 0) }}
            </template>
          </el-table-column>
          <el-table-column label="总大小" width="140">
            <template #default="scope">
              {{ formatFileSize(scope.row.total_size || 0) }}
            </template>
          </el-table-column>
        </el-table>
        <div class="partition-table__pagination">
          <el-pagination
            background
            layout="prev, pager, next, sizes, total"
            :total="total"
            :current-page="page"
            :page-size="pageSize"
            :page-sizes="[50, 100, 200]"
            @size-change="$emit('size-change', $event)"
            @current-change="$emit('page-change', $event)"
          />
        </div>
      </div>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { Grid, Refresh } from '@element-plus/icons-vue'
import { formatFileSize } from '@/utils/formatFileSize'
import { getProgressColor } from '@/utils/tableHelpers'

interface Props {
  loading: boolean
  error: string
  items: any[]
  total: number
  page: number
  pageSize: number
  concurrency: number
}

defineProps<Props>()
defineEmits(['refresh', 'size-change', 'page-change', 'update:concurrency'])

const calcSmallRatio = (row: any): number => {
  const files = Number(row?.file_count || 0)
  const small = Number(row?.small_file_count || 0)
  if (!files) return 0
  return Math.round((small / files) * 100)
}
</script>

<style scoped>
.detail-card--span-12 {
  grid-column: span 12;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2d3d;
  margin-bottom: 10px;
}

.partition-table__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.partition-table__controls {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 12px;
}

.partition-table__pagination {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.loading-container {
  padding: 16px;
}

.mono-text {
  font-family: 'SFMono-Regular', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  display: inline-block;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ratio-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.ratio-bar__track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: #ebeef5;
  overflow: hidden;
}

.ratio-bar__fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.3s ease;
}

.ratio-bar__label {
  font-size: 12px;
  color: #606266;
  min-width: 48px;
  text-align: right;
}
</style>
