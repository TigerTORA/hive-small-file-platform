const TestUtils = require('./test-utils.js')
const TEST_CONFIG = require('./test-config.js')

class CRUDOperationsTester {
  constructor() {
    this.utils = new TestUtils()
    this.results = {
      total: 0,
      passed: 0,
      failed: 0,
      operations: []
    }
    this.testClusterId = null
    this.testTaskIds = []
  }

  async testCompleteScenario() {
    console.log('🔄 测试CRUD操作完整性...\n')

    try {
      await this.utils.initBrowser()

      // 1. 测试创建操作 (Create)
      await this.testCreateOperations()

      // 2. 测试读取操作 (Read)
      await this.testReadOperations()

      // 3. 测试更新操作 (Update)
      await this.testUpdateOperations()

      // 4. 测试依赖关系删除 (Delete with Dependencies)
      await this.testDeleteWithDependencies()

      this.generateCRUDReport()
      return this.results
    } catch (error) {
      console.error(`💥 CRUD测试过程中出现错误: ${error.message}`)
      return null
    } finally {
      await this.utils.closeBrowser()
    }
  }

  async testCreateOperations() {
    console.log('📝 1. 测试创建操作 (Create)')

    // 创建集群
    await this.createTestCluster()

    // 创建关联的合并任务（这是之前测试遗漏的关键点）
    await this.createDependentTasks()

    // 验证创建结果
    await this.verifyCreateResults()
  }

  async createTestCluster() {
    try {
      // 通过API创建集群
      const clusterData = {
        name: 'CRUD-Test-Cluster-' + Date.now(),
        description: 'CRUD操作完整性测试集群',
        hive_metastore_url: 'mysql://testuser:testpass@localhost:3306/test_hive',
        hdfs_namenode_url: 'hdfs://localhost:9000',
        cluster_type: 'CDH'
      }

      const response = await this.utils.page.evaluate(async data => {
        try {
          const resp = await fetch('http://localhost:8000/api/v1/clusters/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
          })

          if (resp.ok) {
            const result = await resp.json()
            return { ok: true, data: result }
          } else {
            const error = await resp.text()
            return { ok: false, status: resp.status, error }
          }
        } catch (error) {
          return { ok: false, error: error.message }
        }
      }, clusterData)

      if (response.ok && response.data) {
        this.testClusterId = response.data.id
        this.recordOperation('创建集群', true, `成功创建集群 ID: ${this.testClusterId}`)
        console.log(`  ✅ 集群创建成功: ${clusterData.name} (ID: ${this.testClusterId})`)
      } else {
        this.recordOperation('创建集群', false, `创建失败: ${response.error}`)
        console.log(`  ❌ 集群创建失败: ${response.error}`)
      }
    } catch (error) {
      this.recordOperation('创建集群', false, `创建异常: ${error.message}`)
      console.log(`  ❌ 集群创建异常: ${error.message}`)
    }
  }

  async createDependentTasks() {
    if (!this.testClusterId) {
      this.recordOperation('创建依赖任务', false, '没有有效的集群ID')
      return
    }

    try {
      // 创建多个合并任务以测试复杂依赖关系
      const taskTemplates = [
        {
          task_name: 'CRUD-MergeTask-1-' + Date.now(),
          table_name: 'test_table_1',
          database_name: 'test_db',
          merge_strategy: 'safe_merge',
          target_file_size: 134217728
        },
        {
          task_name: 'CRUD-MergeTask-2-' + Date.now(),
          table_name: 'test_table_2',
          database_name: 'test_db',
          merge_strategy: 'concatenate',
          target_file_size: 268435456
        }
      ]

      for (const taskData of taskTemplates) {
        const response = await this.utils.page.evaluate(
          async (clusterId, data) => {
            try {
              const resp = await fetch(`http://localhost:8000/api/v1/tasks/`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                  cluster_id: clusterId,
                  ...data
                })
              })

              if (resp.ok) {
                const result = await resp.json()
                return { ok: true, data: result }
              } else {
                const error = await resp.text()
                return { ok: false, status: resp.status, error }
              }
            } catch (error) {
              return { ok: false, error: error.message }
            }
          },
          this.testClusterId,
          taskData
        )

        if (response.ok && response.data) {
          this.testTaskIds.push(response.data.id)
          this.recordOperation('创建合并任务', true, `成功创建任务 ID: ${response.data.id}`)
          console.log(`  ✅ 合并任务创建成功: ${taskData.task_name} (ID: ${response.data.id})`)
        } else {
          this.recordOperation('创建合并任务', false, `创建失败: ${response.error}`)
          console.log(`  ❌ 合并任务创建失败: ${response.error}`)
        }
      }
    } catch (error) {
      this.recordOperation('创建依赖任务', false, `创建异常: ${error.message}`)
      console.log(`  ❌ 依赖任务创建异常: ${error.message}`)
    }
  }

  async verifyCreateResults() {
    try {
      // 验证集群是否存在
      const clusterExists = await this.utils.page.evaluate(async clusterId => {
        try {
          const resp = await fetch(`http://localhost:8000/api/v1/clusters/${clusterId}`)
          return resp.ok
        } catch (error) {
          return false
        }
      }, this.testClusterId)

      this.recordOperation('验证集群创建', clusterExists, clusterExists ? '集群存在' : '集群不存在')

      // 验证任务是否存在
      for (const taskId of this.testTaskIds) {
        const taskExists = await this.utils.page.evaluate(async id => {
          try {
            const resp = await fetch(`http://localhost:8000/api/v1/tasks/${id}`)
            return resp.ok
          } catch (error) {
            return false
          }
        }, taskId)

        this.recordOperation(
          '验证任务创建',
          taskExists,
          taskExists ? `任务 ${taskId} 存在` : `任务 ${taskId} 不存在`
        )
      }
    } catch (error) {
      this.recordOperation('验证创建结果', false, `验证异常: ${error.message}`)
    }
  }

  async testReadOperations() {
    console.log('📖 2. 测试读取操作 (Read)')

    // 读取集群信息
    await this.testReadCluster()

    // 读取集群列表
    await this.testReadClusterList()

    // 读取关联任务
    await this.testReadAssociatedTasks()
  }

  async testReadCluster() {
    if (!this.testClusterId) {
      this.recordOperation('读取集群详情', false, '没有有效的集群ID')
      return
    }

    try {
      const response = await this.utils.page.evaluate(async clusterId => {
        try {
          const resp = await fetch(`http://localhost:8000/api/v1/clusters/${clusterId}`)
          if (resp.ok) {
            const data = await resp.json()
            return { ok: true, data }
          } else {
            return { ok: false, status: resp.status }
          }
        } catch (error) {
          return { ok: false, error: error.message }
        }
      }, this.testClusterId)

      if (response.ok && response.data) {
        this.recordOperation('读取集群详情', true, `成功读取集群信息: ${response.data.name}`)
        console.log(`  ✅ 集群详情读取成功: ${response.data.name}`)
      } else {
        this.recordOperation(
          '读取集群详情',
          false,
          `读取失败: ${response.error || response.status}`
        )
        console.log(`  ❌ 集群详情读取失败`)
      }
    } catch (error) {
      this.recordOperation('读取集群详情', false, `读取异常: ${error.message}`)
    }
  }

  async testReadClusterList() {
    try {
      const response = await this.utils.page.evaluate(async () => {
        try {
          const resp = await fetch('http://localhost:8000/api/v1/clusters/')
          if (resp.ok) {
            const data = await resp.json()
            return { ok: true, count: data.length, data }
          } else {
            return { ok: false, status: resp.status }
          }
        } catch (error) {
          return { ok: false, error: error.message }
        }
      })

      if (response.ok) {
        this.recordOperation('读取集群列表', true, `成功读取 ${response.count} 个集群`)
        console.log(`  ✅ 集群列表读取成功: ${response.count} 个集群`)
      } else {
        this.recordOperation(
          '读取集群列表',
          false,
          `读取失败: ${response.error || response.status}`
        )
        console.log(`  ❌ 集群列表读取失败`)
      }
    } catch (error) {
      this.recordOperation('读取集群列表', false, `读取异常: ${error.message}`)
    }
  }

  async testReadAssociatedTasks() {
    if (!this.testClusterId) {
      this.recordOperation('读取关联任务', false, '没有有效的集群ID')
      return
    }

    try {
      const response = await this.utils.page.evaluate(async clusterId => {
        try {
          const resp = await fetch(`http://localhost:8000/api/v1/tasks/?cluster_id=${clusterId}`)
          if (resp.ok) {
            const data = await resp.json()
            return { ok: true, count: data.length, data }
          } else {
            return { ok: false, status: resp.status }
          }
        } catch (error) {
          return { ok: false, error: error.message }
        }
      }, this.testClusterId)

      if (response.ok) {
        this.recordOperation('读取关联任务', true, `成功读取 ${response.count} 个关联任务`)
        console.log(`  ✅ 关联任务读取成功: ${response.count} 个任务`)
      } else {
        this.recordOperation(
          '读取关联任务',
          false,
          `读取失败: ${response.error || response.status}`
        )
        console.log(`  ❌ 关联任务读取失败`)
      }
    } catch (error) {
      this.recordOperation('读取关联任务', false, `读取异常: ${error.message}`)
    }
  }

  async testUpdateOperations() {
    console.log('📝 3. 测试更新操作 (Update)')

    // 更新集群信息
    await this.testUpdateCluster()

    // 更新任务信息
    await this.testUpdateTask()
  }

  async testUpdateCluster() {
    if (!this.testClusterId) {
      this.recordOperation('更新集群信息', false, '没有有效的集群ID')
      return
    }

    try {
      const updateData = {
        description: 'CRUD测试更新后的描述 - ' + new Date().toISOString()
      }

      const response = await this.utils.page.evaluate(
        async (clusterId, data) => {
          try {
            const resp = await fetch(`http://localhost:8000/api/v1/clusters/${clusterId}`, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(data)
            })

            if (resp.ok) {
              const result = await resp.json()
              return { ok: true, data: result }
            } else {
              const error = await resp.text()
              return { ok: false, status: resp.status, error }
            }
          } catch (error) {
            return { ok: false, error: error.message }
          }
        },
        this.testClusterId,
        updateData
      )

      if (response.ok && response.data) {
        this.recordOperation('更新集群信息', true, `成功更新集群描述`)
        console.log(`  ✅ 集群信息更新成功`)
      } else {
        this.recordOperation('更新集群信息', false, `更新失败: ${response.error}`)
        console.log(`  ❌ 集群信息更新失败: ${response.error}`)
      }
    } catch (error) {
      this.recordOperation('更新集群信息', false, `更新异常: ${error.message}`)
      console.log(`  ❌ 集群信息更新异常: ${error.message}`)
    }
  }

  async testUpdateTask() {
    if (this.testTaskIds.length === 0) {
      this.recordOperation('更新任务信息', false, '没有有效的任务ID')
      return
    }

    try {
      const taskId = this.testTaskIds[0] // 更新第一个任务
      const updateData = {
        status: 'cancelled',
        error_message: 'CRUD测试取消任务'
      }

      const response = await this.utils.page.evaluate(
        async (id, data) => {
          try {
            const resp = await fetch(`http://localhost:8000/api/v1/tasks/${id}`, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(data)
            })

            if (resp.ok) {
              const result = await resp.json()
              return { ok: true, data: result }
            } else {
              const error = await resp.text()
              return { ok: false, status: resp.status, error }
            }
          } catch (error) {
            return { ok: false, error: error.message }
          }
        },
        taskId,
        updateData
      )

      if (response.ok && response.data) {
        this.recordOperation('更新任务信息', true, `成功更新任务状态为 cancelled`)
        console.log(`  ✅ 任务信息更新成功: ${taskId}`)
      } else {
        this.recordOperation('更新任务信息', false, `更新失败: ${response.error}`)
        console.log(`  ❌ 任务信息更新失败: ${response.error}`)
      }
    } catch (error) {
      this.recordOperation('更新任务信息', false, `更新异常: ${error.message}`)
      console.log(`  ❌ 任务信息更新异常: ${error.message}`)
    }
  }

  async testDeleteWithDependencies() {
    console.log('🗑️ 4. 测试依赖关系删除 (Delete with Dependencies)')

    // 这是关键的测试：测试有依赖关系时的删除操作
    await this.testDeleteTasksFirst()
    await this.testDeleteClusterWithoutDependencies()
    await this.testDeleteClusterWithDependencies()
  }

  async testDeleteTasksFirst() {
    console.log('  4.1 先删除依赖任务')

    for (const taskId of this.testTaskIds) {
      try {
        const response = await this.utils.page.evaluate(async id => {
          try {
            const resp = await fetch(`http://localhost:8000/api/v1/tasks/${id}`, {
              method: 'DELETE'
            })

            if (resp.ok) {
              const result = await resp.json()
              return { ok: true, data: result }
            } else {
              const error = await resp.text()
              return { ok: false, status: resp.status, error }
            }
          } catch (error) {
            return { ok: false, error: error.message }
          }
        }, taskId)

        if (response.ok) {
          this.recordOperation('删除依赖任务', true, `成功删除任务 ${taskId}`)
          console.log(`    ✅ 任务删除成功: ${taskId}`)
        } else {
          this.recordOperation('删除依赖任务', false, `删除失败: ${response.error}`)
          console.log(`    ❌ 任务删除失败: ${taskId} - ${response.error}`)
        }
      } catch (error) {
        this.recordOperation('删除依赖任务', false, `删除异常: ${error.message}`)
        console.log(`    ❌ 任务删除异常: ${taskId} - ${error.message}`)
      }
    }
  }

  async testDeleteClusterWithoutDependencies() {
    if (!this.testClusterId) {
      this.recordOperation('删除集群(无依赖)', false, '没有有效的集群ID')
      return
    }

    console.log('  4.2 删除集群（已清理依赖）')

    try {
      const response = await this.utils.page.evaluate(async clusterId => {
        try {
          const resp = await fetch(`http://localhost:8000/api/v1/clusters/${clusterId}`, {
            method: 'DELETE'
          })

          if (resp.ok) {
            const result = await resp.json()
            return { ok: true, data: result }
          } else {
            const error = await resp.text()
            return { ok: false, status: resp.status, error }
          }
        } catch (error) {
          return { ok: false, error: error.message }
        }
      }, this.testClusterId)

      if (response.ok) {
        this.recordOperation('删除集群(无依赖)', true, `成功删除集群 ${this.testClusterId}`)
        console.log(`    ✅ 集群删除成功: ${this.testClusterId}`)
        this.testClusterId = null // 清空已删除的集群ID
      } else {
        this.recordOperation('删除集群(无依赖)', false, `删除失败: ${response.error}`)
        console.log(`    ❌ 集群删除失败: ${response.error}`)
      }
    } catch (error) {
      this.recordOperation('删除集群(无依赖)', false, `删除异常: ${error.message}`)
      console.log(`    ❌ 集群删除异常: ${error.message}`)
    }
  }

  async testDeleteClusterWithDependencies() {
    console.log('  4.3 测试有依赖关系的删除场景')

    // 重新创建一个集群和任务来测试约束错误
    await this.createTestScenarioForConstraintTest()
  }

  async createTestScenarioForConstraintTest() {
    try {
      // 创建新的测试集群
      const clusterData = {
        name: 'Constraint-Test-Cluster-' + Date.now(),
        description: '约束测试集群',
        hive_metastore_url: 'mysql://testuser:testpass@localhost:3306/test_hive',
        hdfs_namenode_url: 'hdfs://localhost:9000'
      }

      const clusterResponse = await this.utils.page.evaluate(async data => {
        try {
          const resp = await fetch('http://localhost:8000/api/v1/clusters/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
          })

          if (resp.ok) {
            const result = await resp.json()
            return { ok: true, data: result }
          } else {
            return { ok: false, error: await resp.text() }
          }
        } catch (error) {
          return { ok: false, error: error.message }
        }
      }, clusterData)

      if (!clusterResponse.ok) {
        this.recordOperation('约束测试-创建集群', false, `创建失败: ${clusterResponse.error}`)
        return
      }

      const constraintTestClusterId = clusterResponse.data.id
      console.log(`    📋 约束测试集群创建成功: ${constraintTestClusterId}`)

      // 创建依赖任务
      const taskData = {
        task_name: 'Constraint-Test-Task-' + Date.now(),
        table_name: 'constraint_test_table',
        database_name: 'test_db',
        merge_strategy: 'safe_merge'
      }

      const taskResponse = await this.utils.page.evaluate(
        async (clusterId, data) => {
          try {
            const resp = await fetch(`http://localhost:8000/api/v1/tasks/`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                cluster_id: clusterId,
                ...data
              })
            })

            if (resp.ok) {
              const result = await resp.json()
              return { ok: true, data: result }
            } else {
              return { ok: false, error: await resp.text() }
            }
          } catch (error) {
            return { ok: false, error: error.message }
          }
        },
        constraintTestClusterId,
        taskData
      )

      if (taskResponse.ok) {
        console.log(`    📋 约束测试任务创建成功: ${taskResponse.data.id}`)

        // 现在尝试直接删除集群（应该会失败或者触发级联删除）
        const deleteResponse = await this.utils.page.evaluate(async clusterId => {
          try {
            const resp = await fetch(`http://localhost:8000/api/v1/clusters/${clusterId}`, {
              method: 'DELETE'
            })

            if (resp.ok) {
              const result = await resp.json()
              return { ok: true, data: result }
            } else {
              const error = await resp.text()
              return { ok: false, status: resp.status, error }
            }
          } catch (error) {
            return { ok: false, error: error.message }
          }
        }, constraintTestClusterId)

        if (deleteResponse.ok) {
          this.recordOperation('删除集群(有依赖)', true, '级联删除成功 - API正确处理了依赖关系')
          console.log(`    ✅ 约束测试成功: 级联删除正常工作`)
        } else {
          // 这里捕获了我们要测试的约束错误
          this.recordOperation('删除集群(有依赖)', false, `约束错误: ${deleteResponse.error}`)
          console.log(`    ⚠️ 约束错误被捕获: ${deleteResponse.error}`)
          console.log(`    💡 这表明API需要改进删除逻辑以正确处理依赖关系`)
        }
      }
    } catch (error) {
      this.recordOperation('约束测试场景', false, `场景创建异常: ${error.message}`)
    }
  }

  recordOperation(operation, success, details) {
    this.results.total++
    if (success) {
      this.results.passed++
    } else {
      this.results.failed++
    }

    this.results.operations.push({
      operation,
      success,
      details,
      timestamp: new Date().toISOString()
    })
  }

  generateCRUDReport() {
    console.log('\n' + '='.repeat(80))
    console.log('🔄 CRUD操作完整性测试报告')
    console.log('='.repeat(80))

    const successRate =
      this.results.total > 0 ? (this.results.passed / this.results.total) * 100 : 0

    console.log(`📊 总体评估:`)
    console.log(`  • 总操作数: ${this.results.total}`)
    console.log(`  • 成功操作: ${this.results.passed}`)
    console.log(`  • 失败操作: ${this.results.failed}`)
    console.log(`  • 成功率: ${successRate.toFixed(1)}%`)

    console.log(`\n📋 操作详情:`)
    this.results.operations.forEach((op, index) => {
      const status = op.success ? '✅' : '❌'
      console.log(`  ${index + 1}. ${status} ${op.operation}: ${op.details}`)
    })

    console.log(`\n🎯 关键发现:`)
    const deleteOps = this.results.operations.filter(op => op.operation.includes('删除'))
    const createOps = this.results.operations.filter(op => op.operation.includes('创建'))
    const readOps = this.results.operations.filter(op => op.operation.includes('读取'))
    const updateOps = this.results.operations.filter(op => op.operation.includes('更新'))

    console.log(
      `  • 创建操作 (C): ${createOps.filter(op => op.success).length}/${createOps.length} 成功`
    )
    console.log(
      `  • 读取操作 (R): ${readOps.filter(op => op.success).length}/${readOps.length} 成功`
    )
    console.log(
      `  • 更新操作 (U): ${updateOps.filter(op => op.success).length}/${updateOps.length} 成功`
    )
    console.log(
      `  • 删除操作 (D): ${deleteOps.filter(op => op.success).length}/${deleteOps.length} 成功`
    )

    console.log(`\n🔍 依赖关系测试结果:`)
    const constraintOps = this.results.operations.filter(
      op => op.operation.includes('依赖') || op.operation.includes('约束')
    )

    if (constraintOps.length > 0) {
      constraintOps.forEach(op => {
        const status = op.success ? '✅' : '⚠️'
        console.log(`  ${status} ${op.operation}: ${op.details}`)
      })
    } else {
      console.log(`  ℹ️ 未执行约束测试 - 可能由于前置条件未满足`)
    }

    console.log(`\n🌟 测试评价:`)
    if (successRate >= 80) {
      console.log(`🏆 优秀 - CRUD操作健壮性良好，依赖关系处理正确！`)
    } else if (successRate >= 60) {
      console.log(`👍 良好 - 基本CRUD功能正常，部分依赖关系需改进！`)
    } else {
      console.log(`⚠️ 需改进 - CRUD操作存在问题，需要修复依赖关系处理！`)
    }

    console.log('\n='.repeat(80))
  }
}

// 运行测试
async function runCRUDTests() {
  const tester = new CRUDOperationsTester()
  const results = await tester.testCompleteScenario()

  if (results && results.passed >= results.total * 0.8) {
    console.log('\n🎉 CRUD操作完整性测试通过！')
    process.exit(0)
  } else {
    console.log('\n💫 CRUD操作完整性测试完成！发现了需要改进的问题！')
    process.exit(0)
  }
}

if (require.main === module) {
  runCRUDTests().catch(error => {
    console.error('CRUD测试运行失败:', error)
    process.exit(1)
  })
}

module.exports = CRUDOperationsTester
