# 文档索引（Documentation Index）

本页汇总本项目的关键文档，便于快速定位与协作。

## 使用与发布
- 快速发布指南：`RELEASE.md`
- 生产编排（Docker Compose）：`docker-compose.prod.yml`
- 迁移与环境配置：`MIGRATION_GUIDE.md`

### 本地数据目录（工程化）
- 推荐将本地 SQLite 数据文件放在 `backend/var/data/` 下：
  - `.env` 示例：`DATABASE_URL=sqlite:///./var/data/hive_small_file_db.db`
  - 该目录已被 `.gitignore` 忽略，避免数据入库；不同操作系统下路径一致，便于协作。
  - 生产环境请使用 PostgreSQL/MySQL，并通过环境变量覆盖。

## 产品与需求（建议迁移到内部知识库，仅保留索引）
- 功能清单：`FEATURE_LIST.md`（可迁移）
- 功能跟踪：`FEATURE_TRACKER.md`（可迁移）
- 用户使用场景：`用户使用场景.md`（可迁移）
- 用户查询/交互分析：`USER_QUERY_FLOW_ANALYSIS.md`（可迁移）
- 仪表板规则说明：`DASHBOARD-RULES.md`

## 工程与实现
- 项目分析：`PROJECT_ANALYSIS.md`
- 问题清单：`PROJECT_ISSUES.md`
- 集群管理报告（样例）：`archive/docs/CLUSTER_MANAGEMENT_REPORT.md`
- 集成报告：`archive/docs/INTEGRATION_REPORT.md`
- 测试规则：`TESTING_RULES.md`
- 脚本说明：`scripts/README.md`
 - 开发联调脚本：`scripts/dev/`（原根目录的临时脚本已归档至此）

## 架构决策（ADR）
- 目录：`docs/adr/`
- 导读：`docs/adr/README.md`
- 示例：
  - `docs/adr/0001-hdfs-access-and-scan-approach.md`
  - `docs/adr/0002-strict-real-default.md`（如存在）
  - `docs/adr/0003-unify-celery-scanner-to-hybrid.md`（如存在）

## 参考
- 根 README：`README.md`
- 版本号：`VERSION`

提示：本次整理仅归拢文档入口，未调整源码与测试目录，确保现有功能与 CI 流水线保持稳定。
