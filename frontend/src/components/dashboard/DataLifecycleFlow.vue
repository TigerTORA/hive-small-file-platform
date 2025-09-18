<template>
  <div class="data-lifecycle-flow">
    <div class="flow-header">
      <h3 class="flow-title">
        <el-icon><TrendCharts /></el-icon>
        数据生命周期管理流程
      </h3>
      <div class="flow-summary">
        <span class="summary-text">实时监控您的数据从活跃使用到归档存储的完整生命周期</span>
      </div>
    </div>

    <div class="lifecycle-pipeline">
      <!-- 数据流程节点 -->
      <div class="pipeline-stages">
        <div
          v-for="(stage, index) in lifecycleStages"
          :key="stage.key"
          class="stage-container"
        >
          <!-- 阶段节点 -->
          <div
            class="stage-node"
            :class="[`stage-${stage.type}`, { active: stage.isActive }]"
            @click="handleStageClick(stage)"
          >
            <div class="stage-icon">
              <el-icon><component :is="stage.icon" /></el-icon>
            </div>
            <div class="stage-content">
              <div class="stage-name">{{ stage.name }}</div>
              <div class="stage-metric">{{ stage.metric }}</div>
              <div class="stage-description">{{ stage.description }}</div>
            </div>

            <!-- 状态指示器 -->
            <div
              class="stage-status"
              v-if="stage.status"
            >
              <div
                class="status-dot"
                :class="stage.status.type"
              ></div>
              <span class="status-text">{{ stage.status.text }}</span>
            </div>
          </div>

          <!-- 连接箭头 -->
          <div
            v-if="index < lifecycleStages.length - 1"
            class="stage-connector"
            :class="{
              active: stage.isActive && lifecycleStages[index + 1].isActive
            }"
          >
            <div class="connector-line"></div>
            <div class="connector-arrow">
              <el-icon><ArrowRight /></el-icon>
            </div>
            <div
              class="connector-label"
              v-if="stage.transitionInfo"
            >
              {{ stage.transitionInfo }}
            </div>
          </div>
        </div>
      </div>

      <!-- 价值产出指标 -->
      <div class="value-outputs">
        <div class="output-section">
          <h4 class="output-title">业务价值产出</h4>
          <div class="output-metrics">
            <div
              v-for="output in valueOutputs"
              :key="output.key"
              class="output-item"
              :class="output.type"
            >
              <div class="output-icon">
                <el-icon><component :is="output.icon" /></el-icon>
              </div>
              <div class="output-content">
                <div class="output-value">{{ output.value }}</div>
                <div class="output-label">{{ output.label }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import {
    TrendCharts,
    ArrowRight,
    Grid,
    Warning,
    DataBoard,
    FolderRemove,
    Search,
    Operation,
    Download,
    Monitor
  } from '@element-plus/icons-vue'
  import type { Component } from 'vue'

  interface LifecycleStage {
    key: string
    name: string
    type: 'active' | 'optimization' | 'identification' | 'archive'
    icon: Component
    metric: string
    description: string
    isActive: boolean
    status?: {
      type: 'success' | 'warning' | 'danger' | 'info'
      text: string
    }
    transitionInfo?: string
  }

  interface ValueOutput {
    key: string
    label: string
    value: string
    type: 'performance' | 'cost' | 'efficiency'
    icon: Component
  }

  interface QuickAction {
    key: string
    label: string
    type: string
    icon: Component
    loading?: boolean
  }

  interface Props {
    lifecycleData?: {
      activeTables: number
      smallFileTables: number
      coldDataTables: number
      archivedTables: number
    }
    performanceGain?: number
    costSavings?: number
    efficiencyImprovement?: number
  }

  const props = withDefaults(defineProps<Props>(), {
    lifecycleData: () => ({
      activeTables: 1200,
      smallFileTables: 245,
      coldDataTables: 213,
      archivedTables: 156
    }),
    performanceGain: 42,
    costSavings: 12800,
    efficiencyImprovement: 35
  })

  const emit = defineEmits<{
    stageClick: [stage: LifecycleStage]
    actionClick: [action: QuickAction]
  }>()

  // 生命周期阶段数据
  const lifecycleStages = computed<LifecycleStage[]>(() => [
    {
      key: 'active',
      name: '活跃数据',
      type: 'active',
      icon: Grid,
      metric: `${props.lifecycleData.activeTables}张表`,
      description: '正在被频繁访问和查询的数据',
      isActive: true,
      status: {
        type: 'success',
        text: '健康运行'
      },
      transitionInfo: '监控文件碎片化'
    },
    {
      key: 'optimization',
      name: '小文件优化',
      type: 'optimization',
      icon: Warning,
      metric: `${props.lifecycleData.smallFileTables}张表`,
      description: '检测到小文件问题，需要合并优化',
      isActive: props.lifecycleData.smallFileTables > 0,
      status: {
        type: 'warning',
        text: '需要优化'
      },
      transitionInfo: '合并完成后监控访问频率'
    },
    {
      key: 'identification',
      name: '冷数据识别',
      type: 'identification',
      icon: DataBoard,
      metric: `${props.lifecycleData.coldDataTables}张表`,
      description: '长期未访问，符合归档条件',
      isActive: props.lifecycleData.coldDataTables > 0,
      status: {
        type: 'info',
        text: '待归档'
      },
      transitionInfo: '执行归档操作'
    },
    {
      key: 'archive',
      name: '归档存储',
      type: 'archive',
      icon: FolderRemove,
      metric: `${props.lifecycleData.archivedTables}张表`,
      description: '已移至低成本存储，降低运营开销',
      isActive: props.lifecycleData.archivedTables > 0,
      status: {
        type: 'success',
        text: '已归档'
      }
    }
  ])

  // 价值产出指标
  const valueOutputs = computed<ValueOutput[]>(() => [
    {
      key: 'performance',
      label: '查询性能提升',
      value: `+${props.performanceGain}%`,
      type: 'performance',
      icon: TrendCharts
    },
    {
      key: 'cost',
      label: '存储成本节省',
      value: `$${(props.costSavings / 1000).toFixed(1)}K/月`,
      type: 'cost',
      icon: Download
    },
    {
      key: 'efficiency',
      label: '存储效率提升',
      value: `+${props.efficiencyImprovement}%`,
      type: 'efficiency',
      icon: Monitor
    }
  ])

  // 快速操作
  const quickActions = ref<QuickAction[]>([
    {
      key: 'scan',
      label: '批量扫描',
      type: 'primary',
      icon: Search,
      loading: false
    },
    {
      key: 'merge',
      label: '开始合并',
      type: 'warning',
      icon: Operation,
      loading: false
    },
    {
      key: 'cold_scan',
      label: '冷数据扫描',
      type: 'info',
      icon: DataBoard,
      loading: false
    },
    {
      key: 'archive',
      label: '批量归档',
      type: 'success',
      icon: FolderRemove,
      loading: false
    }
  ])

  function handleStageClick(stage: LifecycleStage) {
    emit('stageClick', stage)
  }

  function handleActionClick(action: QuickAction) {
    emit('actionClick', action)
  }
</script>

<style scoped>
  .data-lifecycle-flow {
    background: var(--bg-primary);
    border: 1px solid var(--gray-200);
    border-radius: var(--radius-xl);
    padding: var(--space-6);
    margin-bottom: var(--space-6);
  }

  /* 头部 */
  .flow-header {
    margin-bottom: var(--space-6);
    text-align: center;
  }

  .flow-title {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-3);
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
    color: var(--gray-900);
    margin-bottom: var(--space-3);
  }

  .flow-title .el-icon {
    color: var(--primary-500);
  }

  .flow-summary {
    color: var(--gray-600);
    font-size: var(--text-sm);
  }

  /* 管道流程 */
  .lifecycle-pipeline {
    margin-bottom: var(--space-4);
  }

  .pipeline-stages {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-6);
    overflow-x: auto;
    padding: var(--space-3) 0;
  }

  .stage-container {
    display: flex;
    align-items: center;
    min-width: 200px;
  }

  /* 阶段节点 */
  .stage-node {
    background: var(--bg-secondary);
    border: 2px solid var(--gray-200);
    border-radius: var(--radius-xl);
    padding: var(--space-6);
    min-width: 180px;
    cursor: pointer;
    transition: all var(--transition-normal);
    position: relative;
  }

  .stage-node:hover {
    border-color: var(--gray-300);
    transform: translateY(-2px);
    box-shadow: var(--elevation-2);
  }

  .stage-node.active {
    border-color: var(--primary-300);
    background: var(--primary-50);
  }

  .stage-active .stage-node {
    border-color: var(--blue-300);
    background: var(--blue-50);
  }

  .stage-optimization .stage-node {
    border-color: var(--warning-300);
    background: var(--warning-50);
  }

  .stage-identification .stage-node {
    border-color: var(--info-300);
    background: var(--info-50);
  }

  .stage-archive .stage-node {
    border-color: var(--success-300);
    background: var(--success-50);
  }

  .stage-icon {
    width: 48px;
    height: 48px;
    border-radius: var(--radius-lg);
    background: var(--primary-100);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: var(--space-4);
    font-size: var(--text-xl);
    color: var(--primary-600);
  }

  .stage-content {
    text-align: center;
  }

  .stage-name {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--gray-900);
    margin-bottom: var(--space-1);
  }

  .stage-metric {
    font-size: var(--text-lg);
    font-weight: var(--font-bold);
    color: var(--primary-600);
    margin-bottom: var(--space-2);
  }

  .stage-description {
    font-size: var(--text-xs);
    color: var(--gray-600);
    line-height: 1.4;
    margin-bottom: var(--space-3);
  }

  .stage-status {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-1);
    font-size: var(--text-xs);
  }

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: var(--radius-full);
  }

  .status-dot.success {
    background: var(--success-500);
  }

  .status-dot.warning {
    background: var(--warning-500);
  }

  .status-dot.danger {
    background: var(--danger-500);
  }

  .status-dot.info {
    background: var(--info-500);
  }

  .status-text {
    color: var(--gray-600);
    font-weight: var(--font-medium);
  }

  /* 连接器 */
  .stage-connector {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 0 var(--space-4);
  }

  .connector-line {
    width: 60px;
    height: 2px;
    background: var(--gray-300);
    position: relative;
    margin-bottom: var(--space-1);
  }

  .stage-connector.active .connector-line {
    background: var(--primary-400);
  }

  .connector-arrow {
    color: var(--gray-400);
    font-size: var(--text-sm);
  }

  .stage-connector.active .connector-arrow {
    color: var(--primary-500);
  }

  .connector-label {
    font-size: var(--text-xs);
    color: var(--gray-500);
    margin-top: var(--space-1);
    text-align: center;
    max-width: 80px;
  }

  /* 价值输出 */
  .value-outputs {
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
    padding: var(--space-6);
    margin-bottom: var(--space-6);
  }

  .output-title {
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    color: var(--gray-900);
    margin-bottom: var(--space-4);
    text-align: center;
  }

  .output-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: var(--space-4);
  }

  .output-item {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-4);
    background: var(--bg-primary);
    border-radius: var(--radius-lg);
    border: 1px solid var(--gray-200);
  }

  .output-icon {
    width: 36px;
    height: 36px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--text-lg);
  }

  .output-item.performance .output-icon {
    background: var(--blue-100);
    color: var(--blue-600);
  }

  .output-item.cost .output-icon {
    background: var(--green-100);
    color: var(--green-600);
  }

  .output-item.efficiency .output-icon {
    background: var(--orange-100);
    color: var(--orange-600);
  }

  .output-content {
    flex: 1;
  }

  .output-value {
    font-size: var(--text-lg);
    font-weight: var(--font-bold);
    color: var(--gray-900);
  }

  .output-label {
    font-size: var(--text-xs);
    color: var(--gray-600);
  }

  /* 快速操作 */
  .quick-actions {
    border-top: 1px solid var(--gray-200);
    padding-top: var(--space-6);
  }

  .actions-title {
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    color: var(--gray-900);
    margin-bottom: var(--space-4);
    text-align: center;
  }

  .actions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: var(--space-4);
  }

  .action-button {
    min-height: 48px;
  }

  /* 响应式适配 */
  @media (max-width: 768px) {
    .pipeline-stages {
      flex-direction: column;
      gap: var(--space-6);
    }

    .stage-container {
      flex-direction: column;
      min-width: auto;
      width: 100%;
    }

    .stage-connector {
      transform: rotate(90deg);
      margin: var(--space-4) 0;
    }

    .output-metrics {
      grid-template-columns: 1fr;
    }

    .actions-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
