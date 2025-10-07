<template>
  <el-card class="table-summary-card" shadow="hover">
    <div class="table-summary-card__header">
      <div>
        <div class="table-summary-card__title">{{ tableQualifiedName }}</div>
        <div class="table-summary-card__subtitle">
          最近扫描：{{ summaryMeta.lastScanText }}
          <span v-if="summaryMeta.lastScanFromNow">（{{ summaryMeta.lastScanFromNow }}）</span>
        </div>
        <div class="table-summary-card__tags">
          <el-tag :type="tableTypeTag.type">{{ tableTypeTag.label }}</el-tag>
          <el-tag v-if="storageFormatTag" type="info">{{ storageFormatTag }}</el-tag>
          <el-tag :type="isPartitioned ? 'success' : 'warning'" size="small">
            {{ isPartitioned ? '分区表' : '非分区表' }}
          </el-tag>
        </div>
      </div>
      <div class="table-summary-card__actions">
        <el-button type="primary" :loading="scanning" @click="$emit('scan')">
          <el-icon><RefreshRight /></el-icon>
          单表扫描
        </el-button>
        <template v-if="mergeSupported">
          <el-tooltip
            v-if="smallFiles === 0"
            content="暂无小文件，无需治理"
            placement="top"
          >
            <span>
              <el-button type="success" :disabled="smallFiles === 0" @click="$emit('open-merge')">
                <el-icon><Operation /></el-icon>
                发起治理
              </el-button>
            </span>
          </el-tooltip>
          <el-button v-else type="success" @click="$emit('open-merge')">
            <el-icon><Operation /></el-icon>
            发起治理
          </el-button>
        </template>
        <el-tooltip v-else :content="unsupportedReason || '该表类型不支持合并'" placement="top">
          <span>
            <el-button type="success" disabled>
              <el-icon><Operation /></el-icon>
              发起治理
            </el-button>
          </span>
        </el-tooltip>
      </div>
    </div>

    <div class="table-summary-card__metrics">
      <div
        v-for="stat in summaryStats"
        :key="stat.label"
        class="summary-metric"
      >
        <div class="summary-metric__icon" :class="`summary-metric__icon--${stat.color}`">
          <el-icon><component :is="stat.icon" /></el-icon>
        </div>
        <div class="summary-metric__content">
          <div class="summary-metric__label">{{ stat.label }}</div>
          <div class="summary-metric__value">{{ stat.value }}</div>
          <div v-if="stat.description" class="summary-metric__desc">{{ stat.description }}</div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { RefreshRight, Operation } from '@element-plus/icons-vue'

interface Props {
  tableQualifiedName: string
  summaryMeta: { lastScanText: string; lastScanFromNow: string }
  tableTypeTag: { label: string; type: 'success' | 'warning' | 'info' }
  storageFormatTag: string
  isPartitioned: boolean
  smallFiles: number
  summaryStats: any[]
  mergeSupported: boolean
  unsupportedReason: string
  scanning: boolean
}

defineProps<Props>()
defineEmits(['scan', 'open-merge'])
</script>

<style scoped>
.table-summary-card {
  position: relative;
  padding-bottom: 4px;
  width: 100%;
  box-sizing: border-box;
}

.table-summary-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
}

.table-summary-card__title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 2px;
}

.table-summary-card__subtitle {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.table-summary-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.table-summary-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.table-summary-card__metrics {
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.summary-metric {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f5f7fa;
}

.summary-metric__icon {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
}

.summary-metric__icon--primary { background: var(--el-color-primary); }
.summary-metric__icon--warning { background: var(--el-color-warning); }
.summary-metric__icon--danger { background: var(--el-color-danger); }
.summary-metric__icon--success { background: var(--el-color-success); }
.summary-metric__icon--info { background: var(--el-color-info); }

.summary-metric__content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-metric__label {
  font-size: 10px;
  color: #909399;
}

.summary-metric__value {
  font-size: 14px;
  font-weight: 600;
  color: #1f2d3d;
}

.summary-metric__desc {
  font-size: 9px;
  color: #909399;
}
</style>
