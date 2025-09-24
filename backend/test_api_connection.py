#!/usr/bin/env python3
"""
测试通过API进行集群连接测试
"""
import json

import requests


def test_cluster_connection_api():
    """通过API测试集群连接"""

    api_url = "http://localhost:8000"

    # 测试集群配置
    cluster_config = {
        "name": "测试MySQL集群",
        "description": "测试MySQL Hive MetaStore连接",
        "hive_host": "192.168.0.105",
        "hive_port": 10000,
        "hive_database": "default",
        "hive_metastore_url": "mysql://root:!qaz2wsx3edC@192.168.0.105:3306/hive",
        "hdfs_namenode_url": "http://192.168.0.105:14000/webhdfs/v1",
        "hdfs_user": "hdfs",
        "small_file_threshold": 134217728,
        "scan_enabled": True,
    }

    print("🧪 API连接测试")
    print("=" * 60)
    print(f"API地址: {api_url}")
    print(f"MetaStore: {cluster_config['hive_metastore_url']}")
    print("-" * 60)

    try:
        # 1. 测试API健康状态
        print("1. 测试API健康状态...")
        health_response = requests.get(f"{api_url}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ API服务正常")
        else:
            print(f"⚠️  API状态异常: {health_response.status_code}")

        # 2. 测试连接配置API
        print("\n2. 测试连接配置...")
        test_response = requests.post(
            f"{api_url}/api/v1/clusters/test-connection-config",
            json=cluster_config,
            timeout=30,
        )

        print(f"状态码: {test_response.status_code}")

        if test_response.status_code == 200:
            result = test_response.json()
            print("✅ API调用成功")
            print("\n📊 连接测试结果:")

            # Hive MetaStore测试结果
            if "hive_metastore" in result:
                ms_result = result["hive_metastore"]
                status = "✅" if ms_result.get("success") else "❌"
                print(f"  {status} Hive MetaStore: {ms_result.get('message', 'N/A')}")
                if ms_result.get("success"):
                    print(f"    - 数据库数: {ms_result.get('databases', 0)}")
                    print(f"    - 表总数: {ms_result.get('tables', 0)}")

            # WebHDFS测试结果
            if "webhdfs" in result:
                hdfs_result = result["webhdfs"]
                status = "✅" if hdfs_result.get("success") else "❌"
                print(f"  {status} WebHDFS: {hdfs_result.get('message', 'N/A')}")

            # Beeline测试结果
            if "beeline" in result:
                beeline_result = result["beeline"]
                status = "✅" if beeline_result.get("success") else "❌"
                print(f"  {status} Beeline: {beeline_result.get('message', 'N/A')}")

            # 总体评估
            if "overall_assessment" in result:
                assessment = result["overall_assessment"]
                print(f"\n🔍 总体评估: {assessment.get('status', 'unknown')}")
                print(f"   建议: {assessment.get('recommendation', 'N/A')}")

            return True

        else:
            print("❌ API调用失败")
            try:
                error_detail = test_response.json()
                print(
                    f"错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}"
                )
            except:
                print(f"错误内容: {test_response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务")
        print("💡 请确保后端服务在 http://localhost:8000 运行")
        return False
    except requests.exceptions.Timeout:
        print("❌ API请求超时")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        return False


def test_cluster_crud_api():
    """测试集群CRUD API"""

    api_url = "http://localhost:8000"

    cluster_config = {
        "name": "API测试集群",
        "description": "通过API创建的测试集群",
        "hive_host": "192.168.0.105",
        "hive_port": 10000,
        "hive_database": "default",
        "hive_metastore_url": "mysql://root:!qaz2wsx3edC@192.168.0.105:3306/hive",
        "hdfs_namenode_url": "http://192.168.0.105:14000/webhdfs/v1",
        "hdfs_user": "hdfs",
        "small_file_threshold": 134217728,
        "scan_enabled": True,
        "status": "active",
    }

    print("\n🔧 测试集群CRUD操作")
    print("-" * 60)

    try:
        # 1. 创建集群
        print("1. 创建测试集群...")
        create_response = requests.post(
            f"{api_url}/api/v1/clusters/", json=cluster_config, timeout=10
        )

        if create_response.status_code == 200:
            cluster = create_response.json()
            cluster_id = cluster["id"]
            print(f"✅ 集群创建成功，ID: {cluster_id}")

            # 2. 测试集群连接
            print("2. 测试集群连接...")
            test_response = requests.post(
                f"{api_url}/api/v1/clusters/{cluster_id}/test-connection", timeout=30
            )

            if test_response.status_code == 200:
                result = test_response.json()
                print("✅ 连接测试成功")

                # 显示测试结果详情
                if isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, dict) and "success" in value:
                            status = "✅" if value["success"] else "❌"
                            print(f"  {status} {key}: {value.get('message', 'N/A')}")
            else:
                print(f"❌ 连接测试失败: {test_response.status_code}")
                print(test_response.text)

            # 3. 删除测试集群
            print("3. 清理测试集群...")
            delete_response = requests.delete(
                f"{api_url}/api/v1/clusters/{cluster_id}", timeout=10
            )

            if delete_response.status_code == 200:
                print("✅ 测试集群已删除")
            else:
                print(f"⚠️  删除集群失败: {delete_response.status_code}")

            return True

        else:
            print(f"❌ 创建集群失败: {create_response.status_code}")
            try:
                error_detail = create_response.json()
                print(
                    f"错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}"
                )
            except:
                print(f"错误内容: {create_response.text}")
            return False

    except Exception as e:
        print(f"❌ CRUD测试异常: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 启动API连接测试")
    print("=" * 80)

    # 测试连接配置
    config_test_ok = test_cluster_connection_api()

    # 测试CRUD操作
    if config_test_ok:
        crud_test_ok = test_cluster_crud_api()

        if crud_test_ok:
            print("\n🎉 所有API测试通过！")
            print("💡 MySQL连接正常，可以在界面中配置集群了。")
        else:
            print("\n⚠️  连接测试正常，但CRUD操作有问题。")
    else:
        print("\n❌ 连接配置测试失败")
        print("💡 建议检查:")
        print("  1. 后端服务是否在 http://localhost:8000 运行")
        print("  2. API路由配置是否正确")
        print("  3. 数据库连接池设置")
