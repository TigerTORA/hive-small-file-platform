<template>
  <div class="chart-card">
    <div class="chart-header">
      <h3>
        <el-icon><component :is="icon" /></el-icon>
        {{ title }}
      </h3>
      <el-tag size="small" :type="tagType">
        {{ tag }}
      </el-tag>
    </div>
    <div class="chart-content">
      <PieChart
        :data="data"
        :height="380"
        :color-scheme="colorScheme"
        :tooltip-formatter="tooltipFormatter"
        @sector-click="handleSectorClick"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Component } from 'vue'
import PieChart from '@/components/charts/PieChart.vue'

defineProps<{
  title: string
  tag: string
  tagType?: 'primary' | 'success' | 'info' | 'warning' | 'danger'
  icon: Component
  data: Array<{ name: string; value: number; details?: any }>
  colorScheme: string[]
  tooltipFormatter?: (item: any) => string
}>()

const emit = defineEmits<{
  sectorClick: [item: any]
}>()

const handleSectorClick = (item: any) => {
  emit('sectorClick', item)
}
</script>

<style scoped>
.chart-card {
  background: var(--bg-primary);
  border: 1px solid var(--gray-150);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--elevation-1);
  transition: all var(--transition-normal);
}

.chart-card:hover {
  box-shadow: var(--elevation-3);
  transform: translateY(-1px);
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--gray-200);
}

.chart-header h3 {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
  margin: 0;
}

.chart-header .el-icon {
  color: var(--primary-500);
  font-size: var(--text-lg);
}

.chart-content {
  padding: var(--space-4) var(--space-3) var(--space-4);
  background: var(--bg-primary);
}
</style>
