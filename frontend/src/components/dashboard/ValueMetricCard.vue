<template>
  <div
    class="value-metric-card"
    :class="[`metric-${type}`, { 'metric-primary': isPrimary }]"
  >
    <div class="metric-header">
      <div class="metric-icon" :class="type">
        <el-icon><component :is="icon" /></el-icon>
      </div>
      <div class="metric-trend" v-if="trend">
        <el-icon class="trend-icon" :class="trend.direction">
          <component :is="trend.icon" />
        </el-icon>
        <span class="trend-value" :class="trend.direction">{{
          trend.value
        }}</span>
      </div>
    </div>

    <div class="metric-content">
      <div class="metric-value">{{ displayValue }}</div>
      <div class="metric-label">{{ label }}</div>
      <div class="metric-description" v-if="description">{{ description }}</div>
    </div>

    <!-- 业务价值量化 -->
    <div class="business-impact" v-if="businessImpact">
      <div
        class="impact-item"
        v-for="impact in businessImpact"
        :key="impact.key"
      >
        <span class="impact-label">{{ impact.label }}:</span>
        <span class="impact-value" :class="impact.type">{{
          impact.value
        }}</span>
      </div>
    </div>

    <!-- 进度条（用于显示优化进度） -->
    <div class="metric-progress" v-if="progress">
      <div class="progress-bar">
        <div
          class="progress-fill"
          :style="{ width: progress.percentage + '%' }"
          :class="getProgressColor(progress.percentage)"
        ></div>
      </div>
      <div class="progress-text">{{ progress.text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Component } from "vue";

interface TrendData {
  direction: "up" | "down" | "stable";
  icon: Component;
  value: string;
}

interface BusinessImpact {
  key: string;
  label: string;
  value: string;
  type: "positive" | "negative" | "neutral";
}

interface ProgressData {
  percentage: number;
  text: string;
}

interface Props {
  type: "performance" | "cost" | "efficiency" | "lifecycle";
  icon: Component;
  label: string;
  value: string | number;
  unit?: string;
  description?: string;
  trend?: TrendData;
  businessImpact?: BusinessImpact[];
  progress?: ProgressData;
  isPrimary?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isPrimary: false,
});

const displayValue = computed(() => {
  if (typeof props.value === "number") {
    return formatNumber(props.value);
  }
  return props.value;
});

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + "M";
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K";
  }
  return num.toString();
}

function getProgressColor(percentage: number): string {
  if (percentage >= 80) return "progress-excellent";
  if (percentage >= 60) return "progress-good";
  if (percentage >= 40) return "progress-normal";
  return "progress-poor";
}
</script>

<style scoped>
.value-metric-card {
  background: var(--bg-primary);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.value-metric-card:hover {
  border-color: var(--gray-300);
  box-shadow: var(--elevation-2);
  transform: translateY(-2px);
}

.value-metric-card.metric-primary {
  background: linear-gradient(
    135deg,
    var(--primary-50) 0%,
    var(--primary-100) 100%
  );
  border-color: var(--primary-300);
  box-shadow: var(--elevation-2);
}

.value-metric-card.metric-primary .metric-value {
  color: var(--primary-700);
}

/* 卡片类型样式 */
.metric-performance .metric-icon {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  color: var(--blue-600);
}

.metric-cost .metric-icon {
  background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
  color: var(--green-600);
}

.metric-efficiency .metric-icon {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  color: var(--orange-600);
}

.metric-lifecycle .metric-icon {
  background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
  color: var(--purple-600);
}

/* 头部区域 */
.metric-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xl);
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.trend-icon.up {
  color: var(--success-500);
}

.trend-icon.down {
  color: var(--danger-500);
}

.trend-icon.stable {
  color: var(--warning-500);
}

.trend-value.up {
  color: var(--success-600);
}

.trend-value.down {
  color: var(--danger-600);
}

.trend-value.stable {
  color: var(--warning-600);
}

/* 内容区域 */
.metric-content {
  margin-bottom: var(--space-4);
}

.metric-value {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--gray-900);
  line-height: 1.2;
  margin-bottom: var(--space-1);
}

.metric-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--gray-700);
  margin-bottom: var(--space-2);
}

.metric-description {
  font-size: var(--text-xs);
  color: var(--gray-500);
  line-height: 1.4;
}

/* 业务影响区域 */
.business-impact {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  margin-bottom: var(--space-3);
}

.impact-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-1);
}

.impact-item:last-child {
  margin-bottom: 0;
}

.impact-label {
  font-size: var(--text-xs);
  color: var(--gray-600);
  font-weight: var(--font-medium);
}

.impact-value {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.impact-value.positive {
  color: var(--success-600);
}

.impact-value.negative {
  color: var(--danger-600);
}

.impact-value.neutral {
  color: var(--gray-600);
}

/* 进度条 */
.metric-progress {
  margin-top: var(--space-3);
}

.progress-bar {
  width: 100%;
  height: 4px;
  background: var(--gray-200);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: var(--space-2);
}

.progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--transition-normal);
}

.progress-excellent {
  background: linear-gradient(
    90deg,
    var(--success-400) 0%,
    var(--success-500) 100%
  );
}

.progress-good {
  background: linear-gradient(90deg, var(--blue-400) 0%, var(--blue-500) 100%);
}

.progress-normal {
  background: linear-gradient(
    90deg,
    var(--warning-400) 0%,
    var(--warning-500) 100%
  );
}

.progress-poor {
  background: linear-gradient(
    90deg,
    var(--danger-400) 0%,
    var(--danger-500) 100%
  );
}

.progress-text {
  font-size: var(--text-xs);
  color: var(--gray-600);
  text-align: center;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .value-metric-card {
    padding: var(--space-4);
  }

  .metric-value {
    font-size: var(--text-2xl);
  }

  .metric-icon {
    width: 40px;
    height: 40px;
  }
}
</style>
