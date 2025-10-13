# 文档导航

**欢迎来到Hive小文件治理平台文档中心!**

本项目采用**BMAD方法论**进行开发,所有需求和架构设计集中在两个核心文档中,确保单一事实源。

---

## 🎯 核心文档(必读)

| 文档 | 用途 | 何时阅读 |
|-----|------|---------|
| **[PRD - 产品需求文档](./prd.md)** | 功能需求、用户场景、Epic列表、非功能需求 | 理解产品目标、规划新功能、评估需求优先级 |
| **[Architecture - 架构设计文档](./architecture.md)** | 系统架构、模块设计、API规范、测试规范、部署指南 | 开发新功能、重构代码、解决架构问题、配置环境 |

**重要原则**:
> **"If it's not in prd.md or architecture.md, it doesn't exist!"**
> - 需求疑问?看prd.md
> - 架构疑问?看architecture.md
> - 测试规范?看architecture.md第9章
> - 部署配置?看architecture.md第7章 + 第10章

---

## 📖 架构决策记录(ADR)

重要技术决策的记录和理由,帮助理解"为什么这样设计":

- **[ADR索引](./adr/README.md)** - 所有ADR的目录
- **[ADR-0001: HDFS访问和扫描方案](./adr/0001-hdfs-access-and-scan-approach.md)** - 为什么选择WebHDFS而不是原生HDFS
- **[ADR-0002: 默认启用严格实连模式](./adr/0002-strict-real-default.md)** - 为什么strict_real默认为true
- **[ADR-0003: 统一Celery和Scanner为混合模式](./adr/0003-unify-celery-scanner-to-hybrid.md)** - 混合扫描架构的演进

**何时查看ADR**:
- 质疑某个设计决策时
- 要修改核心架构时
- 新成员了解历史背景时

---

## 📚 BMAD生成文档(自动生成,勿手工编辑)

以下目录由BMAD方法论自动生成和维护:

| 目录 | 用途 | 生成方式 |
|-----|------|---------|
| **epics/** | Epic级需求文档(大功能模块) | `/BMadpo shard-doc docs/prd.md` |
| **stories/** | Story级任务文档(小功能/bug修复) | `/BMadsm create-story` |
| **architecture/** | 架构详细拆分(coding-standards/tech-stack/source-tree) | `/BMadpo shard-doc docs/architecture.md` |
| **qa/** | QA评估和质量门禁(风险评估/测试设计/评审报告) | `/BMadqa *risk` `/BMadqa *review` |

**注意**:
- 这些目录的文档由BMAD Agent自动生成和更新
- 不要手工编辑这些文件,通过更新prd.md/architecture.md并重新生成
- 如果目录还不存在,执行`/BMadpo shard-doc docs/prd.md`会自动创建

---

## 📦 历史归档

| 目录 | 说明 |
|-----|------|
| **[../archive/docs/legacy/](../../archive/docs/legacy/)** | 已被prd.md/architecture.md替代的历史文档(18个文档归档) |

**归档文档列表**:
- Hive小文件治理平台_概要设计说明书.md (已整合到prd.md + architecture.md)
- FEATURE_LIST.md / FEATURE_TRACKER.md (已整合到prd.md的Epic列表)
- TESTING_RULES.md (已整合到architecture.md第9章)
- PRODUCTION_READINESS_CHECKLIST.md (已整合到architecture.md第7章)
- PORT_CONFIG.md (已整合到architecture.md第10章)
- MIGRATION_GUIDE.md (已整合到architecture.md第11章)
- dev-env.md (已整合到根目录README.md)
- ...其他13个历史文档

**何时查看归档**:
- 需要回溯历史决策时
- 查找被删除的旧文档时
- 了解项目演进历史时

---

## 🔄 文档更新流程

### 需求变更流程
```bash
# 1. 更新PRD文档
编辑 docs/prd.md (添加新Epic或修改需求)

# 2. 重新生成Epic/Story
/BMadpo shard-doc docs/prd.md

# 3. 验证生成结果
查看 docs/epics/ 和 docs/stories/ 目录
```

### 架构变更流程
```bash
# 1. 更新Architecture文档
编辑 docs/architecture.md (修改模块设计或技术栈)

# 2. 重新生成架构详细文档
/BMadpo shard-doc docs/architecture.md

# 3. 验证生成结果
查看 docs/architecture/ 目录下的coding-standards.md等
```

### Story开发流程(BMAD驱动)
```bash
# 1. 创建Story
/BMadsm create-story

# 2. 风险评估
/BMadqa *risk docs/stories/epic-6/story-001.md

# 3. 测试设计
/BMadqa *design docs/stories/epic-6/story-001.md

# 4. 开发并验证覆盖率
编写代码 + 单元测试
/BMadqa *trace docs/stories/epic-6/story-001.md

# 5. 完成后质量评审
/BMadqa *review docs/stories/epic-6/story-001.md

# 6. 通过QA Gate后合并代码
git add . && git commit
```

---

## 🎓 BMAD学习资源

如果你是第一次接触BMAD方法论:

1. **快速入门**: 阅读 `.bmad-core/user-guide.md`
   - 重点看"Core Development Cycle"流程图
   - 重点看"Test Architect (QA Agent)"部分

2. **Brownfield指南**: 阅读 `.bmad-core/working-in-the-brownfield.md`
   - 本项目是典型Brownfield(现有代码库),这个文档教你如何渐进式重构

3. **IDE工作流**: 阅读 `.bmad-core/enhanced-ide-development-workflow.md`
   - 学习如何在IDE中高效使用BMAD Agent

---

## 📊 文档健康度

| 指标 | 当前值 | 目标 |
|-----|-------|------|
| 核心文档数 | 3个 | 保持3个 |
| 需手工维护文档 | 2个(prd+arch) | 保持2个 |
| 文档碎片化程度 | 消除(单一事实源) | ✅ |
| 归档历史文档 | 18个 | 持续归档 |
| BMAD自动生成文档 | epics/stories/qa | 持续增长 |

---

## ❓ 常见问题

### Q: 我要添加新功能,应该更新哪个文档?
A: 更新`docs/prd.md`,添加新的Epic或Story,然后运行`/BMadpo shard-doc docs/prd.md`重新生成。

### Q: 我要修改架构设计,应该更新哪个文档?
A: 更新`docs/architecture.md`,然后运行`/BMadpo shard-doc docs/architecture.md`重新生成。

### Q: 测试规范在哪里?
A: `docs/architecture.md`第9章 - 测试架构。

### Q: 部署配置在哪里?
A: `docs/architecture.md`第7章(部署架构) + 第10章(端口和配置约定)。

### Q: 数据库迁移怎么操作?
A: `docs/architecture.md`第11章 - 数据库迁移。

### Q: 历史文档去哪了?
A: 全部归档到`../archive/docs/legacy/`,但建议优先查看prd.md/architecture.md。

### Q: 为什么文档这么少?
A: 我们遵循"单一事实源"原则,所有信息集中在prd.md和architecture.md,避免碎片化和维护成本。

---

**文档维护者**: 项目负责人
**最后更新**: 2025-10-12
**下次评审**: 每Sprint评审会
