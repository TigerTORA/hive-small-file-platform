<template>
  <div class="overview-stats">
    <div class="stat-card" v-loading="loading">
      <div class="stat-icon">
        <el-icon><Files /></el-icon>
      </div>
      <div class="stat-content">
        <div class="stat-value">{{ summary?.total_files?.toLocaleString() || '-' }}</div>
        <div class="stat-label">总文件数</div>
      </div>
    </div>

    <div class="stat-card" v-loading="loading">
      <div class="stat-icon small-files">
        <el-icon><Warning /></el-icon>
      </div>
      <div class="stat-content">
        <div class="stat-value">{{ summary?.small_file_ratio?.toFixed(1) || '-' }}%</div>
        <div class="stat-label">小文件比例</div>
      </div>
    </div>

    <div class="stat-card" v-loading="loading">
      <div class="stat-icon storage">
        <el-icon><Coin /></el-icon>
      </div>
      <div class="stat-content">
        <div class="stat-value">{{ summary?.total_size_gb?.toFixed(2) || '-' }}GB</div>
        <div class="stat-label">总存储空间</div>
      </div>
    </div>

    <div class="stat-card" v-loading="loading">
      <div class="stat-icon clusters">
        <el-icon><Monitor /></el-icon>
      </div>
      <div class="stat-content">
        <div class="stat-value">{{ summary?.monitored_tables?.toLocaleString() || '-' }}</div>
        <div class="stat-label">监控表数</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Files, Warning, Coin, Monitor } from '@element-plus/icons-vue'
import type { DashboardSummary } from '@/api/dashboard'

defineProps<{
  summary: DashboardSummary | null
  loading?: boolean
}>()
</script>

<style scoped>
.overview-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--gray-150);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  box-shadow: var(--elevation-0);
  transition: all var(--transition-normal);
  min-height: 60px;
}

.stat-card:hover {
  box-shadow: var(--elevation-2);
  transform: translateY(-1px);
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
    grid-template-columns: 1fr;
    gap: var(--space-3);
  }
}
</style>
