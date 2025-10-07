import dayjs from 'dayjs'

/**
 * 格式化时间
 */
export function formatTime(time: string): string {
  return dayjs(time).format('MM-DD HH:mm:ss')
}

/**
 * 格式化字节大小
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 格式化持续时间
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}秒`
  if (seconds < 3600) return `${Math.round(seconds / 60)}分钟`
  return `${Math.round(seconds / 3600)}小时`
}

/**
 * 人性化显示时长
 */
export function humanizeDuration(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  if (m <= 0) return `${s}s`
  return `${m}m${s.toString().padStart(2, '0')}s`
}

/**
 * 缩短ID显示
 */
export function shortId(id: string): string {
  if (!id) return '-'
  return id.slice(0, 10) + '…' + id.slice(-6)
}

/**
 * 缩短路径显示
 */
export function shortPath(p?: string): string {
  if (!p) return '-'
  if (p.length <= 36) return p
  const parts = p.split('/')
  if (parts.length > 4) return `${parts.slice(0, 3).join('/')}/…/${parts.slice(-2).join('/')}`
  return p.slice(0, 16) + '…' + p.slice(-12)
}

/**
 * 显示文件数（处理空值）
 */
export function displayFiles(value: number | null | undefined): number | string {
  if (value === null || value === undefined) return 'NaN'
  return value
}
