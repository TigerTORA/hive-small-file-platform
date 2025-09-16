<template>
  <BigScreenMonitor :cluster-id="clusterId" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import BigScreenMonitor from '@/components/BigScreenMonitor.vue'

const route = useRoute()

const clusterId = computed(() => {
  return route.query.cluster as string || 'cluster-1'
})
</script>

<style scoped>
/* 大屏页面不需要额外样式，由BigScreenMonitor组件处理 */
</style>