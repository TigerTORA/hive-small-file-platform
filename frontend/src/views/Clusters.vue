<template>
  <div class="clusters">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>集群管理</span>
          <div class="header-actions">
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
            <el-button type="primary" @click="showCreateDialog = true">
              <el-icon><Plus /></el-icon>
              添加集群
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="clusters" stripe v-loading="loading">
        <el-table-column prop="name" label="集群名称" />
        <el-table-column prop="hive_host" label="Hive 地址" />
        <el-table-column prop="hdfs_namenode_url" label="HDFS/HttpFS 地址" width="220" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '正常' : '异常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320">
          <template #default="{ row }">
            <el-button type="info" size="small" @click="testConnection(row, 'mock')">
              Mock测试
            </el-button>
            <el-button type="primary" size="small" @click="testConnection(row, 'real')">
              详细测试
            </el-button>
            <el-button type="success" size="small" @click="editCluster(row)">
              编辑
            </el-button>
            <el-button type="danger" size="small" @click="deleteCluster(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CaretBottom, Plus } from '@element-plus/icons-vue'
import { clustersApi, type Cluster, type ClusterCreate } from '@/api/clusters'
import ConnectionTestDialog from '@/components/ConnectionTestDialog.vue'
import dayjs from 'dayjs'

// 数据
const clusters = ref<Cluster[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const editingCluster = ref<Cluster | null>(null)
const selectedTemplate = ref('')
const validateConnection = ref(false)

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
  small_file_threshold: 128 * 1024 * 1024,
  scan_enabled: true
})

const clusterRules = {
  name: [{ required: true, message: '请输入集群名称', trigger: 'blur' }],
  hive_host: [{ required: true, message: '请输入 Hive 主机地址', trigger: 'blur' }],
  hive_metastore_url: [{ required: true, message: '请输入 MetaStore URL', trigger: 'blur' }],
  hdfs_namenode_url: [{ required: true, message: '请输入 HDFS/HttpFS 地址', trigger: 'blur' }]
}

const clusterFormRef = ref()

// 方法
const loadClusters = async () => {
  loading.value = true
  try {
    clusters.value = await clustersApi.list()
  } catch (error) {
    console.error('Failed to load clusters:', error)
  } finally {
    loading.value = false
  }
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
    try {
      const result = await clustersApi.testConnection(cluster.id, mode)
      
      if (result.connections?.metastore?.status === 'success') {
        const hdfsStatus = result.connections.hdfs?.status
        const hdfsMode = result.connections.hdfs?.mode
        
        if (hdfsStatus === 'success') {
          ElMessage.success(`Mock连接测试成功 (HDFS模式: ${hdfsMode})`)
        } else {
          ElMessage.warning(`MetaStore连接成功，但HDFS连接失败 (${hdfsMode}模式)`)
        }
      } else {
        ElMessage.error(`连接测试失败: ${result.connections?.metastore?.message || '未知错误'}`)
      }
    } catch (error: any) {
      console.error('Failed to test connection:', error)
      const errorMsg = error.response?.data?.detail || error.message || '测试失败'
      ElMessage.error(errorMsg)
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
    hdfs_namenode_url: 'http://cdp-master:14000/webhdfs/v1',
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
    hdfs_namenode_url: 'http://cdh-master:14000/webhdfs/v1',
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
    hdfs_namenode_url: 'http://hdp-master:14000/webhdfs/v1',
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
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  loadClusters()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}
</style>