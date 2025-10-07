<template>
  <div class="dashboard">
    <el-alert
      v-if="renderError"
      :title="'监控中心加载失败：' + renderError"
      type="error"
      show-icon
      style="margin-bottom: 12px"
    />

    <!-- 顶部概览统计卡片区域 -->
    <DashboardSummaryCards :summary="dashboardSummary" :loading="isLoadingCharts" />

    <!-- 三饼状图布局 -->
    <div class="pie-charts-section">
      <div class="triple-pie-charts">
        <!-- 小文件分析饼状图 -->
        <DashboardPieChart
          title="小文件分析"
          :tag="`总文件：${fileClassificationTotal.toLocaleString()}`"
          tag-type="primary"
          :icon="Files"
          :data="fileClassificationData"
          :color-scheme="ChartColorSchemes.fileClassification"
          @sector-click="onFileClassificationClick"
        />

        <!-- 最后访问时间分布饼状图 -->
        <DashboardPieChart
          title="最后访问时间分布"
          :tag="`总大小：${coldDataTotal.toFixed(2)}GB`"
          tag-type="primary"
          :icon="Clock"
          :data="coldnessDistributionData"
          :color-scheme="ChartColorSchemes.coldness"
          :tooltip-formatter="formatColdnessTooltip"
          @sector-click="onColdnessDistributionClick"
        />

        <!-- 存储&压缩格式组合分布饼状图 -->
        <DashboardPieChart
          title="存储&压缩格式分布"
          :tag="`总表数：${formatCompressionTotal.toLocaleString()}`"
          tag-type="primary"
          :icon="Setting"
          :data="formatCompressionData"
          :color-scheme="ChartColorSchemes.formatCompression"
          :tooltip-formatter="formatCompressionTooltip"
          @sector-click="onFormatCompressionClick"
        />
      </div>
    </div>

    <!-- 排行榜区域 -->
    <div class="rankings-section">
      <div class="dual-rankings">
        <!-- 问题表排行榜 -->
        <DashboardRankingTable
          title="问题表排行榜"
          tag="小文件最多TOP10"
          tag-type="danger"
          :icon="Warning"
        >
          <el-table :data="topTables" size="small" :show-header="true" max-height="300">
            <el-table-column prop="cluster_name" label="集群" width="80" />
            <el-table-column prop="database_name" label="数据库" width="120" />
            <el-table-column prop="table_name" label="表名" min-width="150" show-overflow-tooltip />
            <el-table-column label="小文件数" width="100" align="right">
              <template #default="scope">
                <el-text type="danger" size="small">
                  {{ scope.row.small_files.toLocaleString() }}
                </el-text>
              </template>
            </el-table-column>
            <el-table-column label="占比" width="80" align="right">
              <template #default="scope">
                <el-text size="small">
                  {{ scope.row.small_file_ratio.toFixed(1) }}%
                </el-text>
              </template>
            </el-table-column>
            <el-table-column label="大小" width="90" align="right">
              <template #default="scope">
                <el-text size="small">
                  {{ scope.row.total_size_gb.toFixed(2) }}GB
                </el-text>
              </template>
            </el-table-column>
          </el-table>
        </DashboardRankingTable>

        <!-- 冷数据排行榜 -->
        <DashboardRankingTable
          title="冷数据排行榜"
          tag="最久未访问TOP10"
          tag-type="info"
          :icon="Timer"
        >
          <el-table :data="coldestData" size="small" :show-header="true" max-height="300">
            <el-table-column prop="cluster_name" label="集群" width="80" />
            <el-table-column prop="database_name" label="数据库" width="120" />
            <el-table-column prop="table_name" label="表名" min-width="150" show-overflow-tooltip />
            <el-table-column label="未访问天数" width="100" align="right">
              <template #default="scope">
                <el-text type="warning" size="small">
                  {{ scope.row.days_since_last_access }}天
                </el-text>
              </template>
            </el-table-column>
            <el-table-column label="大小" width="90" align="right">
              <template #default="scope">
                <el-text size="small">
                  {{ scope.row.total_size_gb.toFixed(2) }}GB
                </el-text>
              </template>
            </el-table-column>
            <el-table-column label="文件数" width="80" align="right">
              <template #default="scope">
                <el-text size="small">
                  {{ scope.row.file_count }}
                </el-text>
              </template>
            </el-table-column>
          </el-table>
        </DashboardRankingTable>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { Files, Clock, Setting, Warning, Timer } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { ChartColorSchemes } from '@/config/chartColors'
import { useDashboardData } from '@/composables/useDashboardData'
import DashboardSummaryCards from '@/components/dashboard/DashboardSummaryCards.vue'
import DashboardPieChart from '@/components/dashboard/DashboardPieChart.vue'
import DashboardRankingTable from '@/components/dashboard/DashboardRankingTable.vue'

const {
  renderError,
  isLoadingCharts,
  dashboardSummary,
  fileClassificationData,
  fileClassificationTotal,
  coldnessDistributionData,
  coldDataTotal,
  formatCompressionData,
  formatCompressionTotal,
  topTables,
  coldestData,
  loadChartData
} = useDashboardData()

// 冷数据饼状图提示框格式化
const formatColdnessTooltip = (item: any) => {
  const details = item.details
  if (!details) return ''

  return `
    <div style="font-weight: bold; margin-bottom: 8px;">${item.name}</div>
    <div>📊 分区：${details.partitions.count}个 (${details.partitions.size_gb.toFixed(2)}GB)</div>
    <div>📋 表：${details.tables.count}个 (${details.tables.size_gb.toFixed(2)}GB)</div>
    <div style="margin-top: 4px; font-weight: bold;">💾 总计：${item.value.toFixed(2)}GB</div>
  `
}

// 组合格式tooltip格式化函数
const formatCompressionTooltip = (item: any) => {
  const details = item.details
  if (!details) return ''

  const smallFileRatio = details.total_files > 0
    ? (details.small_files / details.total_files * 100).toFixed(1)
    : '0'

  return `
    <div style="font-weight: bold; margin-bottom: 8px;">${item.name}</div>
    <div>📊 表数量：${details.table_count}个 (${details.percentage}%)</div>
    <div>📁 总文件：${details.total_files.toLocaleString()}个</div>
    <div>⚠️ 小文件：${details.small_files.toLocaleString()}个 (${smallFileRatio}%)</div>
    <div style="margin-top: 4px; font-weight: bold;">💾 总大小：${details.total_size_gb.toFixed(2)}GB</div>
  `
}

// 文件分类饼状图点击事件
const onFileClassificationClick = (item: any) => {
  console.log('文件分类点击:', item)
  ElMessage.info(`点击了 ${item.name}：${item.value.toLocaleString()} 个文件`)
}

// 冷数据分布饼状图点击事件
const onColdnessDistributionClick = (item: any) => {
  console.log('冷数据分布点击:', item)
  ElMessage.info(`点击了 ${item.name}：${item.value.toFixed(2)}GB`)
}

// 组合格式点击处理
const onFormatCompressionClick = (item: any) => {
  console.log('点击组合格式:', item)
}

// 生命周期
onMounted(async () => {
  try {
    await loadChartData()
  } catch (e: any) {
    console.error('Dashboard mount error:', e)
    renderError.value = e?.message || String(e)
  }
})
</script>

<style scoped>
.dashboard {
  padding: var(--space-3);
  min-height: 100vh;
  background: var(--bg-app);
  max-width: 1600px;
  margin: 0 auto;
}

/* 三饼状图区域样式 */
.pie-charts-section {
  background: var(--bg-secondary);
  padding: var(--space-4);
  border-radius: var(--radius-xl);
  border: 1px solid var(--gray-100);
  box-shadow: var(--elevation-1);
  margin-bottom: var(--space-4);
}

.triple-pie-charts {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-4);
  min-height: 480px;
}

/* 排行榜区域样式 */
.rankings-section {
  background: var(--bg-secondary);
  padding: var(--space-4);
  border-radius: var(--radius-xl);
  border: 1px solid var(--gray-100);
  box-shadow: var(--elevation-1);
}

.dual-rankings {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-5);
  min-height: 500px;
  width: 100%;
}

/* 响应式适配 */
@media (max-width: 1200px) {
  .triple-pie-charts {
    grid-template-columns: 1fr 1fr;
    gap: var(--space-4);
    min-height: 400px;
  }

  .dual-rankings {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }
}

@media (max-width: 900px) {
  .triple-pie-charts {
    grid-template-columns: 1fr;
    gap: var(--space-4);
    min-height: 360px;
  }
}

@media (max-width: 768px) {
  .dashboard {
    padding: var(--space-4);
  }

  .pie-charts-section,
  .rankings-section {
    padding: var(--space-3);
  }
}
</style>
