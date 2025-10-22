import type { ClusterCreate } from '@/api/clusters'

export type ClusterFormLike = Partial<ClusterCreate> & Record<string, any>

const KERBEROS_FIELDS = [
  'kerberos_principal',
  'kerberos_keytab_path',
  'kerberos_realm',
  'kerberos_ticket_cache'
] as const

const LDAP_FIELDS = ['hive_username', 'hive_password'] as const

const SHARED_FIELDS = [
  'name',
  'description',
  'hive_host',
  'hive_database',
  'hive_metastore_url',
  'hdfs_namenode_url',
  'hdfs_user',
  'yarn_resource_manager_url'
] as const

const trimOrUndefined = (value: unknown) => {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed === '' ? undefined : trimmed
  }
  return value ?? undefined
}

export function normalizeClusterPayload(form: ClusterFormLike): ClusterFormLike {
  const payload: ClusterFormLike = { ...form }
  payload.auth_type = (payload.auth_type || 'NONE').toUpperCase()

  SHARED_FIELDS.forEach(field => {
    payload[field] = trimOrUndefined(payload[field])
  })

  if (payload.auth_type !== 'LDAP') {
    LDAP_FIELDS.forEach(field => {
      delete payload[field]
    })
  } else {
    LDAP_FIELDS.forEach(field => {
      payload[field] = trimOrUndefined(payload[field])
    })
  }

  if (payload.auth_type === 'KERBEROS') {
    KERBEROS_FIELDS.forEach(field => {
      payload[field] = trimOrUndefined(payload[field])
    })
  } else {
    KERBEROS_FIELDS.forEach(field => {
      delete payload[field]
    })
  }

  return payload
}
