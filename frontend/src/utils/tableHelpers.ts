import dayjs from 'dayjs'

/**
 * 格式化时间
 */
export const formatTime = (time?: string): string => {
  if (!time) return '--'
  return dayjs(time).isValid() ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '--'
}

/**
 * 格式化扫描时长
 */
export const formatScanDuration = (seconds?: number): string => {
  if (!seconds || Number.isNaN(seconds)) return '--'
  if (seconds < 60) return `${Math.round(seconds)} 秒`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return secs ? `${mins} 分 ${secs} 秒` : `${mins} 分`
}

/**
 * 根据百分比获取进度条颜色
 */
export const getProgressColor = (percentage: number): string => {
  if (percentage > 80) return '#f56c6c'
  if (percentage > 50) return '#e6a23c'
  if (percentage > 20) return '#1989fa'
  return '#67c23a'
}

/**
 * 数字格式化
 */
const numberFormatter = new Intl.NumberFormat('zh-CN', {
  maximumFractionDigits: 2
})

export const formatNumber = (num: number | null | undefined): string => {
  if (num === null || num === undefined || Number.isNaN(num)) return '--'
  return numberFormatter.format(num)
}

/**
 * 分区规范转为过滤条件
 * @example "dt=2025-09-01/hour=12" => "dt='2025-09-01' AND hour=12"
 */
export const specToFilter = (spec: string): string => {
  const parts = String(spec || '').split('/')
  const filters = parts
    .map(p => {
      const [k, v] = p.split('=')
      if (!k || v === undefined) return ''
      const quoted = /^\d+$/.test(v) ? v : `'${v}'`
      return `${k}=${quoted}`
    })
    .filter(Boolean)
  return filters.join(' AND ')
}

/**
 * 复制文本到剪贴板
 */
export const copyPlainText = async (value?: string): Promise<boolean> => {
  if (!value) return false
  try {
    await navigator.clipboard.writeText(value)
    return true
  } catch (error) {
    try {
      const input = document.createElement('textarea')
      input.value = value
      input.setAttribute('readonly', '')
      input.style.position = 'absolute'
      input.style.opacity = '0'
      document.body.appendChild(input)
      input.select()
      const success = document.execCommand('copy')
      document.body.removeChild(input)
      return success
    } catch (fallbackError) {
      console.error('Copy failed', fallbackError)
      return false
    }
  }
}
