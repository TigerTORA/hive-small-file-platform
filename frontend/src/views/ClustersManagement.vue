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
          <el-button>
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
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          添加集群
        </el-button>
      </div>
    </div>

    <!-- 集群统计概览 -->
    <el-row :gutter="20" class="stats-section">
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="总集群数" :value="totalClusters">
            <template #suffix>
              <el-icon><Monitor /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="在线集群" :value="onlineClusters">
            <template #suffix>
              <el-icon style="color: #67c23a"><CircleCheckFilled /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="监控的表" :value="totalTables">
            <template #suffix>
              <el-icon><Grid /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="待处理任务" :value="pendingTasks">
            <template #suffix>
              <el-icon style="color: #e6a23c"><Clock /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索和过滤 -->
    <el-card class="filter-section">
      <el-row :gutter="20" align="middle">
        <el-col :span="8">
          <el-input 
            v-model="searchText" 
            placeholder="搜索集群名称或主机..." 
            clearable
            @input="filterClusters"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="6">
          <el-select v-model="statusFilter" placeholder="筛选状态" clearable @change="filterClusters">
            <el-option label="全部状态" value="" />
            <el-option label="正常" value="active" />
            <el-option label="异常" value="inactive" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-button @click="loadClusters" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 集群卡片列表 -->
    <div v-loading="loading" class="clusters-grid">
      <div v-if="filteredClusters.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无集群数据">
          <el-button type="primary" @click="showCreateDialog = true">
            添加第一个集群
          </el-button>
        </el-empty>
      </div>
      
      <el-card 
        v-for="cluster in filteredClusters" 
        :key="cluster.id"
        class="cluster-card"
        @click="enterCluster(cluster.id)"
        :class="{ 'cluster-online': cluster.status === 'active' }"
        shadow="hover"
      >
        <template #header>
          <div class="cluster-header">
            <div class="cluster-title">
              <h3>{{ cluster.name }}</h3>
              <el-tag :type="getStatusType(cluster.status)" size="small">
                {{ cluster.status === 'active' ? '正常' : '异常' }}
              </el-tag>
            </div>
            <div class="cluster-actions" @click.stop>
              <el-tooltip content="全库扫描(带进度)" placement="top">
                <el-button size="small" type="success" @click="startClusterScan(cluster.id)">
                  <el-icon><Refresh /></el-icon>
                  扫描
                </el-button>
              </el-tooltip>
              <el-tooltip content="进入集群详情" placement="top">
                <el-button type="primary" size="small" circle @click="enterCluster(cluster.id)">
                  <el-icon><Right /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </div>
        </template>
        
        <div class="cluster-content">
          <div class="cluster-info">
            <p class="cluster-description">{{ cluster.description || '暂无描述' }}</p>
            <div class="cluster-details">
              <div class="detail-item">
                <el-icon><Monitor /></el-icon>
                <span>{{ cluster.hive_host }}:{{ cluster.hive_port }}</span>
              </div>
              <div class="detail-item">
                <el-icon><Clock /></el-icon>
                <span>{{ formatTime(cluster.created_time) }}</span>
              </div>
            </div>
          </div>

          <div class="cluster-stats">
            <el-row :gutter="16">
              <el-col :span="8">
                <div class="stat-item">
                  <div class="stat-value">{{ getClusterStat(cluster.id, 'databases') }}</div>
                  <div class="stat-label">数据库</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="stat-item">
                  <div class="stat-value">{{ getClusterStat(cluster.id, 'tables') }}</div>
                  <div class="stat-label">表数量</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="stat-item">
                  <div class="stat-value">{{ getClusterStat(cluster.id, 'small_files') }}</div>
                  <div class="stat-label">小文件</div>
                </div>
              </el-col>
            </el-row>
          </div>

          <div class="cluster-operations" @click.stop>
            <el-button size="small" @click="testConnection(cluster, 'mock')">
              <el-icon><Connection /></el-icon>
              快速测试
            </el-button>
            <el-button size="small" @click="editCluster(cluster)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button size="small" type="danger" @click="deleteCluster(cluster)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingCluster ? '编辑集群' : '添加集群'"
      width="600px"
    >
      <el-form :model="clusterForm" :rules="clusterRules" ref="clusterFormRef" label-width="140px">
        <el-form-item label="使用模板" v-if="!editingCluster">
          <el-select v-model="selectedTemplate" placeholder="选择配置模板" @change="applyTemplate" clearable>
            <el-option label="CDP 集群" value="cdp" />
            <el-option label="CDH 集群" value="cdh" />
            <el-option label="HDP 集群" value="hdp" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="集群名称" prop="name">
          <el-input v-model="clusterForm.name" placeholder="请输入集群名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="clusterForm.description" type="textarea" placeholder="集群描述（可选）" />
        </el-form-item>
        <el-form-item label="Hive 主机" prop="hive_host">
          <el-input v-model="clusterForm.hive_host" placeholder="Hive Server2 主机地址" />
        </el-form-item>
        <el-form-item label="Hive 端口">
          <el-input-number v-model="clusterForm.hive_port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="MetaStore URL" prop="hive_metastore_url">
          <el-input v-model="clusterForm.hive_metastore_url" placeholder="postgresql://user:pass@host:5432/hive" />
        </el-form-item>
        <el-form-item label="HDFS/HttpFS 地址" prop="hdfs_namenode_url">
          <el-input v-model="clusterForm.hdfs_namenode_url" placeholder="http://httpfs:14000/webhdfs/v1" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            <div style="margin-bottom: 2px;"><strong>支持的地址格式:</strong></div>
            <div>• HttpFS (推荐): http://httpfs-host:14000/webhdfs/v1</div>
            <div>• WebHDFS: http://namenode:9870/webhdfs/v1</div>
            <div>• HDFS URI: hdfs://nameservice 或 hdfs://namenode:8020</div>
          </div>
        </el-form-item>
        <el-form-item label="HDFS 用户">
          <el-input v-model="clusterForm.hdfs_user" placeholder="hdfs" />
        </el-form-item>
        
        <!-- Hive 认证配置 -->
        <el-divider content-position="left">
          <span style="color: #606266; font-weight: 500;">Hive 认证配置</span>
        </el-divider>
        
        <el-form-item label="认证类型">
          <el-select v-model="clusterForm.auth_type" placeholder="选择认证类型" @change="onAuthTypeChange">
            <el-option label="无认证 (NONE)" value="NONE" />
            <el-option label="LDAP 认证" value="LDAP" />
          </el-select>
        </el-form-item>
        
        <template v-if="clusterForm.auth_type === 'LDAP'">
          <el-form-item label="Hive 用户名" prop="hive_username">
            <el-input v-model="clusterForm.hive_username" placeholder="LDAP 用户名" />
          </el-form-item>
          <el-form-item label="Hive 密码" prop="hive_password">
            <el-input 
              v-model="clusterForm.hive_password" 
              type="password" 
              placeholder="LDAP 密码"
              show-password
            />
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              密码将被安全加密存储
            </div>
          </el-form-item>
        </template>
        
        <!-- YARN 监控配置 -->
        <el-divider content-position="left">
          <span style="color: #606266; font-weight: 500;">YARN 监控配置</span>
        </el-divider>
        
        <el-form-item label="Resource Manager">
          <el-input 
            v-model="clusterForm.yarn_resource_manager_url" 
            placeholder="http://rm1:8088,http://rm2:8088" 
          />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            <div>支持 HA 配置，多个地址用逗号分隔</div>
            <div>示例: http://192.168.0.106:8088,http://192.168.0.107:8088</div>
          </div>
        </el-form-item>
        
        <el-form-item label="小文件阈值">
          <el-input-number v-model="clusterForm.small_file_threshold" :min="1024" :step="1024*1024" />
          <span style="margin-left: 8px; color: #909399;">字节 (默认: 128MB)</span>
        </el-form-item>
        
        <el-form-item label="创建选项" v-if="!editingCluster">
          <el-checkbox v-model="validateConnection">
            创建前验证连接
          </el-checkbox>
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
          <el-button type="primary" @click="saveCluster">
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
import { 
  CaretBottom, Plus, Monitor, CircleCheckFilled, Grid, Clock, 
  Search, Refresh, Right, Connection, Edit, Delete
} from '@element-plus/icons-vue'
import { clustersApi, type Cluster, type ClusterCreate } from '@/api/clusters'
import ConnectionTestDialog from '@/components/ConnectionTestDialog.vue'
import ScanProgressDialog from '@/components/ScanProgressDialog.vue'
import { tablesApi } from '@/api/tables'
import dayjs from 'dayjs'

const router = useRouter()

// 数据
const clusters = ref<Cluster[]>([])
const loading = ref(false)
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
const totalTables = computed(() => Object.values(clusterStats.value).reduce((sum, stat) => sum + (stat.tables || 0), 0))
const pendingTasks = computed(() => Object.values(clusterStats.value).reduce((sum, stat) => sum + (stat.pending_tasks || 0), 0))

const filteredClusters = computed(() => {
  let result = clusters.value
  
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(cluster => 
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
  try {
    clusters.value = await clustersApi.list()
    // 加载集群统计数据
    await loadClusterStats()
  } catch (error) {
    console.error('Failed to load clusters:', error)
  } finally {
    loading.value = false
  }
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
  // 这里应该调用API获取每个集群的统计数据
  // 暂时使用模拟数据
  const stats: Record<number, any> = {}
  for (const cluster of clusters.value) {
    stats[cluster.id] = {
      databases: Math.floor(Math.random() * 20) + 1,
      tables: Math.floor(Math.random() * 100) + 10,
      small_files: Math.floor(Math.random() * 1000) + 50,
      pending_tasks: Math.floor(Math.random() * 10)
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
  router.push(`/clusters/${clusterId}`)
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

const testConnection = async (cluster: Cluster, mode: string = 'mock') => {
  if (mode === 'real') {
    // 详细测试 - 显示测试对话框
    currentTestConfig.value = cluster
    testResult.value = null
    testError.value = null
    testingConnection.value = true
    showTestDialog.value = true
    
    try {
      const result = await clustersApi.testConnection(cluster.id, mode)
      testResult.value = result
    } catch (error: any) {
      console.error('Failed to test connection:', error)
      testError.value = error.response?.data?.detail || error.message || '测试失败'
    } finally {
      testingConnection.value = false
    }
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

onMounted(() => {
  loadClusters()
})
</script>

<style scoped>
.clusters-management {
  padding: 24px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.title-section h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
}

.title-section p {
  margin: 0;
  color: #6b7280;
  font-size: 16px;
}

.actions-section {
  display: flex;
  gap: 12px;
  align-items: center;
}

.stats-section {
  margin-bottom: 24px;
}

.stat-card {
  text-align: center;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.filter-section {
  margin-bottom: 24px;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.clusters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 24px;
}

.cluster-card {
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  cursor: pointer;
}

.cluster-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.cluster-online {
  border-left: 4px solid #67c23a;
}

.cluster-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.cluster-title h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.cluster-description {
  color: #6b7280;
  margin: 0 0 16px 0;
  font-size: 14px;
  line-height: 1.5;
}

.cluster-details {
  margin-bottom: 20px;
}

.detail-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  font-size: 14px;
  color: #6b7280;
}

.detail-item .el-icon {
  margin-right: 8px;
  color: #9ca3af;
}

.cluster-stats {
  margin-bottom: 20px;
  padding: 16px;
  background-color: #f9fafb;
  border-radius: 8px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
}

.cluster-operations {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
}
</style>
