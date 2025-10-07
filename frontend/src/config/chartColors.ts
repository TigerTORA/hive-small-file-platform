/**
 * Dashboard 图表颜色配置
 * 提取自 Dashboard.vue L438-477
 */

export const ChartColorSchemes = {
  // 文件分类颜色 (原 compressionColorScheme)
  fileClassification: [
    '#5470c6', // 可压缩小文件
    '#ee6666', // ACID表小文件
    '#fac858', // 单分区文件
    '#91cc75', // 数据湖表文件
    '#73c0de', // 其他
    '#3ba272',
    '#fc8452',
    '#9a60b4'
  ],

  // 压缩格式颜色
  compressionFormat: [
    '#8C8C8C', // NONE - 灰色
    '#1890FF', // ZLIB - 蓝色
    '#52C41A', // SNAPPY - 绿色
    '#FAAD14', // GZIP - 橙色
    '#722ED1', // LZ4 - 紫色
    '#EB2F96', // BZIP2 - 品红
    '#13C2C2', // DEFLATE - 青色
    '#FA8C16'  // OTHER - 橘色
  ],

  // 冷数据时间分布颜色
  coldness: [
    '#67C23A', // 1-7天 - 绿色
    '#E6A23C', // 1周-1月 - 橙色
    '#F56C6C', // 1-6月 - 红色
    '#409EFF', // 6-12月 - 蓝色
    '#909399'  // 1年以上 - 灰色
  ],

  // 格式压缩组合颜色
  formatCompression: [
    '#faad14', // TEXT(无压缩) - 橙色
    '#52c41a', // ORC(ZLIB压缩) - 绿色
    '#2f54eb', // PARQUET(SNAPPY压缩) - 蓝色
    '#722ed1', // OTHER(无压缩) - 紫色
    '#eb2f96', // 其他组合 - 品红
    '#13c2c2', // 青色
    '#fa8c16', // 橘色
    '#a0d911'  // 青绿色
  ]
} as const
