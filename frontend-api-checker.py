#!/usr/bin/env python3
"""
前端API调用问题系统性检测工具
检测前端代码中的潜在API问题
"""

import re
import os
import json
import requests
import subprocess
from pathlib import Path
from collections import defaultdict
from urllib.parse import urljoin

class FrontendAPIChecker:
    def __init__(self, frontend_dir="frontend/src", backend_url="http://localhost:8000"):
        self.frontend_dir = frontend_dir
        self.backend_url = backend_url
        self.api_calls = []
        self.backend_endpoints = []
        self.issues = []

    def scan_frontend_api_calls(self):
        """扫描前端代码中的所有API调用"""
        print("🔍 扫描前端API调用...")

        api_pattern = re.compile(r'api\.(get|post|put|delete|patch)\([\'"`]([^\'"`]+)[\'"`]')
        template_pattern = re.compile(r'api\.(get|post|put|delete|patch)\(\`([^`]+)\`')

        for root, dirs, files in os.walk(self.frontend_dir):
            for file in files:
                if file.endswith(('.vue', '.ts', '.js')):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')

                        for i, line in enumerate(lines, 1):
                            # 匹配字符串API调用
                            matches = api_pattern.findall(line)
                            for method, endpoint in matches:
                                self.api_calls.append({
                                    'file': file_path,
                                    'line': i,
                                    'method': method,
                                    'endpoint': endpoint,
                                    'raw_line': line.strip()
                                })

                            # 匹配模板字符串API调用
                            template_matches = template_pattern.findall(line)
                            for method, endpoint in template_matches:
                                self.api_calls.append({
                                    'file': file_path,
                                    'line': i,
                                    'method': method,
                                    'endpoint': endpoint,
                                    'raw_line': line.strip(),
                                    'template': True
                                })

        print(f"✅ 发现 {len(self.api_calls)} 个API调用")

    def get_backend_endpoints(self):
        """获取后端实际可用的API端点"""
        print("🚀 检测后端API端点...")

        try:
            # 尝试获取OpenAPI文档
            response = requests.get(f"{self.backend_url}/docs/json", timeout=5)
            if response.status_code == 200:
                openapi_spec = response.json()
                for path, methods in openapi_spec.get('paths', {}).items():
                    for method in methods.keys():
                        self.backend_endpoints.append({
                            'endpoint': path,
                            'method': method.upper()
                        })
                print(f"✅ 从OpenAPI获取 {len(self.backend_endpoints)} 个端点")
                return
        except:
            pass

        # 备用：从路由文件扫描
        print("⚠️ 无法获取OpenAPI文档，使用静态扫描...")
        self._scan_backend_routes()

    def _scan_backend_routes(self):
        """扫描后端路由定义"""
        backend_api_dir = "backend/app/api"
        router_pattern = re.compile(r'@router\.(get|post|put|delete|patch)\([\'"`]([^\'"`]+)[\'"`]')

        for root, dirs, files in os.walk(backend_api_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')

                        for line in lines:
                            matches = router_pattern.findall(line)
                            for method, endpoint in matches:
                                # 推断API前缀
                                api_file = os.path.basename(file_path).replace('.py', '')
                                if api_file == 'tasks':
                                    prefix = '/api/v1/tasks'
                                elif api_file == 'scan_tasks':
                                    prefix = '/api/v1/scan-tasks'
                                elif api_file == 'clusters':
                                    prefix = '/api/v1/clusters'
                                elif api_file == 'tables':
                                    prefix = '/api/v1/tables'
                                elif api_file == 'dashboard':
                                    prefix = '/api/v1/dashboard'
                                else:
                                    prefix = f'/api/v1/{api_file}'

                                full_endpoint = prefix + endpoint if not endpoint.startswith('/') else endpoint
                                self.backend_endpoints.append({
                                    'endpoint': full_endpoint,
                                    'method': method.upper()
                                })

    def validate_api_calls(self):
        """验证前端API调用的有效性"""
        print("🔍 验证API调用...")

        backend_endpoint_map = defaultdict(list)
        for ep in self.backend_endpoints:
            backend_endpoint_map[ep['endpoint']].append(ep['method'])

        for call in self.api_calls:
            endpoint = call['endpoint']
            method = call['method'].upper()

            # 处理模板字符串
            if call.get('template'):
                # 简单的模板变量替换检查
                if '${' in endpoint:
                    template_endpoint = re.sub(r'\$\{[^}]+\}', '{id}', endpoint)
                    endpoint = template_endpoint
                elif '{' in endpoint:
                    # 已经是参数化的端点
                    pass

            # 检查端点是否存在
            found = False
            for backend_ep in backend_endpoint_map:
                if self._match_endpoint(endpoint, backend_ep):
                    if method in backend_endpoint_map[backend_ep]:
                        found = True
                        break

            if not found:
                self.issues.append({
                    'type': 'ENDPOINT_NOT_FOUND',
                    'severity': 'HIGH',
                    'file': call['file'],
                    'line': call['line'],
                    'method': method,
                    'endpoint': endpoint,
                    'message': f"API端点不存在: {method} {endpoint}"
                })

    def _match_endpoint(self, frontend_ep, backend_ep):
        """匹配端点，考虑路径参数"""
        # 简单匹配
        if frontend_ep == backend_ep:
            return True

        # 参数化匹配
        frontend_parts = frontend_ep.split('/')
        backend_parts = backend_ep.split('/')

        if len(frontend_parts) != len(backend_parts):
            return False

        for f_part, b_part in zip(frontend_parts, backend_parts):
            if f_part == b_part:
                continue
            elif b_part.startswith('{') and b_part.endswith('}'):
                continue
            elif f_part.startswith('${') or f_part.startswith('{'):
                continue
            else:
                return False

        return True

    def test_api_endpoints(self):
        """实际测试API端点可访问性"""
        print("🧪 测试API端点可访问性...")

        unique_endpoints = set()
        for call in self.api_calls:
            if not call.get('template'):  # 跳过模板字符串
                endpoint_key = (call['method'], call['endpoint'])
                unique_endpoints.add(endpoint_key)

        for method, endpoint in unique_endpoints:
            if len(unique_endpoints) > 10:  # 限制测试数量
                break

            full_url = urljoin(self.backend_url + "/api/v1", endpoint)

            try:
                if method.lower() == 'get':
                    response = requests.get(full_url, timeout=3)
                elif method.lower() == 'post':
                    response = requests.post(full_url, timeout=3)
                else:
                    continue

                if response.status_code == 404:
                    self.issues.append({
                        'type': 'API_404',
                        'severity': 'HIGH',
                        'endpoint': endpoint,
                        'method': method,
                        'message': f"API返回404: {method} {endpoint}"
                    })
                elif response.status_code >= 500:
                    self.issues.append({
                        'type': 'API_ERROR',
                        'severity': 'MEDIUM',
                        'endpoint': endpoint,
                        'method': method,
                        'message': f"API服务器错误: {method} {endpoint} -> {response.status_code}"
                    })

            except requests.exceptions.RequestException:
                self.issues.append({
                    'type': 'API_UNREACHABLE',
                    'severity': 'HIGH',
                    'endpoint': endpoint,
                    'method': method,
                    'message': f"API无法访问: {method} {endpoint}"
                })

    def check_common_issues(self):
        """检查常见问题模式"""
        print("🔍 检查常见问题...")

        for call in self.api_calls:
            # 检查可能的路径错误
            endpoint = call['endpoint']

            if 'scan-progress' in endpoint:
                self.issues.append({
                    'type': 'DEPRECATED_ENDPOINT',
                    'severity': 'HIGH',
                    'file': call['file'],
                    'line': call['line'],
                    'endpoint': endpoint,
                    'message': f"使用了已废弃的端点: {endpoint}",
                    'suggestion': "应该使用 /scan-tasks/{id} 和 /scan-tasks/{id}/logs"
                })

            if 'task_id' in call['raw_line'] and 'int' not in call['raw_line']:
                if '/tasks/' in endpoint:
                    self.issues.append({
                        'type': 'TYPE_MISMATCH',
                        'severity': 'MEDIUM',
                        'file': call['file'],
                        'line': call['line'],
                        'endpoint': endpoint,
                        'message': f"可能的类型不匹配: 合并任务API期望int类型ID",
                        'suggestion': "检查是否应该使用 scan-tasks API"
                    })

    def generate_report(self):
        """生成问题报告"""
        print("\n" + "="*60)
        print("📊 前端API问题检测报告")
        print("="*60)

        print(f"\n📈 统计信息:")
        print(f"  - 扫描到的API调用: {len(self.api_calls)}")
        print(f"  - 后端端点数量: {len(self.backend_endpoints)}")
        print(f"  - 发现的问题: {len(self.issues)}")

        if self.issues:
            severity_counts = defaultdict(int)
            for issue in self.issues:
                severity_counts[issue['severity']] += 1

            print(f"\n🚨 问题分布:")
            for severity, count in severity_counts.items():
                print(f"  - {severity}: {count}")

            print(f"\n📋 详细问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"\n{i}. {issue['type']} ({issue['severity']})")
                print(f"   📁 {issue.get('file', 'N/A')}:{issue.get('line', 'N/A')}")
                print(f"   💬 {issue['message']}")
                if 'suggestion' in issue:
                    print(f"   💡 建议: {issue['suggestion']}")
        else:
            print("\n✅ 未发现API相关问题！")

    def run_check(self):
        """运行完整检查"""
        self.scan_frontend_api_calls()
        self.get_backend_endpoints()
        self.validate_api_calls()
        self.check_common_issues()
        self.test_api_endpoints()
        self.generate_report()

if __name__ == "__main__":
    checker = FrontendAPIChecker()
    checker.run_check()