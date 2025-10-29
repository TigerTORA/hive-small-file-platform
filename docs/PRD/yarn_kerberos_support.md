# YARN Kerberos 支持需求草案

> 版本：v0.1（2025-10-29）  
> 状态：Draft  
> 关联 ADR：`docs/ADR/2025-10-29-har-ssh-config-and-yarn-kerberos.md`

## 背景
- 当前 `YarnResourceManagerMonitor` 通过 HTTP 访问 RM REST API，仅支持无认证环境。
- 生产环境常启用 Kerberos，导致 RM 状态/诊断能力缺失。
- 集群配置界面已有基础认证字段（Kerberos principal、keytab 等），可复用，但尚未用于 YARN 通路。

## 目标
1. 在启用 Kerberos 的 YARN 集群上获取 RM 健康指标与任务信息。
2. 提供明确的配置项和错误诊断，避免静默失败。
3. 保持对无 Kerberos 环境的向后兼容。

## 用户故事
- **运维**：我在集群管理中填写 RM 地址与 Kerberos 凭据后，期望平台能够自动获取活跃 RM、任务状态等信息；若票据过期，应提示原因。
- **开发者**：在无 Kerberos 环境中不希望增加额外配置或引入新的依赖冲突。

## 范围
- **支持**：
  - 使用 `requests-kerberos`（或替代方案）为 RM REST 请求添加 Kerberos 身份验证。
  - 支持 keytab + principal 方式自动执行 `kinit`，可选自定义 ticket cache。
  - 在连接测试和健康指标接口中返回诊断信息（成功/失败原因、建议）。
- **不含**：
  - YARN 应用提交/终止能力。
  - YARN ProxyUser / Delegation Token 管理。

## 技术方案概要
1. **依赖与环境**
   - 后端引入 `requests-kerberos`（需在 `backend/requirements.txt` 添加，可选按需加载）。
   - `kinit` 调用复用现有 WebHDFS Kerberos 实现逻辑（`WebHDFSClient._configure_kerberos`）。

2. **配置扩展**
   - 复用 `Cluster` 模型中的 `kerberos_principal`、`kerberos_keytab_path`、`kerberos_ticket_cache`。
   - 增加 `yarn_auth_type` 字段？（可选，默认为 `NONE`，启用 Kerberos 时设为 `KERBEROS`）。

3. **客户端改造**
   - 在 `YarnResourceManagerMonitor` 初始化阶段，检测 `yarn_auth_type` 或集群 Kerberos 信息，构建带认证的 `requests.Session`。
   - 复用 `_configure_kerberos` 逻辑：设置 `KRB5CCNAME`、执行 `kinit`、处理 keytab 缺失异常。
   - 增加诊断记录（参考 `KerberosDiagnostic` 工具），便于前端展示错误。

4. **接口更新**
   - `POST /clusters/{id}/test` 与 `/test-enhanced` 中的 YARN 检查项需适配 Kerberos。
   - `GET /clusters/health-metrics`、`/batch-health-check` 返回 YARN 结果时包含认证错误信息。

5. **前端**
   - 集群设置页新增开关或提示：“启用 Kerberos YARN 访问”。
   - 在连接测试弹窗中展示 YARN 认证错误提示及建议。

## 风险与缓解
| 风险 | 描述 | 缓解措施 |
| --- | --- | --- |
| 依赖 `requests-kerberos` 在无 Kerberos 环境下失效 | 部署缺乏库或系统未安装 Kerberos 客户端 | 在启动或连接测试前检查依赖，提示安装说明 |
| keytab 权限/路径问题 | 读取失败导致测试报错 | 复用 WebHDFS 的路径检查及友好报错 |
| `kinit` 阻塞或票据泄漏 | 长时间运行产生残留 | 使用子进程执行并捕获输出；在退出时恢复 `KRB5CCNAME` |

## 验收标准
- Kerberos 环境下，执行连接测试可获得 `overall_status=success`，并能读取 `/ws/v1/cluster/info`。
- 未配置 Kerberos 时保持现有行为，无需额外输入。
- 错误信息中包含明确诊断（如 keytab 缺失、票据过期）。

## 后续工作
| 序号 | 任务 | 交付物 | 负责人 | 预计完成 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | 依赖评估与 PoC | `requests-kerberos` 可用性验证、keytab/kinit 流程记录 | _待指派_ | _TBD_ | 待建 |
| 2 | 后端实现 | `YarnResourceManagerMonitor` Kerberos 支持、诊断日志、单元测试 | _待指派_ | _TBD_ | 待建 |
| 3 | 前端支持 | 集群表单开关/提示、连接测试 UI 更新 | _待指派_ | _TBD_ | 待建 |
| 4 | 文档与发布说明 | 更新 PRD、用户手册、发布日志 | _待指派_ | _TBD_ | 待建 |
| 5 | 回归测试 | Kerberos / 非 Kerberos 双环境验证、CI 脚本 | _待指派_ | _TBD_ | 待建 |

> 注：创建看板任务时可直接复制上述条目，并补充负责人与时间节点。
