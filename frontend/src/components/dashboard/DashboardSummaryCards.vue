<template>
  <div class="overview-stats">
    <div class="stat-card" v-loading="loading">
      <div class="stat-icon">
        <el-icon><Files /></el-icon>
      </div>
      <div class="stat-content">
        <div class="stat-heading">
          <span class="stat-value">{{ summary?.total_files?.toLocaleString() || '-' }}</span>
          <span class="trend-badge trend-up">
            <el-icon><Top /></el-icon>
            <span>2.3%</span>
          </span>
        </div>
        <div class="stat-label">总文件数</div>
      </div>
    </div>

    <div class="stat-card" v-loading="loading">
      <div class="stat-icon storage">
        <el-icon><Coin /></el-icon>
      </div>
      <div class="stat-content">
        <div class="stat-heading">
          <span class="stat-value">{{ summary?.total_size_gb?.toFixed(2) || '-' }}GB</span>
          <span class="trend-badge trend-up">
            <el-icon><Top /></el-icon>
            <span>1.7%</span>
          </span>
        </div>
        <div class="stat-label">总存储空间</div>
      </div>
    </div>

    <div class="stat-card stat-card--result stat-card--with-chart" v-loading="loading">
      <SavingsDonut
        class="stat-chart"
        :percent="filesReducedPercent"
        color="#2563eb"
        track-color="rgba(37, 99, 235, 0.15)"
        :inner-label="'占比'"
      />
      <div class="stat-content">
        <div class="stat-heading">
          <span class="stat-value">{{ summary?.files_reduced?.toLocaleString() || '-' }}</span>
          <span class="stat-percent">{{ filesReducedPercentLabel }}</span>
        </div>
        <div class="stat-label">累计减少文件数</div>
      </div>
    </div>

    <div class="stat-card stat-card--savings stat-card--with-chart" v-loading="loading">
      <SavingsDonut
        class="stat-chart"
        :percent="sizeSavedPercent"
        color="#9333ea"
        track-color="rgba(147, 51, 234, 0.15)"
        :inner-label="'占比'"
      />
      <div class="stat-content">
        <div class="stat-heading">
          <span class="stat-value">
            {{ summary ? summary.size_saved_gb?.toFixed(2) : '-' }}GB
          </span>
          <span class="stat-percent">{{ sizeSavedPercentLabel }}</span>
        </div>
        <div class="stat-label">累计节省存储</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Files, Coin, Top, Bottom } from '@element-plus/icons-vue'
import type { DashboardSummary } from '@/api/dashboard'
import SavingsDonut from './SavingsDonut.vue'

const props = defineProps<{
  summary: DashboardSummary | null
  loading?: boolean
}>()

const filesReducedPercent = computed(() => {
  const total = props.summary?.total_files ?? 0
  const reduced = Math.max(props.summary?.files_reduced ?? 0, 0)
  if (!total) return 0
  return Math.min(100, (reduced / total) * 100)
})

const filesReducedPercentLabel = computed(() => {
  const value = filesReducedPercent.value
  if (!Number.isFinite(value)) return '0%'
  return value >= 10 ? `${value.toFixed(0)}%` : `${value.toFixed(1)}%`
})

const sizeSavedPercent = computed(() => {
  const total = props.summary?.total_size_gb ?? 0
  const saved = Math.max(props.summary?.size_saved_gb ?? 0, 0)
  if (!total) return 0
  return Math.min(100, (saved / total) * 100)
})

const sizeSavedPercentLabel = computed(() => {
  const value = sizeSavedPercent.value
  if (!Number.isFinite(value)) return '0%'
  return value >= 10 ? `${value.toFixed(0)}%` : `${value.toFixed(1)}%`
})
</script>

<style scoped>
.overview-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
  margin-bottom: 0;
}

.stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--gray-150);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-2);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  box-shadow: var(--elevation-1);
  transition: all var(--transition-normal);
  min-height: 70px;
}

.stat-card:hover {
  box-shadow: var(--elevation-2);
  transform: translateY(-1px);
}

.stat-card--with-chart {
  gap: var(--space-4);
}

.stat-card--with-chart .stat-content {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}

.stat-card--with-chart .stat-chart {
  flex-shrink: 0;
}

.stat-heading {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.stat-percent {
  font-size: 13px;
  font-weight: 500;
  color: var(--gray-500);
}

.trend-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  line-height: 1;
}

.trend-badge .el-icon {
  font-size: 10px;
}

.trend-up {
  color: var(--red-600);
  background: var(--red-50);
}

.trend-down {
  color: var(--green-600);
  background: var(--green-50);
}

.trend-neutral {
  color: var(--gray-600);
  background: var(--gray-100);
}

.stat-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-50);
  color: var(--primary-500);
  font-size: 16px;
  flex-shrink: 0;
}

.stat-icon.small-files {
  background: var(--red-50);
  color: var(--red-500);
}

.stat-icon.storage {
  background: var(--yellow-50);
  color: var(--yellow-600);
}

.stat-icon.clusters {
  background: var(--green-50);
  color: var(--green-500);
}

.stat-icon.result {
  background: var(--blue-50);
  color: var(--blue-500);
}

.stat-icon.savings {
  background: var(--purple-50);
  color: var(--purple-500);
}

.stat-card--result {
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.12), #ffffff);
  border-color: rgba(64, 158, 255, 0.35);
  box-shadow: 0 8px 20px rgba(64, 158, 255, 0.12);
}

.stat-card--result .stat-value {
  color: var(--blue-600, #2563eb);
}

.stat-card--result .stat-label {
  color: rgba(37, 99, 235, 0.8);
}

.stat-card--savings {
  background: linear-gradient(135deg, rgba(154, 52, 255, 0.12), #ffffff);
  border-color: rgba(154, 52, 255, 0.35);
  box-shadow: 0 8px 20px rgba(154, 52, 255, 0.12);
}

.stat-card--savings .stat-value {
  color: var(--purple-600, #9333ea);
}

.stat-card--savings .stat-label {
  color: rgba(147, 51, 234, 0.8);
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
  line-height: 1.2;
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--gray-600);
  margin-top: 2px;
}

@media (max-width: 1200px) {
  .overview-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .overview-stats {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-3);
  }

  .stat-card {
    padding: var(--space-2);
    min-height: 60px;
  }

  .stat-value {
    font-size: var(--text-base);
  }

  .stat-icon {
    width: 28px;
    height: 28px;
    font-size: 14px;
  }
}
</style>
