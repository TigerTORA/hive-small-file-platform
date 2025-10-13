import { ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { tablesApi } from '@/api/tables'
import { tasksApi, type MergeTaskCreate } from '@/api/tasks'
import { storageApi } from '@/api/storage'
import { FeatureManager } from '@/utils/feature-flags'

export const useTableActions = (
  clusterId: Ref<number>,
  database: Ref<string>,
  tableName: Ref<string>,
  tableLocationRaw: Ref<string>
) => {
  const scanningTableStrict = ref(false)
  const creating = ref(false)

  const demoMode = FeatureManager.isEnabled('demoMode')

  const scanCurrentTable = async (strictReal: boolean, onSuccess?: () => void) => {
    if (demoMode) {
      ElMessage.warning('演示模式已禁用实时扫描')
      return
    }
    if (scanningTableStrict.value) return
    scanningTableStrict.value = true
    try {
      await tablesApi.scanTable(clusterId.value, database.value, tableName.value, strictReal)
      ElMessage.success('已启动单表扫描')
      if (onSuccess) {
        setTimeout(onSuccess, 1500)
      }
    } catch (error: any) {
      console.error('scanCurrentTable failed', error)
      const msg = error?.response?.data?.detail || error?.message || '启动单表扫描失败'
      ElMessage.error(msg)
    } finally {
      scanningTableStrict.value = false
    }
  }

  const createMergeTask = async (
    mergeForm: MergeTaskCreate & {
      storagePolicy?: boolean
      policy?: string
      recursive?: boolean
      runMover?: boolean
      ec?: boolean
      ecPolicy?: string
      ecRecursive?: boolean
      setReplication?: boolean
      replicationFactor?: number
      replicationRecursive?: boolean
    },
    mergeScope: 'table' | 'partition',
    selectedPartitions: string[],
    specToFilter: (spec: string) => string
  ): Promise<{ taskId: string; additionalTasks: string[] }> => {
    if (demoMode) {
      ElMessage.warning('演示模式已禁用治理/合并操作')
      return { taskId: '', additionalTasks: [] }
    }
    creating.value = true
    try {
      if (mergeScope === 'partition') {
        if (selectedPartitions.length === 0) {
          throw new Error('请选择至少一个分区')
        }
        if (selectedPartitions.length === 1) {
          mergeForm.partition_filter = specToFilter(selectedPartitions[0])
        } else {
          const filters = selectedPartitions.map(spec => specToFilter(spec))
          mergeForm.partition_filter = `(${filters.join(' OR ')})`
        }
      } else {
        mergeForm.partition_filter = ''
      }

      mergeForm.merge_strategy = 'safe_merge'

      const payload = { ...mergeForm }
      if (mergeScope === 'partition') {
        payload.use_ec = false
      }
      if (!payload.target_storage_format) {
        delete payload.target_storage_format
      } else {
        payload.target_storage_format = payload.target_storage_format.toUpperCase() as MergeTaskCreate['target_storage_format']
      }
      if (payload.target_compression) {
        payload.target_compression = payload.target_compression.toUpperCase() as MergeTaskCreate['target_compression']
      }

      const task = await tasksApi.create(payload)
      await tasksApi.execute(task.id)

      const additionalTasks: string[] = []
      const path = tableLocationRaw.value
      const cid = clusterId.value

      if (mergeForm.storagePolicy) {
        const resp = await tablesApi.archiveTableWithProgress(cid, database.value, tableName.value, false, {
          mode: 'storage-policy',
          policy: mergeForm.policy!,
          recursive: mergeForm.recursive!
        })
        if ((resp as any)?.task_id) additionalTasks.push((resp as any).task_id)
      }

      if (mergeForm.setReplication) {
        const targetRep = Math.max(1, Number(mergeForm.replicationFactor || 1))
        const repResp = await storageApi.setReplication(cid, {
          path,
          replication: targetRep,
          recursive: mergeForm.replicationRecursive!
        })
        if ((repResp as any)?.task_id) additionalTasks.push((repResp as any).task_id)
      }

      if (mergeForm.ec) {
        const ssh = getHarSshDefaults(clusterId.value)
        if (!ssh || !ssh.host) {
          ElMessage.warning('请先在集群管理维护 SSH 配置')
        } else {
          const ecResp = await storageApi.setEcPolicy(cid, {
            path,
            policy: mergeForm.ecPolicy || 'RS-6-3-1024k',
            recursive: mergeForm.ecRecursive!,
            ssh_host: ssh.host,
            ssh_user: ssh.user || 'hdfs',
            ssh_port: ssh.port || 22,
            ssh_key_path: ssh.keyPath,
            kinit_principal: ssh.principal,
            kinit_keytab: ssh.keytab
          })
          if ((ecResp as any)?.task_id) additionalTasks.push((ecResp as any).task_id)
        }
      }

      if (mergeForm.runMover) {
        const ssh = getHarSshDefaults(clusterId.value)
        if (!ssh || !ssh.host) {
          ElMessage.warning('请先在集群管理维护 SSH 配置')
        } else {
          const mover = await storageApi.runMover(cid, {
            path,
            ssh_host: ssh.host,
            ssh_user: ssh.user || 'hdfs',
            ssh_port: ssh.port || 22,
            ssh_key_path: ssh.keyPath,
            kinit_principal: ssh.principal,
            kinit_keytab: ssh.keytab
          })
          if ((mover as any)?.task_id) additionalTasks.push((mover as any).task_id)
        }
      }

      return { taskId: task.id, additionalTasks }
    } finally {
      creating.value = false
    }
  }

  const getHarSshDefaults = (clusterId: number) => {
    try {
      const raw = localStorage.getItem(`har-ssh.${clusterId}`)
      return raw ? JSON.parse(raw) : null
    } catch (error) {
      return null
    }
  }

  return {
    scanningTableStrict,
    creating,
    scanCurrentTable,
    createMergeTask
  }
}
