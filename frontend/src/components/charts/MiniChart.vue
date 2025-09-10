<template>
  <div class="mini-chart" :style="containerStyle">
    <v-chart
      class="mini-echarts"
      :option="chartOption"
      autoresize
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { useCharts } from '@/composables/useCharts'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  GridComponent
])

interface Props {
  data: number[]
  type?: 'line' | 'bar'
  width?: number
  height?: number
  color?: string
  backgroundColor?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'line',
  width: 120,
  height: 60,
  color: '#409EFF',
  backgroundColor: 'transparent'
})

const { getMiniChartOption } = useCharts()

// 计算属性
const containerStyle = computed(() => ({
  width: `${props.width}px`,
  height: `${props.height}px`,
  background: props.backgroundColor
}))

const chartOption = computed(() => {
  return getMiniChartOption(props.data, props.type)
})
</script>

<style scoped>
.mini-chart {
  position: relative;
  overflow: hidden;
}

.mini-echarts {
  width: 100%;
  height: 100%;
}
</style>