#!/bin/bash
# 计算每个月HDFS数据量的脚本

echo "=== HDFS每月数据量统计 ==="
echo "格式: 年-月 数据量(字节) 数据量(MB) 数据量(GB)"
echo "========================================"

# 方法1: 直接处理你提供的输出格式 (文件大小 日期)
hdfs dfs -ls -R /tmp | awk '{print $5" "$6}' | awk '
BEGIN {
    # 月份名称映射
    months["01"] = "一月"; months["02"] = "二月"; months["03"] = "三月"
    months["04"] = "四月"; months["05"] = "五月"; months["06"] = "六月"
    months["07"] = "七月"; months["08"] = "八月"; months["09"] = "九月"
    months["10"] = "十月"; months["11"] = "十一月"; months["12"] = "十二月"
}
/^[0-9]+ [0-9]{4}-[0-9]{2}-[0-9]{2}$/ {
    # 提取文件大小和日期
    size = $1
    date = $2
    
    # 提取年月 (YYYY-MM)
    year_month = substr(date, 1, 7)
    
    # 累加每月数据量
    monthly_data[year_month] += size
    
    # 统计文件数量
    monthly_files[year_month]++
}
END {
    # 输出结果，按年月排序
    PROCINFO["sorted_in"] = "@ind_str_asc"
    
    total_size = 0
    total_files = 0
    
    for (year_month in monthly_data) {
        size_bytes = monthly_data[year_month]
        size_mb = size_bytes / (1024 * 1024)
        size_gb = size_mb / 1024
        file_count = monthly_files[year_month]
        
        printf "%-8s %12d字节 %8.2fMB %6.2fGB (%d个文件)\n", 
               year_month, size_bytes, size_mb, size_gb, file_count
        
        total_size += size_bytes
        total_files += file_count
    }
    
    print "========================================"
    total_mb = total_size / (1024 * 1024)
    total_gb = total_mb / 1024
    printf "总计:    %12d字节 %8.2fMB %6.2fGB (%d个文件)\n", 
           total_size, total_mb, total_gb, total_files
}'

echo ""
echo "=== 详细分析 ==="
echo "最近3个月数据量趋势:"

# 方法2: 更详细的分析，包含趋势分析
hdfs dfs -ls -R /tmp | awk '{print $5" "$6}' | awk '
/^[0-9]+ [0-9]{4}-[0-9]{2}-[0-9]{2}$/ {
    size = $1
    date = $2
    year_month = substr(date, 1, 7)
    monthly_data[year_month] += size
}
END {
    PROCINFO["sorted_in"] = "@ind_str_desc"
    
    count = 0
    for (year_month in monthly_data) {
        if (count < 3) {
            size_gb = monthly_data[year_month] / (1024 * 1024 * 1024)
            printf "%s: %.2f GB\n", year_month, size_gb
            count++
        }
    }
}'

echo ""
echo "=== 年度汇总 ==="
hdfs dfs -ls -R /tmp | awk '{print $5" "$6}' | awk '
/^[0-9]+ [0-9]{4}-[0-9]{2}-[0-9]{2}$/ {
    size = $1
    date = $2
    year = substr(date, 1, 4)
    yearly_data[year] += size
}
END {
    PROCINFO["sorted_in"] = "@ind_str_asc"
    
    for (year in yearly_data) {
        size_gb = yearly_data[year] / (1024 * 1024 * 1024)
        printf "%s年: %.2f GB\n", year, size_gb
    }
}'