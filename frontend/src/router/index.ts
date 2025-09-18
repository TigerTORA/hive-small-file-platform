import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: '监控中心' }
    },
    {
      path: '/clusters',
      name: 'ClustersManagement',
      component: () => import('@/views/ClustersManagement.vue'),
      meta: { title: '集群管理' }
    },
    {
      path: '/clusters/:id',
      name: 'ClusterDetail',
      component: () => import('@/views/ClusterDetail.vue'),
      meta: { title: '集群详情' },
      props: true
    },
    {
      path: '/tables',
      name: 'Tables',
      component: () => import('@/views/Tables.vue'),
      meta: { title: '表管理' }
    },
    {
      path: '/tables/:clusterId/:database/:tableName',
      name: 'TableDetail',
      component: () => import('@/views/TableDetail.vue'),
      meta: { title: '表详情' },
      props: true
    },
    {
      path: '/tasks',
      name: 'Tasks',
      component: () => import('@/views/Tasks.vue'),
      meta: { title: '任务管理' }
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/Settings.vue'),
      meta: { title: '系统设置' }
    },
    {
      path: '/big-screen',
      name: 'BigScreen',
      component: () => import('@/views/BigScreen.vue'),
      meta: { title: '实时监控大屏', fullscreen: true }
    },
    {
      path: '/demo',
      name: 'DemoComponents',
      component: () => import('@/views/DemoComponents.vue'),
      meta: { title: 'DataNova 组件库展示' }
    }
  ]
})

// 设置页面标题
router.beforeEach((to, from, next) => {
  if (to.meta?.title) {
    document.title = `${to.meta.title} - DataNova`
  }
  next()
})

export default router
