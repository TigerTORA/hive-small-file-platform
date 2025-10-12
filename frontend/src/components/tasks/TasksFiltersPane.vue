<template>
  <el-card class="filters-pane" shadow="never">
    <div class="filters-title">筛选器</div>

    <el-input
      v-model="globalSearch"
      placeholder="搜索任务名称 / 数据库 / 表 / 集群"
      clearable
      size="small"
      class="filters-search"
    />

    <div class="filter-section">
      <div class="filter-header">集群</div>
      <el-select
        v-model="selectedCluster"
        placeholder="全部集群"
        size="small"
        class="filter-select"
        clearable
        @clear="selectedCluster = 'all'"
      >
        <el-option
          v-for="option in clusterOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </el-select>
    </div>

    <div class="filter-section">
      <div class="filter-header">时间范围</div>
      <el-button-group class="timeframe-group">
        <el-button
          v-for="option in timeframeOptions"
          :key="option.value"
          size="small"
          :type="selectedTimeframe === option.value ? 'primary' : 'default'"
          @click="selectedTimeframe = option.value"
        >
          {{ option.label }}
        </el-button>
      </el-button-group>
    </div>

    <div class="filter-section">
      <div class="filter-header">状态</div>
      <div class="filter-list">
        <div
          v-for="status in statusOptions"
          :key="status.value"
          :class="['filter-item', { active: selectedStatuses.has(status.value) }]"
          @click="$emit('toggleStatus', status.value)"
        >
          <span class="name">{{ status.label }}</span>
          <span class="count">{{ statusCounts[status.value] || 0 }}</span>
        </div>
      </div>
    </div>

    <div class="filter-section">
      <div class="filter-header">类型</div>
      <div class="filter-list">
        <div
          v-for="type in typeOptions"
          :key="type.value"
          :class="['filter-item', { active: selectedTypes.has(type.value) }]"
          @click="$emit('toggleType', type.value)"
        >
          <span class="name">{{ type.label }}</span>
          <span class="count">{{ typeCounts[type.value] || 0 }}</span>
        </div>
      </div>
    </div>

    <div class="filter-section" v-if="archiveSubtypeOptions.length">
      <div class="filter-header">归档子类型</div>
      <div class="filter-list">
        <div
          v-for="sub in archiveSubtypeOptions"
          :key="sub.value"
          :class="['filter-item', { active: selectedArchiveSubtypes.has(sub.value) }]"
          @click="$emit('toggleArchiveSubtype', sub.value)"
        >
          <span class="name">{{ sub.label }}</span>
          <span class="count">{{ archiveSubtypeCounts[sub.value] || 0 }}</span>
        </div>
      </div>
    </div>

    <div class="filter-actions">
      <el-button text size="small" @click="$emit('reset')">清除筛选</el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
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
  clusterOptions: Array<{ label: string; value: number | 'all' }>
  timeframeOptions: Array<{ label: string; value: '24h' | '7d' | '30d' | 'all' }>
}>()

defineEmits<{
  (e: 'update:globalSearch', value: string): void
  (e: 'toggleStatus', value: string): void
  (e: 'toggleType', value: string): void
  (e: 'toggleArchiveSubtype', value: string): void
  (e: 'reset'): void
}>()

const globalSearch = defineModel<string>('globalSearch')
const selectedCluster = defineModel<number | 'all'>('selectedCluster', { default: 'all' })
const selectedTimeframe = defineModel<'24h' | '7d' | '30d' | 'all'>('selectedTimeframe', {
  default: 'all'
})
</script>

<style scoped>
.filters-pane {
  position: sticky;
  top: var(--space-2);
  align-self: start;
  max-height: calc(100vh - 96px);
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.filters-title {
  font-weight: 600;
  color: var(--gray-900);
}

.filters-search {
  width: 100%;
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.filter-header {
  font-size: 13px;
  color: #606266;
}

.filter-select {
  width: 100%;
}

.timeframe-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
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
  margin-top: auto;
  text-align: right;
}

@media (max-width: 1280px) {
  .filters-pane {
    position: static;
    order: -1;
  }
}
</style>
