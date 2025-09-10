<template>
  <div class="app">
    <el-container>
      <!-- Header -->
      <el-header class="app-header">
        <div class="header-left">
          <h1 class="app-title">
            <el-icon><DataBoard /></el-icon>
            Hive 小文件治理平台
          </h1>
        </div>
        <div class="header-right">
          <el-dropdown>
            <span class="user-info">
              <el-icon><User /></el-icon>
              管理员
              <el-icon class="el-icon--right"><CaretBottom /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>设置</el-dropdown-item>
                <el-dropdown-item>退出</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-container>
        <!-- Sidebar -->
        <el-aside width="250px" class="app-sidebar">
          <el-menu
            :default-active="$route.path"
            router
            class="sidebar-menu"
            background-color="#304156"
            text-color="#bfcbd9"
            active-text-color="#409eff"
          >
            <el-menu-item index="/dashboard">
              <el-icon><Monitor /></el-icon>
              <span>监控仪表板</span>
            </el-menu-item>
            
            <el-menu-item index="/clusters">
              <el-icon><Connection /></el-icon>
              <span>集群管理</span>
            </el-menu-item>
            
            <el-menu-item index="/tables">
              <el-icon><Grid /></el-icon>
              <span>表管理</span>
            </el-menu-item>
            
            <el-menu-item index="/tasks">
              <el-icon><List /></el-icon>
              <span>任务管理</span>
            </el-menu-item>
            
            <el-menu-item index="/settings">
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <!-- Main Content -->
        <el-main class="app-main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { 
  User, 
  CaretBottom, 
  DataBoard, 
  Monitor, 
  Connection, 
  Grid, 
  List, 
  Setting 
} from '@element-plus/icons-vue'
</script>

<style scoped>
.app {
  height: 100vh;
}

.app-header {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.app-title {
  margin: 0;
  color: #2c3e50;
  font-size: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: #606266;
}

.app-sidebar {
  background-color: #304156;
}

.sidebar-menu {
  border: none;
  height: 100%;
}

.app-main {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>

<style>
html, body {
  margin: 0;
  padding: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

#app {
  height: 100vh;
}
</style>