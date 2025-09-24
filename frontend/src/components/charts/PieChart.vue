<template>
  <div class="pie-chart-container">
    <div
      ref="chartRef"
      :style="{ width: '100%', height: height + 'px' }"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

interface PieChartData {
  name: string
  value: number
  description?: string
  details?: {
    count?: number
    size_gb?: number
    partitions?: { count: number; size_gb: number }
    tables?: { count: number; size_gb: number }
  }
}

interface Props {
  data: PieChartData[]
  title?: string
  height?: number
  showLegend?: boolean
  colorScheme?: string[]
  labelFormatter?: (item: PieChartData) => string
  tooltipFormatter?: (item: PieChartData) => string
}

const props = withDefaults(defineProps<Props>(), {
  height: 400,
  showLegend: true,
  colorScheme: () => [
    '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
    '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'
  ]
})

const emit = defineEmits<{
  sectorClick: [item: PieChartData]
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const formatTooltip = (params: any) => {
  const item = props.data.find(d => d.name === params.name)
  if (!item) return ''

  if (props.tooltipFormatter) {
    return props.tooltipFormatter(item)
  }

  let html = `<div style="font-weight: bold; margin-bottom: 8px;">${params.name}</div>`

  if (item.details) {
    if (item.details.partitions && item.details.tables) {
      // 冷数据分布格式
      html += `
        <div>📊 分区：${item.details.partitions.count}个 (${item.details.partitions.size_gb.toFixed(2)}GB)</div>
        <div>📋 表：${item.details.tables.count}个 (${item.details.tables.size_gb.toFixed(2)}GB)</div>
        <div style="margin-top: 4px; font-weight: bold;">💾 总计：${item.value.toFixed(2)}GB</div>
      `
    } else if (item.details.count !== undefined) {
      // 文件分类格式
      html += `
        <div>文件数：${item.details.count.toLocaleString()}</div>
        <div>大小：${item.details.size_gb?.toFixed(2)}GB</div>
        <div>占比：${params.percent}%</div>
      `
    }
  } else {
    html += `
      <div>数值：${item.value.toLocaleString()}</div>
      <div>占比：${params.percent}%</div>
    `
  }

  if (item.description) {
    html += `<div style="margin-top: 8px; color: #666; font-size: 12px;">${item.description}</div>`
  }

  return html
}

const initChart = () => {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)

  const option = {
    title: {
      text: props.title,
      left: 'center',
      top: 20,
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: formatTooltip,
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#ccc',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      }
    },
    legend: {
      show: props.showLegend,
      orient: 'vertical',
      left: 10,
      top: 'middle',
      textStyle: {
        fontSize: 12
      },
      itemWidth: 14,
      itemHeight: 10,
      itemGap: 8,
      formatter: (name: string) => {
        const item = props.data.find(d => d.name === name)
        if (props.labelFormatter && item) {
          return props.labelFormatter(item)
        }
        // 显示名称和数据
        if (item) {
          if (item.details) {
            if (item.details.count !== undefined) {
              return `${name}: ${item.details.count.toLocaleString()}`
            } else if (item.value) {
              return `${name}: ${item.value.toFixed(1)}GB`
            }
          }
          return `${name}: ${item.value.toLocaleString()}`
        }
        return name
      }
    },
    series: [
      {
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['65%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        labelLine: {
          show: false
        },
        data: props.data.map((item, index) => ({
          name: item.name,
          value: item.value,
          itemStyle: {
            color: props.colorScheme[index % props.colorScheme.length]
          }
        }))
      }
    ]
  }

  chart.setOption(option)

  // 点击事件
  chart.on('click', (params) => {
    const item = props.data.find(d => d.name === params.name)
    if (item) {
      emit('sectorClick', item)
    }
  })
}

const resizeChart = () => {
  if (chart) {
    chart.resize()
  }
}

onMounted(() => {
  nextTick(() => {
    initChart()
  })

  window.addEventListener('resize', resizeChart)
})

watch(
  () => props.data,
  (newData) => {
    console.log('🔄 PieChart watch触发，新数据:', {
      newData,
      hasChart: !!chart,
      dataLength: newData?.length,
      firstItem: newData?.[0]
    })

    if (chart) {
      // 完整重新设置option，确保legend formatter也使用最新数据
      const option = {
        title: {
          text: props.title,
          left: 'center',
          top: 20,
          textStyle: {
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        tooltip: {
          trigger: 'item',
          formatter: formatTooltip,
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          borderColor: '#ccc',
          borderWidth: 1,
          textStyle: {
            color: '#333'
          }
        },
        legend: {
          show: props.showLegend,
          orient: 'vertical',
          left: 10,
          top: 'middle',
          textStyle: {
            fontSize: 12
          },
          itemWidth: 14,
          itemHeight: 10,
          itemGap: 8,
          formatter: (name: string) => {
            const item = props.data.find(d => d.name === name)
            if (props.labelFormatter && item) {
              return props.labelFormatter(item)
            }
            // 显示名称和数据
            if (item) {
              if (item.details) {
                if (item.details.count !== undefined) {
                  return `${name}: ${item.details.count.toLocaleString()}`
                } else if (item.value) {
                  return `${name}: ${item.value.toFixed(1)}GB`
                }
              }
              return `${name}: ${item.value.toLocaleString()}`
            }
            return name
          }
        },
        series: [
          {
            type: 'pie',
            radius: ['35%', '65%'],
            center: ['65%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: '#fff',
              borderWidth: 2
            },
            label: {
              show: false,
              position: 'center'
            },
            emphasis: {
              label: {
                show: true,
                fontSize: 20,
                fontWeight: 'bold'
              },
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            },
            labelLine: {
              show: false
            },
            data: props.data.map((item, index) => ({
              name: item.name,
              value: item.value,
              itemStyle: {
                color: props.colorScheme[index % props.colorScheme.length]
              }
            }))
          }
        ]
      }
      chart.setOption(option, true) // 第二个参数true表示不合并，完全替换
      console.log('✅ PieChart option已更新')
    } else {
      console.warn('⚠️ PieChart chart实例不存在，无法更新')
    }
  },
  { deep: true }
)

watch(
  () => props.title,
  () => {
    if (chart) {
      chart.setOption({
        title: {
          text: props.title
        }
      })
    }
  }
)
</script>

<style scoped>
.pie-chart-container {
  width: 100%;
  position: relative;
}
</style>