#!/bin/bash

# Hive小文件治理平台演示脚本
# 一键创建测试数据并启动验证流程

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[演示]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[注意]${NC} $1"
}

# 显示欢迎信息
show_welcome() {
    echo -e "${GREEN}"
    cat << 'EOF'
 ╔═══════════════════════════════════════════════════════════════╗
 ║                Hive 小文件治理平台 - 演示工具                    ║
 ║                                                               ║
 ║  🎯 目标: 创建包含1000个小文件的测试表                          ║
 ║  📊 配置: 10个分区，每分区100个50KB小文件                       ║
 ║  🛠️ 功能: 自动创建、验证、集成测试                             ║
 ╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# 检查环境
check_environment() {
    log_info "检查运行环境..."

    local missing_tools=()

    if ! command -v hive &> /dev/null; then
        missing_tools+=("hive")
    fi

    if ! command -v hdfs &> /dev/null; then
        missing_tools+=("hdfs")
    fi

    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo "❌ 缺少必要工具: ${missing_tools[*]}"
        echo "请确保 Hadoop/Hive 环境已正确安装配置"
        exit 1
    fi

    log_success "环境检查通过"
}

# 创建测试表
create_test_table() {
    log_info "开始创建测试表..."

    cd "$SCRIPT_DIR/scripts"

    # 使用默认配置
    export TABLE_NAME="demo_small_files_table"
    export DATABASE_NAME="demo_db"
    export HDFS_BASE_PATH="/user/demo/small_files_demo"
    export PARTITION_COUNT=10
    export FILES_PER_PARTITION=100
    export FILE_SIZE_KB=50

    log_info "配置信息:"
    echo "  - 表名: $TABLE_NAME"
    echo "  - 数据库: $DATABASE_NAME"
    echo "  - 分区数: $PARTITION_COUNT"
    echo "  - 每分区文件数: $FILES_PER_PARTITION"
    echo "  - 总文件数: $((PARTITION_COUNT * FILES_PER_PARTITION))"

    ./create_test_external_table.sh

    log_success "测试表创建完成"
}

# 验证创建结果
verify_results() {
    log_info "验证创建结果..."

    cd "$SCRIPT_DIR/scripts"

    export TABLE_NAME="demo_small_files_table"
    export DATABASE_NAME="demo_db"
    export HDFS_BASE_PATH="/user/demo/small_files_demo"

    ./verify_test_table.sh

    log_success "验证完成"
}

# 集成测试指导
show_integration_guide() {
    log_info "小文件治理平台集成测试指导"

    cat << EOF

${GREEN}🚀 下一步操作指南:${NC}

${YELLOW}1. 启动治理平台:${NC}
   cd $SCRIPT_DIR
   # 启动后端
   cd backend && uvicorn app.main:app --reload --port 8000 &
   # 启动前端
   cd ../frontend && npm run dev &

${YELLOW}2. 配置集群连接:${NC}
   打开浏览器访问: http://localhost:3000
   - 进入"集群管理"页面
   - 添加测试集群配置
   - 配置 Hive 和 HDFS 连接信息

${YELLOW}3. 扫描测试表:${NC}
   curl -X POST "http://localhost:8000/api/v1/tables/scan" \\
     -H "Content-Type: application/json" \\
     -d '{
       "cluster_id": 1,
       "database_name": "demo_db",
       "table_name": "demo_small_files_table"
     }'

${YELLOW}4. 查看小文件统计:${NC}
   - Dashboard页面查看小文件分布图表
   - Tables页面查看具体表的小文件详情
   - 创建合并任务测试治理效果

${YELLOW}5. 清理测试数据:${NC}
   # 删除HDFS数据
   hdfs dfs -rm -r /user/demo/small_files_demo

   # 删除Hive表
   hive -e "DROP DATABASE IF EXISTS demo_db CASCADE;"

${GREEN}🎉 现在你有了完美的小文件测试环境！${NC}

验证报告已保存至: /tmp/table_verification_report.txt

EOF
}

# 主程序
main() {
    show_welcome

    log_warning "警告：此演示会创建1000个小文件用于测试，请确保在测试环境中运行！"
    echo
    read -p "继续执行？(y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "演示已取消"
        exit 0
    fi

    check_environment
    echo

    create_test_table
    echo

    verify_results
    echo

    show_integration_guide

    log_success "演示流程全部完成！🎉"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi