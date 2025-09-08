<template>
  <div id="app">
    <el-container>
      <!-- Header -->
      <el-header height="60px">
        <div class="header">
          <h1>Hive Small File Platform</h1>
          <el-button-group>
            <el-button @click="activeTab = 'clusters'" :type="activeTab === 'clusters' ? 'primary' : ''">
              Clusters
            </el-button>
            <el-button @click="activeTab = 'scanner'" :type="activeTab === 'scanner' ? 'primary' : ''">
              Scanner
            </el-button>
            <el-button @click="activeTab = 'analysis'" :type="activeTab === 'analysis' ? 'primary' : ''">
              Analysis
            </el-button>
          </el-button-group>
        </div>
      </el-header>

      <!-- Main Content -->
      <el-main>
        <!-- Clusters Tab -->
        <div v-if="activeTab === 'clusters'">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-card header="Add Cluster">
                <el-form :model="newCluster" label-width="150px">
                  <el-form-item label="Name">
                    <el-input v-model="newCluster.name" placeholder="Cluster name" />
                  </el-form-item>
                  <el-form-item label="MetaStore URL">
                    <el-input v-model="newCluster.hive_metastore_url" 
                              placeholder="mysql://user:pass@host:port/hive" />
                  </el-form-item>
                  <el-form-item label="HDFS NameNode">
                    <el-input v-model="newCluster.hdfs_namenode_url" 
                              placeholder="http://namenode:9870" />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" @click="createCluster" :loading="loading">
                      Add Cluster
                    </el-button>
                  </el-form-item>
                </el-form>
              </el-card>
            </el-col>

            <el-col :span="12">
              <el-card header="Clusters">
                <el-table :data="clusters" v-loading="loading">
                  <el-table-column prop="name" label="Name" />
                  <el-table-column label="Status">
                    <template #default="{ row }">
                      <el-button size="small" @click="testCluster(row)">Test</el-button>
                    </template>
                  </el-table-column>
                  <el-table-column label="Actions">
                    <template #default="{ row }">
                      <el-button size="small" type="danger" @click="deleteCluster(row)">
                        Delete
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <!-- Scanner Tab -->
        <div v-if="activeTab === 'scanner'">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card header="Scan Configuration">
                <el-form :model="scanConfig" label-width="100px">
                  <el-form-item label="Cluster">
                    <el-select v-model="scanConfig.cluster_id" placeholder="Select cluster" @change="loadDatabases">
                      <el-option v-for="cluster in clusters" :key="cluster.id" 
                                 :label="cluster.name" :value="cluster.id" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="Database">
                    <el-select v-model="scanConfig.database_name" placeholder="Select database" @change="loadTables">
                      <el-option v-for="db in databases" :key="db" :label="db" :value="db" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="Table">
                    <el-select v-model="scanConfig.table_name" placeholder="All tables" clearable>
                      <el-option v-for="table in tables" :key="table.table_name" 
                                 :label="table.table_name" :value="table.table_name" />
                    </el-select>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" @click="startScan" :loading="scanning">
                      Start Scan
                    </el-button>
                  </el-form-item>
                </el-form>
              </el-card>
            </el-col>

            <el-col :span="16">
              <el-card header="Scan Results">
                <div v-if="scanResult">
                  <el-descriptions :column="2" border>
                    <el-descriptions-item label="Cluster">{{ getClusterName(scanConfig.cluster_id) }}</el-descriptions-item>
                    <el-descriptions-item label="Database">{{ scanResult.database_name || scanConfig.database_name }}</el-descriptions-item>
                    <el-descriptions-item label="Status">
                      <el-tag type="success">Completed</el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="Tables Scanned">
                      {{ scanResult.result?.total_tables || 1 }}
                    </el-descriptions-item>
                  </el-descriptions>
                  
                  <div v-if="scanResult.result?.results" class="mt-20">
                    <h3>Table Results</h3>
                    <el-table :data="scanResult.result.results">
                      <el-table-column prop="table_name" label="Table" />
                      <el-table-column prop="status" label="Status">
                        <template #default="{ row }">
                          <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
                            {{ row.status }}
                          </el-tag>
                        </template>
                      </el-table-column>
                      <el-table-column label="Files">
                        <template #default="{ row }">
                          {{ row.stats?.total_files || 0 }}
                        </template>
                      </el-table-column>
                      <el-table-column label="Small Files">
                        <template #default="{ row }">
                          {{ row.stats?.small_files || 0 }}
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
                </div>
                <el-empty v-else description="No scan results" />
              </el-card>
            </el-col>
          </el-row>
        </div>

        <!-- Analysis Tab -->
        <div v-if="activeTab === 'analysis'">
          <el-row :gutter="20">
            <el-col :span="24">
              <el-card header="Small File Analysis">
                <div class="analysis-controls">
                  <el-select v-model="analysisClusterId" placeholder="Select cluster" @change="loadAnalysis">
                    <el-option v-for="cluster in clusters" :key="cluster.id" 
                               :label="cluster.name" :value="cluster.id" />
                  </el-select>
                  <el-button @click="loadAnalysis" :loading="loading">Refresh</el-button>
                </div>

                <div v-if="analysis" class="mt-20">
                  <!-- Summary Cards -->
                  <el-row :gutter="20" class="mb-20">
                    <el-col :span="6">
                      <el-card>
                        <el-statistic title="Total Tables" :value="analysis.summary.total_tables" />
                      </el-card>
                    </el-col>
                    <el-col :span="6">
                      <el-card>
                        <el-statistic title="Critical Tables" :value="analysis.summary.critical_tables" />
                      </el-card>
                    </el-col>
                    <el-col :span="6">
                      <el-card>
                        <el-statistic title="High Priority" :value="analysis.summary.high_priority_tables" />
                      </el-card>
                    </el-col>
                    <el-col :span="6">
                      <el-card>
                        <el-statistic title="Overall Score" :value="getOverallScore()" />
                      </el-card>
                    </el-col>
                  </el-row>

                  <!-- Analysis Table -->
                  <el-table :data="analysis.tables" height="500">
                    <el-table-column prop="database_name" label="Database" width="120" />
                    <el-table-column prop="table_name" label="Table" width="150" />
                    <el-table-column prop="total_files" label="Total Files" width="100" />
                    <el-table-column prop="small_files" label="Small Files" width="100" />
                    <el-table-column prop="small_file_ratio" label="Ratio %" width="100">
                      <template #default="{ row }">
                        <el-progress :percentage="row.small_file_ratio" :color="getProgressColor(row.small_file_ratio)" />
                      </template>
                    </el-table-column>
                    <el-table-column prop="priority" label="Priority" width="100">
                      <template #default="{ row }">
                        <el-tag :type="getPriorityType(row.priority)">{{ row.priority }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="total_size_gb" label="Size (GB)" width="100" />
                    <el-table-column prop="avg_file_size_mb" label="Avg Size (MB)" width="120" />
                    <el-table-column prop="last_scan" label="Last Scan" width="150">
                      <template #default="{ row }">
                        {{ new Date(row.last_scan).toLocaleString() }}
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
                <el-empty v-else description="Select a cluster to view analysis" />
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as api from './api'

// State
const loading = ref(false)
const scanning = ref(false)
const activeTab = ref('clusters')
const clusters = ref<any[]>([])
const databases = ref<string[]>([])
const tables = ref<any[]>([])
const scanResult = ref<any>(null)
const analysis = ref<any>(null)
const analysisClusterId = ref<number>()

// Forms
const newCluster = ref({
  name: '',
  hive_metastore_url: '',
  hdfs_namenode_url: '',
  small_file_threshold: 128 * 1024 * 1024
})

const scanConfig = ref({
  cluster_id: undefined as number | undefined,
  database_name: '',
  table_name: ''
})

// Methods
const loadClusters = async () => {
  try {
    loading.value = true
    const response = await api.getClusters()
    clusters.value = response.data
  } catch (error) {
    ElMessage.error('Failed to load clusters')
  } finally {
    loading.value = false
  }
}

const createCluster = async () => {
  if (!newCluster.value.name || !newCluster.value.hive_metastore_url || !newCluster.value.hdfs_namenode_url) {
    ElMessage.error('Please fill in all required fields')
    return
  }

  try {
    loading.value = true
    await api.createCluster(newCluster.value)
    ElMessage.success('Cluster created successfully')
    newCluster.value = { name: '', hive_metastore_url: '', hdfs_namenode_url: '', small_file_threshold: 128 * 1024 * 1024 }
    await loadClusters()
  } catch (error) {
    ElMessage.error('Failed to create cluster')
  } finally {
    loading.value = false
  }
}

const deleteCluster = async (cluster: any) => {
  try {
    await ElMessageBox.confirm('Are you sure you want to delete this cluster?', 'Confirm Delete')
    await api.deleteCluster(cluster.id)
    ElMessage.success('Cluster deleted successfully')
    await loadClusters()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Failed to delete cluster')
    }
  }
}

const testCluster = async (cluster: any) => {
  try {
    loading.value = true
    const response = await api.testCluster(cluster.id)
    const { connections } = response.data
    
    if (connections.metastore_connection && connections.hdfs_connection) {
      ElMessage.success('All connections successful')
    } else {
      ElMessage.warning('Some connections failed - check configuration')
    }
  } catch (error) {
    ElMessage.error('Connection test failed')
  } finally {
    loading.value = false
  }
}

const loadDatabases = async () => {
  if (!scanConfig.value.cluster_id) return
  
  try {
    const response = await api.getDatabases(scanConfig.value.cluster_id)
    databases.value = response.data.databases
  } catch (error) {
    ElMessage.error('Failed to load databases')
  }
}

const loadTables = async () => {
  if (!scanConfig.value.cluster_id || !scanConfig.value.database_name) return
  
  try {
    const response = await api.getTables(scanConfig.value.cluster_id, scanConfig.value.database_name)
    tables.value = response.data.tables
  } catch (error) {
    ElMessage.error('Failed to load tables')
  }
}

const startScan = async () => {
  if (!scanConfig.value.cluster_id || !scanConfig.value.database_name) {
    ElMessage.error('Please select cluster and database')
    return
  }

  try {
    scanning.value = true
    const response = await api.scanTables(scanConfig.value)
    scanResult.value = response.data
    ElMessage.success('Scan completed successfully')
  } catch (error) {
    ElMessage.error('Scan failed')
  } finally {
    scanning.value = false
  }
}

const loadAnalysis = async () => {
  if (!analysisClusterId.value) return

  try {
    loading.value = true
    const response = await api.getAnalysis(analysisClusterId.value)
    analysis.value = response.data
  } catch (error) {
    ElMessage.error('Failed to load analysis')
  } finally {
    loading.value = false
  }
}

const getClusterName = (id: number) => {
  const cluster = clusters.value.find(c => c.id === id)
  return cluster?.name || 'Unknown'
}

const getOverallScore = () => {
  if (!analysis.value) return 0
  const { total_tables, critical_tables, high_priority_tables } = analysis.value.summary
  if (total_tables === 0) return 100
  
  const problemTables = critical_tables + high_priority_tables
  return Math.max(0, 100 - Math.round((problemTables / total_tables) * 100))
}

const getProgressColor = (ratio: number) => {
  if (ratio > 80) return '#f56c6c'
  if (ratio > 60) return '#e6a23c'
  if (ratio > 40) return '#909399'
  return '#67c23a'
}

const getPriorityType = (priority: string) => {
  const types: Record<string, string> = {
    'CRITICAL': 'danger',
    'HIGH': 'warning',
    'MEDIUM': 'info',
    'LOW': 'success'
  }
  return types[priority] || 'info'
}

// Initialize
onMounted(() => {
  loadClusters()
})
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.header h1 {
  margin: 0;
  color: #409EFF;
}

.analysis-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.mt-20 {
  margin-top: 20px;
}

.mb-20 {
  margin-bottom: 20px;
}
</style>