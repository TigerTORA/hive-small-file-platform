import { computed } from 'vue'
import { useMonitoringStore } from '@/stores/monitoring'
import type { TrendPoint, FileDistributionItem } from '@/api/dashboard'

export function useCharts() {
  const monitoringStore = useMonitoringStore()

  // 基础图表配置
  const baseChartOption = computed(() => ({
    backgroundColor: 'transparent',
    textStyle: {
      fontFamily: 'Arial, sans-serif',
      fontSize: 12
    },
    animation: true,
    animationDuration: 1000,
    animationEasing: 'cubicOut'
  }))

  // 趋势图表配置
  function getTrendChartOption(data: TrendPoint[]) {
    const dates = data.map(item => item.date)
    const smallFiles = data.map(item => item.small_files)
    const totalFiles = data.map(item => item.total_files)
    const ratios = data.map(item => item.ratio)

    return {
      ...baseChartOption.value,
      title: {
        text: '小文件趋势分析',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
          color: monitoringStore.settings.theme === 'dark' ? '#fff' : '#333'
        },
        left: 'center',
        top: 20
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          crossStyle: {
            color: '#999'
          }
        },
        formatter: function (params: any[]) {
          const date = params[0].axisValue
          let html = `<div style="padding: 8px;"><strong>${date}</strong><br/>`
          
          params.forEach((param: any) => {
            const color = param.color
            const name = param.seriesName
            const value = param.value
            
            if (name === '小文件占比') {
              html += `<div style="margin: 4px 0;"><span style="color: ${color};">●</span> ${name}: ${value}%</div>`
            } else {
              html += `<div style="margin: 4px 0;"><span style="color: ${color};">●</span> ${name}: ${monitoringStore.formatNumber(value)}</div>`
            }
          })
          
          return html + '</div>'
        }
      },
      legend: {
        data: ['总文件数', '小文件数', '小文件占比'],
        top: 60,
        textStyle: {
          color: monitoringStore.settings.theme === 'dark' ? '#fff' : '#333'
        }
      },
      xAxis: [
        {
          type: 'category',
          data: dates,
          axisPointer: {
            type: 'shadow'
          },
          axisLabel: {
            color: monitoringStore.settings.theme === 'dark' ? '#ccc' : '#666'
          }
        }
      ],
      yAxis: [
        {
          type: 'value',
          name: '文件数量',
          position: 'left',
          axisLabel: {
            formatter: '{value}',
            color: monitoringStore.settings.theme === 'dark' ? '#ccc' : '#666'
          },
          splitLine: {
            show: true,
            lineStyle: {
              color: monitoringStore.settings.theme === 'dark' ? '#333' : '#e6e6e6'
            }
          }
        },
        {
          type: 'value',
          name: '占比 (%)',
          position: 'right',
          axisLabel: {
            formatter: '{value}%',
            color: monitoringStore.settings.theme === 'dark' ? '#ccc' : '#666'
          }
        }
      ],
      series: [
        {
          name: '总文件数',
          type: 'bar',
          yAxisIndex: 0,
          data: totalFiles,
          itemStyle: {
            color: monitoringStore.getChartColor(0)
          }
        },
        {
          name: '小文件数',
          type: 'bar',
          yAxisIndex: 0,
          data: smallFiles,
          itemStyle: {
            color: monitoringStore.getChartColor(3)
          }
        },
        {
          name: '小文件占比',
          type: 'line',
          yAxisIndex: 1,
          data: ratios,
          smooth: true,
          itemStyle: {
            color: monitoringStore.getChartColor(2)
          },
          lineStyle: {
            width: 3
          },
          symbol: 'circle',
          symbolSize: 6
        }
      ],
      grid: {
        top: 120,
        left: 60,
        right: 60,
        bottom: 60,
        containLabel: true
      }
    }
  }

  // 文件分布饼图配置
  function getDistributionChartOption(data: FileDistributionItem[]) {
    const chartData = data.map((item, index) => ({
      value: item.count,
      name: item.size_range,
      itemStyle: {
        color: monitoringStore.getChartColor(index)
      }
    }))

    return {
      ...baseChartOption.value,
      title: {
        text: '文件大小分布',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
          color: monitoringStore.settings.theme === 'dark' ? '#fff' : '#333'
        },
        left: 'center',
        top: 20
      },
      tooltip: {
        trigger: 'item',
        formatter: function (params: any) {
          const data = params.data
          const percent = params.percent
          return `<div style="padding: 8px;">
            <strong>${data.name}</strong><br/>
            文件数量: ${monitoringStore.formatNumber(data.value)}<br/>
            占比: ${percent}%
          </div>`
        }
      },
      legend: {
        orient: 'horizontal',
        bottom: 10,
        textStyle: {
          color: monitoringStore.settings.theme === 'dark' ? '#fff' : '#333'
        }
      },
      series: [
        {
          type: 'pie',
          radius: ['45%', '75%'],
          center: ['50%', '55%'],
          avoidLabelOverlap: true,
          label: {
            show: true,
            formatter: '{b}: {d}%',
            color: monitoringStore.settings.theme === 'dark' ? '#fff' : '#333'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold'
            },
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          data: chartData
        }
      ]
    }
  }

  // 小型统计图表配置（用于卡片）
  function getMiniChartOption(data: number[], type: 'line' | 'bar' = 'line') {
    return {
      animation: false,
      grid: {
        top: 0,
        left: 0,
        right: 0,
        bottom: 0
      },
      xAxis: {
        type: 'category',
        show: false,
        data: data.map((_, index) => index)
      },
      yAxis: {
        type: 'value',
        show: false
      },
      series: [
        {
          type,
          data,
          showSymbol: false,
          smooth: true,
          lineStyle: {
            width: 2,
            color: monitoringStore.getChartColor(0)
          },
          areaStyle: type === 'line' ? {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: monitoringStore.getChartColor(0) + '40' },
                { offset: 1, color: monitoringStore.getChartColor(0) + '00' }
              ]
            }
          } : undefined,
          itemStyle: {
            color: monitoringStore.getChartColor(0)
          }
        }
      ]
    }
  }

  // 响应式图表选项
  const chartResponsiveOptions = computed(() => ({
    media: [
      {
        query: { maxWidth: 768 },
        option: {
          grid: { left: 20, right: 20, top: 40, bottom: 20 },
          legend: { bottom: 5 },
          title: { textStyle: { fontSize: 14 } }
        }
      },
      {
        query: { minWidth: 769 },
        option: {
          grid: { left: 60, right: 60, top: 80, bottom: 60 },
          legend: { bottom: 10 },
          title: { textStyle: { fontSize: 16 } }
        }
      }
    ]
  }))

  return {
    baseChartOption,
    getTrendChartOption,
    getDistributionChartOption,
    getMiniChartOption,
    chartResponsiveOptions
  }
}