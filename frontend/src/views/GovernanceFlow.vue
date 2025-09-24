<template>
  <div class="ppt-layout">
    <el-card class="ppt-card" shadow="always">
      <header class="ppt-header">
        <el-tag type="success" size="large">DataNova · Hive 治理</el-tag>
        <h1>小文件治理全流程</h1>
        <p>五步闭环帮助我们从发现小文件问题，到执行治理、复核成效并沉淀治理经验。</p>
      </header>

      <section class="flow-diagram">
        <div
          v-for="(node, index) in flowNodes"
          :key="node.title"
          class="flow-node"
        >
          <div class="flow-icon">
            <el-icon><component :is="node.icon" /></el-icon>
          </div>
          <span class="flow-step">STEP {{ index + 1 }}</span>
          <h3>{{ node.title }}</h3>
          <small>{{ node.subtitle }}</small>
          <p>{{ node.description }}</p>
        </div>
      </section>

      <section class="summary-grid">
        <div class="summary-block">
          <h2>平台支撑能力</h2>
          <ul>
            <li v-for="item in platformSupports" :key="item">{{ item }}</li>
          </ul>
        </div>
        <div class="summary-block">
          <h2>执行要点</h2>
          <div class="stage-block" v-for="stage in guardrailStages" :key="stage.title">
            <h3>{{ stage.title }}</h3>
            <ul>
              <li v-for="point in stage.points" :key="point">{{ point }}</li>
            </ul>
          </div>
        </div>
      </section>
    </el-card>
  </div>
</template>

<script setup lang="ts">
  import { Search, DataAnalysis, Setting, Timer, Finished } from '@element-plus/icons-vue'

  interface FlowNode {
    title: string
    subtitle: string
    description: string
    icon: any
  }

  interface GuardrailStage {
    title: string
    points: string[]
  }

  const flowNodes: FlowNode[] = [
    {
      title: '扫描发现',
      subtitle: 'Scan Tasks → TableMetric/PartitionMetric',
      description: '调度器定时扫描 Hive 元数据与 HDFS 路径，生成 total_files、small_files、冷数据标签等基础指标。',
      icon: Search
    },
    {
      title: '洞察分析',
      subtitle: 'Dashboard 视图',
      description: 'Dashboard 将指标按存储/压缩、访问热度、问题表 TOP10 等维度可视化，辅助定位优先治理对象。',
      icon: DataAnalysis
    },
    {
      title: '策略编排',
      subtitle: 'TableDetail 治理面板',
      description: '在表详情发起治理，默认安全合并，可配置目标文件大小、格式升级及存储策略（纠删码、副本等）。',
      icon: Setting
    },
    {
      title: '治理执行',
      subtitle: 'MergeTask + 调度器',
      description: '任务中心统一排产执行，跟踪进度、日志与资源使用；失败自动重试并保留回退能力。',
      icon: Timer
    },
    {
      title: '验证回收',
      subtitle: '复扫校验 + 历史沉淀',
      description: '任务完成后自动复扫对比治理效果，并归档执行记录，支撑持续优化和审计追溯。',
      icon: Finished
    }
  ]

  const platformSupports: string[] = [
    '任务中心统一调度：MergeTask、Celery Scheduler、WebSocket 推送',
    '治理策略引擎：安全合并、存储/压缩格式转换、纠删码与副本策略',
    '指标与可视化：Dashboard、冷数据分层、治理前后对比视图',
    '审计与集成：REST API、Webhook、执行与回滚日志全留痕'
  ]

  const guardrailStages: GuardrailStage[] = [
    {
      title: '执行前',
      points: [
        '确认表是否为 ACID 或关键业务表，必要时选择维护窗口',
        '评估目标格式与压缩对上下游的兼容性，避免查询行为受影响'
      ]
    },
    {
      title: '执行中',
      points: [
        '关注任务中心实时日志，异常时及时排查 HDFS / YARN 资源压力',
        '分区治理控制并发，避免对 NameNode/网络造成尖峰负载'
      ]
    },
    {
      title: '执行后',
      points: [
        '复扫校验治理效果，确认小文件指标下降并记录治理报告',
        '如需回滚可在任务中心快速恢复原始文件，保障业务连续性'
      ]
    }
  ]
</script>

<style scoped>
  .ppt-layout {
    display: flex;
    justify-content: center;
    padding: 32px;
    background: var(--bg-app);
  }

  .ppt-card {
    width: 100%;
    max-width: 1080px;
    border-radius: 24px;
    border: 1px solid var(--gray-200);
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.04), rgba(64, 158, 255, 0));
    display: flex;
    flex-direction: column;
    gap: 28px;
    padding: 32px 36px 36px;
  }

  .ppt-header {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .ppt-header h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 600;
    color: var(--gray-900);
  }

  .ppt-header p {
    margin: 0;
    color: var(--gray-600);
    line-height: 1.6;
  }

  .flow-diagram {
    position: relative;
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 16px 0;
  }

  .flow-diagram::before {
    content: '';
    position: absolute;
    top: 64px;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, rgba(64, 158, 255, 0.2) 0%, rgba(64, 158, 255, 0.6) 50%, rgba(64, 158, 255, 0.2) 100%);
    z-index: 0;
  }

  .flow-node {
    position: relative;
    width: 20%;
    min-width: 160px;
    background: white;
    border-radius: 18px;
    padding: 18px;
    box-shadow: var(--elevation-1);
    border: 1px solid rgba(64, 158, 255, 0.2);
    display: flex;
    flex-direction: column;
    gap: 6px;
    z-index: 1;
  }

  .flow-icon {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    background: rgba(64, 158, 255, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--primary-500, #409eff);
    font-size: 22px;
  }

  .flow-step {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--primary-600, #337ecc);
  }

  .flow-node h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--gray-900);
  }

  .flow-node small {
    color: var(--gray-500);
    font-size: 12px;
  }

  .flow-node p {
    margin: 0;
    font-size: 13px;
    color: var(--gray-600);
    line-height: 1.5;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 28px;
  }

  .summary-block {
    background: white;
    border-radius: 20px;
    padding: 20px 24px;
    border: 1px solid var(--gray-200);
    box-shadow: var(--elevation-1);
  }

  .summary-block h2 {
    margin: 0 0 12px;
    font-size: 18px;
    font-weight: 600;
    color: var(--gray-900);
  }

  .summary-block ul {
    margin: 0;
    padding-left: 18px;
    color: var(--gray-600);
    line-height: 1.6;
    font-size: 13px;
  }

  .stage-block + .stage-block {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px dashed var(--gray-200);
  }

  .stage-block h3 {
    margin: 0 0 4px;
    font-size: 14px;
    font-weight: 600;
    color: var(--gray-700);
  }

  @media (max-width: 1024px) {
    .flow-diagram {
      flex-direction: column;
      align-items: stretch;
    }

    .flow-diagram::before {
      display: none;
    }

    .flow-node {
      width: 100%;
    }

    .summary-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 768px) {
    .ppt-layout {
      padding: 20px;
    }

    .ppt-card {
      padding: 24px 20px 28px;
    }

    .ppt-header h1 {
      font-size: 24px;
    }
  }
</style>
