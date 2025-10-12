#!/bin/bash

# Hive外部表快速创建脚本 - 10个分区，每分区100个小文件
# 警告：此脚本专门用于测试小文件治理平台，请勿在生产环境使用！

set -e

# 配置参数
TABLE_NAME="${TABLE_NAME:-test_small_files_table}"
DATABASE_NAME="${DATABASE_NAME:-test_db}"
HDFS_BASE_PATH="${HDFS_BASE_PATH:-/user/test/small_files_test}"
PARTITION_COUNT=10
FILES_PER_PARTITION=100
FILE_SIZE_KB=50  # 每个文件50KB，确保是小文件

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查必要工具
check_tools() {
    log_info "检查必要工具..."

    if ! command -v hive &> /dev/null; then
        log_error "hive 客户端未找到，请确保 Hive 环境已配置"
        exit 1
    fi

    if ! command -v hdfs &> /dev/null; then
        log_error "hdfs 客户端未找到，请确保 Hadoop 环境已配置"
        exit 1
    fi

    log_success "工具检查完成"
}

# 创建HDFS目录结构
create_hdfs_structure() {
    log_info "创建HDFS目录结构..."

    # 创建基础目录
    hdfs dfs -mkdir -p "$HDFS_BASE_PATH" 2>/dev/null || true

    # 创建分区目录
    for i in $(seq 1 $PARTITION_COUNT); do
        partition_dir="$HDFS_BASE_PATH/year=2024/month=$(printf "%02d" $i)"
        hdfs dfs -mkdir -p "$partition_dir" 2>/dev/null || true
        log_info "创建分区目录: $partition_dir"
    done

    log_success "HDFS目录结构创建完成"
}

# 生成测试数据文件
generate_test_data() {
    log_info "开始生成测试数据文件..."
    log_warning "警告：即将创建 $((PARTITION_COUNT * FILES_PER_PARTITION)) 个小文件！"

    local temp_dir="/tmp/hive_test_data_$$"
    mkdir -p "$temp_dir"

    # 创建样本数据文件
    cat > "$temp_dir/sample_data.txt" << 'EOF'
id,name,age,city,salary,department,join_date
1,张三,28,北京,8000.50,技术部,2024-01-15
2,李四,32,上海,12000.00,销售部,2023-12-10
3,王五,25,广州,6500.75,市场部,2024-02-20
4,赵六,35,深圳,15000.00,技术部,2023-11-05
5,钱七,29,杭州,9500.25,产品部,2024-01-30
EOF

    for i in $(seq 1 $PARTITION_COUNT); do
        partition_dir="year=2024/month=$(printf "%02d" $i)"
        local_partition_dir="$temp_dir/$partition_dir"
        mkdir -p "$local_partition_dir"

        log_info "为分区 $partition_dir 生成 $FILES_PER_PARTITION 个文件..."

        # 使用并行处理提高速度
        for j in $(seq 1 $FILES_PER_PARTITION); do
            {
                file_name="data_$(printf "%03d" $j).txt"
                file_path="$local_partition_dir/$file_name"

                # 生成指定大小的文件（重复数据以达到目标大小）
                {
                    echo "# Partition: year=2024, month=$i, File: $j"
                    echo "# Generated at: $(date)"
                    echo "#"

                    # 重复样本数据直到达到目标大小
                    lines_needed=$((FILE_SIZE_KB * 1024 / 150))  # 估算每行约150字节
                    for ((k=1; k<=lines_needed; k++)); do
                        # 修改数据使其唯一
                        sed "s/^[0-9]\+/$((($i-1)*FILES_PER_PARTITION*lines_needed + ($j-1)*lines_needed + k))/g" "$temp_dir/sample_data.txt" | tail -n +2
                    done
                } > "$file_path"
            } &

            # 控制并发数，避免系统过载
            if (( j % 20 == 0 )); then
                wait
            fi
        done
        wait

        # 上传到HDFS
        hdfs_partition_path="$HDFS_BASE_PATH/$partition_dir"
        hdfs dfs -put "$local_partition_dir"/* "$hdfs_partition_path/" 2>/dev/null || {
            log_error "上传分区 $partition_dir 到HDFS失败"
            continue
        }

        log_success "分区 $partition_dir 完成 ($FILES_PER_PARTITION 个文件)"
    done

    # 清理临时目录
    rm -rf "$temp_dir"

    log_success "测试数据生成完成！总计：$((PARTITION_COUNT * FILES_PER_PARTITION)) 个文件"
}

# 创建Hive外部表
create_hive_table() {
    log_info "创建Hive数据库和外部表..."

    # 创建临时SQL文件
    local sql_file="/tmp/create_table_$$.sql"

    cat > "$sql_file" << EOF
-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS $DATABASE_NAME
COMMENT 'Test database for small files testing'
LOCATION '$HDFS_BASE_PATH/${DATABASE_NAME}.db';

USE $DATABASE_NAME;

-- 删除已存在的表（如果存在）
DROP TABLE IF EXISTS $TABLE_NAME;

-- 创建外部分区表
CREATE EXTERNAL TABLE $TABLE_NAME (
    id BIGINT COMMENT '用户ID',
    name STRING COMMENT '姓名',
    age INT COMMENT '年龄',
    city STRING COMMENT '城市',
    salary DECIMAL(10,2) COMMENT '薪资',
    department STRING COMMENT '部门',
    join_date DATE COMMENT '入职日期'
)
COMMENT 'Test table with many small files for small file management testing'
PARTITIONED BY (
    year INT COMMENT '年份',
    month INT COMMENT '月份'
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
STORED AS TEXTFILE
LOCATION '$HDFS_BASE_PATH'
TBLPROPERTIES (
    'creator'='small_file_test_script',
    'created_time'='$(date)',
    'purpose'='small_file_testing'
);

EOF

    # 生成分区添加语句
    for i in $(seq 1 $PARTITION_COUNT); do
        cat >> "$sql_file" << EOF
-- 添加分区 year=2024, month=$i
ALTER TABLE $TABLE_NAME ADD PARTITION (year=2024, month=$i)
LOCATION '$HDFS_BASE_PATH/year=2024/month=$(printf "%02d" $i)';

EOF
    done

    # 添加表统计信息更新
    cat >> "$sql_file" << EOF
-- 刷新表统计信息
ANALYZE TABLE $TABLE_NAME COMPUTE STATISTICS;
ANALYZE TABLE $TABLE_NAME COMPUTE STATISTICS FOR COLUMNS;

-- 显示表信息
DESCRIBE FORMATTED $TABLE_NAME;
SHOW PARTITIONS $TABLE_NAME;
EOF

    log_info "执行Hive SQL..."
    hive -f "$sql_file" || {
        log_error "Hive表创建失败"
        cat "$sql_file"
        rm -f "$sql_file"
        exit 1
    }

    rm -f "$sql_file"
    log_success "Hive外部表创建完成"
}

# 验证创建结果
verify_table() {
    log_info "验证表创建结果..."

    # 检查HDFS文件
    total_files=$(hdfs dfs -find "$HDFS_BASE_PATH" -name "*.txt" | wc -l)
    log_info "HDFS文件总数: $total_files"

    # 检查每个分区的文件数
    for i in $(seq 1 $PARTITION_COUNT); do
        partition_path="$HDFS_BASE_PATH/year=2024/month=$(printf "%02d" $i)"
        files_count=$(hdfs dfs -ls "$partition_path" | grep -c "\.txt$" || echo "0")
        log_info "分区 year=2024/month=$(printf "%02d" $i): $files_count 个文件"
    done

    # 检查Hive表
    local verify_sql="/tmp/verify_$$.sql"
    cat > "$verify_sql" << EOF
USE $DATABASE_NAME;
SELECT COUNT(*) as total_records FROM $TABLE_NAME;
SELECT year, month, COUNT(*) as records_count FROM $TABLE_NAME GROUP BY year, month ORDER BY year, month;
EOF

    log_info "验证表数据..."
    hive -f "$verify_sql" || log_warning "表数据验证失败，请手动检查"
    rm -f "$verify_sql"

    log_success "验证完成"
}

# 显示使用说明
show_usage() {
    cat << EOF

${GREEN}=== Hive外部表创建成功 ===${NC}

表信息:
- 数据库: $DATABASE_NAME
- 表名: $TABLE_NAME
- 分区数: $PARTITION_COUNT
- 每分区文件数: $FILES_PER_PARTITION
- 总文件数: $((PARTITION_COUNT * FILES_PER_PARTITION))
- HDFS路径: $HDFS_BASE_PATH

验证命令:
${YELLOW}# 查看表结构${NC}
hive -e "USE $DATABASE_NAME; DESCRIBE FORMATTED $TABLE_NAME;"

${YELLOW}# 查看分区信息${NC}
hive -e "USE $DATABASE_NAME; SHOW PARTITIONS $TABLE_NAME;"

${YELLOW}# 查询数据示例${NC}
hive -e "USE $DATABASE_NAME; SELECT * FROM $TABLE_NAME LIMIT 10;"

${YELLOW}# 查看文件分布${NC}
hdfs dfs -find $HDFS_BASE_PATH -name "*.txt" | head -20

${YELLOW}# 检查小文件情况${NC}
hdfs fsck $HDFS_BASE_PATH -files -blocks

小文件治理平台测试:
${BLUE}现在可以使用这个表来测试你的小文件治理平台功能了！${NC}

EOF
}

# 主执行流程
main() {
    echo -e "${GREEN}"
    cat << 'EOF'
 _   _ _                ____                 _ _   _____ _ _
| | | (_)_   _____     / ___| _ __ ___   __ _| | | |  ___(_) | ___  ___
| |_| | \ \ / / _ \   | |  _ | '_ ` _ \ / _` | | | | |_  | | |/ _ \/ __|
|  _  | |\ V /  __/   | |_| || | | | | | (_| | | | |  _| | | |  __/\__ \
|_| |_|_| \_/ \___|    \____||_| |_| |_|\__,_|_|_| |_|   |_|_|\___||___/

   Test External Table Creator - 小文件治理平台测试工具
EOF
    echo -e "${NC}"

    log_info "开始创建测试用外部表..."
    log_info "配置: $PARTITION_COUNT 个分区，每分区 $FILES_PER_PARTITION 个文件"

    check_tools
    create_hdfs_structure
    generate_test_data
    create_hive_table
    verify_table
    show_usage

    log_success "外部表创建流程全部完成！"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi