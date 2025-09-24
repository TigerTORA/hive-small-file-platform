import api from './index'

export const storageApi = {
  // EC policy (SSH)
  setEcPolicy(clusterId: number, payload: {
    path: string
    policy: string
    recursive?: boolean
    ssh_host: string
    ssh_user?: string
    ssh_port?: number
    ssh_key_path?: string
    kinit_principal?: string
    kinit_keytab?: string
    dry_run?: boolean
  }): Promise<{ task_id: string }> {
    return api.post(`/ec/set-policy/${clusterId}`, payload)
  },

  // mover (SSH)
  runMover(clusterId: number, payload: {
    path: string
    ssh_host: string
    ssh_user?: string
    ssh_port?: number
    ssh_key_path?: string
    kinit_principal?: string
    kinit_keytab?: string
    dry_run?: boolean
  }): Promise<{ task_id: string }> {
    return api.post(`/storage/mover/${clusterId}`, payload)
  },

  // 设置副本数 (SSH)
  setReplication(clusterId: number, payload: {
    path: string
    replication: number
    recursive?: boolean
    dry_run?: boolean
  }): Promise<{ task_id: string }> {
    return api.post(`/storage/set-replication/${clusterId}`, payload)
  }
}
