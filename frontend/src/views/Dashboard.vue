<template>
  <div class="dashboard">
    <section class="dashboard-hero">
      <div class="dashboard-hero__glow" />
      <div class="dashboard-hero__content">
        <div class="hero-header">
          <h1>数据治理驾驶舱</h1>
          <div class="hero-stats">
            <div class="hero-stat">
              <span class="stat-label">监控表</span>
              <strong class="stat-value">{{ monitoredTables }}</strong>
            </div>
            <div class="hero-stat-divider"></div>
            <div class="hero-stat">
              <span class="stat-label">活跃集群</span>
              <strong class="stat-value">{{ activeClusters }}</strong>
            </div>
            <div class="hero-stat-divider"></div>
            <div class="hero-stat">
              <span class="stat-label">小文件占比</span>
              <strong class="stat-value">{{ smallFileRatio }}%</strong>
            </div>
          </div>
        </div>
        <el-alert
          v-if="renderError"
          type="error"
          :title="'数据加载失败：' + renderError"
          show-icon
          class="hero-alert"
        />
      </div>
    </section>

    <div class="dashboard-body">
      <section class="glass-panel summary-panel">
        <DashboardSummaryCards :summary="dashboardSummary" :loading="isLoadingCharts" />
      </section>

      <section class="glass-panel charts-panel">
        <div class="charts-grid">
          <DashboardPieChart
            title="小文件分析"
            :tag="`总文件：${fileClassificationTotal.toLocaleString()}`"
            tag-type="primary"
            :icon="Files"
            :data="fileClassificationData"
            :color-scheme="ChartColorSchemes.fileClassification"
            @sector-click="onFileClassificationClick"
          />

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
      </section>

      <section class="glass-panel rankings-panel">
        <div class="dual-rankings">
          <DashboardRankingTable
            title="问题表排行榜"
            tag="小文件最多TOP10"
            tag-type="danger"
            :icon="Warning"
          >
            <el-table v-if="topTables.length > 0" :data="topTables" size="small" :show-header="true" max-height="320">
              <el-table-column prop="cluster_name" label="集群" width="70" />
              <el-table-column prop="database_name" label="数据库" width="100" />
              <el-table-column prop="table_name" label="表名" min-width="120" show-overflow-tooltip />
              <el-table-column label="小文件数" width="85" align="right">
                <template #default="scope">
                  <el-text type="danger" size="small">
                    {{ scope.row.small_files.toLocaleString() }}
                  </el-text>
                </template>
              </el-table-column>
              <el-table-column label="占比" width="65" align="right">
                <template #default="scope">
                  <el-text size="small">
                    {{ scope.row.small_file_ratio.toFixed(1) }}%
                  </el-text>
                </template>
              </el-table-column>
              <el-table-column label="大小" width="75" align="right">
                <template #default="scope">
                  <el-text size="small">
                    {{ scope.row.total_size_gb.toFixed(2) }}GB
                  </el-text>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="110" align="center" fixed="right">
                <template #default="scope">
                  <el-button size="small" type="primary" link @click="handleCompress(scope.row)">
                    压缩
                  </el-button>
                  <el-button size="small" type="info" link @click="handleArchive(scope.row)">
                    归档
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="暂无问题表数据" :image-size="80">
              <template #image>
                <el-icon :size="60" color="var(--gray-400)"><Warning /></el-icon>
              </template>
              <el-text type="info" size="small">开始扫描表格以发现小文件问题</el-text>
            </el-empty>
          </DashboardRankingTable>

          <DashboardRankingTable
            title="冷数据排行榜"
            tag="最久未访问TOP10"
            tag-type="info"
            :icon="Timer"
          >
            <el-table v-if="coldestData.length > 0" :data="coldestData" size="small" :show-header="true" max-height="320">
              <el-table-column prop="cluster_name" label="集群" width="70" />
              <el-table-column prop="database_name" label="数据库" width="100" />
              <el-table-column prop="table_name" label="表名" min-width="120" show-overflow-tooltip />
              <el-table-column label="未访问天数" width="90" align="right">
                <template #default="scope">
                  <el-text type="warning" size="small">
                    {{ scope.row.days_since_last_access }}天
                  </el-text>
                </template>
              </el-table-column>
              <el-table-column label="大小" width="75" align="right">
                <template #default="scope">
                  <el-text size="small">
                    {{ scope.row.total_size_gb.toFixed(2) }}GB
                  </el-text>
                </template>
              </el-table-column>
              <el-table-column label="文件数" width="70" align="right">
                <template #default="scope">
                  <el-text size="small">
                    {{ scope.row.file_count }}
                  </el-text>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="110" align="center" fixed="right">
                <template #default="scope">
                  <el-button size="small" type="primary" link @click="handleCompress(scope.row)">
                    压缩
                  </el-button>
                  <el-button size="small" type="info" link @click="handleArchive(scope.row)">
                    归档
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="暂无冷数据统计" :image-size="80">
              <template #image>
                <el-icon :size="60" color="var(--gray-400)"><Timer /></el-icon>
              </template>
              <el-text type="info" size="small">扫描表格后可查看访问时间分析</el-text>
            </el-empty>
          </DashboardRankingTable>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Files, Clock, Setting, Warning, Timer } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { ChartColorSchemes } from '@/config/chartColors'
import { useDashboardData } from '@/composables/useDashboardData'
import { useGlobalRefresh } from '@/composables/useGlobalRefresh'
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
  refreshChartData
} = useDashboardData()

useGlobalRefresh(() => {
  void refreshChartData()
})

const monitoredTables = computed(() =>
  (dashboardSummary.value?.monitored_tables || 0).toLocaleString()
)
const activeClusters = computed(() => (dashboardSummary.value?.active_clusters || 0).toLocaleString())
const smallFileRatio = computed(() => (dashboardSummary.value?.small_file_ratio || 0).toFixed(1))
const filesReduced = computed(() => (dashboardSummary.value?.files_reduced || 0).toLocaleString())
const sizeSaved = computed(() => (dashboardSummary.value?.size_saved_gb || 0).toFixed(2))
const savedPercent = computed(() => {
  const saved = dashboardSummary.value?.size_saved_gb ?? 0
  const total = dashboardSummary.value?.total_size_gb ?? 0
  if (!total) return 0
  return Math.min(100, Math.max(0, (saved / total) * 100))
})

// 冷数据饼状图提示框格式化
const formatColdnessTooltip = (item: any) => {
  const details = item.details
  if (!details) return ''

  return `
    <div style="font-weight: bold; margin-bottom: 6px;">${item.name}</div>
    <div>分区：${details.partitions.count} 个（${details.partitions.size_gb.toFixed(2)} GB）</div>
    <div>表：${details.tables.count} 个（${details.tables.size_gb.toFixed(2)} GB）</div>
    <div style="margin-top: 4px; font-weight: bold;">总计：${item.value.toFixed(2)} GB</div>
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
    <div style="font-weight: bold; margin-bottom: 6px;">${item.name}</div>
    <div>表数量：${details.table_count} 个（${details.percentage}%）</div>
    <div>总文件：${details.total_files.toLocaleString()} 个</div>
    <div>小文件：${details.small_files.toLocaleString()} 个（${smallFileRatio}%）</div>
    <div style="margin-top: 4px; font-weight: bold;">总大小：${details.total_size_gb.toFixed(2)} GB</div>
  `
}

// 文件分类饼状图点击事件
const onFileClassificationClick = (item: any) => {
  ElMessage.info(`点击了 ${item.name}：${item.value.toLocaleString()} 个文件`)
}

// 冷数据分布饼状图点击事件
const onColdnessDistributionClick = (item: any) => {
  ElMessage.info(`点击了 ${item.name}：${item.value.toFixed(2)}GB`)
}

// 格式与压缩饼状图点击事件
const onFormatCompressionClick = (item: any) => {
  ElMessage.info(`点击了 ${item.name}：${item.value.toLocaleString()} 张表`)
}

// 压缩操作处理
const handleCompress = (row: any) => {
  ElMessage.success(`准备压缩表: ${row.database_name}.${row.table_name}`)
  // TODO: 实现跳转到任务创建页面或直接创建压缩任务
}

// 归档操作处理
const handleArchive = (row: any) => {
  ElMessage.success(`准备归档表: ${row.database_name}.${row.table_name}`)
  // TODO: 实现跳转到归档管理页面
}
</script>

<style scoped>
.dashboard {
  width: clamp(960px, 88vw, 1440px);
  margin: 0 auto;
  padding: clamp(1rem, 3vw, 1.5rem) clamp(1.5rem, 4vw, 2rem);
  display: flex;
  flex-direction: column;
  gap: clamp(1.25rem, 2.5vw, 1.75rem);
  position: relative;
}

.glass-panel {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 24px;
  padding: clamp(1.5rem, 2vw, 2.5rem);
  box-shadow: var(--glass-shadow);
  backdrop-filter: var(--glass-backdrop);
  -webkit-backdrop-filter: var(--glass-backdrop);
  position: relative;
  overflow: hidden;
}

.glass-panel::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  box-shadow: var(--glass-highlight);
  pointer-events: none;
}

.dashboard-hero {
  width: 100%;
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  padding: clamp(1.25rem, 2.5vw, 1.5rem) clamp(2rem, 4vw, 3rem);
  display: flex;
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.9), rgba(147, 51, 234, 0.8));
  color: white;
  box-shadow: 0 20px 40px rgba(79, 70, 229, 0.2);
}

.dashboard-hero__glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.25), transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(236, 72, 153, 0.2), transparent 50%);
  opacity: 0.8;
}

.dashboard-hero__content {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: var(--space-3);
}

.hero-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: clamp(1.5rem, 3vw, 2rem);
  flex-wrap: wrap;
}

.hero-header h1 {
  font-size: clamp(1.5rem, 3vw, 2rem);
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.02em;
}


.hero-stats {
  display: flex;
  gap: clamp(1.5rem, 3vw, 2.5rem);
  flex-wrap: wrap;
}

.hero-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 80px;
}

.hero-stat .stat-label {
  font-size: 0.75rem;
  opacity: 0.7;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 500;
}

.hero-stat .stat-value {
  font-size: clamp(1.5rem, 2.5vw, 1.875rem);
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
}

.hero-stat-divider {
  width: 1px;
  height: 40px;
  background: linear-gradient(to bottom, transparent, rgba(255, 255, 255, 0.3), transparent);
  align-self: center;
}

.hero-stat--accent {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 12px;
  padding: var(--space-2) var(--space-3);
  backdrop-filter: blur(10px);
}

.hero-alert {
  margin-top: var(--space-2);
}

.dashboard-body {
  display: flex;
  flex-direction: column;
  gap: clamp(1.25rem, 2vw, 1.5rem);
}

.summary-panel {
  padding: clamp(1rem, 1.5vw, 1.5rem);
}

.charts-panel {
  padding: clamp(1.25rem, 1.5vw, 1.75rem);
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: clamp(1rem, 1.5vw, 1.5rem);
}

.rankings-panel {
  padding: clamp(1.25rem, 1.5vw, 1.75rem);
}

.dual-rankings {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: clamp(1.25rem, 2vw, 1.5rem);
}

@media (max-width: 1024px) {
  .dashboard-hero {
    flex-direction: column;
  }

  .dashboard-hero__content {
    flex-direction: column;
  }

  .hero-sidecard {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .dashboard {
    width: 100%;
    padding: clamp(0.75rem, 2vw, 1rem) clamp(1rem, 3vw, 1.5rem);
  }

  .hero-tags {
    gap: var(--space-2);
  }

  .hero-tag {
    width: calc(50% - var(--space-2));
    justify-content: space-between;
  }
}
</style>
