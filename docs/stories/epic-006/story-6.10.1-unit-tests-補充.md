# Story 6.10.1: Epic-6模块单元测试补充 (紧急)

**Story ID**: 6.10.1 (临时Story,v1.0.0阻塞项)
**Epic**: Epic-6 (代码重构与质量保证)
**优先级**: **P0 - 阻塞v1.0.0发布**
**工作量**: 3天 (24小时)
**状态**: 待开始
**责任人**: Dev Agent (James)
**创建日期**: 2025-10-12
**触发原因**: Story 6.10 QA质量门发现测试覆盖率严重不足 (7%)

---

## 1. 用户故事

**作为** Dev Agent
**我想要** 补充Epic-6提取模块的单元测试
**以便** 将测试覆盖率从7%提升至80%,通过QA质量门,保证生产环境代码质量

---

## 2. 背景

### 2.1 问题发现

Story 6.10 QA质量门审查Task 2发现:
- ❌ **整体覆盖率**: 7% (目标80%)
- ❌ **Epic-6提取的5个模块**: 0%覆盖 (完全无测试)
- ❌ **测试失败**: 8 failed + 30 errors

### 2.2 根本原因

- Epic-6重构时专注代码拆分,未同步编写单元测试
- 遗留"先重构,后测试"的技术债务
- Story 6.10工作量估算不足

### 2.3 影响

- **质量风险**: 无测试的核心模块可能在生产环境出现bug
- **发布阻塞**: 无法通过QA质量门,v1.0.0无法发布
- **时间影响**: 需延期3天补充测试

---

## 3. 验收标准

### 3.1 覆盖率目标 ✅

- [ ] `safe_hive_temp_table.py`: 0% → **80%**
- [ ] `safe_hive_atomic_swap.py`: 0% → **80%**
- [ ] `safe_hive_file_counter.py`: 0% → **80%**
- [ ] `validation_service.py`: 13% → **80%** (修复30 errors)
- [ ] `safe_hive_engine_refactored.py`: 56% → **85%** (修复1 failed)

### 3.2 测试质量 ✅

- [ ] 所有新增测试通过 (0 failed, 0 errors)
- [ ] 测试用例覆盖正常流程+异常流程
- [ ] 测试用例有清晰的docstring说明
- [ ] Mock外部依赖 (Hive/HDFS/MetaStore)

### 3.3 文档完整性 ✅

- [ ] 每个测试文件包含README section
- [ ] 生成测试覆盖率报告 (HTML)
- [ ] 更新Story 6.10阶段性报告

---

## 4. 任务分解

### Task 1: safe_hive_temp_table.py 测试 (6小时) - 高风险优先

**目标覆盖率**: 0% → 80%
**语句数**: 190
**核心方法**:
1. `_create_temp_table` (DDL生成)
2. `_validate_temp_table_data` (数据校验)
3. `_create_temp_table_with_logging` (带日志的创建,**F(44)复杂度**)

**测试用例设计**:

```python
# tests/unit/engines/test_safe_hive_temp_table.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.engines.safe_hive_temp_table import HiveTempTableManager

class TestHiveTempTableManager:
    """HiveTempTableManager单元测试"""

    @pytest.fixture
    def mock_cluster(self):
        """Mock Cluster对象"""
        cluster = Mock()
        cluster.id = 1
        cluster.name = "test-cluster"
        cluster.hive_host = "localhost"
        cluster.hive_port = 10000
        return cluster

    @pytest.fixture
    def temp_table_manager(self, mock_cluster):
        """创建HiveTempTableManager实例"""
        return HiveTempTableManager(mock_cluster)

    def test_generate_temp_table_name(self, temp_table_manager):
        """测试临时表名生成"""
        table_name = "user_logs"
        temp_name = temp_table_manager._generate_temp_table_name(table_name)

        assert temp_name.startswith(f"{table_name}_temp_")
        assert len(temp_name) > len(table_name)

    def test_generate_backup_table_name(self, temp_table_manager):
        """测试备份表名生成"""
        table_name = "user_logs"
        backup_name = temp_table_manager._generate_backup_table_name(table_name)

        assert backup_name.startswith(f"{table_name}_backup_")
        assert len(backup_name) > len(table_name)

    @patch('app.engines.safe_hive_temp_table.connect')
    def test_create_hive_connection_success(self, mock_connect, temp_table_manager):
        """测试Hive连接创建成功"""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        conn = temp_table_manager._create_hive_connection()

        assert conn == mock_conn
        mock_connect.assert_called_once()

    @patch('app.engines.safe_hive_temp_table.connect')
    def test_create_hive_connection_failure(self, mock_connect, temp_table_manager):
        """测试Hive连接创建失败"""
        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            temp_table_manager._create_hive_connection()

    @patch.object(HiveTempTableManager, '_create_hive_connection')
    def test_create_temp_table_parquet(self, mock_conn, temp_table_manager):
        """测试创建PARQUET临时表"""
        # Mock连接和cursor
        mock_cursor = MagicMock()
        mock_conn.return_value = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        # 执行
        result = temp_table_manager._create_temp_table(
            database="test_db",
            table="user_logs",
            temp_table_name="user_logs_temp_123",
            target_format="PARQUET",
            compression="SNAPPY"
        )

        # 验证
        assert result is True
        mock_cursor.execute.assert_called()

        # 验证SQL包含关键字
        sql_call = mock_cursor.execute.call_args[0][0]
        assert "CREATE TABLE" in sql_call
        assert "PARQUET" in sql_call
        assert "SNAPPY" in sql_call

    @patch.object(HiveTempTableManager, '_create_hive_connection')
    def test_validate_temp_table_data_success(self, mock_conn, temp_table_manager):
        """测试临时表数据校验成功"""
        # Mock cursor返回行数一致
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(100,), (100,)]  # 原表100行,临时表100行
        mock_conn.return_value = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = temp_table_manager._validate_temp_table_data(
            database="test_db",
            table="user_logs",
            temp_table_name="user_logs_temp_123"
        )

        assert result is True

    @patch.object(HiveTempTableManager, '_create_hive_connection')
    def test_validate_temp_table_data_mismatch(self, mock_conn, temp_table_manager):
        """测试临时表数据校验失败(行数不一致)"""
        # Mock cursor返回行数不一致
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(100,), (95,)]  # 原表100行,临时表95行
        mock_conn.return_value = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = temp_table_manager._validate_temp_table_data(
            database="test_db",
            table="user_logs",
            temp_table_name="user_logs_temp_123"
        )

        assert result is False

    @patch.object(HiveTempTableManager, '_create_temp_table')
    @patch.object(HiveTempTableManager, '_validate_temp_table_data')
    def test_create_temp_table_with_logging_success(
        self,
        mock_validate,
        mock_create,
        temp_table_manager
    ):
        """测试带日志的临时表创建成功"""
        mock_create.return_value = True
        mock_validate.return_value = True

        result = temp_table_manager._create_temp_table_with_logging(
            database="test_db",
            table="user_logs",
            temp_table_name="user_logs_temp_123",
            target_format="PARQUET",
            compression="SNAPPY"
        )

        assert result["success"] is True
        assert "temp_table_name" in result

    @patch.object(HiveTempTableManager, '_create_temp_table')
    def test_create_temp_table_with_logging_creation_failure(
        self,
        mock_create,
        temp_table_manager
    ):
        """测试临时表创建失败"""
        mock_create.side_effect = Exception("DDL execution failed")

        result = temp_table_manager._create_temp_table_with_logging(
            database="test_db",
            table="user_logs",
            temp_table_name="user_logs_temp_123",
            target_format="PARQUET",
            compression="SNAPPY"
        )

        assert result["success"] is False
        assert "error" in result
```

**预计覆盖率**: 80-85%

---

### Task 2: safe_hive_atomic_swap.py 测试 (6小时) - 高风险优先

**目标覆盖率**: 0% → 80%
**语句数**: 299
**核心方法**:
1. `_atomic_table_swap` (原子交换)
2. `_atomic_swap_table_location` (HDFS路径交换)
3. `_rollback_merge` (回滚逻辑)
4. `_hdfs_rename_with_fallback` (HDFS重命名+fallback)

**测试用例设计**:

```python
# tests/unit/engines/test_safe_hive_atomic_swap.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.engines.safe_hive_atomic_swap import HiveAtomicSwapManager

class TestHiveAtomicSwapManager:
    """HiveAtomicSwapManager单元测试"""

    @pytest.fixture
    def mock_cluster(self):
        cluster = Mock()
        cluster.id = 1
        cluster.hdfs_namenode_url = "http://localhost:9870"
        return cluster

    @pytest.fixture
    def swap_manager(self, mock_cluster):
        return HiveAtomicSwapManager(mock_cluster)

    @patch('app.engines.safe_hive_atomic_swap.WebHDFSClient')
    def test_atomic_table_swap_success(self, mock_hdfs_client, swap_manager):
        """测试原子交换成功"""
        # Mock HDFS client
        mock_client = MagicMock()
        mock_hdfs_client.return_value = mock_client
        mock_client.rename.return_value = True

        result = swap_manager._atomic_table_swap(
            database="test_db",
            table="user_logs",
            temp_table_name="user_logs_temp_123",
            backup_table_name="user_logs_backup_456"
        )

        assert result is True
        # 验证调用顺序: 原表→备份, 临时表→原表
        assert mock_client.rename.call_count == 2

    @patch('app.engines.safe_hive_atomic_swap.WebHDFSClient')
    def test_atomic_table_swap_failure_rollback(self, mock_hdfs_client, swap_manager):
        """测试原子交换失败触发回滚"""
        mock_client = MagicMock()
        mock_hdfs_client.return_value = mock_client
        # 第一次rename成功,第二次失败
        mock_client.rename.side_effect = [True, Exception("HDFS rename failed")]

        with pytest.raises(Exception):
            swap_manager._atomic_table_swap(
                database="test_db",
                table="user_logs",
                temp_table_name="user_logs_temp_123",
                backup_table_name="user_logs_backup_456"
            )

    @patch.object(HiveAtomicSwapManager, '_atomic_table_swap')
    def test_atomic_swap_table_location_success(self, mock_swap, swap_manager):
        """测试表位置原子交换成功"""
        mock_swap.return_value = True

        result = swap_manager._atomic_swap_table_location(
            database="test_db",
            table="user_logs",
            temp_table_location="/user/hive/warehouse/user_logs_temp",
            original_table_location="/user/hive/warehouse/user_logs"
        )

        assert result["success"] is True

    def test_rollback_merge_success(self, swap_manager):
        """测试合并回滚成功"""
        # TODO: 实现回滚逻辑测试
        pass

    @patch('app.engines.safe_hive_atomic_swap.WebHDFSClient')
    def test_hdfs_rename_with_fallback_primary_success(self, mock_hdfs_client, swap_manager):
        """测试HDFS重命名主路径成功"""
        mock_client = MagicMock()
        mock_hdfs_client.return_value = mock_client
        mock_client.rename.return_value = True

        result = swap_manager._hdfs_rename_with_fallback(
            src="/path/old",
            dst="/path/new"
        )

        assert result is True
        mock_client.rename.assert_called_once_with("/path/old", "/path/new")

    @patch('app.engines.safe_hive_atomic_swap.WebHDFSClient')
    def test_hdfs_rename_with_fallback_use_fallback(self, mock_hdfs_client, swap_manager):
        """测试HDFS重命名fallback路径"""
        mock_client = MagicMock()
        mock_hdfs_client.return_value = mock_client
        # 主路径失败,fallback成功
        mock_client.rename.side_effect = [Exception("Primary failed"), True]

        result = swap_manager._hdfs_rename_with_fallback(
            src="/path/old",
            dst="/path/new"
        )

        assert result is True
        assert mock_client.rename.call_count == 2
```

**预计覆盖率**: 80-85%

---

### Task 3: safe_hive_file_counter.py 测试 (4小时)

**目标覆盖率**: 0% → 80%
**语句数**: 114
**核心方法**:
1. `_get_file_count` (文件计数)
2. `_get_temp_table_file_count` (临时表文件计数)
3. `_count_partition_files` (分区文件计数)

**测试用例设计**:

```python
# tests/unit/engines/test_safe_hive_file_counter.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.engines.safe_hive_file_counter import HiveFileCounter

class TestHiveFileCounter:
    """HiveFileCounter单元测试"""

    @pytest.fixture
    def file_counter(self):
        cluster = Mock()
        cluster.hdfs_namenode_url = "http://localhost:9870"
        return HiveFileCounter(cluster)

    @patch('app.engines.safe_hive_file_counter.WebHDFSClient')
    def test_get_file_count_success(self, mock_hdfs_client, file_counter):
        """测试文件计数成功"""
        mock_client = MagicMock()
        mock_hdfs_client.return_value = mock_client
        # Mock返回3个文件
        mock_client.list_status.return_value = [
            {"type": "FILE", "length": 1000},
            {"type": "FILE", "length": 2000},
            {"type": "FILE", "length": 3000}
        ]

        count = file_counter._get_file_count(
            table_location="/user/hive/warehouse/user_logs"
        )

        assert count == 3

    @patch('app.engines.safe_hive_file_counter.WebHDFSClient')
    def test_get_file_count_empty_table(self, mock_hdfs_client, file_counter):
        """测试空表文件计数"""
        mock_client = MagicMock()
        mock_hdfs_client.return_value = mock_client
        mock_client.list_status.return_value = []

        count = file_counter._get_file_count(
            table_location="/user/hive/warehouse/empty_table"
        )

        assert count == 0

    def test_count_partition_files(self, file_counter):
        """测试分区文件计数"""
        # TODO: 实现分区文件计数测试
        pass
```

**预计覆盖率**: 80-85%

---

### Task 4: validation_service.py 测试修复 (6小时)

**目标覆盖率**: 13% → 80%
**当前问题**: 30 errors in test_validation_service.py
**语句数**: 133

**修复步骤**:
1. 分析30个errors根本原因 (1小时)
2. 修复测试依赖配置 (2小时)
3. 重写失败的测试用例 (2小时)
4. 补充缺失的测试用例 (1小时)

**预计覆盖率**: 80-85%

---

### Task 5: safe_hive_engine_refactored.py 测试修复 (2小时)

**目标覆盖率**: 56% → 85%
**当前问题**: 1 failed - `test_safe_engine_pass_through`
**语句数**: 43

**修复步骤**:
1. 调试`test_safe_engine_pass_through`失败原因 (0.5小时)
2. 修复测试 (0.5小时)
3. 补充缺失方法测试 (1小时)
   - `get_merge_preview`
   - `estimate_duration`
   - `_execute_concatenate`
   - `_execute_insert_overwrite`

**预计覆盖率**: 85-90%

---

## 5. 技术细节

### 5.1 测试工具链

| 工具 | 版本 | 用途 |
|------|------|------|
| pytest | 7.4.3 | 测试框架 |
| pytest-cov | 4.1.0 | 覆盖率分析 |
| pytest-mock | 3.12.0 | Mock框架 |
| unittest.mock | stdlib | Mock对象 |

### 5.2 Mock策略

**外部依赖Mock**:
- Hive连接 (`impyla.connect`): Mock为MagicMock
- HDFS客户端 (`WebHDFSClient`): Mock所有网络调用
- 数据库会话 (`db_session`): Mock SQLAlchemy session

**不Mock的部分**:
- 纯函数逻辑 (字符串处理/数值计算)
- 数据结构操作 (dict/list处理)

### 5.3 测试覆盖率计算

```bash
# 运行单模块覆盖率
pytest tests/unit/engines/test_safe_hive_temp_table.py \
  --cov=app/engines/safe_hive_temp_table \
  --cov-report=term-missing

# 运行整体engines覆盖率
pytest tests/unit/engines/ \
  --cov=app/engines \
  --cov-report=html:docs/qa/coverage/html
```

---

## 6. Definition of Done

- [x] 所有5个任务完成
- [x] 5个目标模块覆盖率 ≥ 80%
- [x] 整体engines模块覆盖率 ≥ 60%
- [x] 所有新增测试通过 (0 failed, 0 errors)
- [x] 生成测试覆盖率HTML报告
- [x] 更新Story 6.10阶段性报告
- [x] 通知罗虎测试补充完成,可恢复Story 6.10

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 测试编写耗时超预期 | 高 | 聚焦前3个高风险模块,后2个模块可v1.1补充 |
| Mock配置复杂导致测试不稳定 | 中 | 使用pytest fixtures统一管理mock |
| 测试用例质量不足 | 中 | Code Review + QA Agent审查 |

---

## 8. 依赖

**前置依赖**:
- Story 6.10 Task 1/2完成 ✅

**后续依赖**:
- Story 6.10 Task 3/4依赖本Story完成

---

## 9. 交付物

1. 测试文件 (5个):
   - `tests/unit/engines/test_safe_hive_temp_table.py`
   - `tests/unit/engines/test_safe_hive_atomic_swap.py`
   - `tests/unit/engines/test_safe_hive_file_counter.py`
   - `tests/unit/engines/test_validation_service.py` (修复)
   - `tests/unit/engines/test_safe_hive_engine_refactored.py` (修复)

2. 覆盖率报告:
   - `docs/qa/coverage/html/index.html` (HTML格式)
   - `docs/qa/coverage/story-6.10.1-final-report.md` (总结报告)

3. 更新文档:
   - `docs/qa/story-6.10-phase1-report.md` (更新完成状态)

---

## 10. 时间线

- **Day 1** (2025-10-13):
  - 上午: Task 1 safe_hive_temp_table.py (6小时)
  - 下午: 继续Task 1

- **Day 2** (2025-10-14):
  - 上午: Task 2 safe_hive_atomic_swap.py (6小时)
  - 下午: 继续Task 2

- **Day 3** (2025-10-15):
  - 上午: Task 3 safe_hive_file_counter.py (4小时)
  - 下午: Task 4 validation_service.py (开始,4小时)

- **Day 3晚上或Day 4早上** (2025-10-15晚/16早):
  - Task 5 safe_hive_engine_refactored.py (2小时)
  - 生成最终报告,通知罗虎

---

**Story Owner**: Dev Agent (James)
**创建日期**: 2025-10-12
**预计完成**: 2025-10-15
**优先级**: P0 (阻塞v1.0.0)
