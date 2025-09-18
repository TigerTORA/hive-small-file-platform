<template>
  <el-dialog
    v-model="visible"
    :title="editingCluster ? '编辑集群' : '添加集群'"
    width="600px"
    @close="handleClose"
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
        <el-button @click="handleClose">取消</el-button>
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
</template>

<script setup lang="ts">
  import { ref, watch, computed } from 'vue'
  import { ElMessage } from 'element-plus'
  import type { ClusterCreate, Cluster } from '@/api/clusters'

  interface Props {
    visible: boolean
    editingCluster?: Cluster | null
    testingConfig?: boolean
  }

  interface Emits {
    (e: 'update:visible', visible: boolean): void
    (
      e: 'save-cluster',
      data: {
        form: ClusterCreate
        validateConnection: boolean
        isEdit: boolean
        clusterId?: number
      }
    ): void
    (e: 'test-connection-config', config: ClusterCreate): void
  }

  const props = defineProps<Props>()
  const emit = defineEmits<Emits>()

  const clusterFormRef = ref()
  const selectedTemplate = ref('')
  const validateConnection = ref(false)

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

  const clusterRules = computed(() => ({
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
  }))

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

  // 监听编辑集群变化
  watch(
    () => props.editingCluster,
    newCluster => {
      if (newCluster) {
        clusterForm.value = { ...newCluster }
      } else {
        resetForm()
      }
    },
    { immediate: true }
  )

  const applyTemplate = (templateName: string) => {
    if (templateName && clusterTemplates[templateName as keyof typeof clusterTemplates]) {
      const template = clusterTemplates[templateName as keyof typeof clusterTemplates]
      clusterForm.value = { ...template }
      ElMessage.info(`已应用 ${templateName.toUpperCase()} 集群模板，请根据实际情况修改配置`)
    }
  }

  const onAuthTypeChange = (authType: string) => {
    if (authType === 'NONE') {
      clusterForm.value.hive_username = ''
      clusterForm.value.hive_password = ''
    }
    clusterFormRef.value?.clearValidate(['hive_username', 'hive_password'])
  }

  const saveCluster = async () => {
    try {
      await clusterFormRef.value.validate()
      emit('save-cluster', {
        form: clusterForm.value,
        validateConnection: validateConnection.value,
        isEdit: !!props.editingCluster,
        clusterId: props.editingCluster?.id
      })
    } catch (error) {
      console.error('Form validation failed:', error)
    }
  }

  const testConfigConnection = async () => {
    try {
      await clusterFormRef.value.validate()
      emit('test-connection-config', clusterForm.value)
    } catch (error: any) {
      if (error.fields) {
        ElMessage.error('请先完成表单填写')
      }
    }
  }

  const handleClose = () => {
    emit('update:visible', false)
  }

  const resetForm = () => {
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

  defineExpose({ resetForm })
</script>

<style scoped>
  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: var(--space-3);
  }
</style>
