<template>
  <div class="header-section">
    <div class="title-section">
      <h1>任务管理</h1>
      <p>统一管理与监控扫描任务、合并任务、归档任务</p>
    </div>
    <div class="actions-section">
      <el-button
        @click="$emit('refresh')"
        :loading="loading"
        class="cloudera-btn secondary"
      >
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
      <el-button
        @click="$emit('create')"
        class="cloudera-btn primary"
      >
        <el-icon><Plus /></el-icon>
        创建任务
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus, Refresh } from '@element-plus/icons-vue'

defineProps<{
  loading: boolean
}>()

defineEmits<{
  (e: 'refresh'): void
  (e: 'create'): void
}>()
</script>

<style scoped>
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

@media (max-width: 768px) {
  .header-section {
    flex-direction: column;
    gap: var(--space-4);
    text-align: center;
  }
}
</style>
