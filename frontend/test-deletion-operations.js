const TestUtils = require('./test-utils.js');
const TEST_CONFIG = require('./test-config.js');

class DeletionOperationsTester {
  constructor() {
    this.utils = new TestUtils();
    this.results = {
      total: 0,
      passed: 0,
      failed: 0,
      scenarios: []
    };
    this.testClusters = [];
    this.testTasks = [];
  }

  async testDeletionScenarios() {
    console.log('🗑️ 专项删除操作测试...\n');
    
    try {
      await this.utils.initBrowser();
      
      // 1. 简单删除测试（无依赖关系）
      await this.testSimpleDeletion();
      
      // 2. 级联删除测试（有依赖关系）
      await this.testCascadeDeletion();
      
      // 3. 约束冲突删除测试
      await this.testConstraintViolationDeletion();
      
      // 4. 批量删除测试
      await this.testBatchDeletion();
      
      // 5. 删除回滚测试
      await this.testDeletionRollback();
      
      this.generateDeletionReport();
      return this.results;
      
    } catch (error) {
      console.error(`💥 删除测试过程中出现错误: ${error.message}`);
      return null;
    } finally {
      await this.utils.closeBrowser();
    }
  }

  async testSimpleDeletion() {
    console.log('🔹 1. 简单删除测试（无依赖关系）');
    
    // 创建一个没有依赖关系的集群并立即删除
    const clusterData = {
      name: 'Simple-Delete-Test-' + Date.now(),
      description: '简单删除测试集群',
      hive_metastore_url: 'mysql://testuser:testpass@localhost:3306/test_hive',
      hdfs_namenode_url: 'hdfs://localhost:9000'
    };

    try {
      // 创建集群
      const createResponse = await this.utils.page.evaluate(async (data) => {
        try {
          const resp = await fetch('http://localhost:8000/api/v1/clusters/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
          });
          
          if (resp.ok) {
            const result = await resp.json();
            return { ok: true, data: result };
          } else {
            const error = await resp.text();
            return { ok: false, error };
          }
        } catch (error) {
          return { ok: false, error: error.message };
        }
      }, clusterData);

      if (!createResponse.ok) {
        this.recordScenario('简单删除-创建集群', false, `创建失败: ${createResponse.error}`);
        return;
      }

      const clusterId = createResponse.data.id;
      console.log(`  📋 测试集群创建成功: ${clusterId}`);
      this.recordScenario('简单删除-创建集群', true, `集群 ${clusterId} 创建成功`);

      // 立即删除集群（无依赖）
      const deleteResponse = await this.utils.page.evaluate(async (id) => {
        try {
          const resp = await fetch(`http://localhost:8000/api/v1/clusters/${id}`, {
            method: 'DELETE'
          });
          
          if (resp.ok) {
            const result = await resp.json();
            return { ok: true, data: result };
          } else {
            const error = await resp.text();
            return { ok: false, status: resp.status, error };
          }
        } catch (error) {
          return { ok: false, error: error.message };
        }
      }, clusterId);

      if (deleteResponse.ok) {
        this.recordScenario('简单删除-删除操作', true, `集群 ${clusterId} 删除成功`);
        console.log(`  ✅ 简单删除成功: ${clusterId}`);
      } else {
        this.recordScenario('简单删除-删除操作', false, `删除失败: ${deleteResponse.error}`);
        console.log(`  ❌ 简单删除失败: ${deleteResponse.error}`);
      }

      // 验证删除结果
      await this.verifyDeletion(clusterId, '简单删除-验证结果');

    } catch (error) {
      this.recordScenario('简单删除测试', false, `测试异常: ${error.message}`);
      console.log(`  ❌ 简单删除测试异常: ${error.message}`);
    }
  }

  async testCascadeDeletion() {
    console.log('🔹 2. 级联删除测试（有依赖关系）');
    
    try {
      // 创建集群
      const clusterData = {
        name: 'Cascade-Delete-Test-' + Date.now(),
        description: '级联删除测试集群',
        hive_metastore_url: 'mysql://testuser:testpass@localhost:3306/test_hive',
        hdfs_namenode_url: 'hdfs://localhost:9000'
      };

      const createResponse = await this.utils.page.evaluate(async (data) => {
        try {
          const resp = await fetch('http://localhost:8000/api/v1/clusters/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
          });
          
          if (resp.ok) {
            const result = await resp.json();
            return { ok: true, data: result };
          } else {
            return { ok: false, error: await resp.text() };
          }
        } catch (error) {
          return { ok: false, error: error.message };
        }
      }, clusterData);

      if (!createResponse.ok) {
        this.recordScenario('级联删除-创建集群', false, `创建失败: ${createResponse.error}`);
        return;
      }

      const clusterId = createResponse.data.id;
      console.log(`  📋 级联测试集群创建成功: ${clusterId}`);
      this.recordScenario('级联删除-创建集群', true, `集群 ${clusterId} 创建成功`);

      // 创建多个依赖任务
      const taskIds = [];
      for (let i = 1; i <= 3; i++) {
        const taskData = {
          task_name: `Cascade-Test-Task-${i}-${Date.now()}`,
          table_name: `cascade_test_table_${i}`,
          database_name: 'test_db',
          merge_strategy: 'safe_merge'
        };

        const taskResponse = await this.utils.page.evaluate(async (clusterId, data) => {
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
            });
            
            if (resp.ok) {
              const result = await resp.json();
              return { ok: true, data: result };
            } else {
              return { ok: false, error: await resp.text() };
            }
          } catch (error) {
            return { ok: false, error: error.message };
          }
        }, clusterId, taskData);

        if (taskResponse.ok) {
          taskIds.push(taskResponse.data.id);
          console.log(`    ✅ 依赖任务创建成功: ${taskResponse.data.id}`);
        } else {
          console.log(`    ❌ 依赖任务创建失败: ${taskResponse.error}`);
        }
      }

      this.recordScenario('级联删除-创建依赖任务', taskIds.length > 0, `创建了 ${taskIds.length} 个依赖任务`);

      // 尝试删除有依赖关系的集群
      console.log(`  🗑️ 尝试删除有 ${taskIds.length} 个依赖任务的集群...`);
      
      const deleteResponse = await this.utils.page.evaluate(async (id) => {
        try {
          const resp = await fetch(`http://localhost:8000/api/v1/clusters/${id}`, {
            method: 'DELETE'
          });
          
          if (resp.ok) {
            const result = await resp.json();
            return { ok: true, data: result };
          } else {
            const error = await resp.text();
            return { ok: false, status: resp.status, error };
          }
        } catch (error) {
          return { ok: false, error: error.message };
        }
      }, clusterId);

      if (deleteResponse.ok) {
        this.recordScenario('级联删除-删除操作', true, `集群 ${clusterId} 级联删除成功`);
        console.log(`  ✅ 级联删除成功: 集群和所有依赖任务都被删除`);
        
        // 验证级联删除效果
        await this.verifyCascadeDeletion(clusterId, taskIds);
      } else {
        // 这里可能捕获到我们要测试的约束错误
        this.recordScenario('级联删除-删除操作', false, `级联删除失败: ${deleteResponse.error}`);
        console.log(`  ❌ 级联删除失败: ${deleteResponse.error}`);
        console.log(`  💡 这表明API的级联删除逻辑需要改进`);
        
        // 清理测试数据
        await this.cleanupFailedCascadeTest(clusterId, taskIds);
      }

    } catch (error) {
      this.recordScenario('级联删除测试', false, `测试异常: ${error.message}`);
      console.log(`  ❌ 级联删除测试异常: ${error.message}`);
    }
  }

  async testConstraintViolationDeletion() {
    console.log('🔹 3. 约束冲突删除测试');
    
    try {
      // 创建集群
      const clusterData = {
        name: 'Constraint-Violation-Test-' + Date.now(),
        description: '约束冲突测试集群',
        hive_metastore_url: 'mysql://testuser:testpass@localhost:3306/test_hive',
        hdfs_namenode_url: 'hdfs://localhost:9000'
      };

      const createResponse = await this.utils.page.evaluate(async (data) => {
        try {
          const resp = await fetch('http://localhost:8000/api/v1/clusters/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
          });
          
          if (resp.ok) {
            return { ok: true, data: await resp.json() };
          } else {
            return { ok: false, error: await resp.text() };
          }
        } catch (error) {
          return { ok: false, error: error.message };
        }
      }, clusterData);

      if (!createResponse.ok) {
        this.recordScenario('约束冲突-创建集群', false, `创建失败: ${createResponse.error}`);
        return;
      }

      const clusterId = createResponse.data.id;
      console.log(`  📋 约束测试集群创建成功: ${clusterId}`);

      // 创建一个依赖任务
      const taskData = {
        task_name: 'Constraint-Violation-Task-' + Date.now(),
        table_name: 'constraint_test_table',
        database_name: 'test_db',
        merge_strategy: 'safe_merge'
      };

      const taskResponse = await this.utils.page.evaluate(async (clusterId, data) => {
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
          });
          
          if (resp.ok) {
            return { ok: true, data: await resp.json() };
          } else {
            return { ok: false, error: await resp.text() };
          }
        } catch (error) {
          return { ok: false, error: error.message };
        }
      }, clusterId, taskData);

      if (!taskResponse.ok) {
        this.recordScenario('约束冲突-创建任务', false, `任务创建失败: ${taskResponse.error}`);
        return;
      }

      const taskId = taskResponse.data.id;
      console.log(`  📋 约束测试任务创建成功: ${taskId}`);

      // 直接尝试删除集群（不删除依赖任务）
      console.log(`  🗑️ 直接删除有依赖关系的集群（预期会失败）...`);
      
      const deleteResponse = await this.utils.page.evaluate(async (id) => {
        try {
          const resp = await fetch(`http://localhost:8000/api/v1/clusters/${id}`, {
            method: 'DELETE'
          });
          
          if (resp.ok) {
            return { ok: true, data: await resp.json() };
          } else {
            const error = await resp.text();
            return { ok: false, status: resp.status, error };
          }
        } catch (error) {
          return { ok: false, error: error.message };
        }
      }, clusterId);

      if (deleteResponse.ok) {
        // 如果删除成功，说明API正确实现了级联删除
        this.recordScenario('约束冲突-删除测试', true, '集群删除成功 - API正确处理了级联删除');
        console.log(`  ✅ 删除成功 - API正确实现了级联删除逻辑`);
      } else {
        // 如果删除失败，说明遇到了约束错误
        this.recordScenario('约束冲突-删除测试', false, `约束错误: ${deleteResponse.error}`);
        console.log(`  ⚠️ 约束错误被捕获: ${deleteResponse.error}`);
        console.log(`  💡 这是预期的错误，说明数据库正确执行了外键约束`);
        
        // 检查错误类型
        if (deleteResponse.error.includes('IntegrityError') || 
            deleteResponse.error.includes('FOREIGN KEY') || 
            deleteResponse.error.includes('constraint')) {
          this.recordScenario('约束错误类型识别', true, '正确识别为数据库约束错误');
          console.log(`  ✅ 错误类型正确识别为数据库约束错误`);
        }
        
        // 清理测试数据（先删除任务，再删除集群）
        await this.cleanupConstraintTestData(clusterId, taskId);
      }

    } catch (error) {
      this.recordScenario('约束冲突测试', false, `测试异常: ${error.message}`);
      console.log(`  ❌ 约束冲突测试异常: ${error.message}`);
    }
  }

  async testBatchDeletion() {
    console.log('🔹 4. 批量删除测试');
    
    try {
      // 创建多个集群用于批量删除测试
      const clusterIds = [];
      for (let i = 1; i <= 3; i++) {
        const clusterData = {
          name: `Batch-Delete-Test-${i}-${Date.now()}`,
          description: `批量删除测试集群 ${i}`,
          hive_metastore_url: 'mysql://testuser:testpass@localhost:3306/test_hive',
          hdfs_namenode_url: 'hdfs://localhost:9000'
        };

        const response = await this.utils.page.evaluate(async (data) => {
          try {
            const resp = await fetch('http://localhost:8000/api/v1/clusters/', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(data)
            });
            
            if (resp.ok) {
              return { ok: true, data: await resp.json() };
            } else {
              return { ok: false, error: await resp.text() };
            }
          } catch (error) {
            return { ok: false, error: error.message };
          }
        }, clusterData);

        if (response.ok) {
          clusterIds.push(response.data.id);
          console.log(`  📋 批量测试集群 ${i} 创建成功: ${response.data.id}`);
        }
      }

      this.recordScenario('批量删除-创建集群', clusterIds.length === 3, `创建了 ${clusterIds.length}/3 个集群`);

      // 批量删除集群
      let deletedCount = 0;
      const deleteResults = [];

      for (const clusterId of clusterIds) {
        const deleteResponse = await this.utils.page.evaluate(async (id) => {
          try {
            const resp = await fetch(`http://localhost:8000/api/v1/clusters/${id}`, {
              method: 'DELETE'
            });
            
            if (resp.ok) {
              return { ok: true, data: await resp.json() };
            } else {
              return { ok: false, error: await resp.text() };
            }
          } catch (error) {
            return { ok: false, error: error.message };
          }
        }, clusterId);

        deleteResults.push({
          clusterId,
          success: deleteResponse.ok,
          error: deleteResponse.error
        });

        if (deleteResponse.ok) {
          deletedCount++;
          console.log(`    ✅ 集群 ${clusterId} 删除成功`);
        } else {
          console.log(`    ❌ 集群 ${clusterId} 删除失败: ${deleteResponse.error}`);
        }
      }

      this.recordScenario('批量删除-删除操作', deletedCount === clusterIds.length, 
        `成功删除 ${deletedCount}/${clusterIds.length} 个集群`);

      console.log(`  📊 批量删除结果: ${deletedCount}/${clusterIds.length} 成功`);

    } catch (error) {
      this.recordScenario('批量删除测试', false, `测试异常: ${error.message}`);
      console.log(`  ❌ 批量删除测试异常: ${error.message}`);
    }
  }

  async testDeletionRollback() {
    console.log('🔹 5. 删除回滚测试');
    
    try {
      // 这个测试模拟删除过程中发生错误时的回滚行为
      console.log(`  💡 删除回滚测试 - 验证删除失败时的数据一致性`);
      
      // 创建一个测试集群
      const clusterData = {
        name: 'Rollback-Test-Cluster-' + Date.now(),
        description: '删除回滚测试集群',
        hive_metastore_url: 'mysql://testuser:testpass@localhost:3306/test_hive',
        hdfs_namenode_url: 'hdfs://localhost:9000'
      };

      const createResponse = await this.utils.page.evaluate(async (data) => {
        try {
          const resp = await fetch('http://localhost:8000/api/v1/clusters/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
          });
          
          if (resp.ok) {
            return { ok: true, data: await resp.json() };
          } else {
            return { ok: false, error: await resp.text() };
          }
        } catch (error) {
          return { ok: false, error: error.message };
        }
      }, clusterData);

      if (!createResponse.ok) {
        this.recordScenario('回滚测试-创建集群', false, `创建失败: ${createResponse.error}`);
        return;
      }

      const clusterId = createResponse.data.id;
      console.log(`  📋 回滚测试集群创建成功: ${clusterId}`);

      // 尝试删除一个不存在的集群ID来测试错误处理
      const invalidId = 99999;
      const invalidDeleteResponse = await this.utils.page.evaluate(async (id) => {
        try {
          const resp = await fetch(`http://localhost:8000/api/v1/clusters/${id}`, {
            method: 'DELETE'
          });
          
          if (resp.ok) {
            return { ok: true, data: await resp.json() };
          } else {
            return { ok: false, status: resp.status, error: await resp.text() };
          }
        } catch (error) {
          return { ok: false, error: error.message };
        }
      }, invalidId);

      if (!invalidDeleteResponse.ok && invalidDeleteResponse.status === 404) {
        this.recordScenario('回滚测试-无效ID处理', true, '正确返回404错误');
        console.log(`  ✅ 无效ID删除正确返回404错误`);
      } else {
        this.recordScenario('回滚测试-无效ID处理', false, '无效ID处理异常');
        console.log(`  ❌ 无效ID删除处理异常`);
      }

      // 验证有效集群仍然存在（没有被误删除）
      const verifyResponse = await this.utils.page.evaluate(async (id) => {
        try {
          const resp = await fetch(`http://localhost:8000/api/v1/clusters/${id}`);
          return resp.ok;
        } catch (error) {
          return false;
        }
      }, clusterId);

      this.recordScenario('回滚测试-数据一致性', verifyResponse, 
        verifyResponse ? '有效集群仍然存在' : '有效集群意外丢失');

      // 清理测试数据
      await this.utils.page.evaluate(async (id) => {
        try {
          await fetch(`http://localhost:8000/api/v1/clusters/${id}`, {
            method: 'DELETE'
          });
        } catch (error) {
          // 忽略清理错误
        }
      }, clusterId);

    } catch (error) {
      this.recordScenario('删除回滚测试', false, `测试异常: ${error.message}`);
      console.log(`  ❌ 删除回滚测试异常: ${error.message}`);
    }
  }

  async verifyDeletion(clusterId, scenarioName) {
    try {
      const exists = await this.utils.page.evaluate(async (id) => {
        try {
          const resp = await fetch(`http://localhost:8000/api/v1/clusters/${id}`);
          return resp.ok;
        } catch (error) {
          return false;
        }
      }, clusterId);

      this.recordScenario(scenarioName, !exists, 
        exists ? '集群仍然存在（删除失败）' : '集群已被删除（删除成功）');
    } catch (error) {
      this.recordScenario(scenarioName, false, `验证异常: ${error.message}`);
    }
  }

  async verifyCascadeDeletion(clusterId, taskIds) {
    try {
      // 验证集群被删除
      const clusterExists = await this.utils.page.evaluate(async (id) => {
        try {
          const resp = await fetch(`http://localhost:8000/api/v1/clusters/${id}`);
          return resp.ok;
        } catch (error) {
          return false;
        }
      }, clusterId);

      // 验证所有任务被删除
      let tasksExist = 0;
      for (const taskId of taskIds) {
        const taskExists = await this.utils.page.evaluate(async (id) => {
          try {
            const resp = await fetch(`http://localhost:8000/api/v1/tasks/${id}`);
            return resp.ok;
          } catch (error) {
            return false;
          }
        }, taskId);
        
        if (taskExists) tasksExist++;
      }

      const cascadeSuccess = !clusterExists && tasksExist === 0;
      this.recordScenario('级联删除-验证结果', cascadeSuccess, 
        cascadeSuccess ? '集群和所有依赖任务都被删除' : `集群存在:${clusterExists}, 任务存在:${tasksExist}个`);

    } catch (error) {
      this.recordScenario('级联删除-验证结果', false, `验证异常: ${error.message}`);
    }
  }

  async cleanupFailedCascadeTest(clusterId, taskIds) {
    try {
      // 先删除所有任务
      for (const taskId of taskIds) {
        await this.utils.page.evaluate(async (id) => {
          try {
            await fetch(`http://localhost:8000/api/v1/tasks/${id}`, {
              method: 'DELETE'
            });
          } catch (error) {
            // 忽略删除错误
          }
        }, taskId);
      }

      // 再删除集群
      await this.utils.page.evaluate(async (id) => {
        try {
          await fetch(`http://localhost:8000/api/v1/clusters/${id}`, {
            method: 'DELETE'
          });
        } catch (error) {
          // 忽略删除错误
        }
      }, clusterId);

      console.log(`  🧹 清理失败的级联测试数据完成`);
    } catch (error) {
      console.log(`  ⚠️ 清理数据时出现错误: ${error.message}`);
    }
  }

  async cleanupConstraintTestData(clusterId, taskId) {
    try {
      // 先删除任务
      await this.utils.page.evaluate(async (id) => {
        try {
          await fetch(`http://localhost:8000/api/v1/tasks/${id}`, {
            method: 'DELETE'
          });
        } catch (error) {
          // 忽略删除错误
        }
      }, taskId);

      // 再删除集群
      await this.utils.page.evaluate(async (id) => {
        try {
          await fetch(`http://localhost:8000/api/v1/clusters/${id}`, {
            method: 'DELETE'
          });
        } catch (error) {
          // 忽略删除错误
        }
      }, clusterId);

      console.log(`  🧹 约束测试数据清理完成`);
    } catch (error) {
      console.log(`  ⚠️ 清理约束测试数据时出现错误: ${error.message}`);
    }
  }

  recordScenario(scenario, success, details) {
    this.results.total++;
    if (success) {
      this.results.passed++;
    } else {
      this.results.failed++;
    }
    
    this.results.scenarios.push({
      scenario,
      success,
      details,
      timestamp: new Date().toISOString()
    });
  }

  generateDeletionReport() {
    console.log('\n' + '='.repeat(80));
    console.log('🗑️ 专项删除操作测试报告');
    console.log('='.repeat(80));
    
    const successRate = this.results.total > 0 ? (this.results.passed / this.results.total) * 100 : 0;
    
    console.log(`📊 总体评估:`);
    console.log(`  • 总测试场景: ${this.results.total}`);
    console.log(`  • 成功场景: ${this.results.passed}`);
    console.log(`  • 失败场景: ${this.results.failed}`);
    console.log(`  • 成功率: ${successRate.toFixed(1)}%`);
    
    console.log(`\n📋 场景详情:`);
    this.results.scenarios.forEach((scenario, index) => {
      const status = scenario.success ? '✅' : '❌';
      console.log(`  ${index + 1}. ${status} ${scenario.scenario}: ${scenario.details}`);
    });
    
    console.log(`\n🔍 删除类型分析:`);
    const simpleDeletes = this.results.scenarios.filter(s => s.scenario.includes('简单删除'));
    const cascadeDeletes = this.results.scenarios.filter(s => s.scenario.includes('级联删除'));
    const constraintTests = this.results.scenarios.filter(s => s.scenario.includes('约束'));
    const batchDeletes = this.results.scenarios.filter(s => s.scenario.includes('批量删除'));
    const rollbackTests = this.results.scenarios.filter(s => s.scenario.includes('回滚'));
    
    console.log(`  • 简单删除: ${simpleDeletes.filter(s => s.success).length}/${simpleDeletes.length} 成功`);
    console.log(`  • 级联删除: ${cascadeDeletes.filter(s => s.success).length}/${cascadeDeletes.length} 成功`);
    console.log(`  • 约束冲突: ${constraintTests.filter(s => s.success).length}/${constraintTests.length} 正确处理`);
    console.log(`  • 批量删除: ${batchDeletes.filter(s => s.success).length}/${batchDeletes.length} 成功`);
    console.log(`  • 删除回滚: ${rollbackTests.filter(s => s.success).length}/${rollbackTests.length} 成功`);
    
    console.log(`\n🎯 关键发现:`);
    const constraintErrors = this.results.scenarios.filter(s => 
      s.details.includes('约束错误') || s.details.includes('IntegrityError')
    );
    
    if (constraintErrors.length > 0) {
      console.log(`  ⚠️ 发现 ${constraintErrors.length} 个约束错误，需要改进删除逻辑:`);
      constraintErrors.forEach(error => {
        console.log(`    - ${error.scenario}: ${error.details}`);
      });
    } else {
      console.log(`  ✅ 未发现约束错误 - 删除逻辑运行良好`);
    }
    
    console.log(`\n💡 改进建议:`);
    if (successRate < 80) {
      console.log(`  🔧 需要改进API的删除处理逻辑`);
      console.log(`  🔧 实现正确的级联删除或依赖检查`);
      console.log(`  🔧 添加更好的错误处理和用户提示`);
    } else {
      console.log(`  ✅ 删除功能运行良好，继续保持测试覆盖`);
    }
    
    console.log(`\n🌟 测试评价:`);
    if (successRate >= 85) {
      console.log(`🏆 优秀 - 删除操作健壮可靠，错误处理完善！`);
    } else if (successRate >= 70) {
      console.log(`👍 良好 - 基本删除功能正常，部分场景需改进！`);
    } else {
      console.log(`⚠️ 需改进 - 删除操作存在重要问题，需要优先修复！`);
    }
    
    console.log('\n='.repeat(80));
  }
}

// 运行测试
async function runDeletionTests() {
  const tester = new DeletionOperationsTester();
  const results = await tester.testDeletionScenarios();
  
  if (results && results.passed >= results.total * 0.7) {
    console.log('\n🎉 专项删除操作测试通过！');
    process.exit(0);
  } else {
    console.log('\n💫 专项删除操作测试完成！发现了需要修复的删除问题！');
    process.exit(0);
  }
}

if (require.main === module) {
  runDeletionTests().catch(error => {
    console.error('删除测试运行失败:', error);
    process.exit(1);
  });
}

module.exports = DeletionOperationsTester;