<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- 统计卡片 -->
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon clusters">
              <el-icon><Connection /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-number">{{ summary.totalClusters }}</div>
              <div class="stat-label">集群总数</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon tables">
              <el-icon><Grid /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-number">{{ summary.totalTables }}</div>
              <div class="stat-label">监控表数</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon files">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-number">{{ formatNumber(summary.totalFiles) }}</div>
              <div class="stat-label">文件总数</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon small-files">
              <el-icon><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-number">{{ formatNumber(summary.totalSmallFiles) }}</div>
              <div class="stat-label">小文件数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 小文件趋势图表 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>小文件趋势</span>
              <el-select v-model="selectedCluster" placeholder="选择集群" style="width: 200px;">
                <el-option
                  v-for="cluster in clusters"
                  :key="cluster.id"
                  :label="cluster.name"
                  :value="cluster.id"
                />
              </el-select>
            </div>
          </template>
          <div style="height: 400px;">
            <v-chart class="chart" :option="trendChartOption" />
          </div>
        </el-card>
      </el-col>

      <!-- 文件大小分布 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>文件大小分布</span>
          </template>
          <div style="height: 400px;">
            <v-chart class="chart" :option="distributionChartOption" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 最近任务 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近任务</span>
              <el-button type="primary" size="small" @click="$router.push('/tasks')">
                查看更多
              </el-button>
            </div>
          </template>
          <el-table :data="recentTasks" stripe>
            <el-table-column prop="task_name" label="任务名称" />
            <el-table-column prop="table_name" label="表名" />
            <el-table-column prop="status" label="状态">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_time" label="创建时间" width="160">
              <template #default="{ row }">
                {{ formatTime(row.created_time) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 问题表排行 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>小文件数量 TOP10</span>
          </template>
          <el-table :data="topTables" stripe>
            <el-table-column prop="table_name" label="表名" />
            <el-table-column prop="small_files" label="小文件数" />
            <el-table-column prop="small_file_ratio" label="占比">
              <template #default="{ row }">
                {{ (row.small_files / row.total_files * 100).toFixed(1) }}%
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import dayjs from 'dayjs'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  LineChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

// 数据定义
const summary = ref({
  totalClusters: 0,
  totalTables: 0,
  totalFiles: 0,
  totalSmallFiles: 0
})

const clusters = ref<any[]>([])
const selectedCluster = ref<number | null>(null)
const recentTasks = ref<any[]>([])
const topTables = ref<any[]>([])

// 图表配置
const trendChartOption = ref({
  title: {
    text: '小文件数量趋势'
  },
  tooltip: {
    trigger: 'axis'
  },
  xAxis: {
    type: 'category',
    data: [] // 将从 API 获取
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      name: '小文件数量',
      type: 'line',
      data: [] // 将从 API 获取
    }
  ]
})

const distributionChartOption = ref({
  title: {
    text: '文件大小分布',
    left: 'center'
  },
  tooltip: {
    trigger: 'item'
  },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: 1048, name: '< 1MB' },
        { value: 735, name: '1MB-128MB' },
        { value: 580, name: '128MB-1GB' },
        { value: 484, name: '> 1GB' }
      ]
    }
  ]
})

// 方法
const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

const formatTime = (time: string): string => {
  return dayjs(time).format('MM-DD HH:mm')
}

const getStatusType = (status: string): string => {
  const statusMap: Record<string, string> = {
    'pending': 'info',
    'running': 'warning',
    'success': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    'pending': '等待中',
    'running': '运行中',
    'success': '成功',
    'failed': '失败'
  }
  return statusMap[status] || status
}

// 加载数据
const loadDashboardData = async () => {
  try {
    // TODO: 调用实际的 API
    // 模拟数据
    summary.value = {
      totalClusters: 3,
      totalTables: 156,
      totalFiles: 2340000,
      totalSmallFiles: 1560000
    }
    
    clusters.value = [
      { id: 1, name: '生产集群' },
      { id: 2, name: '测试集群' },
      { id: 3, name: '开发集群' }
    ]
    
    recentTasks.value = [
      {
        task_name: '用户行为表合并',
        table_name: 'user_behavior',
        status: 'success',
        created_time: '2023-12-01T10:30:00Z'
      },
      {
        task_name: '订单数据合并',
        table_name: 'orders',
        status: 'running',
        created_time: '2023-12-01T09:15:00Z'
      }
    ]
    
    topTables.value = [
      {
        table_name: 'user_logs',
        small_files: 15600,
        total_files: 18900
      },
      {
        table_name: 'click_stream',
        small_files: 12300,
        total_files: 15600
      }
    ]
    
    if (clusters.value.length > 0) {
      selectedCluster.value = clusters.value[0].id
    }
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stat-card {
  height: 120px;
}

.stat-content {
  display: flex;
  align-items: center;
  height: 80px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  font-size: 24px;
  color: white;
}

.stat-icon.clusters {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-icon.tables {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.stat-icon.files {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.stat-icon.small-files {
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
  color: #e67e22;
}

.stat-info {
  flex: 1;
}

.stat-number {
  font-size: 28px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #7f8c8d;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart {
  height: 100%;
  width: 100%;
}
</style>