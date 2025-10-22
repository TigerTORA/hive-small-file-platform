# 项目文档目录

## 📚 文档导航

### 功能测试文档

> **从这里开始**: [testing-README.md](./testing-README.md)

| 文档 | 说明 | 更新频率 |
|------|------|----------|
| [testing-README.md](./testing-README.md) | 📍 测试文档总索引 | 有新文档时更新 |
| [testing-guide.md](./testing-guide.md) | 📖 测试使用指南 | 流程变更时更新 |
| [functional-test-checklist.md](./functional-test-checklist.md) | 📋 测试清单模板（v1.1） | 测试项变更时更新 |
| [functional-test-report-YYYY-MM-DD.md](./functional-test-report-2025-10-21.md) | ✅ 测试报告实例 | 每次测试生成新文件 |

### 其他文档

| 文档 | 说明 |
|------|------|
| [AGENTS_BMAD.md](./AGENTS_BMAD.md) | Agent 开发相关文档 |

---

## 🎯 快速开始

### 执行功能测试

```bash
# 1. 阅读测试指南
cat docs/testing-guide.md

# 2. 查看测试清单
cat docs/functional-test-checklist.md

# 3. 创建测试报告
cp docs/functional-test-checklist.md docs/functional-test-report-$(date +%Y-%m-%d).md

# 4. 开始测试
# 打开测试报告，参照清单逐项执行
```

### 更新测试清单

```bash
# 1. 编辑测试清单
vim docs/functional-test-checklist.md

# 2. 更新版本号和历史记录

# 3. 提交变更
git add docs/functional-test-checklist.md
git commit -m "docs(test): 更新测试清单 vX.X"
```

---

## 📖 文档分类说明

### 📋 TEMPLATE（模板文档）

**定义**: 可复用的模板，定义标准和检查点

**文件**:
- `functional-test-checklist.md` - 功能测试检查清单

**特点**:
- 内容相对固定
- 修改需要团队审核
- 有版本控制

### ✅ REPORT（报告文档）

**定义**: 每次测试的实际执行记录

**文件**:
- `functional-test-report-YYYY-MM-DD.md` - 按日期命名的测试报告

**特点**:
- 每次测试生成新文件
- 记录实际测试结果
- 可归档到 `archive/` 目录

### 📖 GUIDE（指南文档）

**定义**: 操作指南和最佳实践

**文件**:
- `testing-guide.md` - 测试使用指南
- `testing-README.md` - 测试文档索引

**特点**:
- 帮助理解和使用
- 流程变更时更新
- 面向新手友好

---

## 🗂️ 目录结构

```
docs/
├── README.md                            # 📍 本文件：文档总索引
│
├── testing-README.md                    # 测试文档总索引
├── testing-guide.md                     # 测试使用指南
├── functional-test-checklist.md         # 测试清单模板 v1.1
├── functional-test-report-2025-10-21.md # 测试报告示例
│
└── AGENTS_BMAD.md                       # Agent 开发文档
```

---

## 📝 文档维护规范

### 添加新文档

1. 在 `docs/` 目录下创建文档
2. 使用清晰的文件名（小写，用 `-` 分隔）
3. 在本 README 中添加链接和说明
4. 提交 commit 说明文档用途

### 归档旧文档

```bash
# 定期归档测试报告
mkdir -p archive/test-reports/YYYY-QX/
mv docs/functional-test-report-YYYY-MM-*.md archive/test-reports/YYYY-QX/
```

### 版本控制

- 重要文档（如测试清单）需要版本号
- 版本号格式：`vX.Y` (如 v1.1, v2.0)
- 在文档头部和版本历史中记录

---

## 🔗 相关资源

- **项目主 README**: [../README.md](../README.md)
- **API 文档**: http://localhost:8000/docs (服务运行时)
- **前端应用**: http://localhost:5173 (服务运行时)

---

**最后更新**: 2025-10-21
**维护者**: 开发团队
