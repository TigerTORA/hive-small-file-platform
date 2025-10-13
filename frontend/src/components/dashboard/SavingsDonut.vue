<template>
  <div class="savings-donut" :style="sizeStyle">
    <v-chart class="savings-donut__chart" :option="chartOption" autoresize />
    <div class="savings-donut__center">
      <span class="savings-donut__value">{{ percentLabel }}</span>
      <span v-if="innerLabel" class="savings-donut__label">{{ innerLabel }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'

use([CanvasRenderer, PieChart])

interface Props {
  percent?: number
  color?: string
  trackColor?: string
  size?: number
  thickness?: number
  innerLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  percent: 0,
  color: '#2563eb',
  trackColor: 'rgba(15, 23, 42, 0.12)',
  size: 96,
  thickness: 12,
  innerLabel: ''
})

const clampedPercent = computed(() => {
  if (!Number.isFinite(props.percent)) return 0
  return Math.max(0, Math.min(100, Number(props.percent)))
})

const percentLabel = computed(() => `${clampedPercent.value.toFixed(clampedPercent.value >= 10 ? 0 : 1)}%`)

const sizeStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`
}))

const chartOption = computed(() => {
  const ringRadiusOuter = '100%'
  const ringRadiusInner = `${100 - (props.thickness / (props.size / 2)) * 100}%`
  return {
    animation: false,
    tooltip: { show: false },
    legend: { show: false },
    series: [
      {
        type: 'pie',
        radius: [ringRadiusInner, ringRadiusOuter],
        avoidLabelOverlap: true,
        silent: true,
        clockwise: true,
        hoverAnimation: false,
        label: { show: false },
        labelLine: { show: false },
        data: [
          {
            value: clampedPercent.value,
            name: 'value',
            itemStyle: {
              color: props.color
            }
          },
          {
            value: 100 - clampedPercent.value,
            name: 'remaining',
            itemStyle: {
              color: props.trackColor
            }
          }
        ]
      }
    ]
  }
})
</script>

<style scoped>
.savings-donut {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.savings-donut__chart {
  width: 100%;
  height: 100%;
}

.savings-donut__center {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 2px;
  pointer-events: none;
}

.savings-donut__value {
  font-size: 18px;
  font-weight: 600;
  color: var(--gray-900);
}

.savings-donut__label {
  font-size: 11px;
  color: var(--gray-500);
}
</style>
