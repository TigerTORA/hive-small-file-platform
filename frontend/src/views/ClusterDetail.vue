<template>
  <div class="cluster-detail">
    <!-- Cluster Header -->
    <el-card class="cluster-header">
      <div class="header-content">
        <div class="cluster-info">
          <el-button
            type="text"
            @click="$router.push('/clusters')"
            class="back-button"
          >
            <el-icon><ArrowLeft /></el-icon>
            返回集群列表
          </el-button>
          <div class="cluster-title">
            <h2>{{ cluster?.name || `集群 ${$route.params.id}` }}</h2>
            <el-tag
              :type="cluster?.status === 'active' ? 'success' : 'danger'"
              size="large"
            >
              {{ cluster?.status === 'active' ? '正常' : '异常' }}
            </el-tag>
          </div>
          <div
            class="cluster-meta"
            v-if="cluster"
          >
            <span>Hive: {{ cluster.hive_host }}:{{ cluster.hive_port }}</span>
            <span>HDFS: {{ cluster.hdfs_namenode_url }}</span>
          </div>
        </div>
        <div class="header-actions">
          <el-button @click="testConnection">
            <el-icon><Connection /></el-icon>
            测试连接
          </el-button>
          <el-button
            type="primary"
            @click="showScanDialog = true"
          >
            <el-icon><Search /></el-icon>
            扫描数据库
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- Statistics Overview -->
    <div class="stats-grid">
      <el-card>
        <el-statistic
          title="总数据库数"
          :value="stats.total_databases"
          suffix="个"
        >
          <template #prefix>
            <el-icon style="color: #409eff"><Grid /></el-icon>
          </template>
        </el-statistic>
      </el-card>

      <el-card>
        <el-statistic
          title="总表数"
          :value="stats.total_tables"
          suffix="张"
        >
          <template #prefix>
            <el-icon style="color: #67c23a"><Grid /></el-icon>
          </template>
        </el-statistic>
      </el-card>

      <el-card>
        <el-statistic
          title="小文件表数"
          :value="stats.small_file_tables"
          suffix="张"
        >
          <template #prefix>
            <el-icon style="color: #e6a23c"><Warning /></el-icon>
          </template>
        </el-statistic>
      </el-card>

      <el-card>
        <el-statistic
          title="小文件总数"
          :value="stats.total_small_files"
          suffix="个"
        >
          <template #prefix>
            <el-icon style="color: #f56c6c"><Document /></el-icon>
          </template>
        </el-statistic>
      </el-card>
    </div>

    <!-- Main Content Tabs -->
    <el-card class="main-content">
      <el-tabs
        v-model="activeTab"
        type="border-card"
      >
        <el-tab-pane
          label="表管理"
          name="tables"
        >
          <TablesView :cluster-id="clusterId" />
        </el-tab-pane>

        <el-tab-pane
          label="任务管理"
          name="tasks"
        >
          <TasksView :cluster-id="clusterId" />
        </el-tab-pane>

        <el-tab-pane
          label="小文件分析"
          name="analysis"
        >
          <SmallFilesAnalysis :cluster-id="clusterId" />
        </el-tab-pane>

        <el-tab-pane
          label="设置"
          name="settings"
        >
          <ClusterSettings
            :cluster-id="clusterId"
            @updated="loadClusterInfo"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- Scan Database Dialog -->
    <el-dialog
      v-model="showScanDialog"
      title="扫描数据库"
      width="500px"
    >
      <el-form
        :model="scanForm"
        label-width="100px"
      >
        <el-form-item label="扫描模式">
          <el-radio-group v-model="scanForm.mode">
            <el-radio value="all">扫描所有数据库</el-radio>
            <el-radio value="single">扫描指定数据库</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          label="数据库名"
          v-if="scanForm.mode === 'single'"
        >
          <el-select
            v-model="scanForm.database"
            placeholder="选择数据库"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="db in availableDatabases"
              :key="db"
              :label="db"
              :value="db"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showScanDialog = false">取消</el-button>
          <el-button
            type="primary"
            @click="startScan"
            :loading="scanning"
          >
            开始扫描
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Connection Test Dialog -->
    <ConnectionTestDialog
      v-model:visible="showTestDialog"
      :cluster-config="cluster"
      :test-result="testResult"
      :testing="testingConnection"
      :error="testError"
      @retest="handleRetest"
    />

    <!-- 统一任务执行详情（扫描） -->
    <TaskRunDialog
      v-model="showProgressDialog"
      type="scan"
      :scan-task-id="currentScanTaskId || undefined"
    />
  </div>
</template>

<script setup lang="ts">
  import { ref, computed, onMounted } from 'vue'
  import { useRoute } from 'vue-router'
  import { ElMessage } from 'element-plus'
  import { ArrowLeft, Connection, Search, Grid, Warning, Document } from '@element-plus/icons-vue'
  import { clustersApi, type Cluster } from '@/api/clusters'
  import { tablesApi } from '@/api/tables'
  import ConnectionTestDialog from '@/components/ConnectionTestDialog.vue'
  import TaskRunDialog from '@/components/TaskRunDialog.vue'
  import TablesView from '@/components/TablesView.vue'
  import TasksView from '@/components/TasksView.vue'
  import SmallFilesAnalysis from '@/components/SmallFilesAnalysis.vue'
  import ClusterSettings from '@/components/ClusterSettings.vue'

  // Router and props
  const route = useRoute()
  const clusterId = computed(() => parseInt(route.params.id as string))

  // Data
  const cluster = ref<Cluster | null>(null)
  const activeTab = ref('tables')
  const loading = ref(false)

  // Statistics
  const stats = ref({
    total_databases: 0,
    total_tables: 0,
    small_file_tables: 0,
    total_small_files: 0
  })

  // Scan dialog
  const showScanDialog = ref(false)
  const scanning = ref(false)
  const showProgressDialog = ref(false)
  const currentScanTaskId = ref<string | null>(null)
  const scanForm = ref({
    mode: 'all',
    database: ''
  })
  const availableDatabases = ref<string[]>([])

  // Connection test
  const showTestDialog = ref(false)
  const testingConnection = ref(false)
  const testResult = ref<any>(null)
  const testError = ref<string | null>(null)

  // Methods
  const loadClusterInfo = async () => {
    loading.value = true
    try {
      cluster.value = await clustersApi.get(clusterId.value)
      await loadStats()
      await loadDatabases()
    } catch (error) {
      console.error('Failed to load cluster info:', error)
      ElMessage.error('加载集群信息失败')
    } finally {
      loading.value = false
    }
  }

  const loadStats = async () => {
    try {
      // Load cluster statistics
      const response = await tablesApi.getClusterStats(clusterId.value)
      stats.value = response
    } catch (error: any) {
      console.error('Failed to load stats:', error)
      // 如果统计加载失败，使用默认值
      stats.value = {
        total_databases: 0,
        total_tables: 0,
        small_file_tables: 0,
        total_small_files: 0
      }
      const errorMsg = error.response?.data?.detail || error.message || '加载统计数据失败'
      ElMessage.warning(`统计数据加载失败: ${errorMsg}`)
    }
  }

  const loadDatabases = async () => {
    try {
      const databases = await tablesApi.getDatabases(clusterId.value)
      availableDatabases.value = databases
    } catch (error: any) {
      console.error('Failed to load databases:', error)
      availableDatabases.value = []
      const errorMsg = error.response?.data?.detail || error.message || '加载数据库列表失败'
      ElMessage.warning(`数据库列表加载失败: ${errorMsg}`)
    }
  }

  const testConnection = async () => {
    if (!cluster.value) return

    testResult.value = null
    testError.value = null
    testingConnection.value = true
    showTestDialog.value = true

    try {
      const result = await clustersApi.testConnection(cluster.value.id, 'real')
      testResult.value = result
    } catch (error: any) {
      console.error('Failed to test connection:', error)
      testError.value = error.response?.data?.detail || error.message || '测试失败'
    } finally {
      testingConnection.value = false
    }
  }

  const handleRetest = async () => {
    if (!cluster.value) return
    await testConnection()
  }

  const startScan = async () => {
    scanning.value = true
    try {
      let response
      if (scanForm.value.mode === 'all') {
        response = await tablesApi.scanAllDatabases(clusterId.value)
      } else {
        response = await tablesApi.scanDatabase(clusterId.value, scanForm.value.database)
      }

      // 获取任务ID并显示进度对话框
      if (response?.task_id) {
        currentScanTaskId.value = response.task_id
        showScanDialog.value = false
        showProgressDialog.value = true
        ElMessage.success('扫描任务已启动，正在显示实时进度...')
      } else {
        // 兼容旧版本API响应
        ElMessage.success('扫描任务已启动，请稍等...')
        showScanDialog.value = false
      }
    } catch (error: any) {
      console.error('Failed to start scan:', error)
      const errorMsg = error.response?.data?.detail || error.message || '扫描启动失败'
      ElMessage.error(errorMsg)
    } finally {
      scanning.value = false
    }
  }

  const onScanCompleted = (taskId: string) => {
    // 扫描完成后刷新统计信息
    loadStats()
    loadDatabases()
    ElMessage.success('扫描任务完成！统计信息已更新')
  }

  onMounted(() => {
    loadClusterInfo()
  })
</script>

<style scoped>
  .cluster-detail {
    padding: 20px;
    max-width: 1400px;
    margin: 0 auto;
  }

  .cluster-header {
    margin-bottom: 20px;
  }

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .back-button {
    margin-bottom: 10px;
    padding: 4px 8px;
    font-size: 14px;
  }

  .cluster-title {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 10px;
  }

  .cluster-title h2 {
    margin: 0;
    color: #303133;
  }

  .cluster-meta {
    display: flex;
    flex-direction: column;
    gap: 5px;
    color: #909399;
    font-size: 14px;
  }

  .header-actions {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
  }

  .stats-grid .el-card {
    text-align: center;
  }

  .main-content {
    min-height: 600px;
  }

  .main-content :deep(.el-tabs__content) {
    padding: 20px;
  }

  .dialog-footer {
    text-align: right;
  }

  @media (max-width: 768px) {
    .cluster-detail {
      padding: 10px;
    }

    .header-content {
      flex-direction: column;
      gap: 15px;
    }

    .stats-grid {
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
    }
  }
</style>
