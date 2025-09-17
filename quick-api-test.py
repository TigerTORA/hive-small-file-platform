#!/usr/bin/env python3
"""
快速API测试工具 - 测试前端调用的关键API
"""

import requests
import json

def test_api_endpoint(method, endpoint, description):
    """测试API端点"""
    base_url = "http://localhost:8000"
    full_url = f"{base_url}{endpoint}"

    try:
        if method.upper() == 'GET':
            response = requests.get(full_url, timeout=5)
        elif method.upper() == 'POST':
            response = requests.post(full_url, json={}, timeout=5)
        else:
            return f"❓ {method} {endpoint} - 暂不测试"

        if response.status_code == 200:
            return f"✅ {method} {endpoint} - 正常"
        elif response.status_code == 404:
            return f"❌ {method} {endpoint} - 404 未找到"
        elif response.status_code == 422:
            return f"⚠️ {method} {endpoint} - 422 参数错误"
        else:
            return f"⚠️ {method} {endpoint} - {response.status_code}"

    except Exception as e:
        return f"💥 {method} {endpoint} - 连接失败: {str(e)}"

def main():
    print("🧪 快速API测试 - 检验前端关键API调用")
    print("="*50)

    # 关键API端点测试
    test_cases = [
        # Dashboard APIs
        ("GET", "/api/v1/dashboard/summary", "仪表板概要"),
        ("GET", "/api/v1/dashboard/trends", "趋势数据"),
        ("GET", "/api/v1/dashboard/cluster-stats", "集群统计"),

        # Clusters APIs
        ("GET", "/api/v1/clusters/", "集群列表"),
        ("POST", "/api/v1/clusters/", "创建集群"),

        # Tables APIs
        ("GET", "/api/v1/tables/metrics", "表指标"),
        ("POST", "/api/v1/tables/scan/1", "扫描集群"),

        # Tasks APIs
        ("GET", "/api/v1/tasks/", "任务列表"),
        ("POST", "/api/v1/tasks/", "创建任务"),

        # Scan Tasks APIs
        ("GET", "/api/v1/scan-tasks/", "扫描任务列表"),
        ("GET", "/api/v1/scan-tasks/dd94e047-5f94-4490-aa88-897d080da062", "获取扫描任务"),
        ("GET", "/api/v1/scan-tasks/dd94e047-5f94-4490-aa88-897d080da062/logs", "扫描任务日志"),
    ]

    results = []
    for method, endpoint, desc in test_cases:
        result = test_api_endpoint(method, endpoint, desc)
        results.append(result)
        print(result)

    print("\n" + "="*50)
    print("📊 测试总结:")

    success_count = len([r for r in results if "✅" in r])
    error_count = len([r for r in results if "❌" in r])
    warning_count = len([r for r in results if "⚠️" in r])

    print(f"✅ 正常: {success_count}")
    print(f"❌ 错误: {error_count}")
    print(f"⚠️ 警告: {warning_count}")
    print(f"📈 成功率: {success_count/len(results)*100:.1f}%")

if __name__ == "__main__":
    main()