<template>
  <div class="clusters">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>集群管理</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            添加集群
          </el-button>
        </div>
      </template>

      <el-table :data="clusters" stripe v-loading="loading">
        <el-table-column prop="name" label="集群名称" />
        <el-table-column prop="hive_host" label="Hive 地址" />
        <el-table-column prop="hdfs_namenode_url" label="HDFS 地址" width="200" />
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
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="testConnection(row)">
              测试连接
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
        <el-form-item label="HDFS NameNode" prop="hdfs_namenode_url">
          <el-input v-model="clusterForm.hdfs_namenode_url" placeholder="hdfs://namenode:9000" />
        </el-form-item>
        <el-form-item label="HDFS 用户">
          <el-input v-model="clusterForm.hdfs_user" placeholder="hdfs" />
        </el-form-item>
        <el-form-item label="小文件阈值">
          <el-input-number v-model="clusterForm.small_file_threshold" :min="1024" :step="1024*1024" />
          <span style="margin-left: 8px; color: #909399;">字节</span>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" @click="saveCluster">
            {{ editingCluster ? '更新' : '创建' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { clustersApi, type Cluster, type ClusterCreate } from '@/api/clusters'
import dayjs from 'dayjs'

// 数据
const clusters = ref<Cluster[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const editingCluster = ref<Cluster | null>(null)

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
  hdfs_namenode_url: [{ required: true, message: '请输入 HDFS NameNode URL', trigger: 'blur' }]
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
      await clustersApi.create(clusterForm.value)
      ElMessage.success('集群创建成功')
    }
    
    showCreateDialog.value = false
    resetForm()
    loadClusters()
  } catch (error) {
    console.error('Failed to save cluster:', error)
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

const testConnection = async (cluster: Cluster) => {
  try {
    const result = await clustersApi.testConnection(cluster.id)
    if (result.status === 'success') {
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.error(`连接测试失败: ${result.message}`)
    }
  } catch (error) {
    console.error('Failed to test connection:', error)
  }
}

const resetForm = () => {
  editingCluster.value = null
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
</style>