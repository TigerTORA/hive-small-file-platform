#!/bin/bash

# Hive外部表验证脚本
# 用于验证create_test_external_table.sh创建的测试表

set -e

# 配置参数
TABLE_NAME="${TABLE_NAME:-test_small_files_table}"
DATABASE_NAME="${DATABASE_NAME:-test_db}"
HDFS_BASE_PATH="${HDFS_BASE_PATH:-/user/test/small_files_test}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[验证]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[通过]${NC} $1"
}

log_error() {
    echo -e "${RED}[失败]${NC} $1"
}

# 验证HDFS文件
verify_hdfs() {
    log_info "检查HDFS文件..."

    if ! hdfs dfs -test -d "$HDFS_BASE_PATH"; then
        log_error "HDFS基础路径不存在: $HDFS_BASE_PATH"
        return 1
    fi

    # 统计文件总数
    total_files=$(hdfs dfs -find "$HDFS_BASE_PATH" -name "*.txt" | wc -l)
    log_info "HDFS文件总数: $total_files"

    # 检查每个分区
    for i in $(seq 1 10); do
        partition_path="$HDFS_BASE_PATH/year=2024/month=$(printf "%02d" $i)"
        if hdfs dfs -test -d "$partition_path"; then
            files_count=$(hdfs dfs -ls "$partition_path" | grep -c "\.txt$" || echo "0")
            if [ "$files_count" -eq 100 ]; then
                log_success "分区 month=$(printf "%02d" $i): $files_count 文件"
            else
                log_error "分区 month=$(printf "%02d" $i): $files_count 文件（期望100）"
            fi
        else
            log_error "分区目录不存在: $partition_path"
        fi
    done
}

# 验证Hive表
verify_hive() {
    log_info "检查Hive表..."

    # 检查数据库是否存在
    if ! hive -e "SHOW DATABASES;" | grep -q "^$DATABASE_NAME$"; then
        log_error "数据库不存在: $DATABASE_NAME"
        return 1
    fi

    # 检查表是否存在
    if ! hive -e "USE $DATABASE_NAME; SHOW TABLES;" | grep -q "^$TABLE_NAME$"; then
        log_error "表不存在: $DATABASE_NAME.$TABLE_NAME"
        return 1
    fi

    log_success "数据库和表存在"

    # 检查分区
    partitions=$(hive -e "USE $DATABASE_NAME; SHOW PARTITIONS $TABLE_NAME;" | wc -l)
    log_info "分区数量: $partitions"

    if [ "$partitions" -eq 10 ]; then
        log_success "分区数量正确 (10)"
    else
        log_error "分区数量错误: $partitions (期望10)"
    fi

    # 检查数据行数
    log_info "统计数据行数..."
    row_count=$(hive -e "USE $DATABASE_NAME; SELECT COUNT(*) FROM $TABLE_NAME;" 2>/dev/null | tail -1)
    log_info "数据行数: $row_count"

    if [ "$row_count" -gt 0 ]; then
        log_success "表中有数据 ($row_count 行)"
    else
        log_error "表中无数据"
    fi
}

# 生成验证报告
generate_report() {
    log_info "生成验证报告..."

    cat > "/tmp/table_verification_report.txt" << EOF
=== Hive外部表验证报告 ===
生成时间: $(date)

表信息:
- 数据库: $DATABASE_NAME
- 表名: $TABLE_NAME
- HDFS路径: $HDFS_BASE_PATH

HDFS验证:
$(hdfs dfs -find "$HDFS_BASE_PATH" -name "*.txt" | wc -l) 个数据文件
$(hdfs dfs -du -s "$HDFS_BASE_PATH" | awk '{print $1/1024/1024 "MB"}') 总占用空间

Hive验证:
分区数: $(hive -e "USE $DATABASE_NAME; SHOW PARTITIONS $TABLE_NAME;" 2>/dev/null | wc -l)
数据行数: $(hive -e "USE $DATABASE_NAME; SELECT COUNT(*) FROM $TABLE_NAME;" 2>/dev/null | tail -1)

分区详情:
$(hive -e "USE $DATABASE_NAME; SELECT year, month, COUNT(*) as records FROM $TABLE_NAME GROUP BY year, month ORDER BY month;" 2>/dev/null)

文件大小分析:
$(hdfs dfs -find "$HDFS_BASE_PATH" -name "*.txt" -exec hdfs dfs -ls {} \; | awk '{sum+=$5; count++} END {print "平均文件大小: " sum/count/1024 "KB, 总文件数: " count}')
EOF

    log_success "报告已生成: /tmp/table_verification_report.txt"
    cat "/tmp/table_verification_report.txt"
}

# 主程序
main() {
    echo -e "${GREEN}=== Hive外部表验证工具 ===${NC}"
    echo "验证表: $DATABASE_NAME.$TABLE_NAME"
    echo "HDFS路径: $HDFS_BASE_PATH"
    echo

    verify_hdfs
    echo
    verify_hive
    echo
    generate_report

    echo
    log_success "验证完成！"
}

# 执行验证
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi