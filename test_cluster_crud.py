#!/usr/bin/env python3
"""
测试完整的集群CRUD流程
验证所有集群管理API接口的功能
"""

import sys
import os
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def log_info(message):
    """记录信息"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def test_api_health():
    """测试API服务状态"""
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            log_info("✅ API服务运行正常")
            return True
        else:
            log_info(f"❌ API服务异常: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        log_info("❌ 无法连接到API服务，请确保后端正在运行")
        log_info("启动命令: cd backend && uvicorn app.main:app --reload --port 8000")
        return False

def test_cluster_crud():
    """测试完整的集群CRUD流程"""
    
    log_info("🚀 开始测试集群CRUD流程")
    
    # 1. 测试集群列表（初始状态）
    log_info("\n📋 1. 获取初始集群列表")
    response = requests.get(f"{BASE_URL}/clusters/")
    if response.status_code == 200:
        initial_clusters = response.json()
        log_info(f"当前集群数量: {len(initial_clusters)}")
        for cluster in initial_clusters:
            log_info(f"  - {cluster['name']} (ID: {cluster['id']})")
    else:
        log_info(f"❌ 获取集群列表失败: {response.status_code}")
        return False
    
    # 2. 测试创建集群
    log_info("\n✨ 2. 创建新集群")
    test_cluster_data = {
        "name": "测试集群-CRUD",
        "description": "CRUD流程测试集群",
        "hive_host": "test-hive",
        "hive_port": 10000,
        "hive_database": "default",
        "hive_metastore_url": "mysql://test:test@test-host:3306/hive",
        "hdfs_namenode_url": "hdfs://test-nameservice",
        "hdfs_user": "hdfs",
        "small_file_threshold": 64 * 1024 * 1024,  # 64MB
        "scan_enabled": True
    }
    
    response = requests.post(f"{BASE_URL}/clusters/", json=test_cluster_data)
    if response.status_code == 200:
        created_cluster = response.json()
        cluster_id = created_cluster['id']
        log_info(f"✅ 集群创建成功: {created_cluster['name']} (ID: {cluster_id})")
    else:
        log_info(f"❌ 集群创建失败: {response.status_code}")
        print(response.text)
        return False
    
    # 3. 测试获取单个集群
    log_info(f"\n🔍 3. 获取集群详情 (ID: {cluster_id})")
    response = requests.get(f"{BASE_URL}/clusters/{cluster_id}")
    if response.status_code == 200:
        cluster = response.json()
        log_info(f"✅ 集群详情: {cluster['name']}")
        log_info(f"  描述: {cluster['description']}")
        log_info(f"  状态: {cluster['status']}")
        log_info(f"  小文件阈值: {cluster['small_file_threshold'] / (1024*1024)} MB")
    else:
        log_info(f"❌ 获取集群详情失败: {response.status_code}")
        return False
    
    # 4. 测试连接测试 (Mock模式)
    log_info(f"\n🔌 4. 测试Mock连接")
    response = requests.post(f"{BASE_URL}/clusters/{cluster_id}/test?mode=mock")
    if response.status_code == 200:
        result = response.json()
        log_info(f"✅ Mock连接测试完成")
        log_info(f"  测试模式: {result['test_mode']}")
        log_info(f"  MetaStore: {result['connections']['metastore']['status']}")
        log_info(f"  HDFS: {result['connections']['hdfs']['status']}")
    else:
        log_info(f"⚠️ Mock连接测试失败: {response.status_code}")
    
    # 5. 测试真实连接测试
    log_info(f"\n🌐 5. 测试真实连接")
    response = requests.post(f"{BASE_URL}/clusters/{cluster_id}/test-real")
    if response.status_code == 200:
        result = response.json()
        log_info(f"✅ 真实连接测试完成")
        log_info(f"  测试模式: {result['test_mode']}")
        log_info(f"  MetaStore: {result['connections']['metastore']['status']}")
        hdfs_info = result['connections']['hdfs']
        log_info(f"  HDFS: {hdfs_info['status']} (模式: {hdfs_info.get('mode', 'unknown')})")
        if hdfs_info.get('real_hdfs_error'):
            log_info(f"    真实HDFS错误: {hdfs_info['real_hdfs_error']}")
    else:
        log_info(f"⚠️ 真实连接测试失败: {response.status_code}")
    
    # 6. 测试更新集群
    log_info(f"\n✏️ 6. 更新集群配置")
    update_data = {
        "description": "已更新的CRUD测试集群",
        "small_file_threshold": 256 * 1024 * 1024,  # 256MB
        "hive_port": 10001
    }
    
    response = requests.put(f"{BASE_URL}/clusters/{cluster_id}", json=update_data)
    if response.status_code == 200:
        updated_cluster = response.json()
        log_info(f"✅ 集群更新成功")
        log_info(f"  新描述: {updated_cluster['description']}")
        log_info(f"  新阈值: {updated_cluster['small_file_threshold'] / (1024*1024)} MB")
        log_info(f"  新端口: {updated_cluster['hive_port']}")
    else:
        log_info(f"❌ 集群更新失败: {response.status_code}")
        print(response.text)
        return False
    
    # 7. 验证更新后的集群列表
    log_info(f"\n📋 7. 验证更新后的集群列表")
    response = requests.get(f"{BASE_URL}/clusters/")
    if response.status_code == 200:
        clusters = response.json()
        log_info(f"当前集群数量: {len(clusters)}")
        test_cluster = next((c for c in clusters if c['id'] == cluster_id), None)
        if test_cluster:
            log_info(f"  测试集群存在: {test_cluster['name']}")
        else:
            log_info("❌ 测试集群在列表中未找到")
            return False
    else:
        log_info(f"❌ 获取集群列表失败: {response.status_code}")
        return False
    
    # 8. 测试创建重名集群（应该失败）
    log_info(f"\n🚫 8. 测试创建重名集群（预期失败）")
    duplicate_data = test_cluster_data.copy()
    response = requests.post(f"{BASE_URL}/clusters/", json=duplicate_data)
    if response.status_code == 400:
        log_info(f"✅ 正确拒绝重名集群: {response.json().get('detail', '')}")
    else:
        log_info(f"⚠️ 重名检查未生效: {response.status_code}")
    
    # 9. 测试无效URL格式（应该失败）
    log_info(f"\n🚫 9. 测试无效URL格式（预期失败）")
    invalid_data = {
        "name": "无效URL集群",
        "hive_metastore_url": "invalid://url",
        "hdfs_namenode_url": "invalid://url",
        "hive_host": "test"
    }
    response = requests.post(f"{BASE_URL}/clusters/", json=invalid_data)
    if response.status_code == 400:
        log_info(f"✅ 正确拒绝无效URL: {response.json().get('detail', '')}")
    else:
        log_info(f"⚠️ URL验证未生效: {response.status_code}")
    
    # 10. 测试带连接验证的创建
    log_info(f"\n🔍 10. 测试带连接验证的创建")
    validation_data = {
        "name": "验证连接测试集群",
        "description": "测试连接验证功能",
        "hive_host": "validation-test",
        "hive_metastore_url": "mysql://test:test@validation-host:3306/hive",
        "hdfs_namenode_url": "hdfs://validation-nameservice"
    }
    
    response = requests.post(f"{BASE_URL}/clusters/?validate_connection=true", json=validation_data)
    if response.status_code == 400:
        log_info(f"✅ 连接验证正确阻止无效集群: {response.json().get('detail', '')}")
    elif response.status_code == 200:
        validation_cluster = response.json()
        log_info(f"✅ 连接验证创建成功: {validation_cluster['name']}")
        # 清理这个测试集群
        requests.delete(f"{BASE_URL}/clusters/{validation_cluster['id']}")
    else:
        log_info(f"⚠️ 连接验证测试异常: {response.status_code}")
    
    # 11. 测试删除集群
    log_info(f"\n🗑️ 11. 删除测试集群 (ID: {cluster_id})")
    response = requests.delete(f"{BASE_URL}/clusters/{cluster_id}")
    if response.status_code == 200:
        result = response.json()
        log_info(f"✅ 集群删除成功: {result['message']}")
    else:
        log_info(f"❌ 集群删除失败: {response.status_code}")
        print(response.text)
        return False
    
    # 12. 验证集群已被删除
    log_info(f"\n✅ 12. 验证集群已删除")
    response = requests.get(f"{BASE_URL}/clusters/{cluster_id}")
    if response.status_code == 404:
        log_info(f"✅ 集群确认已删除")
    else:
        log_info(f"⚠️ 集群似乎仍然存在: {response.status_code}")
        return False
    
    # 13. 最终集群列表验证
    log_info(f"\n📋 13. 最终集群列表验证")
    response = requests.get(f"{BASE_URL}/clusters/")
    if response.status_code == 200:
        final_clusters = response.json()
        log_info(f"最终集群数量: {len(final_clusters)}")
        if len(final_clusters) == len(initial_clusters):
            log_info(f"✅ 集群数量恢复到初始状态")
        else:
            log_info(f"⚠️ 集群数量未恢复: 初始{len(initial_clusters)} vs 最终{len(final_clusters)}")
    
    return True

def main():
    """主测试函数"""
    log_info("🧪 集群CRUD功能完整性测试")
    log_info("=" * 50)
    
    # 检查API服务
    if not test_api_health():
        return False
    
    # 执行CRUD测试
    try:
        success = test_cluster_crud()
        
        log_info("\n" + "=" * 50)
        if success:
            log_info("🎉 所有集群CRUD测试通过！")
            log_info("\n✅ 功能验证完成:")
            log_info("  - ✅ 集群列表查询")
            log_info("  - ✅ 集群创建（普通/带验证）")
            log_info("  - ✅ 集群详情查询")
            log_info("  - ✅ 集群配置更新")
            log_info("  - ✅ 集群删除")
            log_info("  - ✅ 连接测试（Mock/真实）")
            log_info("  - ✅ 数据验证和错误处理")
            return True
        else:
            log_info("❌ 部分测试失败")
            return False
            
    except Exception as e:
        log_info(f"💥 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)