# 项目脚本工具集

本目录包含项目开发和测试相关的工具脚本。

## 脚本分类

### 🧪 测试工具
- **`create_test_external_table.sh`**: Hive外部表测试数据生成器
- **`test-table-config.conf`**: 测试表配置文件

### 🛠️ 代码质量工具
- **`quality_check.py`**: 完整的代码质量检查
- **`format_code.py`**: 自动代码格式化

## Hive 小文件测试工具

### 快速使用
```bash
# 基础使用 - 默认配置（10分区，每分区100文件）
cd scripts
./create_test_external_table.sh

# 高级使用 - 自定义配置
source test-table-config.conf
./create_test_external_table.sh
```

### 快速测试场景
```bash
# 轻量测试（100个小文件）
export PARTITION_COUNT=5 FILES_PER_PARTITION=20
./create_test_external_table.sh

# 重度测试（2000个小文件）- 谨慎使用
export PARTITION_COUNT=20 FILES_PER_PARTITION=100
./create_test_external_table.sh
```

### 功能特性
- ✅ **全自动化**：一键创建完整的外部表和测试数据
- ✅ **可配置**：支持自定义分区数、文件数、文件大小
- ✅ **并发优化**：多线程生成文件，提升创建速度
- ✅ **验证机制**：自动验证创建结果
- ✅ **清理机制**：自动清理临时文件

### 配置参数
| 参数 | 默认值 | 说明 |
|-----|--------|------|
| `TABLE_NAME` | test_small_files_table | 表名 |
| `DATABASE_NAME` | test_db | 数据库名 |
| `PARTITION_COUNT` | 10 | 分区数量 |
| `FILES_PER_PARTITION` | 100 | 每分区文件数 |
| `FILE_SIZE_KB` | 50 | 单文件大小(KB) |

## 代码质量工具

### 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 使用方法
```bash
# 格式化代码
python scripts/format_code.py

# 检查代码质量
python scripts/quality_check.py

# 使用 Makefile（推荐）
make install-dev  # 安装开发依赖
make format       # 格式化代码
make check        # 质量检查
make test         # 运行测试
```

### 质量标准
- ✅ Black 格式化
- ✅ Flake8 代码规范（最大行长度88）
- ✅ isort 导入排序
- ✅ MyPy 类型检查（基础模式）

## 小文件治理平台集成测试

创建完测试表后，可以在平台中：

1. **添加集群配置**：配置测试环境连接
2. **扫描测试表**：
   ```bash
   curl -X POST "http://localhost:8000/api/v1/tables/scan" \
     -H "Content-Type: application/json" \
     -d '{
       "cluster_id": 1,
       "database_name": "test_db",
       "table_name": "test_small_files_table"
     }'
   ```
3. **查看统计**：在Dashboard观察小文件分布
4. **测试合并**：创建合并任务验证治理效果

## 清理测试数据

### 完全清理
```bash
# 删除HDFS数据
hdfs dfs -rm -r /user/test/small_files_test

# 删除Hive表
hive -e "DROP DATABASE IF EXISTS test_db CASCADE;"
```

## 性能参考

| 场景 | 分区数 | 文件数/分区 | 总文件数 | 预估时间 | 磁盘占用 |
|------|--------|-------------|----------|---------|----------|
| 轻量 | 5 | 20 | 100 | 1-2分钟 | ~5MB |
| 默认 | 10 | 100 | 1,000 | 5-10分钟 | ~50MB |
| 重度 | 20 | 100 | 2,000 | 10-20分钟 | ~100MB |

⚠️ **警告**：测试工具故意创建大量小文件，请勿在生产环境使用！