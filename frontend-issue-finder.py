#!/usr/bin/env python3
"""
前端实际问题精准检测工具
专注于真正影响用户体验的问题
"""

import re
import os
import requests
from pathlib import Path

class FrontendIssueFinder:
    def __init__(self):
        self.frontend_dir = "frontend/src"
        self.backend_url = "http://localhost:8000"
        self.real_issues = []

    def find_deprecated_api_calls(self):
        """查找已废弃的API调用"""
        print("🔍 查找已废弃的API调用...")

        deprecated_patterns = [
            r'scan-progress',  # 已废弃的扫描进度API
            r'/tables/scan-progress',  # 具体的废弃端点
        ]

        for root, dirs, files in os.walk(self.frontend_dir):
            for file in files:
                if file.endswith(('.vue', '.ts', '.js')):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()

                        for i, line in enumerate(lines, 1):
                            for pattern in deprecated_patterns:
                                if re.search(pattern, line):
                                    self.real_issues.append({
                                        'type': 'DEPRECATED_API',
                                        'severity': 'HIGH',
                                        'file': file_path,
                                        'line': i,
                                        'content': line.strip(),
                                        'issue': f"使用已废弃API: {pattern}"
                                    })

    def find_error_prone_patterns(self):
        """查找容易出错的代码模式"""
        print("🔍 查找错误模式...")

        error_patterns = [
            (r'task_id.*int', "任务ID类型可能不匹配"),
            (r'\.get\([\'"`]/[^/]', "可能缺少API版本前缀"),
            (r'api\.get.*\$\{.*\}.*logs', "日志API调用模式"),
        ]

        for root, dirs, files in os.walk(self.frontend_dir):
            for file in files:
                if file.endswith(('.vue', '.ts', '.js')):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()

                        for i, line in enumerate(lines, 1):
                            for pattern, description in error_patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    self.real_issues.append({
                                        'type': 'ERROR_PRONE_PATTERN',
                                        'severity': 'MEDIUM',
                                        'file': file_path,
                                        'line': i,
                                        'content': line.strip(),
                                        'issue': description
                                    })

    def find_console_errors(self):
        """查找可能导致控制台错误的代码"""
        print("🔍 查找控制台错误源...")

        console_error_patterns = [
            r'console\.error',
            r'ElMessage\.error',
            r'throw new Error',
        ]

        for root, dirs, files in os.walk(self.frontend_dir):
            for file in files:
                if file.endswith(('.vue', '.ts', '.js')):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()

                        for i, line in enumerate(lines, 1):
                            for pattern in console_error_patterns:
                                if re.search(pattern, line):
                                    # 检查是否是错误处理
                                    context_lines = lines[max(0, i-3):i+2]
                                    context = ''.join(context_lines)

                                    if 'catch' in context or 'error' in context.lower():
                                        continue  # 跳过正常的错误处理

                                    self.real_issues.append({
                                        'type': 'CONSOLE_ERROR',
                                        'severity': 'LOW',
                                        'file': file_path,
                                        'line': i,
                                        'content': line.strip(),
                                        'issue': "可能的控制台错误"
                                    })

    def find_missing_error_handling(self):
        """查找缺少错误处理的API调用"""
        print("🔍 查找缺少错误处理的API调用...")

        for root, dirs, files in os.walk(self.frontend_dir):
            for file in files:
                if file.endswith(('.vue', '.ts', '.js')):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')

                        for i, line in enumerate(lines):
                            if re.search(r'api\.(get|post|put|delete)', line):
                                # 检查接下来的几行是否有错误处理
                                next_lines = lines[i:i+10]
                                has_catch = any('catch' in line for line in next_lines)
                                has_try = any('try' in line for line in lines[max(0, i-5):i])

                                if not has_catch and not has_try:
                                    self.real_issues.append({
                                        'type': 'MISSING_ERROR_HANDLING',
                                        'severity': 'MEDIUM',
                                        'file': file_path,
                                        'line': i + 1,
                                        'content': line.strip(),
                                        'issue': "API调用可能缺少错误处理"
                                    })

    def test_critical_user_flows(self):
        """测试关键用户流程的API"""
        print("🧪 测试关键用户流程...")

        critical_flows = [
            ("GET", "/api/v1/scan-tasks/", "扫描任务列表加载"),
            ("GET", "/api/v1/clusters/", "集群列表加载"),
            ("GET", "/api/v1/dashboard/summary", "仪表板数据加载"),
            ("GET", "/api/v1/tasks/", "任务列表加载"),
        ]

        for method, endpoint, description in critical_flows:
            try:
                response = requests.get(f"{self.backend_url}{endpoint}", timeout=5)
                if response.status_code >= 400:
                    self.real_issues.append({
                        'type': 'CRITICAL_API_FAILURE',
                        'severity': 'HIGH',
                        'endpoint': endpoint,
                        'status_code': response.status_code,
                        'issue': f"关键用户流程失败: {description}",
                        'impact': "直接影响用户体验"
                    })
            except Exception as e:
                self.real_issues.append({
                    'type': 'API_CONNECTION_FAILURE',
                    'severity': 'HIGH',
                    'endpoint': endpoint,
                    'error': str(e),
                    'issue': f"API连接失败: {description}",
                    'impact': "用户功能不可用"
                })

    def generate_actionable_report(self):
        """生成可操作的问题报告"""
        print("\n" + "="*60)
        print("🎯 前端实际问题报告 - 专注用户体验影响")
        print("="*60)

        if not self.real_issues:
            print("✅ 未发现影响用户体验的关键问题！")
            return

        # 按严重程度分组
        high_issues = [i for i in self.real_issues if i['severity'] == 'HIGH']
        medium_issues = [i for i in self.real_issues if i['severity'] == 'MEDIUM']
        low_issues = [i for i in self.real_issues if i['severity'] == 'LOW']

        print(f"📊 问题统计:")
        print(f"  🔴 高优先级 (需立即修复): {len(high_issues)}")
        print(f"  🟡 中优先级 (建议修复): {len(medium_issues)}")
        print(f"  🟢 低优先级 (可选修复): {len(low_issues)}")

        if high_issues:
            print(f"\n🔴 高优先级问题 (影响功能):")
            for i, issue in enumerate(high_issues, 1):
                print(f"\n{i}. {issue['type']}")
                if 'file' in issue:
                    print(f"   📁 {issue['file']}:{issue['line']}")
                    print(f"   📝 {issue['content']}")
                print(f"   ❗ {issue['issue']}")
                if 'impact' in issue:
                    print(f"   💥 影响: {issue['impact']}")

        if medium_issues:
            print(f"\n🟡 中优先级问题 (建议修复):")
            for i, issue in enumerate(medium_issues[:5], 1):  # 只显示前5个
                print(f"\n{i}. {issue['type']}")
                if 'file' in issue:
                    print(f"   📁 {issue['file']}:{issue['line']}")
                print(f"   💬 {issue['issue']}")

        print(f"\n💡 修复建议:")
        print(f"1. 优先处理高优先级问题，直接影响用户功能")
        print(f"2. 移除已废弃的API调用")
        print(f"3. 增强错误处理机制")
        print(f"4. 监控关键用户流程的API稳定性")

    def run_analysis(self):
        """运行完整分析"""
        print("🚀 开始前端实际问题分析...")

        self.find_deprecated_api_calls()
        self.find_error_prone_patterns()
        self.test_critical_user_flows()
        self.find_missing_error_handling()

        self.generate_actionable_report()

if __name__ == "__main__":
    finder = FrontendIssueFinder()
    finder.run_analysis()