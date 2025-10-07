<template>
  <div class="table-info-section">
    <el-card class="detail-card detail-card--span-6" shadow="never">
      <div class="section-title">
        <el-icon><Collection /></el-icon>
        <span>基础信息</span>
      </div>
      <div class="info-grid">
        <InfoItem label="数据库" :value="tableInfoSource.database_name" icon="Collection" />
        <InfoItem label="表类型" :value="tableTypeTag.label" icon="Tickets" />
        <InfoItem label="所有者" :value="tableInfoSource.table_owner" icon="User" />
        <InfoItem label="创建时间" :value="formatTime(tableInfoSource.table_create_time)" icon="Timer" />
        <InfoItem label="归档状态" :value="archiveStatusLabel" icon="FolderChecked" :highlight="isArchived" />
        <InfoItem label="最后访问" :value="lastAccessLabel" icon="Clock" />
        <InfoItem label="数据活跃度" :value="coldDataLabel" icon="Histogram" />
      </div>
    </el-card>

    <el-card class="detail-card detail-card--span-6" shadow="never">
      <div class="section-title">
        <el-icon><FolderOpened /></el-icon>
        <span>存储信息</span>
      </div>
      <div class="info-grid">
        <InfoItem
          label="表路径"
          :value="tableLocationDisplay"
          icon="Folder"
          layout="vertical"
          :tooltip="tableLocationDisplay"
          :copyable="!!tableLocationRaw"
          :copy-text="tableLocationRaw"
        />
        <InfoItem label="存储格式" :value="storageFormatTag || 'UNKNOWN'" icon="CollectionTag" />
        <InfoItem label="压缩方式" :value="compressionLabel" icon="DataAnalysis" />
        <InfoItem
          label="InputFormat"
          :value="tableInfoSource.input_format"
          icon="ArrowDownBold"
          layout="vertical"
          :tooltip="tableInfoSource.input_format"
        />
        <InfoItem
          label="OutputFormat"
          :value="tableInfoSource.output_format"
          icon="ArrowUpBold"
          layout="vertical"
          :tooltip="tableInfoSource.output_format"
        />
        <InfoItem
          label="SerDe"
          :value="tableInfoSource.serde_lib"
          icon="MagicStick"
          layout="vertical"
          :tooltip="tableInfoSource.serde_lib"
        />
        <InfoItem
          label="分区字段"
          :value="partitionColumnsLabel"
          icon="Grid"
          layout="vertical"
          :tooltip="partitionColumnsLabel"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Collection, FolderOpened } from '@element-plus/icons-vue'
import InfoItem from '@/components/InfoItem.vue'
import { formatTime } from '@/utils/tableHelpers'

interface Props {
  tableInfoSource: any
  tableTypeTag: { label: string; type: string }
  archiveStatusLabel: string
  isArchived: boolean
  lastAccessLabel: string
  coldDataLabel: string
  tableLocationDisplay: string
  tableLocationRaw: string
  storageFormatTag: string
  compressionLabel: string
  partitionColumnsLabel: string
}

defineProps<Props>()
</script>

<style scoped>
.table-info-section {
  display: contents;
}

.detail-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
}

.detail-card--span-6 {
  grid-column: span 6;
}

@media (max-width: 1280px) {
  .detail-card--span-6 {
    grid-column: span 12;
  }
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2d3d;
  margin-bottom: 10px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 6px;
}
</style>
