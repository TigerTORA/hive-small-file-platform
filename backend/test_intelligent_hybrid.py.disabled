#!/usr/bin/env python3
"""
测试智能混合扫描器
"""
import sys
import os
sys.path.append('/Users/luohu/new_project/hive-small-file-platform/backend')

from app.monitor.intelligent_hybrid_scanner import IntelligentHybridScanner
import json

def test_intelligent_hybrid_scanner():
    """测试智能混合扫描器"""
    print("=== 智能混合扫描器测试 ===")
    
    # 测试HttpFS配置
    scanner = IntelligentHybridScanner(
        namenode_url="http://192.168.0.105:14000",
        user="hdfs"
    )
    
    print(f"初始化完成: {scanner.webhdfs_base_url}")
    
    # 测试连接
    print("\n1. 测试连接...")
    result = scanner.test_connection()
    print(f"连接结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 测试路径扫描
    print("\n2. 测试路径扫描...")
    scan_result = scanner.scan_path("/user/hive/warehouse/test_table")
    print(f"扫描结果: {json.dumps(scan_result, indent=2, ensure_ascii=False)}")
    
    # 测试兼容性方法
    print("\n3. 测试兼容性方法...")
    
    # 连接测试
    connect_result = scanner.connect()
    print(f"connect() 结果: {connect_result}")
    
    # 表分区扫描测试
    table_stats, partition_stats = scanner.scan_table_partitions(
        "/user/hive/warehouse/test_table", 
        "default", 
        "test_table"
    )
    print(f"表统计: {json.dumps(table_stats, indent=2, ensure_ascii=False)}")
    print(f"分区统计数量: {len(partition_stats)}")
    
    # 获取连接信息
    conn_info = scanner.get_connection_info()
    print(f"连接信息: {json.dumps(conn_info, indent=2, ensure_ascii=False)}")
    
    # 断开连接
    scanner.disconnect()
    print("disconnect() 完成")

if __name__ == "__main__":
    test_intelligent_hybrid_scanner()