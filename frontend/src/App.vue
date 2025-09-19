<template>
  <FeatureFlagProvider>
    <template #default="{ features, isEnabled }">
      <div
        class="app cloudera-app"
        data-testid="app-loaded"
      >
        <!-- Cloudera 风格侧边栏 -->
        <aside
          class="cloudera-sidebar"
          :class="{ collapsed: sidebarCollapsed }"
        >
          <!-- 品牌区域 -->
          <div class="sidebar-brand">
            <div class="logo">DN</div>
            <div class="brand-text">DataNova</div>
          </div>

          <!-- 导航菜单 -->
          <nav class="sidebar-nav">
            <!-- 核心功能 - 仅在选择集群后且不在集群管理页面时显示 -->
            <div class="nav-section" v-if="monitoringStore.hasSelectedCluster && !isInClusterManagement">
              <div class="nav-section-title">核心功能</div>
              <!-- 监控中心 -->
              <div class="nav-item">
                <router-link
                  to="/"
                  class="nav-link"
                  :class="{ active: $route.path === '/' }"
                >
                  <div class="nav-icon">
                    <el-icon><Monitor /></el-icon>
                  </div>
                  <span class="nav-text">监控中心</span>
                </router-link>
              </div>
              <!-- 表管理 -->
              <div class="nav-item">
                <router-link
                  to="/tables"
                  class="nav-link"
                  :class="{ active: $route.path.startsWith('/tables') }"
                >
                  <div class="nav-icon">
                    <el-icon><Grid /></el-icon>
                  </div>
                  <span class="nav-text">表管理</span>
                </router-link>
              </div>
              <!-- 任务管理 -->
              <div class="nav-item">
                <router-link
                  to="/tasks"
                  class="nav-link"
                  :class="{ active: $route.path === '/tasks' }"
                >
                  <div class="nav-icon">
                    <el-icon><List /></el-icon>
                  </div>
                  <span class="nav-text">任务管理</span>
                </router-link>
              </div>
            </div>

            <div class="nav-section">
              <div class="nav-section-title">系统管理</div>
              <!-- 集群管理 - 总是显示 -->
              <div class="nav-item">
                <router-link
                  to="/clusters"
                  class="nav-link"
                  :class="{ active: $route.path.startsWith('/clusters') }"
                >
                  <div class="nav-icon">
                    <el-icon><Connection /></el-icon>
                  </div>
                  <span class="nav-text">集群管理</span>
                </router-link>
              </div>
              <div class="nav-item">
                <router-link
                  to="/settings"
                  class="nav-link"
                  :class="{ active: $route.path === '/settings' }"
                >
                  <div class="nav-icon">
                    <el-icon><Setting /></el-icon>
                  </div>
                  <span class="nav-text">系统设置</span>
                </router-link>
              </div>
            </div>
          </nav>

          <!-- 折叠按钮 -->
          <div
            class="sidebar-toggle"
            @click="toggleSidebar"
          >
            <el-icon>
              <component :is="sidebarCollapsed ? 'Expand' : 'Fold'" />
            </el-icon>
          </div>
        </aside>

        <!-- 主内容区域 -->
        <div
          class="cloudera-main"
          :class="{ 'sidebar-collapsed': sidebarCollapsed }"
        >
          <!-- Cloudera 风格头部 -->
          <header class="cloudera-header">
            <div class="header-left">
              <div class="header-breadcrumb">
                <span>{{ currentPageTitle }}</span>
                <el-tag
                  v-if="isEnabled('demoMode')"
                  type="warning"
                  size="small"
                  style="margin-left: 8px"
                >
                  演示模式
                </el-tag>
              </div>
            </div>
            <div class="header-right">
              <!-- 刷新按钮 -->
              <el-button
                :icon="Refresh"
                circle
                size="small"
                @click="refreshPage"
                title="刷新数据"
                class="cloudera-btn secondary"
              />

              <!-- 全屏模式切换 -->
              <el-button
                v-if="isEnabled('fullscreenMode')"
                :icon="isFullscreen ? Close : FullScreen"
                circle
                size="small"
                @click="toggleFullscreen"
                :title="isFullscreen ? '退出全屏' : '进入全屏'"
                class="cloudera-btn secondary"
              />

              <!-- 主题切换 -->
              <el-switch
                v-if="isEnabled('darkTheme')"
                v-model="isDarkTheme"
                :active-action-icon="Moon"
                :inactive-action-icon="Sunny"
                size="large"
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
          </header>

          <!-- 主内容区域 -->
          <main class="page-content">
            <router-view v-slot="{ Component }">
              <transition
                name="page"
                mode="out-in"
              >
                <component :is="Component" />
              </transition>
            </router-view>
          </main>
        </div>
      </div>
    </template>
  </FeatureFlagProvider>
</template>

<script setup lang="ts">
  import { ref, computed } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
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
    Sunny,
    Refresh,
    Expand,
    Fold
  } from '@element-plus/icons-vue'
  import FeatureFlagProvider from '@/components/FeatureFlagProvider.vue'
  import { useMonitoringStore } from '@/stores/monitoring'

  const route = useRoute()
  const router = useRouter()
  const monitoringStore = useMonitoringStore()

  // 侧边栏状态
  const sidebarCollapsed = ref(false)

  // 全屏状态
  const isFullscreen = ref(false)
  const isDarkTheme = ref(false)

  // 检查是否在集群管理页面
  const isInClusterManagement = computed(() => route.path.startsWith('/clusters'))

  // 页面标题计算
  const currentPageTitle = computed(() => {
    const titleMap: Record<string, string> = {
      '/': '监控中心',
      '/clusters': '集群管理',
      '/tasks': '任务管理',
      '/settings': '系统设置'
    }

    // 处理动态路由
    if (route.path.startsWith('/clusters/')) {
      return '集群详情'
    }

    return titleMap[route.path] || '页面'
  })

  // 侧边栏切换
  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  // 刷新页面
  const refreshPage = () => {
    window.location.reload()
  }

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

<style>
  /* 引入设计系统 */
  @import './styles/design-system.css';
  @import './styles/cloudera-theme.css';

  /* 应用全局样式 */
  .cloudera-app {
    min-height: 100vh;
    overflow: visible;
  }

  /* 页面内容区域 */
  .page-content {
    padding: 0;
    min-height: auto;
    overflow-y: visible;
    background: var(--bg-app);
  }

  /* 用户信息样式 */
  .user-info {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    cursor: pointer;
    color: var(--gray-600);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-lg);
    transition: all var(--transition-fast);
  }

  .user-info:hover {
    background: var(--gray-100);
    color: var(--gray-900);
  }

  /* 页面过渡动画 */
  .page-enter-active,
  .page-leave-active {
    transition: all var(--transition-normal);
  }

  .page-enter-from {
    opacity: 0;
    transform: translateY(20px);
  }

  .page-leave-to {
    opacity: 0;
    transform: translateY(-20px);
  }
</style>
