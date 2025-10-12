# Story 6.1风险评估报告

**Story**: Epic-6 Story-1 - 提取MetadataManager模块
**评估时间**: 2025-10-12
**评估方法**: BMAD QA Agent风险评估框架
**评估者**: QA Architect (基于BMAD方法论)

---

## 执行摘要

**总体风险等级**: 🟡 中等风险
**建议是否继续**: ✅ 建议继续,但需严格执行缓解措施
**关键风险数量**: 3个高风险,4个中风险
**预估成功率**: 75% (基于上次失败教训调整后)

---

## 1. 历史失败分析 (Critical Context)

### 1.1 上次重构失败回顾 (Commit 840f29b)

**失败时间**: 2025-09-XX (根据git log推断)
**失败方式**: 回滚整个重构 (6b6ef84拆分 → 840f29b回滚)
**影响范围**: safe_hive_engine.py从431行回滚到4081行

**失败根本原因** (来自Commit Message):
1. ❌ **execute_merge未实现**: 方法体为stub,抛出NotImplementedError
2. ❌ **方法名映射不一致**: 使用`self.metadata`但实际为`self.metadata_manager`
3. ❌ **方法签名不匹配**: 模块使用keyword-only参数,主引擎传位置参数
4. ❌ **依赖方法缺失**: 部分方法在拆分过程中遗漏

**教训**:
- 渐进式重构优于一次性大规模重构
- 方法签名必须100%一致,包括参数类型/顺序/默认值
- 必须保留execute_merge的完整实现,不能留stub
- 依赖方法必须通过代码分析完整识别,不能遗漏

---

## 2. 风险识别矩阵

| 风险ID | 风险描述 | 概率 | 影响 | 风险等级 | 缓解措施 |
|--------|---------|------|------|---------|---------|
| R1 | 方法签名不匹配(重复失败原因#3) | 高 | 极高 | 🔴 HIGH | mypy静态检查 + 逐方法对照 |
| R2 | 依赖方法遗漏(重复失败原因#4) | 中 | 高 | 🟡 MEDIUM | IDE "Find Usages" + Grep扫描 |
| R3 | execute_merge调用路径破坏(重复失败原因#1) | 高 | 极高 | 🔴 HIGH | 提取前编写完整集成测试 |
| R4 | 命名不一致(重复失败原因#2) | 低 | 中 | 🟢 LOW | 代码审查强制检查 |
| R5 | 单元测试覆盖不足 | 中 | 中 | 🟡 MEDIUM | 强制80%覆盖率 |
| R6 | 回归测试失败 | 中 | 高 | 🟡 MEDIUM | 每次修改后立即测试 |
| R7 | 生产环境数据丢失 | 极低 | 极高 | 🟡 MEDIUM | 仅在开发环境重构,不直接上生产 |

---

## 3. 高风险详细分析

### 风险R1: 方法签名不匹配 🔴

**风险描述**:
上次重构失败的关键原因之一。新提取的MetadataManager方法签名与原safe_hive_engine.py不一致,导致主引擎调用失败。

**具体场景**:
```python
# ❌ 上次错误示例(推测)
# safe_hive_metadata_manager.py
def _get_table_location(self, *, database_name: str, table_name: str) -> Optional[str]:
    # 使用了keyword-only参数(*)

# safe_hive_engine.py
result = self.metadata._get_table_location(database, table)  # 位置参数调用失败!
```

**当前Story中的10个方法签名** (必须100%一致):
1. `_get_table_location(database_name: str, table_name: str) -> Optional[str]`
2. `_table_exists(database_name: str, table_name: str) -> bool`
3. `_is_partitioned_table(database_name: str, table_name: str) -> bool`
4. `_get_table_partitions(database_name: str, table_name: str) -> List[str]`
5. `_get_table_format_info(database_name: str, table_name: str) -> Dict[str, Any]`
6. `_get_table_columns(database_name: str, table_name: str) -> Tuple[List[str], List[str]]`
7. `_is_unsupported_table_type(fmt: Dict) -> bool`
8. `_unsupported_reason(fmt: Dict) -> str`
9. `_infer_storage_format_name(fmt: Dict) -> str`
10. `_infer_table_compression(fmt: Dict, storage_format: str) -> str`

**缓解措施**:
- ✅ **Step 1**: 使用`/tmp/safe_hive_engine_documented.md`作为方法签名参考
- ✅ **Step 2**: 提取前运行`mypy backend/app/engines/safe_hive_engine.py`确保原文件类型正确
- ✅ **Step 3**: 提取后运行`mypy backend/app/engines/safe_hive_metadata_manager.py`验证新文件
- ✅ **Step 4**: 集成后运行`mypy backend/app/engines/`验证调用链
- ✅ **Step 5**: 代码审查重点检查方法签名一致性

**验收标准**:
- [ ] Mypy静态检查无错误
- [ ] 所有方法签名与原文件100%一致
- [ ] 集成测试通过

---

### 风险R3: execute_merge调用路径破坏 🔴

**风险描述**:
execute_merge是safe_hive_engine.py的核心方法(294-798行,504行代码),包含3个分支逻辑:
1. 分支1: 分区表整表合并 (`_execute_full_table_dynamic_partition_merge`)
2. 分支2: 分区级合并 (`_execute_partition_native_merge`)
3. 分支3: 整表合并 (主流程)

上次重构失败的根本原因是execute_merge留了stub导致所有合并任务失败。

**依赖分析** (基于`/tmp/safe_hive_engine_documented.md`):
```python
execute_merge()
  ├── _is_partitioned_table()  ← MetadataManager方法
  ├── _get_table_format_info()  ← MetadataManager方法
  ├── _get_table_location()  ← MetadataManager方法
  └── [如果_is_partitioned_table返回True]
      └── _execute_full_table_dynamic_partition_merge()
          ├── _get_table_columns()  ← MetadataManager方法
          └── _infer_storage_format_name()  ← MetadataManager方法
```

**关键风险点**:
1. 提取MetadataManager后,execute_merge的调用链可能破坏
2. 3个分支的逻辑可能受影响
3. 如果execute_merge留stub,所有合并任务失败

**缓解措施**:
- ✅ **Step 1 (提取前)**: 为execute_merge编写完整集成测试
  ```python
  # backend/tests/engines/test_safe_hive_engine_integration.py
  def test_execute_merge_non_partitioned_table():
      """测试整表合并(分支3)"""
      pass

  def test_execute_merge_with_partition_filter():
      """测试分区级合并(分支2)"""
      pass

  def test_execute_merge_full_table_partitioned():
      """测试分区表整表合并(分支1)"""
      pass
  ```

- ✅ **Step 2 (提取时)**: 保留execute_merge完整实现,仅替换方法调用
  ```python
  # safe_hive_engine.py (重构后)
  def execute_merge(self, task: MergeTask, db_session: Session) -> Dict[str, Any]:
      # ✅ 完整保留原逻辑,仅替换:
      # self._is_partitioned_table(...) → self.metadata_manager._is_partitioned_table(...)
      # self._get_table_format_info(...) → self.metadata_manager._get_table_format_info(...)
      # ... 其他8个方法同理 ...
      pass
  ```

- ✅ **Step 3 (提取后)**: 每次修改后运行回归测试
  ```bash
  pytest backend/tests/engines/test_safe_hive_engine_integration.py -v
  ```

**验收标准**:
- [ ] execute_merge完整实现保留(非stub)
- [ ] 3个分支逻辑100%保留
- [ ] 集成测试覆盖3个分支
- [ ] 回归测试通过

---

### 风险R2: 依赖方法遗漏 🟡

**风险描述**:
MetadataManager的10个方法可能调用其他私有方法,如果遗漏依赖方法,会导致运行时错误。

**依赖分析** (需人工分析源码):
```python
# 示例: _get_table_format_info可能调用_parse_serde_lib
def _get_table_format_info(self, database: str, table: str) -> Dict:
    raw_format = self.hive_connector.get_format(database, table)
    # 如果这里调用了_parse_serde_lib,必须一并提取!
    return self._parse_serde_lib(raw_format)
```

**缓解措施**:
- ✅ **Step 1**: 使用IDE的"Find Usages"功能找到10个方法的所有调用点
- ✅ **Step 2**: 使用Grep扫描10个方法内部是否调用其他私有方法
  ```bash
  cd backend/app/engines
  for method in "_get_table_location" "_table_exists" "_is_partitioned_table" ...
  do
    echo "=== $method 依赖分析 ==="
    grep -A 30 "def $method" safe_hive_engine.py | grep "self\._"
  done
  ```

- ✅ **Step 3**: 单元测试验证所有方法独立可用

**验收标准**:
- [ ] IDE "Find Usages"扫描完成
- [ ] Grep扫描无遗漏依赖
- [ ] 单元测试独立运行通过

---

## 4. 中风险详细分析

### 风险R5: 单元测试覆盖不足 🟡

**风险描述**:
如果单元测试覆盖率<80%,无法保证MetadataManager的正确性。

**缓解措施**:
- ✅ 强制要求单元测试覆盖率>80%
- ✅ 使用pytest-cov检查覆盖率
  ```bash
  pytest backend/tests/engines/test_safe_hive_metadata_manager.py --cov=backend/app/engines/safe_hive_metadata_manager --cov-report=term-missing
  ```

**验收标准**:
- [ ] 覆盖率>80%
- [ ] 所有公共方法有测试
- [ ] 关键分支有测试

---

### 风险R6: 回归测试失败 🟡

**风险描述**:
MetadataManager集成后,现有测试可能失败。

**缓解措施**:
- ✅ 提取前运行所有测试确保基线通过
- ✅ 每次修改后立即运行回归测试
- ✅ 测试失败立即回滚

**验收标准**:
- [ ] 所有现有测试通过
- [ ] 无新增测试失败

---

## 5. 风险缓解时间线

| 阶段 | 时间 | 关键缓解措施 | 验证方式 |
|-----|------|------------|---------|
| **Day 1上午** | 4h | 创建模块+提取方法+编写单元测试 | 单元测试通过 |
| **Day 1下午** | 4h | 运行单元测试+修复Bug | 覆盖率>80% |
| **Day 2上午** | 4h | 集成到主引擎+回归测试 | 回归测试通过 |
| **Day 2下午** | 4h | Mypy检查+代码审查+QA评审 | Mypy无错误 |

---

## 6. 应急预案

### 场景1: Mypy发现类型错误

**应对**:
1. 立即停止集成
2. 修复类型错误
3. 重新运行mypy验证
4. 继续集成

### 场景2: 回归测试失败

**应对**:
1. 分析失败原因
2. 如果是方法签名问题,立即修正
3. 如果是execute_merge逻辑问题,立即回滚
4. 重新运行测试

### 场景3: 生产环境发现Bug

**应对**:
1. **不会发生**: Story 6.1仅在开发环境重构,不直接发布到生产
2. 如发生,立即回滚到safe_hive_engine.py原始版本
3. 分析Bug原因,修复后重新测试

---

## 7. 质量门禁 (QA Gates)

### Gate 1: 单元测试通过 (必须)
- [ ] 所有单元测试通过
- [ ] 覆盖率>80%
- [ ] 无跳过的测试用例

### Gate 2: Mypy静态检查通过 (必须)
- [ ] Mypy无错误
- [ ] Mypy无警告
- [ ] 类型注解完整

### Gate 3: 回归测试通过 (必须)
- [ ] 所有现有测试通过
- [ ] execute_merge的3个分支测试通过
- [ ] 无性能退化

### Gate 4: 代码审查通过 (必须)
- [ ] 方法签名100%一致
- [ ] 无遗漏依赖方法
- [ ] execute_merge完整保留

---

## 8. 成功指标

| 指标 | 目标 | 测量方式 |
|-----|------|---------|
| 单元测试覆盖率 | >80% | pytest-cov |
| 回归测试通过率 | 100% | pytest |
| Mypy错误数 | 0 | mypy |
| 代码行数 | safe_hive_engine.py减少~900行 | wc -l |
| 重构工期 | ≤2天 | 时间追踪 |

---

## 9. 风险总结

### 可接受的风险
- ✅ R4 (命名不一致): 低风险,可控
- ✅ R7 (生产数据丢失): 极低概率,且有备份

### 需重点监控的风险
- 🟡 R1 (方法签名不匹配): 高概率,极高影响,需Mypy严格检查
- 🟡 R3 (execute_merge调用路径破坏): 高概率,极高影响,需完整集成测试
- 🟡 R2 (依赖方法遗漏): 中概率,高影响,需代码分析

### 不可接受的风险
- ❌ 无: 所有高风险都有缓解措施

---

## 10. 最终建议

**建议**: ✅ **批准Story 6.1执行,但需严格执行以下措施**

**前置条件**:
1. ✅ 完整阅读`/tmp/safe_hive_engine_documented.md`
2. ✅ 为execute_merge编写完整集成测试
3. ✅ 准备好mypy/pytest环境

**执行要求**:
1. ✅ 严格按照Story文档的"技术实现要点"执行
2. ✅ 每次修改后立即运行回归测试
3. ✅ 遇到测试失败立即停止,分析原因后再继续
4. ✅ 通过所有4个质量门禁后才能合并代码

**预期结果**:
- 成功率: 75%(基于上次失败教训调整后)
- 工期: 2天(不包括Bug修复时间)
- 代码质量: 高(单元测试>80%,Mypy通过)

---

**风险评估者**: QA Architect (BMAD)
**评估完成时间**: 2025-10-12
**下次评审**: Story 6.1完成后进行回顾
