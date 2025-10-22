# 测试文档索引

## 📚 文档结构

```
docs/
├── testing-README.md                    # 📍 本文件：测试文档导航
├── testing-guide.md                     # 📖 使用指南
├── functional-test-checklist.md         # 📋 测试清单模板（v1.1）
├── functional-test-report-2025-10-21.md # ✅ 测试报告示例
└── functional-test-report-YYYY-MM-DD.md # 📝 每次测试报告
```

---

## 🎯 快速导航

### 👥 不同角色的使用指引

#### 测试执行者

1. **首次使用**：
   - 阅读 [testing-guide.md](./testing-guide.md) 了解测试流程
   - 熟悉 [functional-test-checklist.md](./functional-test-checklist.md) 的测试项

2. **执行测试**：
   - 复制测试报告模板，创建新的测试报告
   - 参照测试清单逐项执行
   - 记录结果和问题

3. **报告归档**：
   - 完成测试后提交报告到版本控制
   - 严重问题提交 issue 追踪

#### 开发人员

1. **修复问题**：
   - 查看最新测试报告中的 `⚠️ ISSUE` 部分
   - 修复后通知测试人员回归测试

2. **添加功能**：
   - 功能完成后，在测试清单中添加对应测试项（需审核）
   - 提供测试用例和预期结果

#### 项目管理者

1. **跟踪进度**：
   - 查看最新测试报告的完成度
   - 统计测试覆盖率和通过率

2. **审核变更**：
   - 审核测试清单的修改 PR
   - 确保测试标准的一致性

---

## 📋 核心文档说明

### 1. 测试清单模板（functional-test-checklist.md）

**性质**：可复用模板，包含所有测试检查点

**内容分类**：
- 📋 **TEMPLATE**：固定测试项（需审核才能修改）
- 📖 参考命令和示例
- ✅ 预期结果说明

**版本管理**：
- 当前版本：v1.1 (2025-10-21)
- 修改记录在文档末尾的"版本历史"

**适用场景**：
- 制定测试计划
- 评审测试标准
- 新人培训参考

### 2. 测试报告实例（functional-test-report-YYYY-MM-DD.md）

**性质**：每次测试的实际执行记录

**内容分类**：
- ✏️ **FILL**：填写测试环境信息
- ✅ **RESULT**：记录实际测试结果
- ⚠️ **ISSUE**：记录问题（解决后可删除）

**命名规则**：
- 格式：`functional-test-report-YYYY-MM-DD.md`
- 同一天多次测试：`functional-test-report-YYYY-MM-DD-01.md`

**归档规则**：
- 保留最近 3-6 个月的报告
- 历史报告归档到 `archive/test-reports/`

### 3. 使用指南（testing-guide.md）

**性质**：操作手册

**包含内容**：
- 测试流程说明
- 内容分类详解
- 最佳实践
- 常见问题解答

**适合对象**：
- 首次执行测试的人员
- 需要了解文档规范的团队成员

---

## 🔄 工作流程

### 新建测试任务

```bash
# 1. 创建测试报告
cp docs/functional-test-checklist.md docs/functional-test-report-$(date +%Y-%m-%d).md

# 2. 清理上次的结果
# 删除所有 ✅ RESULT 和 ⚠️ ISSUE 部分的内容

# 3. 开始测试
# 填写 ✏️ FILL 部分，执行测试并记录结果
```

### 更新测试清单

```bash
# 1. 创建分支
git checkout -b update-test-checklist

# 2. 修改 functional-test-checklist.md

# 3. 更新版本号和版本历史

# 4. 提交 PR 等待审核
git add docs/functional-test-checklist.md
git commit -m "docs(test): 添加XXX功能的测试项"
git push origin update-test-checklist
```

### 归档测试报告

```bash
# 定期归档（每月或每季度）
mkdir -p archive/test-reports/2025-Q4/
mv docs/functional-test-report-2025-10-*.md archive/test-reports/2025-Q4/
```

---

## 📊 当前状态

### 最新测试

- **日期**: 2025-10-21
- **报告**: [functional-test-report-2025-10-21.md](./functional-test-report-2025-10-21.md)
- **进度**: 🟡 进行中（已完成 1/10）
- **状态**: ✅ 环境搭建成功，服务正常运行

### 测试覆盖率

| 部分 | 状态 | 完成度 |
|------|------|--------|
| 一、前置条件 | ✅ 完成 | 100% |
| 二、API基础 | ⏳ 待测 | 0% |
| 三、集群管理 | ⏳ 待测 | 0% |
| 四、表与扫描 | ⏳ 待测 | 0% |
| 五、数据归档 | ⏳ 待测 | 0% |
| 六、存储管理 | ⏳ 待测 | 0% |
| 七、任务中心 | ⏳ 待测 | 0% |
| 八、WebSocket | ⏳ 待测 | 0% |
| 九、前端路径 | ⏳ 待测 | 0% |
| 十、通过标准 | ⏳ 待测 | 0% |

---

## 🔗 相关资源

### 项目文档

- [项目 README](../README.md)
- [开发指南](../docs/development-guide.md)（如有）
- [API 文档](http://localhost:8000/docs)（服务运行时）

### 测试工具

- **API 测试**: curl, Postman, httpie
- **前端测试**: Chrome DevTools, Playwright
- **性能测试**: Apache Bench, wrk（如需要）

### 持续集成

- **CI 配置**: `.github/workflows/`（如有）
- **自动化测试**: `make test`, `pytest`
- **代码覆盖**: `make coverage`

---

## 💡 贡献指南

### 完善测试清单

1. 发现遗漏的测试点？
   - 在 GitHub 提交 issue
   - 说明功能和建议的测试项

2. 改进测试描述？
   - 提交 PR 并说明改进原因
   - 小改动（错别字、格式）可直接修改
   - 大改动（测试项、标准）需审核

### 提交测试报告

1. 完成测试后：
   - 提交报告到版本控制
   - 标题：`docs(test): 添加 YYYY-MM-DD 功能测试报告`

2. 发现严重问题：
   - 在 GitHub 提交 issue
   - 关联对应的测试报告

---

## 📞 联系方式

- **问题反馈**: 提交 GitHub Issue
- **文档改进**: 提交 Pull Request
- **紧急问题**: 联系项目维护者

---

**最后更新**: 2025-10-21
**文档版本**: v1.0
