# Story 6.1测试设计

**Story**: Epic-6 Story-1 - 提取MetadataManager模块
**测试设计时间**: 2025-10-12
**测试方法**: BMAD Test Architect框架
**测试设计者**: QA Architect (BMAD)

---

## 执行摘要

**测试目标**: 确保MetadataManager模块提取后功能100%保留,无回归Bug
**测试范围**: 单元测试 + 集成测试 + 回归测试
**覆盖率目标**: 单元测试>80%,集成测试覆盖execute_merge的3个分支
**预估测试工时**: 1.5天 (12小时)

---

## 1. 测试策略

### 1.1 测试金字塔

```
         /\
        /集成\     20% - 集成测试(execute_merge的3个分支)
       /----\
      /单元测试\   80% - 单元测试(10个方法独立测试)
     /--------\
```

### 1.2 测试层次

| 测试类型 | 覆盖范围 | 测试数量 | 优先级 |
|---------|---------|---------|--------|
| 单元测试 | MetadataManager的10个方法 | 20+个用例 | P0 |
| 集成测试 | safe_hive_engine与MetadataManager的集成 | 3个用例 | P0 |
| 回归测试 | 所有现有测试 | 现有全部 | P0 |

---

## 2. 单元测试设计 (80%比重)

### 2.1 测试文件

**文件路径**: `backend/tests/engines/test_safe_hive_metadata_manager.py`

**测试类结构**:
```python
import pytest
from unittest.mock import Mock, MagicMock
from backend.app.engines.safe_hive_metadata_manager import SafeHiveMetadataManager

class TestSafeHiveMetadataManager:
    @pytest.fixture
    def mock_hive_connector(self):
        """模拟HiveMetastoreConnector"""
        return Mock()

    @pytest.fixture
    def mock_path_resolver(self):
        """模拟HivePartitionPathResolver"""
        return Mock()

    @pytest.fixture
    def metadata_manager(self, mock_hive_connector, mock_path_resolver):
        """创建MetadataManager实例"""
        return SafeHiveMetadataManager(
            hive_connector=mock_hive_connector,
            path_resolver=mock_path_resolver
        )

    # 测试用例...
```

### 2.2 测试用例清单 (20+个)

#### 测试组1: _get_table_location (4个用例)

| 用例ID | 用例名称 | 输入 | 预期输出 | 覆盖场景 |
|--------|---------|------|---------|---------|
| TC-1.1 | test_get_table_location_success | database="test_db", table="user_logs" | "/user/hive/warehouse/test_db.db/user_logs" | 正常表 |
| TC-1.2 | test_get_table_location_not_exists | database="test_db", table="non_exist_table" | None | 表不存在 |
| TC-1.3 | test_get_table_location_external_table | database="test_db", table="external_table" | "/data/external/table" | 外部表 |
| TC-1.4 | test_get_table_location_connection_error | database="test_db", table="user_logs" | Raises ConnectionError | 连接失败 |

**示例代码**:
```python
def test_get_table_location_success(self, metadata_manager, mock_hive_connector):
    # Given
    mock_hive_connector.get_table_location.return_value = "/user/hive/warehouse/test_db.db/user_logs"

    # When
    result = metadata_manager._get_table_location("test_db", "user_logs")

    # Then
    assert result == "/user/hive/warehouse/test_db.db/user_logs"
    mock_hive_connector.get_table_location.assert_called_once_with("test_db", "user_logs")

def test_get_table_location_not_exists(self, metadata_manager, mock_hive_connector):
    # Given
    mock_hive_connector.get_table_location.return_value = None

    # When
    result = metadata_manager._get_table_location("test_db", "non_exist_table")

    # Then
    assert result is None
```

---

#### 测试组2: _table_exists (3个用例)

| 用例ID | 用例名称 | 输入 | 预期输出 | 覆盖场景 |
|--------|---------|------|---------|---------|
| TC-2.1 | test_table_exists_true | database="test_db", table="user_logs" | True | 表存在 |
| TC-2.2 | test_table_exists_false | database="test_db", table="non_exist_table" | False | 表不存在 |
| TC-2.3 | test_table_exists_connection_timeout | database="test_db", table="user_logs" | Raises TimeoutError | 连接超时 |

**示例代码**:
```python
def test_table_exists_true(self, metadata_manager, mock_hive_connector):
    # Given
    mock_hive_connector.table_exists.return_value = True

    # When
    result = metadata_manager._table_exists("test_db", "user_logs")

    # Then
    assert result is True

def test_table_exists_false(self, metadata_manager, mock_hive_connector):
    # Given
    mock_hive_connector.table_exists.return_value = False

    # When
    result = metadata_manager._table_exists("test_db", "non_exist_table")

    # Then
    assert result is False
```

---

#### 测试组3: _is_partitioned_table (3个用例)

| 用例ID | 用例名称 | 输入 | 预期输出 | 覆盖场景 |
|--------|---------|------|---------|---------|
| TC-3.1 | test_is_partitioned_table_true | database="test_db", table="partitioned_table" | True | 分区表 |
| TC-3.2 | test_is_partitioned_table_false | database="test_db", table="non_partitioned_table" | False | 非分区表 |
| TC-3.3 | test_is_partitioned_table_empty_partitions | database="test_db", table="empty_partitions_table" | False | 分区列为空 |

**示例代码**:
```python
def test_is_partitioned_table_true(self, metadata_manager, mock_hive_connector):
    # Given
    mock_hive_connector.get_partitions.return_value = ["dt=2025-10-11", "dt=2025-10-12"]

    # When
    result = metadata_manager._is_partitioned_table("test_db", "partitioned_table")

    # Then
    assert result is True

def test_is_partitioned_table_false(self, metadata_manager, mock_hive_connector):
    # Given
    mock_hive_connector.get_partitions.return_value = []

    # When
    result = metadata_manager._is_partitioned_table("test_db", "non_partitioned_table")

    # Then
    assert result is False
```

---

#### 测试组4: _get_table_partitions (2个用例)

| 用例ID | 用例名称 | 输入 | 预期输出 | 覆盖场景 |
|--------|---------|------|---------|---------|
| TC-4.1 | test_get_table_partitions_success | database="test_db", table="partitioned_table" | ["dt=2025-10-11", "dt=2025-10-12"] | 有分区 |
| TC-4.2 | test_get_table_partitions_empty | database="test_db", table="non_partitioned_table" | [] | 无分区 |

---

#### 测试组5: _get_table_format_info (5个用例)

| 用例ID | 用例名称 | 输入 | 预期输出 | 覆盖场景 |
|--------|---------|------|---------|---------|
| TC-5.1 | test_get_table_format_info_textfile | database="test_db", table="textfile_table" | {"InputFormat": "org.apache.hadoop.mapred.TextInputFormat", ...} | TEXTFILE格式 |
| TC-5.2 | test_get_table_format_info_orc | database="test_db", table="orc_table" | {"InputFormat": "org.apache.hadoop.hive.ql.io.orc.OrcInputFormat", ...} | ORC格式 |
| TC-5.3 | test_get_table_format_info_parquet | database="test_db", table="parquet_table" | {"InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat", ...} | PARQUET格式 |
| TC-5.4 | test_get_table_format_info_rc | database="test_db", table="rc_table" | {"InputFormat": "org.apache.hadoop.hive.ql.io.RCFileInputFormat", ...} | RCFILE格式 |
| TC-5.5 | test_get_table_format_info_sequence | database="test_db", table="seq_table" | {"InputFormat": "org.apache.hadoop.mapred.SequenceFileInputFormat", ...} | SEQUENCEFILE格式 |

**示例代码**:
```python
def test_get_table_format_info_orc(self, metadata_manager, mock_hive_connector):
    # Given
    mock_hive_connector.get_table_format.return_value = {
        "InputFormat": "org.apache.hadoop.hive.ql.io.orc.OrcInputFormat",
        "OutputFormat": "org.apache.hadoop.hive.ql.io.orc.OrcOutputFormat",
        "SerdeInfo": {
            "serializationLib": "org.apache.hadoop.hive.ql.io.orc.OrcSerde",
            "parameters": {}
        }
    }

    # When
    result = metadata_manager._get_table_format_info("test_db", "orc_table")

    # Then
    assert "OrcInputFormat" in result["InputFormat"]
    assert "OrcOutputFormat" in result["OutputFormat"]
    assert result["SerdeInfo"]["serializationLib"].endswith("OrcSerde")
```

---

#### 测试组6: _get_table_columns (2个用例)

| 用例ID | 用例名称 | 输入 | 预期输出 | 覆盖场景 |
|--------|---------|------|---------|---------|
| TC-6.1 | test_get_table_columns_success | database="test_db", table="user_logs" | (["user_id", "action"], ["dt"]) | 包含分区列 |
| TC-6.2 | test_get_table_columns_no_partition | database="test_db", table="non_partitioned_table" | (["user_id", "action"], []) | 无分区列 |

**示例代码**:
```python
def test_get_table_columns_success(self, metadata_manager, mock_hive_connector):
    # Given
    mock_hive_connector.get_table_columns.return_value = (["user_id", "action"], ["dt"])

    # When
    regular_cols, partition_cols = metadata_manager._get_table_columns("test_db", "user_logs")

    # Then
    assert regular_cols == ["user_id", "action"]
    assert partition_cols == ["dt"]
```

---

#### 测试组7-10: 工具方法 (4个用例)

| 用例ID | 方法 | 输入 | 预期输出 | 覆盖场景 |
|--------|-----|------|---------|---------|
| TC-7.1 | _is_unsupported_table_type | fmt={"InputFormat": "com.custom.UnsupportedFormat"} | True | 不支持的格式 |
| TC-8.1 | _unsupported_reason | fmt={"InputFormat": "com.custom.UnsupportedFormat"} | "Unsupported format: com.custom.UnsupportedFormat" | 返回原因 |
| TC-9.1 | _infer_storage_format_name | fmt={"InputFormat": "...OrcInputFormat"} | "ORC" | 推断ORC格式 |
| TC-10.1 | _infer_table_compression | (fmt, "ORC") | "SNAPPY" | 推断压缩格式 |

**示例代码**:
```python
def test_infer_storage_format_name_orc(self, metadata_manager):
    # Given
    fmt = {
        "InputFormat": "org.apache.hadoop.hive.ql.io.orc.OrcInputFormat",
        "OutputFormat": "org.apache.hadoop.hive.ql.io.orc.OrcOutputFormat"
    }

    # When
    result = metadata_manager._infer_storage_format_name(fmt)

    # Then
    assert result == "ORC"

def test_infer_storage_format_name_parquet(self, metadata_manager):
    # Given
    fmt = {
        "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
        "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    }

    # When
    result = metadata_manager._infer_storage_format_name(fmt)

    # Then
    assert result == "PARQUET"
```

---

### 2.3 单元测试覆盖率验证

**执行命令**:
```bash
cd backend
pytest tests/engines/test_safe_hive_metadata_manager.py --cov=app/engines/safe_hive_metadata_manager --cov-report=term-missing --cov-report=html
```

**目标覆盖率**: >80%

**覆盖率报告示例**:
```
Name                                          Stmts   Miss  Cover   Missing
---------------------------------------------------------------------------
app/engines/safe_hive_metadata_manager.py       150     25    83%   45-48, 102-105
---------------------------------------------------------------------------
TOTAL                                           150     25    83%
```

---

## 3. 集成测试设计 (20%比重)

### 3.1 测试文件

**文件路径**: `backend/tests/engines/test_safe_hive_engine_integration.py`

**测试目标**: 验证safe_hive_engine与MetadataManager集成后,execute_merge的3个分支逻辑正常工作

### 3.2 集成测试用例清单 (3个)

#### 测试组1: execute_merge整表合并(分支3)

**用例ID**: TC-I1
**用例名称**: test_execute_merge_non_partitioned_table
**测试目标**: 验证非分区表合并流程

**前置条件**:
1. 数据库中存在非分区表`test_db.non_partitioned_table`
2. 表包含3000个小文件
3. 表格式为TEXTFILE

**测试步骤**:
```python
def test_execute_merge_non_partitioned_table(mock_engine, mock_db):
    # Given: 创建非分区表合并任务
    task = MergeTask(
        cluster_id=1,
        database_name="test_db",
        table_name="non_partitioned_table",
        merge_strategy="concatenate",
        partition_filter=None  # 整表合并
    )

    # Mock: 元数据管理器返回
    mock_engine.metadata_manager._is_partitioned_table.return_value = False
    mock_engine.metadata_manager._get_table_format_info.return_value = {
        "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
        "OutputFormat": "org.apache.hadoop.mapred.HiveIgnoreKeyTextOutputFormat"
    }
    mock_engine.metadata_manager._get_table_location.return_value = "/user/hive/warehouse/test_db.db/non_partitioned_table"

    # When: 执行合并
    result = mock_engine.execute_merge(task, mock_db)

    # Then: 验证结果
    assert result["success"] is True
    assert result["files_before"] == 3000
    assert result["files_after"] < result["files_before"]

    # 验证调用了MetadataManager方法
    mock_engine.metadata_manager._is_partitioned_table.assert_called_once_with("test_db", "non_partitioned_table")
    mock_engine.metadata_manager._get_table_format_info.assert_called_once()
    mock_engine.metadata_manager._get_table_location.assert_called_once()
```

---

#### 测试组2: execute_merge分区级合并(分支2)

**用例ID**: TC-I2
**用例名称**: test_execute_merge_with_partition_filter
**测试目标**: 验证分区级合并流程

**前置条件**:
1. 数据库中存在分区表`test_db.partitioned_table`
2. 分区`dt=2025-10-11`包含3000个小文件
3. 表格式为TEXTFILE

**测试步骤**:
```python
def test_execute_merge_with_partition_filter(mock_engine, mock_db):
    # Given: 创建分区级合并任务
    task = MergeTask(
        cluster_id=1,
        database_name="test_db",
        table_name="partitioned_table",
        merge_strategy="concatenate",
        partition_filter="dt='2025-10-11'"  # 分区级合并
    )

    # Mock: 元数据管理器返回
    mock_engine.metadata_manager._is_partitioned_table.return_value = True
    mock_engine.metadata_manager._get_table_format_info.return_value = {
        "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
        "OutputFormat": "org.apache.hadoop.mapred.HiveIgnoreKeyTextOutputFormat"
    }

    # When: 执行合并
    result = mock_engine.execute_merge(task, mock_db)

    # Then: 验证结果
    assert result["success"] is True
    assert "partition_filter" in str(result["message"])
```

---

#### 测试组3: execute_merge分区表整表合并(分支1)

**用例ID**: TC-I3
**用例名称**: test_execute_merge_full_table_partitioned
**测试目标**: 验证分区表整表合并流程

**前置条件**:
1. 数据库中存在分区表`test_db.partitioned_table`
2. 包含100个分区,总计10万个小文件
3. 表格式为ORC

**测试步骤**:
```python
def test_execute_merge_full_table_partitioned(mock_engine, mock_db):
    # Given: 创建分区表整表合并任务
    task = MergeTask(
        cluster_id=1,
        database_name="test_db",
        table_name="partitioned_table",
        merge_strategy="insert_overwrite",
        partition_filter=None  # 整表合并
    )

    # Mock: 元数据管理器返回
    mock_engine.metadata_manager._is_partitioned_table.return_value = True
    mock_engine.metadata_manager._get_table_columns.return_value = (["user_id", "action"], ["dt"])
    mock_engine.metadata_manager._infer_storage_format_name.return_value = "ORC"

    # When: 执行合并
    result = mock_engine.execute_merge(task, mock_db)

    # Then: 验证结果
    assert result["success"] is True
    assert "dynamic partition" in str(result["message"]).lower()

    # 验证调用了_execute_full_table_dynamic_partition_merge分支
    mock_engine.metadata_manager._get_table_columns.assert_called_once()
    mock_engine.metadata_manager._infer_storage_format_name.assert_called_once()
```

---

### 3.3 集成测试验证

**执行命令**:
```bash
cd backend
pytest tests/engines/test_safe_hive_engine_integration.py -v
```

**预期结果**:
```
test_execute_merge_non_partitioned_table PASSED               [33%]
test_execute_merge_with_partition_filter PASSED               [66%]
test_execute_merge_full_table_partitioned PASSED              [100%]

=================== 3 passed in 2.45s ===================
```

---

## 4. 回归测试设计

### 4.1 回归测试范围

**测试目标**: 确保MetadataManager集成后,所有现有功能不受影响

**测试文件**: 所有现有测试文件
- `backend/tests/engines/test_safe_hive_engine.py`
- `backend/tests/api/test_tables.py`
- `backend/tests/api/test_tasks.py`

### 4.2 回归测试执行

**执行命令**:
```bash
cd backend
pytest tests/ -v --tb=short
```

**预期结果**: 所有现有测试通过,无新增失败

---

## 5. 测试数据准备

### 5.1 Mock数据定义

```python
# tests/fixtures/metadata_fixtures.py
@pytest.fixture
def sample_table_location():
    return "/user/hive/warehouse/test_db.db/user_logs"

@pytest.fixture
def sample_textfile_format():
    return {
        "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
        "OutputFormat": "org.apache.hadoop.mapred.HiveIgnoreKeyTextOutputFormat",
        "SerdeInfo": {
            "serializationLib": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
            "parameters": {"field.delim": "\t"}
        }
    }

@pytest.fixture
def sample_orc_format():
    return {
        "InputFormat": "org.apache.hadoop.hive.ql.io.orc.OrcInputFormat",
        "OutputFormat": "org.apache.hadoop.hive.ql.io.orc.OrcOutputFormat",
        "SerdeInfo": {
            "serializationLib": "org.apache.hadoop.hive.ql.io.orc.OrcSerde",
            "parameters": {}
        }
    }

@pytest.fixture
def sample_partitions():
    return ["dt=2025-10-11", "dt=2025-10-12", "dt=2025-10-13"]
```

---

## 6. 测试执行时间线

| 阶段 | 时间 | 测试类型 | 预估用例数 | 执行时间 |
|-----|------|---------|-----------|---------|
| **Day 1下午** | 4h | 单元测试编写 | 20+个 | 3h |
| **Day 1下午** | | 单元测试执行+修复 | | 1h |
| **Day 2上午** | 4h | 集成测试编写 | 3个 | 2h |
| **Day 2上午** | | 集成测试执行 | | 1h |
| **Day 2上午** | | 回归测试执行 | 现有全部 | 1h |

**总计测试工时**: 12小时 (1.5天)

---

## 7. 测试通过标准 (Definition of Pass)

### 7.1 单元测试通过标准
- [ ] 所有单元测试用例通过(20+个)
- [ ] 代码覆盖率>80%
- [ ] 无跳过的测试用例
- [ ] 无待修复的Bug

### 7.2 集成测试通过标准
- [ ] execute_merge的3个分支全部测试通过
- [ ] MetadataManager方法被正确调用
- [ ] 返回结果格式正确
- [ ] 无异常抛出

### 7.3 回归测试通过标准
- [ ] 所有现有测试通过
- [ ] 无新增测试失败
- [ ] 测试执行时间无显著增加(±10%)

---

## 8. 测试风险和缓解

### 风险1: Mock数据与实际数据不一致

**缓解措施**:
- 使用真实Hive环境的元数据作为Mock数据参考
- 在Demo环境执行集成测试验证

### 风险2: 测试用例覆盖不足

**缓解措施**:
- 使用pytest-cov检查覆盖率
- 代码审查确保关键分支有测试

### 风险3: 集成测试环境不稳定

**缓解措施**:
- 使用Docker容器提供隔离测试环境
- 测试前清理数据库状态

---

## 9. 测试工具和配置

### 9.1 测试工具链

| 工具 | 用途 | 命令 |
|-----|------|------|
| Pytest | 测试框架 | `pytest` |
| pytest-cov | 覆盖率 | `pytest --cov` |
| pytest-mock | Mock框架 | 已集成 |
| Mypy | 类型检查 | `mypy backend/app/engines/` |

### 9.2 Pytest配置

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: 单元测试
    integration: 集成测试
    slow: 慢速测试
```

### 9.3 Coverage配置

```ini
# .coveragerc
[run]
source = app/engines
omit =
    */tests/*
    */__pycache__/*
    */venv/*

[report]
precision = 2
show_missing = True
skip_covered = False
```

---

## 10. 测试报告模板

**报告生成命令**:
```bash
pytest tests/engines/test_safe_hive_metadata_manager.py --cov=app/engines/safe_hive_metadata_manager --cov-report=html
```

**报告输出**: `htmlcov/index.html`

**关键指标**:
- 总用例数: 20+
- 通过率: 100%
- 覆盖率: >80%
- 执行时间: <30s

---

**测试设计者**: QA Architect (BMAD)
**设计完成时间**: 2025-10-12
**下次评审**: Story 6.1开发完成后执行测试
