# HDFS每月数据量计算命令集

## 基于你的输出格式处理

你的数据格式：
```
0 2025-09-28
1947 2024-12-22
1075 2024-12-02
601 2024-05-31
6492 2024-12-07
631 2024-12-07
```

## 方法1: 简单月度汇总
```bash
hdfs dfs -ls -R /tmp | awk '{print $5" "$6}' | awk '
/^[0-9]+ [0-9]{4}-[0-9]{2}-[0-9]{2}$/ {
    year_month = substr($2, 1, 7)
    monthly[$year_month] += $1
}
END {
    for (ym in monthly) {
        printf "%s: %d 字节 (%.2f MB)\n", ym, monthly[ym], monthly[ym]/(1024*1024)
    }
}' | sort
```

## 方法2: 详细统计（包含文件数）
```bash
hdfs dfs -ls -R /tmp | awk '{print $5" "$6}' | awk '
/^[0-9]+ [0-9]{4}-[0-9]{2}-[0-9]{2}$/ {
    year_month = substr($2, 1, 7)
    monthly_size[year_month] += $1
    monthly_count[year_month]++
}
END {
    printf "%-8s %12s %8s %6s %s\n", "年月", "字节数", "MB", "GB", "文件数"
    print "=================================================="
    
    for (ym in monthly_size) {
        mb = monthly_size[ym] / (1024*1024)
        gb = mb / 1024
        printf "%-8s %12d %8.2f %6.2f %d\n", ym, monthly_size[ym], mb, gb, monthly_count[ym]
    }
}' | sort
```

## 方法3: 处理你当前的测试数据
基于你提供的示例数据，直接测试：

```bash
echo "0 2025-09-28
1947 2024-12-22
1075 2024-12-02
601 2024-05-31
6492 2024-12-07
631 2024-12-07" | awk '
{
    year_month = substr($2, 1, 7)
    monthly[$year_month] += $1
}
END {
    printf "%-8s %12s %8s\n", "年月", "字节数", "MB"
    print "=========================="
    
    for (ym in monthly) {
        mb = monthly[ym] / (1024*1024)
        printf "%-8s %12d %8.2f\n", ym, monthly[ym], mb
    }
}' | sort
```

## 方法4: 年度趋势分析
```bash
hdfs dfs -ls -R /tmp | awk '{print $5" "$6}' | awk '
/^[0-9]+ [0-9]{4}-[0-9]{2}-[0-9]{2}$/ {
    year = substr($2, 1, 4)
    month = substr($2, 6, 2)
    year_month = substr($2, 1, 7)
    
    yearly[year] += $1
    monthly[year_month] += $1
}
END {
    print "=== 年度汇总 ==="
    for (y in yearly) {
        gb = yearly[y] / (1024*1024*1024)
        printf "%s: %.2f GB\n", y, gb
    }
    
    print "\n=== 月度详情 ==="
    for (ym in monthly) {
        mb = monthly[ym] / (1024*1024)
        printf "%s: %.2f MB\n", ym, mb
    }
}' | sort
```

## 方法5: 最近N个月统计
```bash
# 最近6个月的数据
hdfs dfs -ls -R /tmp | awk '{print $5" "$6}' | awk '
/^[0-9]+ [0-9]{4}-[0-9]{2}-[0-9]{2}$/ {
    year_month = substr($2, 1, 7)
    monthly[year_month] += $1
}
END {
    # 按时间倒序排列，显示最近6个月
    PROCINFO["sorted_in"] = "@ind_str_desc"
    count = 0
    
    print "最近6个月数据量:"
    for (ym in monthly) {
        if (count < 6) {
            gb = monthly[ym] / (1024*1024*1024)
            printf "%s: %.3f GB\n", ym, gb
            count++
        }
    }
}'
```

## 一键执行脚本

运行完整分析：
```bash
./scripts/calculate_monthly_data.sh
```