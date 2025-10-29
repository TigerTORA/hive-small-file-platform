# ADR: HAR SSH 配置下线与 YARN Kerberos 支持规划

- **日期**：2025-10-29
- **状态**：Accepted
- **决策者**：集群管理模块产品与研发团队
- **相关工单 / PR**：待补充

## 背景

前端 `ClustersManagement` 表单中保留了 “HAR SSH 配置（可选）” 区块，用于 Hadoop Archives 任务的默认 SSH 与 Kerberos 参数，并将配置持久化到浏览器本地。然而：

1. 平台目前未提供 HAR 任务编排或执行能力，相关配置没有被后端消费。
2. 该功能为单机本地存储，难以在多人协作或多端环境下复用，增加 UI 复杂度。

另外，在集群配置项中暴露了 YARN Resource Manager 地址，但连接逻辑仅支持无认证的 HTTP 访问。生产环境普遍启用了 Kerberos，现状会造成监控与诊断能力缺失。

## 决策

1. **下线 HAR SSH 配置表单**  
   - 将前端 `HAR SSH 配置（可选）` 区块移除，避免误导用户。  
   - 清理相关本地存储逻辑与命令预览。  
   - 在发布说明中提示该字段取消，确认无历史数据依赖。

2. **规划 YARN Kerberos 支持**  
   - 在后续迭代中评估为 YARN 监控客户端 (`YarnResourceManagerMonitor`) 引入 Kerberos 认证的必要性。  
   - 产出详细方案（使用 `requests-kerberos`、票据管理、配置项）后再推进实现。  
   - 在此期间，文档内明确标注 “当前仅支持非 Kerberos 访问”。

## 备选方案

- 保留 HAR 配置但将其隐藏在高级设置中：仍然缺乏后端支撑，不解决冗余问题。  
- 立即实现 YARN Kerberos：当前工作量与优先级不足，先通过 ADR 留档并在后续排期。

## 影响

- UI 更精简，降低新用户困惑；需同步更新 PRD / 用户文档。  
- 历史本地存储的 HAR 配置将不再使用，可忽略或在变更日志中提醒用户自行清理。  
- 在 YARN Kerberos 支持落地前，使用 Kerberos 的环境仍无法通过平台获取 RM 状态，需要人工监控。

## 实施情况

- ✅ HAR SSH 配置已自 `frontend/src/views/ClustersManagement.vue` 移除，同时清理 `useTableActions` 中的依赖逻辑。  
- ✅ 文档已同步更新：`docs/PRD/集群管理-模块.MD`、`docs/PRD/yarn_kerberos_support.md`。  
- ⏳ YARN Kerberos 方案仍在规划阶段，详见 `docs/PRD/yarn_kerberos_support.md`。

## 后续行动

1. 继续评估并设计 YARN Kerberos 认证方案（如有需要可另起 ADR 或扩展设计文档）。  
2. 完成 Kerberos 支持实施后，更新文档、测试与发布说明。
