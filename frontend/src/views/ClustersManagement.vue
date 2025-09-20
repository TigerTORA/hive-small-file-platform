<template>
  <div class="clusters-management">
    <el-alert
      v-if="loadError"
      :title="'加载集群失败：' + loadError"
      type="error"
      show-icon
      style="margin-bottom: 12px"
    >
      <template #default>
        <el-button size="small" class="cloudera-btn secondary" @click="reloadClusters">重试</el-button>
      </template>
    </el-alert>
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

    <!-- 集群卡片列表 -->
    <div
      v-loading="loading"
      class="clusters-grid"
    >
      <div
        v-if="filteredClusters.length === 0 && !loading"
        class="empty-state"
      >
        <el-empty description="暂无集群数据">
          <el-button
            type="primary"
            @click="showCreateDialog = true"
          >
            添加第一个集群
          </el-button>
        </el-empty>
      </div>

      <div
        v-for="cluster in filteredClusters"
        :key="cluster.id"
        class="cloudera-metric-card cluster-card hover-lift"
        @click="enterCluster(cluster.id)"
        :class="{ 'cluster-online': cluster.status === 'active' }"
      >
        <div class="cluster-header">
          <div class="cluster-title-section">
            <div class="cluster-name-row">
              <h3 class="cluster-name">{{ cluster.name }}</h3>
              <ConnectionStatusIndicator
                :hiveserver-status="getConnectionStatus(cluster.id, 'hiveserver')"
                :hdfs-status="getConnectionStatus(cluster.id, 'hdfs')"
                :metastore-status="getConnectionStatus(cluster.id, 'metastore')"
                :loading="isLoadingConnectionStatus(cluster.id)"
                @test-connection="service => testSpecificConnection(cluster.id, service)"
              />
            </div>
            <p class="cluster-description">
              {{ cluster.description || 'Cloudera Data Platform 集群' }}
            </p>
          </div>
          <div
            class="cluster-actions"
            @click.stop
          >
            <el-tooltip
              content="进入集群详情"
              placement="top"
            >
              <el-button
                size="small"
                circle
                @click="enterCluster(cluster.id)"
                class="cloudera-btn primary"
              >
                <el-icon><Right /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </div>

        <div class="cluster-content">
          <div class="cluster-info-compact">
            <div class="cluster-details">
              <div class="detail-item">
                <el-icon><Monitor /></el-icon>
                <span>{{ cluster.hive_host }}:{{ cluster.hive_port }}</span>
              </div>
            </div>
          </div>

          <div class="cluster-stats-compact">
            <div class="stats-row">
              <div class="stat-item">
                <span class="stat-value">{{ getClusterStat(cluster.id, 'databases') }}</span>
                <span class="stat-label">数据库</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{ getClusterStat(cluster.id, 'tables') }}</span>
                <span class="stat-label">表数量</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{ getClusterStat(cluster.id, 'small_files') }}</span>
                <span class="stat-label">小文件</span>
              </div>
            </div>
          </div>

          <div
            class="cluster-operations"
            @click.stop
          >
            <el-button
              size="small"
              @click="testConnection(cluster, 'enhanced')"
              class="cloudera-btn secondary"
            >
              <el-icon><Connection /></el-icon>
              连接测试
            </el-button>
            <el-button
              size="small"
              @click="editCluster(cluster)"
              class="cloudera-btn secondary"
            >
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-dropdown
              @command="command => handleClusterAction(command, cluster)"
              trigger="click"
            >
              <el-button
                size="small"
                class="cloudera-btn secondary"
              >
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    command="delete"
                    class="danger-item"
                  >
                    <el-icon><Delete /></el-icon>
                    删除集群
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingCluster ? '编辑集群' : '添加集群'"
      width="600px"
    >
      <el-form
        :model="clusterForm"
        :rules="clusterRules"
        ref="clusterFormRef"
        label-width="140px"
      >
        <el-form-item
          label="使用模板"
          v-if="!editingCluster"
        >
          <el-select
            v-model="selectedTemplate"
            placeholder="选择配置模板"
            @change="applyTemplate"
            clearable
          >
            <el-option
              label="CDP 集群"
              value="cdp"
            />
            <el-option
              label="CDH 集群"
              value="cdh"
            />
            <el-option
              label="HDP 集群"
              value="hdp"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="集群名称"
          prop="name"
        >
          <el-input
            v-model="clusterForm.name"
            placeholder="请输入集群名称"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="clusterForm.description"
            type="textarea"
            placeholder="集群描述（可选）"
          />
        </el-form-item>
        <el-form-item
          label="Hive 主机"
          prop="hive_host"
        >
          <el-input
            v-model="clusterForm.hive_host"
            placeholder="Hive Server2 主机地址"
          />
        </el-form-item>
        <el-form-item label="Hive 端口">
          <el-input-number
            v-model="clusterForm.hive_port"
            :min="1"
            :max="65535"
          />
        </el-form-item>
        <el-form-item
          label="MetaStore URL"
          prop="hive_metastore_url"
        >
          <el-input
            v-model="clusterForm.hive_metastore_url"
            placeholder="postgresql://user:pass@host:5432/hive"
          />
        </el-form-item>
        <el-form-item
          label="HDFS/HttpFS 地址"
          prop="hdfs_namenode_url"
        >
          <el-input
            v-model="clusterForm.hdfs_namenode_url"
            placeholder="http://httpfs:14000/webhdfs/v1"
          />
          <div style="font-size: 12px; color: #909399; margin-top: 4px">
            <div style="margin-bottom: 2px"><strong>支持的地址格式:</strong></div>
            <div>• HttpFS (推荐): http://httpfs-host:14000/webhdfs/v1</div>
            <div>• WebHDFS: http://namenode:9870/webhdfs/v1</div>
            <div>• HDFS URI: hdfs://nameservice 或 hdfs://namenode:8020</div>
          </div>
        </el-form-item>
        <el-form-item label="HDFS 用户">
          <el-input
            v-model="clusterForm.hdfs_user"
            placeholder="hdfs"
          />
        </el-form-item>

        <!-- Hive 认证配置 -->
        <el-divider content-position="left">
          <span style="color: #606266; font-weight: 500">Hive 认证配置</span>
        </el-divider>

        <el-form-item label="认证类型">
          <el-select
            v-model="clusterForm.auth_type"
            placeholder="选择认证类型"
            @change="onAuthTypeChange"
          >
            <el-option
              label="无认证 (NONE)"
              value="NONE"
            />
            <el-option
              label="LDAP 认证"
              value="LDAP"
            />
          </el-select>
        </el-form-item>

        <template v-if="clusterForm.auth_type === 'LDAP'">
          <el-form-item
            label="Hive 用户名"
            prop="hive_username"
          >
            <el-input
              v-model="clusterForm.hive_username"
              placeholder="LDAP 用户名"
            />
          </el-form-item>
          <el-form-item
            label="Hive 密码"
            prop="hive_password"
          >
            <el-input
              v-model="clusterForm.hive_password"
              type="password"
              placeholder="LDAP 密码"
              show-password
            />
            <div style="font-size: 12px; color: #909399; margin-top: 4px">密码将被安全加密存储</div>
          </el-form-item>
        </template>

        <!-- YARN 监控配置 -->
        <el-divider content-position="left">
          <span style="color: #606266; font-weight: 500">YARN 监控配置</span>
        </el-divider>

        <el-form-item label="Resource Manager">
          <el-input
            v-model="clusterForm.yarn_resource_manager_url"
            placeholder="http://rm1:8088,http://rm2:8088"
          />
          <div style="font-size: 12px; color: #909399; margin-top: 4px">
            <div>支持 HA 配置，多个地址用逗号分隔</div>
            <div>示例: http://192.168.0.106:8088,http://192.168.0.107:8088</div>
          </div>
        </el-form-item>

        <el-form-item label="小文件阈值">
          <el-input-number
            v-model="clusterForm.small_file_threshold"
            :min="1024"
            :step="1024 * 1024"
          />
          <span style="margin-left: 8px; color: #909399">字节 (默认: 128MB)</span>
        </el-form-item>

        <el-form-item
          label="创建选项"
          v-if="!editingCluster"
        >
          <el-checkbox v-model="validateConnection"> 创建前验证连接 </el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button
            type="info"
            @click="testConfigConnection"
            :loading="testingConfig"
            v-if="!editingCluster"
          >
            测试连接
          </el-button>
          <el-button
            type="primary"
            @click="saveCluster"
          >
            {{ editingCluster ? '更新' : '创建' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 连接测试对话框 -->
    <ConnectionTestDialog
      v-model:visible="showTestDialog"
      :cluster-config="currentTestConfig"
      :test-result="testResult"
      :testing="testingConnection"
      :error="testError"
      @retest="handleRetest"
    />
    <!-- 统一任务执行详情（扫描） -->
    <TaskRunDialog
      v-model="showProgress"
      type="scan"
      :scan-task-id="currentTaskId || undefined"
    />
  </div>
</template>

<script setup lang="ts">
  import { ref, onMounted, onUnmounted, computed } from 'vue'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { useRouter } from 'vue-router'
  import {
    CaretBottom,
    Plus,
    Monitor,
    CircleCheckFilled,
    Grid,
    Clock,
    Search,
    Refresh,
    Right,
    Connection,
    Edit,
    Delete,
    MoreFilled
  } from '@element-plus/icons-vue'
  import { clustersApi, type Cluster, type ClusterCreate } from '@/api/clusters'
  import { useMonitoringStore } from '@/stores/monitoring'
  import ConnectionTestDialog from '@/components/ConnectionTestDialog.vue'
  import TaskRunDialog from '@/components/TaskRunDialog.vue'
  import ConnectionStatusIndicator from '@/components/ConnectionStatusIndicator.vue'
  import { tablesApi } from '@/api/tables'
  import dayjs from 'dayjs'

  const router = useRouter()
  const monitoringStore = useMonitoringStore()

  // 数据
  const clusters = ref<Cluster[]>([])
  const loading = ref(false)
  const loadError = ref<string | null>(null)
  const showCreateDialog = ref(false)
  const showProgress = ref(false)
  const currentTaskId = ref<string | null>(null)
  const strictReal = ref(true)
  const editingCluster = ref<Cluster | null>(null)
  const selectedTemplate = ref('')
  const validateConnection = ref(false)
  const searchText = ref('')
  const statusFilter = ref('')

  // 集群统计数据
  const clusterStats = ref<Record<number, any>>({})

  // 连接状态数据
  const connectionStatus = ref<
    Record<
      number,
      {
        hiveserver?: {
          status: 'success' | 'error' | 'unknown' | 'testing'
          message?: string
          mode?: string
        }
        hdfs?: {
          status: 'success' | 'error' | 'unknown' | 'testing'
          message?: string
          mode?: string
        }
        metastore?: {
          status: 'success' | 'error' | 'unknown' | 'testing'
          message?: string
          mode?: string
        }
        loading?: boolean
        lastChecked?: Date
      }
    >
  >({})

  // 状态检查定时器
  let statusCheckInterval: NodeJS.Timeout | null = null

  // 连接测试相关
  const showTestDialog = ref(false)
  const testingConnection = ref(false)
  const testingConfig = ref(false)
  const testResult = ref<any>(null)
  const testError = ref<string | null>(null)
  const currentTestConfig = ref<any>(null)

  // 表单数据
  const clusterForm = ref<ClusterCreate>({
    name: '',
    description: '',
    hive_host: '',
    hive_port: 10000,
    hive_database: 'default',
    hive_metastore_url: '',
    hdfs_namenode_url: '',
    hdfs_user: 'hdfs',
    auth_type: 'NONE',
    hive_username: '',
    hive_password: '',
    yarn_resource_manager_url: '',
    small_file_threshold: 128 * 1024 * 1024,
    scan_enabled: true
  })

  const clusterRules = {
    name: [{ required: true, message: '请输入集群名称', trigger: 'blur' }],
    hive_host: [{ required: true, message: '请输入 Hive 主机地址', trigger: 'blur' }],
    hive_metastore_url: [{ required: true, message: '请输入 MetaStore URL', trigger: 'blur' }],
    hdfs_namenode_url: [{ required: true, message: '请输入 HDFS/HttpFS 地址', trigger: 'blur' }],
    hive_username: [
      {
        required: true,
        message: '请输入 Hive 用户名',
        trigger: 'blur',
        validator: (rule: any, value: any, callback: any) => {
          if (clusterForm.value.auth_type === 'LDAP' && !value) {
            callback(new Error('使用 LDAP 认证时，用户名不能为空'))
          } else {
            callback()
          }
        }
      }
    ],
    hive_password: [
      {
        required: true,
        message: '请输入 Hive 密码',
        trigger: 'blur',
        validator: (rule: any, value: any, callback: any) => {
          if (clusterForm.value.auth_type === 'LDAP' && !value) {
            callback(new Error('使用 LDAP 认证时，密码不能为空'))
          } else {
            callback()
          }
        }
      }
    ]
  }

  const clusterFormRef = ref()

  // 计算属性
  const totalClusters = computed(() => clusters.value.length)
  const onlineClusters = computed(() => clusters.value.filter(c => c.status === 'active').length)
  const totalTables = computed(() =>
    Object.values(clusterStats.value).reduce((sum, stat) => sum + (stat.tables || 0), 0)
  )
  const pendingTasks = computed(() =>
    Object.values(clusterStats.value).reduce((sum, stat) => sum + (stat.pending_tasks || 0), 0)
  )

  const filteredClusters = computed(() => {
    let result = clusters.value

    if (searchText.value) {
      const search = searchText.value.toLowerCase()
      result = result.filter(
        cluster =>
          cluster.name.toLowerCase().includes(search) ||
          cluster.hive_host.toLowerCase().includes(search) ||
          (cluster.description && cluster.description.toLowerCase().includes(search))
      )
    }

    if (statusFilter.value) {
      result = result.filter(cluster => cluster.status === statusFilter.value)
    }

    return result
  })

  // 方法
  const loadClusters = async () => {
    loading.value = true
    loadError.value = null
    try {
      clusters.value = await clustersApi.list()
      await loadClusterStats()
    } catch (error: any) {
      console.error('Failed to load clusters:', error)
      loadError.value = error?.response?.data?.detail || error?.message || '请求失败'
    } finally {
      loading.value = false
    }
  }

  const reloadClusters = () => {
    loadClusters()
  }

  // 触发集群扫描（带进度）
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

  const loadClusterStats = async () => {
    // 调用真实API获取每个集群的统计数据
    const stats: Record<number, any> = {}

    for (const cluster of clusters.value) {
      try {
        const clusterStats = await clustersApi.getStats(cluster.id)
        stats[cluster.id] = {
          databases: clusterStats.total_databases,
          tables: clusterStats.total_tables,
          small_files: clusterStats.total_small_files,
          pending_tasks: 0 // 暂时设为0，后续可以添加任务统计API
        }
      } catch (error) {
        console.error(`Failed to load stats for cluster ${cluster.id}:`, error)
        // 如果API调用失败，设置默认值
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

  const getClusterStat = (clusterId: number, type: string) => {
    return clusterStats.value[clusterId]?.[type] || 0
  }

  const filterClusters = () => {
    // 过滤逻辑在计算属性中处理
  }

  const onAuthTypeChange = (authType: string) => {
    if (authType === 'NONE') {
      // 清空LDAP认证相关字段
      clusterForm.value.hive_username = ''
      clusterForm.value.hive_password = ''
    }

    // 触发表单验证
    clusterFormRef.value?.clearValidate(['hive_username', 'hive_password'])
  }

  const enterCluster = (clusterId: number) => {
    // 设置选中的集群并跳转到监控中心
    monitoringStore.setSelectedCluster(clusterId)
    ElMessage.success('集群选择成功，正在跳转...')
    router.push('/')  // 跳转到监控中心
  }

  const getStatusType = (status: string) => {
    return status === 'active' ? 'success' : 'danger'
  }

  const saveCluster = async () => {
    try {
      await clusterFormRef.value.validate()

      if (editingCluster.value) {
        await clustersApi.update(editingCluster.value.id, clusterForm.value)
        ElMessage.success('集群更新成功')
      } else {
        // 创建集群时选择是否验证连接
        if (validateConnection.value) {
          await clustersApi.createWithValidation(clusterForm.value)
          ElMessage.success('集群创建成功（已验证连接）')
        } else {
          await clustersApi.create(clusterForm.value)
          ElMessage.success('集群创建成功')
        }
      }

      showCreateDialog.value = false
      resetForm()
      loadClusters()
    } catch (error: any) {
      console.error('Failed to save cluster:', error)
      const errorMsg = error.response?.data?.detail || error.message || '保存失败'
      ElMessage.error(errorMsg)
    }
  }

  const editCluster = (cluster: Cluster) => {
    editingCluster.value = cluster
    clusterForm.value = { ...cluster }
    showCreateDialog.value = true
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

  // 增强连接测试
  const testConnectionEnhanced = async (
    cluster: Cluster,
    options?: {
      connectionTypes?: string[]
      forceRefresh?: boolean
    }
  ) => {
    currentTestConfig.value = cluster
    testResult.value = null
    testError.value = null
    testingConnection.value = true
    showTestDialog.value = true

    try {
      const result = await clustersApi.testConnectionEnhanced(cluster.id, options)
      testResult.value = result

      // 更新连接状态缓存
      if (result.tests) {
        // 状态映射函数：后端状态 -> 前端状态
        const mapStatus = (backendStatus: string) => {
          switch (backendStatus) {
            case 'success':
              return 'success'
            case 'failed':
              return 'error'
            case 'unknown':
              return 'unknown'
            default:
              return 'error'
          }
        }

        // 确保连接状态对象存在
        if (!connectionStatus.value[cluster.id]) {
          connectionStatus.value[cluster.id] = {}
        }

        // 更新每个服务的状态
        for (const [service, serviceResult] of Object.entries(result.tests)) {
          const mappedServiceKey =
            service === 'metastore'
              ? 'metastore'
              : service === 'hdfs'
                ? 'hdfs'
                : service === 'hiveserver2'
                  ? 'hiveserver'
                  : service

          connectionStatus.value[cluster.id][mappedServiceKey] = {
            status: mapStatus(serviceResult.status),
            message:
              serviceResult.error_message ||
              `响应时间: ${serviceResult.response_time_ms.toFixed(0)}ms`,
            lastChecked: new Date(),
            responseTime: serviceResult.response_time_ms,
            failureType: serviceResult.failure_type,
            attemptCount: serviceResult.attempt_count
          }
        }
      }
    } catch (error: any) {
      console.error('Failed to test connection:', error)
      testError.value = error.response?.data?.detail || error.message || '增强连接测试失败'
    } finally {
      testingConnection.value = false
    }
  }

  const testConnection = async (cluster: Cluster, mode: string = 'mock') => {
    if (mode === 'real') {
      // 使用增强连接测试
      await testConnectionEnhanced(cluster, { forceRefresh: true })
    } else if (mode === 'enhanced') {
      // 增强模式，测试所有服务
      await testConnectionEnhanced(cluster, {
        connectionTypes: ['metastore', 'hdfs', 'hiveserver2'],
        forceRefresh: true
      })
    } else {
      // Mock测试 - 简单消息提示
      const loadingMessage = ElMessage({
        message: '正在测试连接...',
        type: 'info',
        duration: 0
      })

      try {
        const result = await clustersApi.testConnection(cluster.id, mode)
        loadingMessage.close()

        // 根据实际API响应结构处理
        const tests = result.tests || result.connections
        const metastoreTest = tests?.metastore
        const hdfsTest = tests?.hdfs

        if (metastoreTest?.status === 'success') {
          const hdfsStatus = hdfsTest?.status
          const hdfsMode = hdfsTest?.mode

          if (hdfsStatus === 'success') {
            ElMessage.success(`✅ 连接测试成功！
          • MetaStore: ${metastoreTest.message || '连接正常'}
          • HDFS: ${hdfsTest.message || '连接正常'} (${hdfsMode}模式)`)
          } else {
            ElMessage.warning(`⚠️ 部分连接成功
          • MetaStore: ${metastoreTest.message || '连接正常'}
          • HDFS: ${hdfsTest?.message || '连接失败'} (${hdfsMode}模式)`)
          }
        } else {
          ElMessage.error(`❌ 连接测试失败
        • MetaStore: ${metastoreTest?.message || '连接失败'}
        ${hdfsTest ? `• HDFS: ${hdfsTest.message || '未测试'}` : ''}`)
        }
      } catch (error: any) {
        loadingMessage.close()
        console.error('Failed to test connection:', error)
        const errorMsg = error.response?.data?.detail || error.message || '网络连接失败'
        ElMessage.error(`❌ 测试失败: ${errorMsg}`)
      }
    }
  }

  // 配置模板
  const clusterTemplates = {
    cdp: {
      name: 'CDP-',
      description: 'Cloudera Data Platform 集群',
      hive_host: 'cdp-master',
      hive_port: 10000,
      hive_database: 'default',
      hive_metastore_url: 'mysql://root:password@cdp-master:3306/hive',
      hdfs_namenode_url: 'hdfs://nameservice1',
      hdfs_user: 'hdfs',
      small_file_threshold: 128 * 1024 * 1024,
      scan_enabled: true
    },
    cdh: {
      name: 'CDH-',
      description: 'Cloudera Distribution Hadoop 集群',
      hive_host: 'cdh-master',
      hive_port: 10000,
      hive_database: 'default',
      hive_metastore_url: 'postgresql://hive:password@cdh-master:5432/hive_metastore',
      hdfs_namenode_url: 'hdfs://cdh-nameservice',
      hdfs_user: 'hdfs',
      small_file_threshold: 128 * 1024 * 1024,
      scan_enabled: true
    },
    hdp: {
      name: 'HDP-',
      description: 'Hortonworks Data Platform 集群',
      hive_host: 'hdp-master',
      hive_port: 10000,
      hive_database: 'default',
      hive_metastore_url: 'mysql://hive:password@hdp-master:3306/hive',
      hdfs_namenode_url: 'hdfs://hdp-cluster',
      hdfs_user: 'hdfs',
      small_file_threshold: 128 * 1024 * 1024,
      scan_enabled: true
    }
  }

  const applyTemplate = (templateName: string) => {
    if (templateName && clusterTemplates[templateName as keyof typeof clusterTemplates]) {
      const template = clusterTemplates[templateName as keyof typeof clusterTemplates]
      clusterForm.value = { ...template }
      ElMessage.info(`已应用 ${templateName.toUpperCase()} 集群模板，请根据实际情况修改配置`)
    }
  }

  const handleTemplate = (command: string) => {
    selectedTemplate.value = command
    applyTemplate(command)
    showCreateDialog.value = true
  }

  const handleClusterAction = (command: string, cluster: any) => {
    if (command === 'delete') {
      deleteCluster(cluster)
    }
  }

  const resetForm = () => {
    editingCluster.value = null
    selectedTemplate.value = ''
    validateConnection.value = false
    clusterForm.value = {
      name: '',
      description: '',
      hive_host: '',
      hive_port: 10000,
      hive_database: 'default',
      hive_metastore_url: '',
      hdfs_namenode_url: '',
      hdfs_user: 'hdfs',
      auth_type: 'NONE',
      hive_username: '',
      hive_password: '',
      yarn_resource_manager_url: '',
      small_file_threshold: 128 * 1024 * 1024,
      scan_enabled: true
    }
  }

  // 连接状态管理函数
  const getConnectionStatus = (clusterId: number, service: string) => {
    const status = connectionStatus.value[clusterId]
    if (!status) return { status: 'unknown' }

    switch (service) {
      case 'hiveserver':
        return status.hiveserver || { status: 'unknown' }
      case 'hdfs':
        return status.hdfs || { status: 'unknown' }
      case 'metastore':
        return status.metastore || { status: 'unknown' }
      default:
        return { status: 'unknown' }
    }
  }

  const isLoadingConnectionStatus = (clusterId: number) => {
    return connectionStatus.value[clusterId]?.loading || false
  }

  const updateConnectionStatus = async (clusterId: number) => {
    if (!connectionStatus.value[clusterId]) {
      connectionStatus.value[clusterId] = {}
    }

    connectionStatus.value[clusterId].loading = true

    try {
      const result = await clustersApi.testConnection(clusterId, 'enhanced')
      const tests = result.tests || {}

      // 状态映射函数：后端状态 -> 前端状态
      const mapStatus = (backendStatus: string) => {
        switch (backendStatus) {
          case 'success':
            return 'success'
          case 'failed':
            return 'error'
          case 'unknown':
            return 'unknown'
          default:
            return 'error'
        }
      }

      connectionStatus.value[clusterId] = {
        hiveserver: {
          // HiveServer2状态暂时使用metastore状态作为参考
          status: mapStatus(tests.metastore?.status || 'unknown'),
          message: tests.metastore?.message || '基于MetaStore连接状态推测',
          mode: tests.metastore?.mode || 'enhanced'
        },
        hdfs: {
          status: mapStatus(tests.hdfs?.status || 'unknown'),
          message: tests.hdfs?.message || '',
          mode: tests.hdfs?.mode || 'enhanced'
        },
        metastore: {
          status: mapStatus(tests.metastore?.status || 'unknown'),
          message: tests.metastore?.message || '',
          mode: tests.metastore?.mode || 'enhanced'
        },
        loading: false,
        lastChecked: new Date()
      }
    } catch (error) {
      console.error(`Failed to check connection status for cluster ${clusterId}:`, error)
      connectionStatus.value[clusterId] = {
        hiveserver: { status: 'error', message: '连接测试失败' },
        hdfs: { status: 'error', message: '连接测试失败' },
        metastore: { status: 'error', message: '连接测试失败' },
        loading: false,
        lastChecked: new Date()
      }
    }
  }

  const testSpecificConnection = async (clusterId: number, service: string) => {
    console.log(`Testing ${service} connection for cluster ${clusterId}`)

    // 设置特定服务为测试中状态
    if (!connectionStatus.value[clusterId]) {
      connectionStatus.value[clusterId] = {}
    }

    const currentStatus = connectionStatus.value[clusterId]
    const serviceKey = service === 'hiveserver' ? 'hiveserver2' : service

    // 设置测试中状态
    currentStatus[serviceKey] = { status: 'testing', message: '正在测试连接...' }

    try {
      // 使用增强API测试特定服务
      const result = await clustersApi.testConnectionEnhanced(clusterId, {
        connectionTypes: [serviceKey],
        forceRefresh: true
      })

      // 更新连接状态
      if (result.tests && result.tests[serviceKey]) {
        const serviceResult = result.tests[serviceKey]
        // 状态映射函数：后端状态 -> 前端状态
        const mapStatus = (backendStatus: string) => {
          switch (backendStatus) {
            case 'success':
              return 'success'
            case 'failed':
              return 'error'
            case 'unknown':
              return 'unknown'
            default:
              return 'error'
          }
        }

        currentStatus[serviceKey] = {
          status: mapStatus(serviceResult.status),
          message:
            serviceResult.error_message ||
            `响应时间: ${serviceResult.response_time_ms.toFixed(0)}ms`,
          lastChecked: new Date(),
          responseTime: serviceResult.response_time_ms,
          failureType: serviceResult.failure_type,
          attemptCount: serviceResult.attempt_count
        }

        // 显示测试结果
        if (serviceResult.status === 'success') {
          ElMessage({
            message: `${service} 连接测试成功 (${serviceResult.response_time_ms.toFixed(0)}ms)`,
            type: 'success'
          })
        } else {
          ElMessage({
            message: `${service} 连接测试失败: ${serviceResult.error_message || '未知错误'}`,
            type: 'error',
            duration: 5000
          })
        }
      }
    } catch (error: any) {
      console.error(`Failed to test ${service} connection:`, error)
      currentStatus[serviceKey] = {
        status: 'error',
        message: error.message || '网络错误',
        lastChecked: new Date()
      }

      ElMessage({
        message: `${service} 连接测试失败: ${error.message || '网络错误'}`,
        type: 'error'
      })
    }
  }

  const checkAllConnectionStatus = async () => {
    const promises = clusters.value.map(cluster => updateConnectionStatus(cluster.id))
    await Promise.allSettled(promises)
  }

  const startStatusCheckInterval = () => {
    // 每30秒检查一次连接状态
    statusCheckInterval = setInterval(() => {
      checkAllConnectionStatus()
    }, 30000)
  }

  const stopStatusCheckInterval = () => {
    if (statusCheckInterval) {
      clearInterval(statusCheckInterval)
      statusCheckInterval = null
    }
  }

  // 测试配置连接（创建前测试）
  const testConfigConnection = async () => {
    try {
      await clusterFormRef.value.validate()

      currentTestConfig.value = { ...clusterForm.value }
      testResult.value = null
      testError.value = null
      testingConfig.value = true

      const result = await clustersApi.testConnectionConfig(clusterForm.value)
      testResult.value = result
      showTestDialog.value = true
    } catch (error: any) {
      if (error.fields) {
        // 表单验证失败
        ElMessage.error('请先完成表单填写')
      } else {
        console.error('Failed to test config connection:', error)
        testError.value = error.response?.data?.detail || error.message || '连接测试失败'
        showTestDialog.value = true
      }
    } finally {
      testingConfig.value = false
    }
  }

  // 重新测试连接
  const handleRetest = async (clusterConfig: any) => {
    testResult.value = null
    testError.value = null
    testingConnection.value = true

    try {
      let result
      if (clusterConfig.id) {
        // 已存在的集群
        result = await clustersApi.testConnection(clusterConfig.id, 'real')
      } else {
        // 配置测试
        result = await clustersApi.testConnectionConfig(clusterConfig)
      }
      testResult.value = result
    } catch (error: any) {
      console.error('Failed to retest connection:', error)
      testError.value = error.response?.data?.detail || error.message || '重新测试失败'
    } finally {
      testingConnection.value = false
    }
  }

  const formatTime = (time: string): string => {
    return dayjs(time).format('YYYY-MM-DD HH:mm')
  }

  onMounted(async () => {
    await loadClusters()
    // 加载完集群后检查连接状态
    await checkAllConnectionStatus()
    // 启动定时检查
    startStatusCheckInterval()
  })

  // 组件卸载时清理定时器
  onUnmounted(() => {
    stopStatusCheckInterval()
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

  /* 筛选区域 */
  .filter-section {
    margin-bottom: var(--space-8);
    padding: var(--space-6);
  }

  .filter-header {
    margin-bottom: var(--space-4);
    padding-bottom: var(--space-3);
    border-bottom: 2px solid var(--primary-500);
  }

  .filter-header h3 {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    color: var(--gray-900);
  }

  .filter-controls {
    display: flex;
    gap: var(--space-4);
    align-items: center;
    flex-wrap: wrap;
  }

  .search-input {
    min-width: 300px;
  }

  .status-filter {
    min-width: 150px;
  }

  /* 集群网格 */
  .clusters-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: var(--space-6);
  }

  .cluster-card {
    cursor: pointer;
    padding: var(--space-6);
    min-height: 240px;
    display: flex;
    flex-direction: column;
  }

  .cluster-online::before {
    background: linear-gradient(90deg, var(--success-500), var(--success-300));
  }

  .cluster-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--space-4);
    padding-bottom: var(--space-4);
    border-bottom: 1px solid var(--gray-200);
  }

  /* 新的标题区域样式 */
  .cluster-title-section {
    flex: 1;
  }

  .cluster-name-row {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    margin-bottom: var(--space-2) !important;
  }

  .cluster-name {
    margin: 0;
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
    color: var(--gray-900);
    flex: 1;
    margin-right: var(--space-3);
  }

  .cluster-title-section .cluster-description {
    color: var(--gray-600);
    margin: 0;
    font-size: var(--text-sm);
    line-height: var(--leading-relaxed);
  }

  .cluster-actions {
    display: flex;
    gap: var(--space-2);
    align-items: center;
  }

  .cluster-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  /* 压缩的信息区域 */
  .cluster-info-compact {
    margin-bottom: var(--space-3);
  }

  .cluster-info-compact .cluster-details {
    display: flex;
    gap: var(--space-4);
  }

  .cluster-details {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .detail-item {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-sm);
    color: var(--gray-600);
  }

  .detail-item .el-icon {
    color: var(--primary-500);
  }

  /* 紧凑的统计样式 */
  .cluster-stats-compact {
    margin-bottom: var(--space-4);
  }

  .stats-row {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: var(--space-3) var(--space-4) !important;
    background: var(--gray-50) !important;
    border-radius: var(--radius-lg) !important;
    border: 1px solid var(--gray-200) !important;
  }

  .stats-row .stat-item {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    text-align: center !important;
    flex: 1 !important;
  }

  .stat-divider {
    width: 1px;
    height: 24px;
    background: var(--gray-300);
    margin: 0 var(--space-2);
  }

  .stats-row .stat-value {
    font-size: var(--text-lg);
    font-weight: var(--font-bold);
    color: var(--primary-600);
    margin-bottom: 2px;
  }

  .stats-row .stat-label {
    font-size: var(--text-xs);
    color: var(--gray-600);
    font-weight: var(--font-medium);
  }

  .stat-item {
    text-align: center;
  }

  .stat-value {
    font-size: var(--text-2xl);
    font-weight: var(--font-bold);
    color: var(--primary-600);
    margin-bottom: var(--space-1);
  }

  .stat-label {
    font-size: var(--text-xs);
    color: var(--gray-600);
    font-weight: var(--font-medium);
  }

  .cluster-operations {
    display: flex;
    gap: var(--space-2);
    align-items: center;
    margin-top: auto;
    padding-top: var(--space-4);
    border-top: 1px solid var(--gray-200);
  }

  /* 危险操作样式 */
  .danger-item {
    color: var(--danger-500) !important;
  }

  .danger-item .el-icon {
    color: var(--danger-500) !important;
  }

  .empty-state {
    grid-column: 1 / -1;
    text-align: center;
    padding: var(--space-16) var(--space-6);
  }

  /* 依次出现动画 */
  .stagger-animation {
    perspective: 1000px;
  }

  .stagger-item {
    animation: staggerIn 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
    opacity: 0;
    transform: translateY(30px) scale(0.95);
    animation-delay: var(--stagger-delay, 0s);
  }

  .stagger-item:hover {
    transform: translateY(-4px) scale(1.02);
    box-shadow: var(--elevation-4);
  }

  @keyframes staggerIn {
    0% {
      opacity: 0;
      transform: translateY(30px) scale(0.95);
    }
    60% {
      opacity: 0.8;
      transform: translateY(-5px) scale(1.02);
    }
    100% {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  /* 响应式适配 */
  @media (max-width: 1200px) {
    .clusters-grid {
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: var(--space-4);
    }
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

    .filter-controls {
      flex-direction: column;
      align-items: stretch;
    }

    .search-input {
      min-width: auto;
    }

    .clusters-grid {
      grid-template-columns: 1fr;
    }

    .cluster-operations {
      justify-content: center;
    }
  }
</style>
