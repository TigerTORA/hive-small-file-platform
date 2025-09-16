<template>
  <FeatureFlagProvider>
    <template #default="{ features, isEnabled }">
      <div class="app" data-testid="app-loaded">
        <el-container>
          <!-- Header -->
          <el-header class="app-header">
            <div class="header-left">
              <h1 class="app-title">
                <el-icon><DataBoard /></el-icon>
                Hive 小文件治理平台
                <el-tag v-if="isEnabled('demoMode')" type="warning" size="small" style="margin-left: 8px;">
                  演示模式
                </el-tag>
              </h1>
            </div>
            <div class="header-right">
              <!-- 全屏模式切换 -->
              <el-button
                v-if="isEnabled('fullscreenMode')"
                :icon="isFullscreen ? Close : FullScreen"
                circle
                size="small"
                @click="toggleFullscreen"
                :title="isFullscreen ? '退出全屏' : '进入全屏'"
                style="margin-right: 12px;"
              />

              <!-- 主题切换 -->
              <el-switch
                v-if="isEnabled('darkTheme')"
                v-model="isDarkTheme"
                :active-action-icon="Moon"
                :inactive-action-icon="Sunny"
                size="large"
                style="margin-right: 16px;"
                @change="toggleTheme"
              />

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
            <el-aside
              v-if="!isFullscreen"
              width="250px"
              class="app-sidebar"
            >
              <el-menu
                :default-active="$route.path"
                router
                class="sidebar-menu"
                :background-color="isDarkTheme ? '#1f2937' : '#304156'"
                :text-color="isDarkTheme ? '#d1d5db' : '#bfcbd9'"
                active-text-color="#409eff"
              >

                <el-menu-item index="/">
                  <el-icon><Monitor /></el-icon>
                  <span>监控中心</span>
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

                <el-menu-item
                  v-if="isEnabled('demoMode')"
                  index="/test-dashboard"
                >
                  <el-icon><DataBoard /></el-icon>
                  <span>测试中心</span>
                </el-menu-item>
              </el-menu>
            </el-aside>

            <!-- Main Content -->
            <el-main
              class="app-main"
              :class="{ 'fullscreen-main': isFullscreen, 'dark-theme': isDarkTheme }"
              data-testid="main-content"
            >
              <router-view />
            </el-main>
          </el-container>
        </el-container>
      </div>
    </template>
  </FeatureFlagProvider>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  User,
  CaretBottom,
  DataBoard,
  Connection,
  Grid,
  List,
  Setting,
  Monitor,
  FullScreen,
  Close,
  Moon,
  Sunny
} from '@element-plus/icons-vue'
import FeatureFlagProvider from '@/components/FeatureFlagProvider.vue'

// 全屏状态
const isFullscreen = ref(false)
const isDarkTheme = ref(false)

// 全屏切换
const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

// 主题切换
const toggleTheme = (isDark: boolean) => {
  isDarkTheme.value = isDark
  document.documentElement.classList.toggle('dark', isDark)
}

// 监听全屏状态变化
document.addEventListener('fullscreenchange', () => {
  isFullscreen.value = !!document.fullscreenElement
})
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
  transition: all 0.3s ease;
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
  transition: all 0.3s ease;
}

.sidebar-menu {
  border: none;
  height: 100%;
}

.app-main {
  background-color: #f0f2f5;
  padding: 20px;
  transition: all 0.3s ease;
}

.fullscreen-main {
  padding: 0;
  background-color: #000;
}

/* 深色主题 */
.dark-theme {
  background-color: #1f2937 !important;
  color: #f9fafb;
}

.dark-theme .app-header {
  background-color: #374151;
  border-bottom-color: #4b5563;
}

.dark-theme .app-title {
  color: #f9fafb;
}

.dark-theme .user-info {
  color: #d1d5db;
}

/* 全屏模式样式 */
.app:fullscreen {
  background: #000;
}

.app:fullscreen .app-header {
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.app:fullscreen .app-title {
  color: #fff;
}

.app:fullscreen .user-info {
  color: #fff;
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