<template>
  <div class="clusters-management">
    <!-- 页面标题和操作栏 -->
    <div class="header-section">
      <div class="title-section">
        <h1>集群管理</h1>
        <p>管理和监控您的 Hive/CDP 集群</p>
      </div>
      <div class="actions-section">
        <el-dropdown @command="handleTemplate">
          <el-button class="cloudera-btn secondary">
            配置模板
            <el-icon><CaretBottom /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="cdp">CDP 集群模板</el-dropdown-item>
              <el-dropdown-item command="cdh">CDH 集群模板</el-dropdown-item>
              <el-dropdown-item command="hdp">HDP 集群模板</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-switch
          v-model="strictReal"
          active-text="严格实连"
          inactive-text="允许Mock"
        />
        <el-button
          @click="showCreateDialog = true"
          class="cloudera-btn primary"
        >
          <el-icon><Plus /></el-icon>
          添加集群
        </el-button>
      </div>
    </div>

    <!-- 集群列表组件 -->
    <ClusterList
      :clusters="clusters"
      :loading="loading"
      :cluster-stats="clusterStats"
      :connection-status="connectionStatus"
      :search-text="searchText"
      :status-filter="statusFilter"
      :redirect-url="redirectUrl"
      @enter-cluster="enterCluster"
      @create-cluster="showCreateDialog = true"
      @test-connection="handleTestConnection"
      @edit-cluster="editCluster"
      @cluster-action="handleClusterAction"
      @test-specific-connection="handleTestSpecificConnection"
    />

    <!-- 集群表单组件 -->
    <ClusterForm
      v-model:visible="showCreateDialog"
      :editing-cluster="editingCluster"
      :testing-config="testingConfig"
      @save-cluster="saveCluster"
      @test-connection-config="testConfigConnection"
    />

    <!-- 连接管理组件 -->
    <ClusterConnectionManager
      ref="connectionManagerRef"
      :clusters="clusters"
      @update-connection-status="updateConnectionStatus"
    />

    <!-- 扫描进度对话框 -->
    <ScanProgressDialog
      v-model="showProgress"
      :task-id="currentTaskId || undefined"
    />
  </div>
</template>

<script setup lang="ts">
  import { ref, onMounted, computed } from 'vue'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { useRouter } from 'vue-router'
  import { CaretBottom, Plus } from '@element-plus/icons-vue'
  import { clustersApi, type Cluster, type ClusterCreate } from '@/api/clusters'
  import { tablesApi } from '@/api/tables'
  import { useMonitoringStore } from '@/stores/monitoring'

  // 组件导入
  import ClusterList from '@/components/cluster/ClusterList.vue'
  import ClusterForm from '@/components/cluster/ClusterForm.vue'
  import ClusterConnectionManager from '@/components/cluster/ClusterConnectionManager.vue'
  import ScanProgressDialog from '@/components/ScanProgressDialog.vue'

  const router = useRouter()
  const monitoringStore = useMonitoringStore()
  const connectionManagerRef = ref()

  // 检查是否有重定向参数
  const redirectUrl = ref((router.currentRoute.value.query.redirect as string) || '')

  // 数据状态
  const clusters = ref<Cluster[]>([])
  const loading = ref(false)
  const showCreateDialog = ref(false)
  const showProgress = ref(false)
  const currentTaskId = ref<string | null>(null)
  const strictReal = ref(true)
  const editingCluster = ref<Cluster | null>(null)
  const testingConfig = ref(false)
  const searchText = ref('')
  const statusFilter = ref('')

  // 集群统计数据
  const clusterStats = ref<Record<number, any>>({})

  // 连接状态数据
  const connectionStatus = ref<Record<number, any>>({})

  // 计算属性
  const totalClusters = computed(() => clusters.value.length)
  const onlineClusters = computed(() => clusters.value.filter(c => c.status === 'active').length)
  const totalTables = computed(() =>
    Object.values(clusterStats.value).reduce((sum, stat) => sum + (stat.tables || 0), 0)
  )
  const pendingTasks = computed(() =>
    Object.values(clusterStats.value).reduce((sum, stat) => sum + (stat.pending_tasks || 0), 0)
  )

  // 数据加载方法
  const loadClusters = async () => {
    loading.value = true
    try {
      clusters.value = await clustersApi.list()
      await loadClusterStats()
    } catch (error) {
      console.error('Failed to load clusters:', error)
    } finally {
      loading.value = false
    }
  }

  const loadClusterStats = async () => {
    const stats: Record<number, any> = {}

    for (const cluster of clusters.value) {
      try {
        const clusterStatsData = await clustersApi.getStats(cluster.id)
        stats[cluster.id] = {
          databases: clusterStatsData.total_databases,
          tables: clusterStatsData.total_tables,
          small_files: clusterStatsData.total_small_files,
          pending_tasks: 0
        }
      } catch (error) {
        console.error(`Failed to load stats for cluster ${cluster.id}:`, error)
        stats[cluster.id] = {
          databases: 0,
          tables: 0,
          small_files: 0,
          pending_tasks: 0
        }
      }
    }

    clusterStats.value = stats
  }

  // 集群操作方法
  const enterCluster = (clusterId: number) => {
    if (redirectUrl.value) {
      selectClusterAndRedirect(clusterId)
    } else {
      router.push(`/clusters/${clusterId}`)
    }
  }

  const selectClusterAndRedirect = async (clusterId: number) => {
    try {
      monitoringStore.setSelectedCluster(clusterId)
      const targetUrl = decodeURIComponent(redirectUrl.value)
      ElMessage.success('集群选择成功，正在跳转...')
      router.push(targetUrl)
    } catch (error) {
      console.error('Failed to select cluster:', error)
      ElMessage.error('集群选择失败')
    }
  }

  const editCluster = (cluster: Cluster) => {
    editingCluster.value = cluster
    showCreateDialog.value = true
  }

  const handleClusterAction = (command: string, cluster: Cluster) => {
    if (command === 'delete') {
      deleteCluster(cluster)
    }
  }

  const deleteCluster = async (cluster: Cluster) => {
    try {
      await ElMessageBox.confirm(
        `确定要删除集群 "${cluster.name}" 吗？此操作不可恢复。`,
        '确认删除',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )

      await clustersApi.delete(cluster.id)
      ElMessage.success('集群删除成功')
      loadClusters()
    } catch (error) {
      if (error !== 'cancel') {
        console.error('Failed to delete cluster:', error)
      }
    }
  }

  const saveCluster = async (data: {
    form: ClusterCreate
    validateConnection: boolean
    isEdit: boolean
    clusterId?: number
  }) => {
    try {
      if (data.isEdit && data.clusterId) {
        await clustersApi.update(data.clusterId, data.form)
        ElMessage.success('集群更新成功')
      } else {
        if (data.validateConnection) {
          await clustersApi.createWithValidation(data.form)
          ElMessage.success('集群创建成功（已验证连接）')
        } else {
          await clustersApi.create(data.form)
          ElMessage.success('集群创建成功')
        }
      }

      showCreateDialog.value = false
      editingCluster.value = null
      loadClusters()
    } catch (error: any) {
      console.error('Failed to save cluster:', error)
      const errorMsg = error.response?.data?.detail || error.message || '保存失败'
      ElMessage.error(errorMsg)
    }
  }

  // 模板处理
  const handleTemplate = (command: string) => {
    // 模板逻辑移到ClusterForm组件内部处理
    showCreateDialog.value = true
    // 可以通过事件通知表单组件应用模板
  }

  // 扫描相关
  const startClusterScan = async (clusterId: number) => {
    try {
      const res = await tablesApi.scanAllDatabases(clusterId, strictReal.value)
      if (res && res.task_id) {
        currentTaskId.value = res.task_id
        showProgress.value = true
      } else {
        ElMessage.error('未获取到任务ID，无法追踪进度')
      }
    } catch (e) {
      console.error('Failed to start cluster scan:', e)
      ElMessage.error('启动集群扫描失败')
    }
  }

  // 连接测试方法
  const handleTestConnection = (cluster: Cluster, mode: string) => {
    connectionManagerRef.value?.testConnection(cluster, mode)
  }

  const handleTestSpecificConnection = (clusterId: number, service: string) => {
    connectionManagerRef.value?.testSpecificConnection(clusterId, service)
  }

  const testConfigConnection = (config: ClusterCreate) => {
    testingConfig.value = true
    connectionManagerRef.value?.testConfigConnection(config)
    testingConfig.value = false
  }

  const updateConnectionStatus = (status: Record<number, any>) => {
    connectionStatus.value = status
  }

  onMounted(async () => {
    await loadClusters()
  })
</script>

<style scoped>
  .clusters-management {
    padding: var(--space-3) var(--space-4) 400px var(--space-4);
    min-height: 150vh;
    background: var(--bg-app);
    overflow-y: visible;
  }

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
    .clusters-management {
      padding: var(--space-4);
    }

    .header-section {
      flex-direction: column;
      gap: var(--space-4);
      text-align: center;
    }
  }
</style>
