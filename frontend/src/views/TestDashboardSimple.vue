<template>
  <div class="test-dashboard-simple">
    <h1>测试中心 - 简化版本</h1>
    <p>这是一个测试页面，用于验证路由是否正常工作。</p>
    <p>如果您能看到这个页面，说明路由配置正确。</p>

    <div class="test-info">
      <h2>测试状态</h2>
      <p>
        API服务:
        <span :class="apiStatus.connected ? 'success' : 'error'">
          {{ apiStatus.connected ? '已连接' : '未连接' }}
        </span>
      </p>
      <p>测试数据: {{ testData ? '已加载' : '加载中...' }}</p>
    </div>

    <div class="actions">
      <button @click="testAPI">测试API连接</button>
      <button @click="loadData">加载测试数据</button>
    </div>

    <div
      v-if="testData"
      class="data-preview"
    >
      <h3>数据预览</h3>
      <pre>{{ JSON.stringify(testData, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup>
  import { ref, onMounted } from 'vue'

  // 响应式数据
  const apiStatus = ref({ connected: false })
  const testData = ref(null)

  // 测试API连接
  const testAPI = async () => {
    try {
      const response = await fetch('http://localhost:3001/api/health')
      if (response.ok) {
        apiStatus.value.connected = true
        console.log('API连接成功')
      } else {
        throw new Error('API响应异常')
      }
    } catch (error) {
      apiStatus.value.connected = false
      console.error('API连接失败:', error)
    }
  }

  // 加载测试数据
  const loadData = async () => {
    try {
      const response = await fetch('http://localhost:3001/api/test/overview')
      if (response.ok) {
        const result = await response.json()
        testData.value = result.data
        console.log('测试数据加载成功:', result.data)
      } else {
        throw new Error('数据加载失败')
      }
    } catch (error) {
      console.error('数据加载失败:', error)
    }
  }

  // 组件挂载时测试连接
  onMounted(() => {
    testAPI()
  })
</script>

<style scoped>
  .test-dashboard-simple {
    padding: 20px;
    max-width: 800px;
    margin: 0 auto;
  }

  .test-info {
    background: #f5f7fa;
    padding: 20px;
    border-radius: 8px;
    margin: 20px 0;
  }

  .success {
    color: #67c23a;
    font-weight: bold;
  }

  .error {
    color: #f56c6c;
    font-weight: bold;
  }

  .actions {
    margin: 20px 0;
  }

  .actions button {
    margin-right: 10px;
    padding: 10px 20px;
    background: #409eff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }

  .actions button:hover {
    background: #66b1ff;
  }

  .data-preview {
    background: #f4f4f5;
    padding: 15px;
    border-radius: 8px;
    margin-top: 20px;
  }

  .data-preview pre {
    font-size: 12px;
    line-height: 1.4;
    overflow-x: auto;
  }
</style>
