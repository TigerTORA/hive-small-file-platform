<template>
  <div class="cluster-settings">
    <el-form
      :model="settings"
      :rules="rules"
      ref="settingsFormRef"
      label-width="140px"
    >
      <el-card>
        <template #header>
          <span>基本配置</span>
        </template>

        <el-form-item label="集群名称" prop="name">
          <el-input v-model="settings.name" placeholder="请输入集群名称" />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="settings.description"
            type="textarea"
            placeholder="集群描述（可选）"
          />
        </el-form-item>
      </el-card>

      <el-card style="margin-top: 20px">
        <template #header>
          <span>连接配置</span>
        </template>

        <el-form-item label="Hive 主机" prop="hive_host">
          <el-input
            v-model="settings.hive_host"
            placeholder="Hive Server2 主机地址"
          />
        </el-form-item>

        <el-form-item label="Hive 端口">
          <el-input-number
            v-model="settings.hive_port"
            :min="1"
            :max="65535"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="MetaStore URL" prop="hive_metastore_url">
          <el-input
            v-model="settings.hive_metastore_url"
            placeholder="postgresql://user:pass@host:5432/hive"
          />
        </el-form-item>

        <el-form-item label="HDFS/HttpFS 地址" prop="hdfs_namenode_url">
          <el-input
            v-model="settings.hdfs_namenode_url"
            placeholder="hdfs://namenode:9000"
          />
        </el-form-item>

        <el-form-item label="HDFS 用户">
          <el-input v-model="settings.hdfs_user" placeholder="hdfs" />
        </el-form-item>
      </el-card>

      <el-card style="margin-top: 20px">
        <template #header>
          <span>小文件配置</span>
        </template>

        <el-form-item label="小文件阈值">
          <el-input-number
            v-model="settings.small_file_threshold"
            :min="1024"
            :step="1024 * 1024"
            style="width: 200px"
          />
          <span style="margin-left: 8px; color: #909399"
            >字节 (默认: 128MB)</span
          >
        </el-form-item>

        <el-form-item label="启用扫描">
          <el-switch v-model="settings.scan_enabled" />
        </el-form-item>
      </el-card>

      <div class="form-actions">
        <el-button @click="resetForm">重置</el-button>
        <el-button @click="testConnection" :loading="testing">
          <el-icon><Connection /></el-icon>
          快速测试
        </el-button>
        <el-button type="primary" @click="saveSettings" :loading="saving">
          保存配置
        </el-button>
      </div>
    </el-form>

    <!-- Connection Test Dialog -->
    <ConnectionTestDialog
      v-model:visible="showTestDialog"
      :cluster-config="settings"
      :test-result="testResult"
      :testing="testingConnection"
      :error="testError"
      @retest="handleRetest"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Connection } from "@element-plus/icons-vue";
import { clustersApi, type Cluster } from "@/api/clusters";
import ConnectionTestDialog from "@/components/ConnectionTestDialog.vue";

interface Props {
  clusterId: number;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  updated: [];
}>();

// Data
const settings = ref<Cluster>({
  id: 0,
  name: "",
  description: "",
  hive_host: "",
  hive_port: 10000,
  hive_database: "default",
  hive_metastore_url: "",
  hdfs_namenode_url: "",
  hdfs_user: "hdfs",
  small_file_threshold: 128 * 1024 * 1024,
  scan_enabled: true,
  status: "active",
  created_time: "",
  updated_time: "",
});

const originalSettings = ref<Cluster | null>(null);
const saving = ref(false);
const testing = ref(false);

// Connection test
const showTestDialog = ref(false);
const testingConnection = ref(false);
const testResult = ref<any>(null);
const testError = ref<string | null>(null);

// Form validation
const rules = {
  name: [{ required: true, message: "请输入集群名称", trigger: "blur" }],
  hive_host: [
    { required: true, message: "请输入 Hive 主机地址", trigger: "blur" },
  ],
  hive_metastore_url: [
    { required: true, message: "请输入 MetaStore URL", trigger: "blur" },
  ],
  hdfs_namenode_url: [
    { required: true, message: "请输入 HDFS/HttpFS 地址", trigger: "blur" },
  ],
};

const settingsFormRef = ref();

// Methods
const loadSettings = async () => {
  try {
    const cluster = await clustersApi.get(props.clusterId);
    settings.value = { ...cluster };
    originalSettings.value = { ...cluster };
  } catch (error) {
    console.error("Failed to load cluster settings:", error);
    ElMessage.error("加载集群配置失败");
  }
};

const saveSettings = async () => {
  try {
    await settingsFormRef.value.validate();

    saving.value = true;
    await clustersApi.update(props.clusterId, settings.value);

    ElMessage.success("配置保存成功");
    originalSettings.value = { ...settings.value };
    emit("updated");
  } catch (error: any) {
    if (error.fields) {
      ElMessage.error("请检查表单填写");
    } else {
      console.error("Failed to save settings:", error);
      const errorMsg =
        error.response?.data?.detail || error.message || "保存失败";
      ElMessage.error(errorMsg);
    }
  } finally {
    saving.value = false;
  }
};

const resetForm = () => {
  if (originalSettings.value) {
    settings.value = { ...originalSettings.value };
  }
};

const testConnection = async () => {
  try {
    await settingsFormRef.value.validate();

    testResult.value = null;
    testError.value = null;
    testingConnection.value = true;
    showTestDialog.value = true;

    const result = await clustersApi.testConnectionConfig(settings.value);
    testResult.value = result;
  } catch (error: any) {
    if (error.fields) {
      ElMessage.error("请先完成表单填写");
      showTestDialog.value = false;
    } else {
      console.error("Failed to test connection:", error);
      testError.value =
        error.response?.data?.detail || error.message || "连接测试失败";
    }
  } finally {
    testingConnection.value = false;
  }
};

const handleRetest = async () => {
  testResult.value = null;
  testError.value = null;
  testingConnection.value = true;

  try {
    const result = await clustersApi.testConnectionConfig(settings.value);
    testResult.value = result;
  } catch (error: any) {
    console.error("Failed to retest connection:", error);
    testError.value =
      error.response?.data?.detail || error.message || "重新测试失败";
  } finally {
    testingConnection.value = false;
  }
};

onMounted(() => {
  loadSettings();
});
</script>

<style scoped>
.cluster-settings {
  height: 100%;
}

.form-actions {
  margin-top: 30px;
  text-align: right;
  display: flex;
  gap: 15px;
  justify-content: flex-end;
}

.el-card {
  margin-bottom: 20px;
}

.el-card:last-child {
  margin-bottom: 0;
}
</style>
