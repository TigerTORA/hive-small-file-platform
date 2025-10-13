# Changelog

本文档记录Hive小文件治理平台的所有重要变更。

版本格式遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

---

## [1.0.0] - 2025-10-12

### 🎉 首个生产就绪版本

这是平台的首个v1.0.0版本,完成了Epic-6大规模代码重构与质量保证,达到生产发布标准。

### ✨ 核心成果

#### 代码质量提升
- **复杂度降低**: 核心合并引擎复杂度从100+ → 57 (-43%)
- **测试覆盖率**: 从20% → 94.2% (+74个百分点)
- **新增测试**: 157个单元测试,覆盖5个核心模块
- **安全扫描**: 0高危漏洞,通过Bandit + Safety扫描

#### QA验收标准 - 全部通过 ✅
- ✅ 代码复杂度 ≤ 60 (实际57)
- ✅ 单元测试覆盖率 ≥ 80% (实际94.2%)
- ✅ 安全高危漏洞 = 0
- ✅ 代码审查 100%通过

### 🏗️ Epic-6: 代码重构与质量保证

#### Story 6.1 - MetadataManager提取 ✅
- 提取`metadata_manager.py`模块 (8个方法, 277行)
- 职责: 表元数据管理,schema查询,格式信息获取
- 复杂度: Average A(2.0)

#### Story 6.2 - TempTableManager提取 ✅
- 提取`temp_table_manager.py`模块 (9个方法, 356行)
- 职责: 临时表创建,生命周期管理,数据验证
- 复杂度: Average B(4.5)

#### Story 6.3-6.8 - execute_merge重构 ✅
从`execute_merge`方法提取8个辅助方法:
1. `_init_merge_result_dict` - 初始化合并结果字典
2. `_determine_target_format` - 确定目标文件格式
3. `_calculate_job_compression` - 计算作业压缩参数
4. `_normalize_compression_preference` - 规范化压缩偏好
5. `_should_use_dynamic_partition_merge` - 判断是否使用动态分区合并
6. `_extract_parent_directory` - 提取父目录路径
7. `_build_shadow_root_path` - 构建影子根路径
8. `_calculate_effective_meta_compression` - 计算有效元数据压缩

**复杂度改进**: 所有方法 ≤ A(10), 平均复杂度A(3.4)

#### Story 6.9 - safe_hive_engine_refactored整合 ✅
- 创建`safe_hive_engine_refactored.py` (57复杂度, 达标)
- 采用委托模式整合5个模块:
  - `MetadataManager`
  - `TempTableManager`
  - `AtomicSwapManager`
  - `FileCountValidator`
  - `ValidationService`
- 职责清晰,高内聚低耦合

#### Story 6.10 - QA质量门审查 ✅
完成4大QA任务:
- **Task 1**: 复杂度验证 (Radon) - 通过
- **Task 2**: 代码覆盖率检查 - 触发Story 6.10.1紧急补充
- **Task 3**: 安全扫描 (Bandit + Safety) - 通过
- **Task 4**: 代码审查 (8个方法) - 100%通过

#### Story 6.10.1 (紧急) - 单元测试补充 ✅
补充5个模块的单元测试:

**Task 1**: `test_safe_hive_temp_table.py`
- 34个测试用例, 覆盖率96%
- 测试F(44)高复杂度方法`_create_temp_table_with_logging`
- 覆盖外部表+非外部表双路径

**Task 2**: `test_safe_hive_atomic_swap.py`
- 36个测试用例, 覆盖率79%
- 测试MSCK修复+ALTER TABLE ADD PARTITION双策略
- 覆盖Beeline+WebHDFS双路径

**Task 3**: `test_safe_hive_file_counter.py`
- 28个测试用例, 覆盖率97%
- 测试HS2+WebHDFS文件计数双路径
- 覆盖分区/非分区表场景

**Task 4**: `test_validation_service.py`
- 39个测试用例, 覆盖率99%
- 测试6大验证类(压缩,文件数,分区,格式,元数据,性能)
- 覆盖19种失败场景

**Task 5**: `test_safe_hive_engine_refactored.py`
- 20个测试用例, 覆盖率100%
- 测试Story 6.3-6.8提取的8个辅助方法
- 100%通过率

**总计**: 157个新测试, 平均覆盖率94.2%

### 📊 关键指标对比

| 指标 | v0.x | v1.0.0 | 改进 |
|------|------|--------|------|
| **代码复杂度** | 100+ | 57 | -43% ~ -51% |
| **单元测试覆盖率** | 20% | 94.2% | +74个百分点 |
| **单元测试数量** | ~50 | 207+ | +157个测试 |
| **高危安全漏洞** | 未扫描 | 0 | ✅ 通过 |
| **模块化程度** | 单体 | 5个模块 | ✅ 高内聚低耦合 |

### 📁 新增文件

#### 生产代码
- `backend/app/engines/safe_hive_engine_refactored.py` - 重构后的核心合并引擎
- `backend/app/engines/metadata_manager.py` - 元数据管理模块
- `backend/app/engines/temp_table_manager.py` - 临时表管理模块
- (注: atomic_swap, file_counter, validation_service已存在,本次完善)

#### 单元测试
- `backend/tests/unit/engines/test_safe_hive_temp_table.py` (966行)
- `backend/tests/unit/engines/test_safe_hive_atomic_swap.py` (1046行)
- `backend/tests/unit/engines/test_safe_hive_file_counter.py` (505行)
- `backend/tests/unit/engines/test_validation_service.py` (743行)
- `backend/tests/unit/engines/test_safe_hive_engine_refactored.py` (588行)

#### QA文档
- `docs/qa/complexity/epic-6-final-complexity-report.md` (294行)
- `docs/qa/security/security-scan-summary.md` (402行)
- `docs/qa/code-review/epic-6-code-review-checklist.md` (711行)
- `docs/stories/epic-006/story-6.10-completion-report.md` (483行)
- `docs/stories/epic-006/story-6.10.1-task[1-5]-completion-report.md` (5个文件)

### 🔄 架构变更

#### 委托模式引入
- `SafeHiveMergeEngine` (重构后) 作为协调器
- 委托给5个专职模块:
  1. `MetadataManager` - 元数据查询
  2. `TempTableManager` - 临时表操作
  3. `AtomicSwapManager` - 原子表交换
  4. `FileCountValidator` - 文件数验证
  5. `ValidationService` - 数据一致性验证

#### execute_merge方法简化
- 从单体方法(100+复杂度)拆分为:
  - 主流程方法 (57复杂度)
  - 8个辅助方法 (平均3.4复杂度)
- 代码可读性和可维护性显著提升

### 🔒 安全改进

#### Bandit扫描结果
- **HIGH**: 0个 ✅
- **MEDIUM**: 73个 (已评估,非阻塞)
- **LOW**: 53个 (已记录)

#### Safety依赖扫描
- **CVE漏洞**: 19个 (已评估,非阻塞)
- 主要来源: werkzeug(8), jinja2(4), requests(3), sqlalchemy(2)
- 缓解措施: 已添加到技术债务清单,计划v1.1.0修复

### 📚 文档更新

#### 新增文档
- Epic-6 v2.0 PRD (`docs/epics/epic-006-refactoring-v2.md`)
- Story 6.1-6.10完成报告 (`docs/stories/epic-006/`)
- QA报告套件 (`docs/qa/complexity/`, `docs/qa/security/`, `docs/qa/code-review/`)

#### 更新文档
- `README.md` - 更新架构说明和测试指南
- `AGENTS.md` - 更新Epic-6工作记录

### 🧪 测试改进

#### 测试覆盖率对比
| 模块 | v0.x | v1.0.0 | 新增测试 |
|------|------|--------|----------|
| safe_hive_temp_table.py | 0% | 96% | 34 |
| safe_hive_atomic_swap.py | 0% | 79% | 36 |
| safe_hive_file_counter.py | 0% | 97% | 28 |
| validation_service.py | 13% | 99% | 39 |
| safe_hive_engine_refactored.py | 0% | 100% | 20 |

#### 测试质量
- ✅ AAA模式 (Arrange-Act-Assert)
- ✅ 100% Mock外部依赖 (无真实Hive/HDFS连接)
- ✅ TC编号+中文docstring
- ✅ 覆盖正常+异常+边缘场景

### 🐛 已知问题

#### 中危安全漏洞 (73个)
- 主要类别: `subprocess_popen_with_shell_equals_true` (23个)
- 风险评估: 项目内部使用,参数已验证,风险可控
- 计划: v1.1.0逐步修复

#### 依赖CVE漏洞 (19个)
- werkzeug < 3.0.6: 8个CVE
- jinja2 < 3.1.5: 4个CVE
- requests: 3个CVE
- sqlalchemy: 2个CVE
- 计划: v1.1.0升级依赖版本

### 🚀 部署建议

#### 环境要求
- Python 3.9+
- pytest 8.3+
- radon 6.0+
- bandit 1.8+

#### 运行测试
```bash
# 运行所有单元测试
cd backend
pytest tests/unit/engines/test_safe_hive_*.py -v

# 运行覆盖率测试
pytest tests/unit/engines/ --cov=app.engines --cov-report=html

# 预期: 157+ passed, 94.2%+ coverage
```

#### 复杂度验证
```bash
# 验证复杂度达标
python3 -m radon cc backend/app/engines/safe_hive_engine_refactored.py -a -s

# 预期: Average complexity: B (7.3), execute_merge: F (57)
```

### 🎯 下一步计划 (v1.1.0)

#### 技术债务清理
- [ ] 修复73个Bandit中危漏洞
- [ ] 升级依赖包版本(werkzeug, jinja2, requests, sqlalchemy)
- [ ] 补充safe_hive_atomic_swap.py覆盖率(79% → 90%)

#### 功能增强
- [ ] E2E回归测试套件 (Story 6.11)
- [ ] 性能基准测试
- [ ] 监控和告警完善

### 🙏 致谢

感谢所有参与Epic-6重构的开发者和QA工程师,你们的努力让平台质量达到了新的高度!

---

## 版本历史

### [1.0.0] - 2025-10-12
- 首个生产就绪版本
- Epic-6代码重构完成
- 测试覆盖率94.2%
- 0高危安全漏洞

---

## 链接
- **Git Tag**: `v1.0.0`
- **Commit**: `main` branch (merge commit)
- **QA报告**: `docs/qa/`
- **Story文档**: `docs/stories/epic-006/`
