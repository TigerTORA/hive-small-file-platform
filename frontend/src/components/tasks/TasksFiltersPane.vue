<template>
  <el-card class="filters-pane" shadow="never">
    <div class="filters-title">筛选器</div>
    <el-input
      v-model="globalSearch"
      placeholder="搜索任务名/表名/数据库"
      clearable
      size="small"
      class="filters-search"
    />
    <div class="filter-section">
      <div class="filter-header">状态</div>
      <div class="filter-list">
        <div
          v-for="s in statusOptions"
          :key="s.value"
          :class="['filter-item', { active: selectedStatuses.has(s.value) }]"
          @click="$emit('toggleStatus', s.value)"
        >
          <span class="name">{{ s.label }}</span>
          <span class="count">{{ statusCounts[s.value] || 0 }}</span>
        </div>
      </div>
    </div>
    <div class="filter-section">
      <div class="filter-header">类型</div>
      <div class="filter-list">
        <div
          v-for="t in typeOptions"
          :key="t.value"
          :class="['filter-item', { active: selectedTypes.has(t.value) }]"
          @click="$emit('toggleType', t.value)"
        >
          <span class="name">{{ t.label }}</span>
          <span class="count">{{ typeCounts[t.value] || 0 }}</span>
        </div>
      </div>
    </div>
    <div class="filter-section">
      <div class="filter-header">归档子类型</div>
      <div class="filter-list">
        <div
          v-for="t in archiveSubtypeOptions"
          :key="t.value"
          :class="['filter-item', { active: selectedArchiveSubtypes.has(t.value) }]"
          @click="$emit('toggleArchiveSubtype', t.value)"
        >
          <span class="name">{{ t.label }}</span>
          <span class="count">{{ archiveSubtypeCounts[t.value] || 0 }}</span>
        </div>
      </div>
    </div>

    <div class="filter-actions">
      <el-button text size="small" @click="$emit('reset')">清除筛选</el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { toRefs } from 'vue'

const props = defineProps<{
  globalSearch: string
  selectedStatuses: Set<string>
  selectedTypes: Set<string>
  selectedArchiveSubtypes: Set<string>
  statusOptions: Array<{ label: string; value: string }>
  typeOptions: Array<{ label: string; value: string }>
  archiveSubtypeOptions: Array<{ label: string; value: string }>
  statusCounts: Record<string, number>
  typeCounts: Record<string, number>
  archiveSubtypeCounts: Record<string, number>
}>()

defineEmits<{
  (e: 'update:globalSearch', value: string): void
  (e: 'toggleStatus', value: string): void
  (e: 'toggleType', value: string): void
  (e: 'toggleArchiveSubtype', value: string): void
  (e: 'reset'): void
}>()

const globalSearch = defineModel<string>('globalSearch')
</script>

<style scoped>
.filters-pane {
  position: sticky;
  top: var(--space-2);
  align-self: start;
  max-height: calc(100vh - 96px);
  overflow: auto;
}

.filters-title {
  font-weight: 600;
  color: var(--gray-900);
  margin-bottom: 8px;
}

.filters-search {
  margin-bottom: 8px;
}

.filter-section {
  margin-top: 12px;
}

.filter-header {
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
}

.filter-list {
  display: flex;
  flex-direction: column;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.filter-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 10px;
  cursor: pointer;
}

.filter-item:hover {
  background: #f5f7fa;
}

.filter-item.active {
  background: #ecf5ff;
}

.filter-item .name {
  color: #303133;
}

.filter-item .count {
  color: #909399;
}

.filter-actions {
  margin-top: 12px;
  text-align: right;
}

@media (max-width: 1280px) {
  .filters-pane {
    position: static;
    order: -1;
  }
}
</style>
