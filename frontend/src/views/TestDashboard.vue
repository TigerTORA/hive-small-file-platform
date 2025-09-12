<template>
  <div class="test-dashboard">
    <div class="dashboard-header">
      <h1 class="page-title">
        <el-icon><DataBoard /></el-icon>
        测试中心
      </h1>
      <div class="header-actions">
        <!-- 模式切换 -->
        <div class="mode-switcher">
          <el-tooltip content="切换测试数据模式" placement="bottom">
            <el-switch
              v-model="isRealMode"
              @change="handleModeChange"
              active-text="真实"
              inactive-text="模拟"
              active-color="#67c23a"
              inactive-color="#409eff"
              size="large"
            />
          </el-tooltip>
          <span class="mode-label">{{ isRealMode ? '真实测试' : '模拟数据' }}</span>
        </div>
        
        <el-divider direction="vertical" />
        
        <el-button type="primary" @click="runAllTests" :loading="isRunning">
          <el-icon><VideoPlay /></el-icon>
          {{ isRealMode ? '执行真实测试' : '模拟执行测试' }}
        </el-button>
        <el-button @click="refreshData" :loading="isRefreshing">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
      </div>
    </div>

    <!-- 测试概览 -->
    <div class="overview-section">
      <el-row :gutter="24">
        <el-col :span="6">
          <el-card class="overview-card success">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><Check /></el-icon>
              </div>
              <div class="card-info">
                <h3>{{ testOverview.totalPassed }}</h3>
                <p>通过测试</p>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="overview-card danger">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><Close /></el-icon>
              </div>
              <div class="card-info">
                <h3>{{ testOverview.totalFailed }}</h3>
                <p>失败测试</p>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="overview-card info">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="card-info">
                <h3>{{ testOverview.totalTests }}</h3>
                <p>总测试数</p>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="overview-card warning">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><TrendCharts /></el-icon>
              </div>
              <div class="card-info">
                <h3>{{ testOverview.successRate }}%</h3>
                <p>成功率</p>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 测试分类展示 -->
    <div class="categories-section">
      <el-card>
        <template #header>
          <div class="section-header">
            <h2>测试分类总览</h2>
            <el-tag>基于11条核心测试规则</el-tag>
          </div>
        </template>
        
        <el-row :gutter="16">
          <el-col :span="12" v-for="category in testCategories" :key="category.id">
            <div class="category-card" @click="viewCategoryDetails(category)">
              <div class="category-header">
                <h3>{{ category.name }}</h3>
                <el-badge :value="category.testCount" type="primary" />
              </div>
              <div class="category-progress">
                <el-progress 
                  :percentage="category.successRate" 
                  :color="getProgressColor(category.successRate)"
                  :stroke-width="8"
                />
              </div>
              <div class="category-stats">
                <span class="stat-item">
                  <el-icon><Check /></el-icon>
                  {{ category.passedTests }}
                </span>
                <span class="stat-item">
                  <el-icon><Close /></el-icon>
                  {{ category.failedTests }}
                </span>
              </div>
            </div>
          </el-col>
        </el-row>
      </el-card>
    </div>

    <!-- 详细测试结果 -->
    <div class="results-section">
      <el-card>
        <template #header>
          <div class="section-header">
            <h2>详细测试结果</h2>
            <div class="header-filters">
              <el-select v-model="filterCategory" placeholder="选择分类" clearable>
                <el-option 
                  v-for="category in testCategories" 
                  :key="category.id"
                  :label="category.name" 
                  :value="category.id"
                />
              </el-select>
              
              <el-select v-model="filterStatus" placeholder="选择状态" clearable>
                <el-option label="全部" value="" />
                <el-option label="通过" value="passed" />
                <el-option label="失败" value="failed" />
                <el-option label="跳过" value="skipped" />
              </el-select>
            </div>
          </div>
        </template>

        <el-table 
          :data="filteredTestResults" 
          stripe 
          style="width: 100%"
          v-loading="isLoading"
        >
          <el-table-column prop="name" label="测试名称" min-width="200">
            <template #default="scope">
              <div class="test-name">
                <el-icon v-if="scope.row.status === 'passed'" class="status-icon success">
                  <Check />
                </el-icon>
                <el-icon v-else-if="scope.row.status === 'failed'" class="status-icon danger">
                  <Close />
                </el-icon>
                <el-icon v-else class="status-icon warning">
                  <Warning />
                </el-icon>
                {{ scope.row.name }}
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="category" label="分类" width="150">
            <template #default="scope">
              <el-tag :type="getCategoryTagType(scope.row.category)">
                {{ scope.row.category }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag 
                :type="scope.row.status === 'passed' ? 'success' : scope.row.status === 'failed' ? 'danger' : 'warning'"
              >
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="duration" label="执行时间" width="120">
            <template #default="scope">
              {{ formatDuration(scope.row.duration) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="lastRun" label="最后运行" width="160">
            <template #default="scope">
              {{ formatTime(scope.row.lastRun) }}
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="200">
            <template #default="scope">
              <el-button size="small" @click="runSingleTest(scope.row)">
                <el-icon><VideoPlay /></el-icon>
                运行
              </el-button>
              <el-button size="small" @click="viewTestDetails(scope.row)">
                <el-icon><View /></el-icon>
                详情
              </el-button>
              <el-button 
                v-if="scope.row.screenshots && scope.row.screenshots.length > 0"
                size="small" 
                @click="viewScreenshots(scope.row)"
              >
                <el-icon><Picture /></el-icon>
                截图
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="filteredTestResults.length"
            layout="total, prev, pager, next, jumper"
            @current-change="handlePageChange"
          />
        </div>
      </el-card>
    </div>

    <!-- 测试详情对话框 -->
    <el-dialog 
      v-model="detailDialogVisible" 
      title="测试详情" 
      width="80%"
      top="5vh"
    >
      <div v-if="selectedTest" class="test-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="测试名称">
            {{ selectedTest.name }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedTest.status === 'passed' ? 'success' : 'danger'">
              {{ getStatusText(selectedTest.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="分类">
            {{ selectedTest.category }}
          </el-descriptions-item>
          <el-descriptions-item label="执行时间">
            {{ formatDuration(selectedTest.duration) }}
          </el-descriptions-item>
          <el-descriptions-item label="最后运行">
            {{ formatTime(selectedTest.lastRun) }}
          </el-descriptions-item>
          <el-descriptions-item label="文件路径">
            {{ selectedTest.filePath }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="selectedTest.logs" class="test-logs">
          <h4>执行日志</h4>
          <el-input
            v-model="selectedTest.logs"
            type="textarea"
            :rows="10"
            readonly
            class="log-textarea"
          />
        </div>

        <div v-if="selectedTest.error" class="test-error">
          <h4>错误信息</h4>
          <el-alert
            :title="selectedTest.error"
            type="error"
            :closable="false"
            show-icon
          />
        </div>
      </div>
    </el-dialog>

    <!-- 截图查看对话框 -->
    <el-dialog 
      v-model="screenshotDialogVisible" 
      title="测试截图" 
      width="90%"
      top="5vh"
    >
      <div v-if="selectedScreenshots.length > 0" class="screenshot-gallery">
        <el-carousel height="500px" indicator-position="outside">
          <el-carousel-item v-for="(screenshot, index) in selectedScreenshots" :key="index">
            <div class="screenshot-item">
              <img :src="screenshot.path" :alt="screenshot.name" />
              <p class="screenshot-caption">{{ screenshot.name }}</p>
            </div>
          </el-carousel-item>
        </el-carousel>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DataBoard, VideoPlay, Refresh, Check, Close, Document, TrendCharts,
  Warning, View, Picture
} from '@element-plus/icons-vue'

// API基础URL - 修复404错误：使用3002端口 (更新于2025-09-11)
const API_BASE_URL = 'http://localhost:3002/api/test'

// 响应式数据
const isRunning = ref(false)
const isRefreshing = ref(false)
const isLoading = ref(false)
const filterCategory = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const detailDialogVisible = ref(false)
const screenshotDialogVisible = ref(false)
const selectedTest = ref(null)
const selectedScreenshots = ref([])

// 新增：模式切换相关
const isRealMode = ref(false)
const testExecutionStatus = ref({
  isRunning: false,
  progress: 0,
  currentTest: '',
  startTime: null
})

// 测试概览数据
const testOverview = reactive({
  totalTests: 0,
  totalPassed: 0,
  totalFailed: 0,
  successRate: 0
})

// 测试分类数据
const testCategories = ref([])

// 详细测试结果
const testResults = ref([])

// API调用方法
const fetchData = async (url, options = {}) => {
  try {
    // 添加时间戳避免缓存
    const timestamp = new Date().getTime()
    const separator = url.includes('?') ? '&' : '?'
    const fullUrl = `${API_BASE_URL}${url}${separator}_t=${timestamp}`
    
    const response = await fetch(fullUrl, {
      headers: {
        'Content-Type': 'application/json',
      },
      ...options
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const result = await response.json()
    if (!result.success) {
      throw new Error(result.error || 'API调用失败')
    }
    
    return result.data
  } catch (error) {
    console.error('API调用失败:', error)
    ElMessage.error('数据获取失败: ' + error.message)
    throw error
  }
}

// 加载测试概览数据
const loadTestOverview = async () => {
  try {
    const data = await fetchData('/overview')
    Object.assign(testOverview, data)
  } catch (error) {
    // 使用默认数据
    console.warn('使用默认概览数据')
  }
}

// 加载测试分类数据
const loadTestCategories = async () => {
  try {
    const data = await fetchData('/categories')
    testCategories.value = data
  } catch (error) {
    // 使用默认数据
    testCategories.value = [
      {
        id: 'data-integrity',
        name: '数据完整性验证',
        testCount: 0,
        passedTests: 0,
        failedTests: 0,
        successRate: 0
      },
      {
        id: 'navigation',
        name: '导航功能测试',
        testCount: 0,
        passedTests: 0,
        failedTests: 0,
        successRate: 0
      }
    ]
    console.warn('使用默认分类数据')
  }
}

// 加载测试结果数据
const loadTestResults = async () => {
  try {
    const params = new URLSearchParams({
      page: currentPage.value,
      pageSize: pageSize.value,
      ...(filterCategory.value && { category: getCategoryName(filterCategory.value) }),
      ...(filterStatus.value && { status: filterStatus.value })
    })
    
    const data = await fetchData(`/results?${params}`)
    testResults.value = data.results || []
  } catch (error) {
    testResults.value = []
    console.warn('使用默认测试结果数据')
  }
}

// 计算属性
const filteredTestResults = computed(() => {
  let filtered = testResults.value

  if (filterCategory.value) {
    filtered = filtered.filter(test => 
      test.category === getCategoryName(filterCategory.value)
    )
  }

  if (filterStatus.value) {
    filtered = filtered.filter(test => test.status === filterStatus.value)
  }

  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filtered.slice(start, end)
})

// 新增：模式切换方法
const handleModeChange = async (value) => {
  try {
    const mode = value ? 'real' : 'mock'
    await fetchData('/mode', {
      method: 'POST',
      body: JSON.stringify({ mode })
    })
    
    ElMessage.success(`已切换到${value ? '真实测试' : '模拟数据'}模式`)
    
    // 刷新数据
    await refreshData()
  } catch (error) {
    ElMessage.error('模式切换失败: ' + error.message)
    // 恢复先前状态
    isRealMode.value = !value
  }
}

// 加载当前模式
const loadCurrentMode = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/mode`)
    const result = await response.json()
    if (result.success) {
      isRealMode.value = result.currentMode === 'real'
      testExecutionStatus.value.isRunning = result.isRunning || false
    }
  } catch (error) {
    console.warn('无法获取当前模式，使用默认设置')
  }
}

// 方法
const runAllTests = async () => {
  isRunning.value = true
  try {
    ElMessage.info('开始执行所有测试...')
    
    await fetchData('/run-all', {
      method: 'POST',
      body: JSON.stringify({
        parallel: false,
        maxConcurrency: 3
      })
    })
    
    ElMessage.success('测试执行已开始，请稍后刷新查看结果')
    
    // 等待一段时间后自动刷新数据
    setTimeout(async () => {
      await refreshData()
    }, 5000)
    
  } catch (error) {
    ElMessage.error('测试执行失败: ' + error.message)
  } finally {
    isRunning.value = false
  }
}

const refreshData = async () => {
  isRefreshing.value = true
  try {
    // 刷新所有数据
    await Promise.all([
      loadTestOverview(),
      loadTestCategories(),
      loadTestResults()
    ])
    
    // 如果需要，也可以调用后端刷新接口
    await fetchData('/refresh', { method: 'POST' })
    
    ElMessage.success('数据刷新成功')
  } catch (error) {
    ElMessage.error('数据刷新失败: ' + error.message)
  } finally {
    isRefreshing.value = false
  }
}

const runSingleTest = async (test) => {
  try {
    ElMessage.info(`开始执行测试: ${test.name}`)
    
    const result = await fetchData('/run-single', {
      method: 'POST',
      body: JSON.stringify({
        testFile: test.filePath
      })
    })
    
    ElMessage.success('测试执行完成')
    
    // 刷新测试结果
    await loadTestResults()
    
  } catch (error) {
    ElMessage.error('测试执行失败: ' + error.message)
  }
}

const viewTestDetails = (test) => {
  selectedTest.value = test
  detailDialogVisible.value = true
}

const viewScreenshots = (test) => {
  selectedScreenshots.value = test.screenshots || []
  screenshotDialogVisible.value = true
}

const viewCategoryDetails = (category) => {
  filterCategory.value = category.id
  filterStatus.value = ''
}

const handlePageChange = (page) => {
  currentPage.value = page
}

// 工具方法
const getProgressColor = (percentage) => {
  if (percentage >= 90) return '#67c23a'
  if (percentage >= 70) return '#e6a23c'
  return '#f56c6c'
}

const getCategoryTagType = (category) => {
  const typeMap = {
    '数据完整性验证': 'primary',
    '导航功能测试': 'success',
    'API连接状态验证': 'info',
    '用户界面元素检查': 'warning',
    '交互功能测试': '',
    '表单验证测试': 'success',
    '端到端用户流程': 'primary',
    '质量标准和错误处理': 'danger'
  }
  return typeMap[category] || ''
}

const getCategoryName = (categoryId) => {
  const category = testCategories.value.find(c => c.id === categoryId)
  return category ? category.name : ''
}

const getStatusText = (status) => {
  const statusMap = {
    'passed': '通过',
    'failed': '失败',
    'skipped': '跳过'
  }
  return statusMap[status] || '未知'
}

const formatDuration = (duration) => {
  if (duration < 1000) return `${duration}ms`
  return `${(duration / 1000).toFixed(1)}s`
}

const formatTime = (time) => {
  return new Date(time).toLocaleString('zh-CN')
}

// 生命周期
onMounted(async () => {
  isLoading.value = true
  try {
    // 先加载当前模式
    await loadCurrentMode()
    // 然后加载数据
    await refreshData()
  } finally {
    isLoading.value = false
  }
})
</script>

<style scoped>
.test-dashboard {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.mode-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.mode-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
  min-width: 60px;
}

.overview-section {
  margin-bottom: 24px;
}

.overview-card {
  border: none;
  border-radius: 8px;
  overflow: hidden;
}

.overview-card.success {
  background: linear-gradient(135deg, #67c23a, #85ce61);
  color: white;
}

.overview-card.danger {
  background: linear-gradient(135deg, #f56c6c, #f78989);
  color: white;
}

.overview-card.info {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: white;
}

.overview-card.warning {
  background: linear-gradient(135deg, #e6a23c, #ebb563);
  color: white;
}

.card-content {
  display: flex;
  align-items: center;
  padding: 20px;
}

.card-icon {
  font-size: 32px;
  margin-right: 16px;
  opacity: 0.8;
}

.card-info h3 {
  margin: 0 0 4px 0;
  font-size: 28px;
  font-weight: bold;
}

.card-info p {
  margin: 0;
  font-size: 14px;
  opacity: 0.9;
}

.categories-section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h2 {
  margin: 0;
  color: #303133;
}

.header-filters {
  display: flex;
  gap: 12px;
}

.category-card {
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 16px;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
}

.category-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.category-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.category-header h3 {
  margin: 0;
  color: #303133;
  font-size: 16px;
}

.category-progress {
  margin-bottom: 12px;
}

.category-stats {
  display: flex;
  gap: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
  font-size: 14px;
}

.results-section {
  margin-bottom: 24px;
}

.test-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-icon.success {
  color: #67c23a;
}

.status-icon.danger {
  color: #f56c6c;
}

.status-icon.warning {
  color: #e6a23c;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.test-detail {
  padding: 16px 0;
}

.test-logs,
.test-error {
  margin-top: 20px;
}

.test-logs h4,
.test-error h4 {
  margin-bottom: 12px;
  color: #303133;
}

.log-textarea {
  font-family: 'Consolas', 'Monaco', monospace;
}

.screenshot-gallery {
  text-align: center;
}

.screenshot-item img {
  max-width: 100%;
  max-height: 450px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.screenshot-caption {
  margin-top: 12px;
  color: #606266;
  font-size: 14px;
}
</style>