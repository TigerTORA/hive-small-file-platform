<template>
  <div class="ranking-card">
    <div class="ranking-header">
      <h3>
        <el-icon><component :is="icon" /></el-icon>
        {{ title }}
      </h3>
      <el-tag size="small" :type="tagType">
        {{ tag }}
      </el-tag>
    </div>
    <div class="ranking-content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Component } from 'vue'

defineProps<{
  title: string
  tag: string
  tagType?: 'primary' | 'success' | 'info' | 'warning' | 'danger'
  icon: Component
}>()
</script>

<style scoped>
.ranking-card {
  background: var(--bg-primary);
  border: 1px solid var(--gray-150);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--elevation-1);
  transition: all var(--transition-normal);
}

.ranking-card:hover {
  box-shadow: var(--elevation-3);
  transform: translateY(-1px);
}

.ranking-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--gray-200);
}

.ranking-header h3 {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
  margin: 0;
}

.ranking-header .el-icon {
  color: var(--primary-500);
  font-size: var(--text-lg);
}

.ranking-content {
  padding: var(--space-4);
  background: var(--bg-primary);
  max-height: 450px;
  overflow-y: auto;
}
</style>
