import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@element-plus/icons-vue', () => ({
  Loading: { name: 'LoadingIcon', render: () => null },
  Coin: { name: 'CoinIcon', render: () => null },
  FolderOpened: { name: 'FolderOpenedIcon', render: () => null },
  Connection: { name: 'ConnectionIcon', render: () => null }
}))

import ConnectionTestDialog from '@/components/ConnectionTestDialog.vue'

describe('ConnectionTestDialog', () => {
  it('renders Kerberos diagnostic details for failing connections', () => {
    const testResult = {
      overall_status: 'failed',
      test_time: '2025-10-13T10:00:00Z',
      tests: {
        hdfs: {
          status: 'failed',
          mode: 'real',
          message: 'Kerberos 认证失败',
          diagnostic_code: 'KERBEROS_AUTHENTICATION_FAILED',
          diagnostic_message: 'Kerberos 认证失败',
          recommended_action: '执行 kinit 续票'
        }
      },
      logs: [
        {
          level: 'ERROR',
          message: 'hdfs: Kerberos 认证失败',
          diagnostic_code: 'KERBEROS_AUTHENTICATION_FAILED',
          diagnostic_message: 'Kerberos 认证失败',
          recommended_action: '执行 kinit 续票'
        }
      ],
      suggestions: ['执行 kinit 续票']
    }

    const wrapper = mount(ConnectionTestDialog, {
      props: {
        visible: true,
        testing: false,
        testResult,
        error: null
      },
      global: {
        stubs: {
          'el-dialog': { template: '<div><slot /><slot name="footer" /></div>' },
          'el-tag': { template: '<span class="el-tag"><slot /></span>' },
          'el-icon': { template: '<span class="el-icon"><slot /></span>' },
          'el-row': { template: '<div class="el-row"><slot /></div>' },
          'el-col': { template: '<div class="el-col"><slot /></div>' },
          'el-card': { template: '<div class="el-card"><slot /></div>' },
          'el-alert': { template: '<div class="el-alert"><slot /></div>' },
          'el-button': { template: '<button><slot /></button>' }
        }
      }
    })

    const html = wrapper.html()
    expect(html).toContain('KERBEROS_AUTHENTICATION_FAILED')
    expect(html).toContain('Kerberos 认证失败')
    expect(html).toContain('执行 kinit 续票')
  })
})
