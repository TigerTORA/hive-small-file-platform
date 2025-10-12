# Backend文档说明

## 📍 文档位置

项目文档已统一迁移到项目根目录的 `/docs/` 目录。

**请访问**: `/Users/luohu/new_project/hive-small-file-platform/docs/`

## 📂 文档结构

```
/docs/
├── adr/                    # 架构决策记录 (Architecture Decision Records)
├── architecture/           # 系统架构文档
├── epics/                  # Epic PRD文档
│   ├── epic-006-code-refactoring.md      # Epic-6 v1.0
│   └── epic-006-refactoring-v2.md        # Epic-6 v2.0
├── qa/                     # QA相关文档
│   ├── complexity/         # 代码复杂度报告
│   ├── risk-assessment/    # 风险评估
│   └── ...
└── stories/                # Story执行记录
    └── epic-006/
```

## 📝 快速导航

### Epic文档
- [Epic-6 v2.0 PRD](../docs/epics/epic-006-refactoring-v2.md)
- [Epic-6 v1.0 PRD](../docs/epics/epic-006-code-refactoring.md)

### 架构文档
- [系统架构](../docs/architecture/)

### QA文档
- [复杂度基线报告](../docs/qa/complexity/)
- [风险评估报告](../docs/qa/risk-assessment/)

## 🗂️ 归档文档

旧版本文档已归档到 `/archive/docs/epic-6-v1/`

## ℹ️ 说明

- **backend/docs/** 目录已不再使用，仅保留此README作为导航
- 所有项目级文档统一在 `/docs/` 目录管理
- Backend特定的技术文档（如API设计、数据库schema等）将来如有需要，可在此目录下创建

---

**维护者**: Dev Team
**最后更新**: 2025-10-12
**文档版本**: v1.0
