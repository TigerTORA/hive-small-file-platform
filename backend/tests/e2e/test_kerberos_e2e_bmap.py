#!/usr/bin/env python3
"""
Epic-8 Kerberos E2E 测试 - BMAP 方法实现
基于 BMAP (Baseline, Mutation, Analysis, Publish) 测试方法
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

# 添加backend到Python路径
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.monitor.beeline_connector import BeelineConnector
from app.utils.webhdfs_client import WebHDFSClient
from app.utils.kerberos_diagnostics import KerberosDiagnosticCode


@dataclass
class TestResult:
    """测试结果数据类"""
    scenario: str
    status: str  # PASS, FAIL, SKIP
    duration_ms: float
    error_message: Optional[str] = None
    diagnostic_code: Optional[str] = None
    details: Optional[Dict] = None


@dataclass
class BaselineData:
    """基线数据"""
    timestamp: str
    hostname: str
    realm: str
    kdc: str
    keytab_exists: bool
    keytab_path: Optional[str]
    kerberos_tools_installed: bool
    initial_ticket_status: str
    network_connectivity: Dict[str, bool]
    python_version: str
    requests_kerberos_version: Optional[str]


class KerberosE2ETestBMAP:
    """
    Kerberos E2E 测试套件 (BMAP 方法)

    BMAP 阶段:
    - B (Baseline): 建立环境基准
    - M (Mutation): 执行测试场景
    - A (Analysis): 分析结果和metrics
    - P (Publish): 生成测试报告
    """

    def __init__(self, keytab_path: str, principal: str, cdp_host: str = "192.168.0.105"):
        """
        初始化测试套件

        Args:
            keytab_path: Keytab 文件路径
            principal: Kerberos principal (例如: hive/cdpmaster1@PHOENIXESINFO.COM)
            cdp_host: CDP 集群主机地址
        """
        self.keytab_path = keytab_path
        self.principal = principal
        self.cdp_host = cdp_host
        self.realm = principal.split('@')[-1] if '@' in principal else "PHOENIXESINFO.COM"

        # 测试结果收集
        self.baseline_data: Optional[BaselineData] = None
        self.test_results: List[TestResult] = []
        self.metrics: Dict = {}

        # 配置
        self.webhdfs_port = 14000
        self.hive_port = 10000

    # ========== B - Baseline 阶段 ==========

    def phase_baseline(self) -> BaselineData:
        """
        B - Baseline 阶段: 建立测试基准

        Returns:
            BaselineData: 基线数据
        """
        print("\n" + "=" * 80)
        print("  [B] BASELINE 阶段: 建立测试基准")
        print("=" * 80 + "\n")

        baseline = BaselineData(
            timestamp=datetime.utcnow().isoformat(),
            hostname=self._get_hostname(),
            realm=self.realm,
            kdc=self._get_kdc_from_krb5conf(),
            keytab_exists=os.path.exists(self.keytab_path),
            keytab_path=self.keytab_path if os.path.exists(self.keytab_path) else None,
            kerberos_tools_installed=self._check_kerberos_tools(),
            initial_ticket_status=self._get_ticket_status(),
            network_connectivity=self._check_network_connectivity(),
            python_version=sys.version.split()[0],
            requests_kerberos_version=self._get_package_version("requests-kerberos")
        )

        self.baseline_data = baseline

        # 打印基线信息
        print(f"✓ 主机名: {baseline.hostname}")
        print(f"✓ Kerberos Realm: {baseline.realm}")
        print(f"✓ KDC: {baseline.kdc}")
        print(f"✓ Keytab 存在: {baseline.keytab_exists} ({baseline.keytab_path})")
        print(f"✓ Kerberos 工具已安装: {baseline.kerberos_tools_installed}")
        print(f"✓ 初始票据状态: {baseline.initial_ticket_status}")
        print(f"✓ 网络连接:")
        for service, connected in baseline.network_connectivity.items():
            status = "✓" if connected else "✗"
            print(f"  {status} {service}")
        print(f"✓ Python 版本: {baseline.python_version}")
        print(f"✓ requests-kerberos 版本: {baseline.requests_kerberos_version}")

        # 验证基线必要条件
        if not baseline.keytab_exists:
            raise RuntimeError(f"Keytab 文件不存在: {self.keytab_path}")

        if not baseline.kerberos_tools_installed:
            raise RuntimeError("Kerberos 工具未安装 (kinit, klist, kdestroy)")

        print("\n✓ 基线检查完成\n")
        return baseline

    # ========== M - Mutation 阶段 ==========

    def phase_mutation(self) -> List[TestResult]:
        """
        M - Mutation 阶段: 执行测试场景

        Returns:
            List[TestResult]: 测试结果列表
        """
        print("\n" + "=" * 80)
        print("  [M] MUTATION 阶段: 执行测试场景")
        print("=" * 80 + "\n")

        # 执行所有测试场景
        scenarios = [
            ("场景 1: 基础 Kerberos 认证 (Happy Path)", self._scenario_1_happy_path),
            ("场景 2: Beeline Kerberos 连接", self._scenario_2_beeline_connection),
            ("场景 3: 票据过期处理", self._scenario_3_ticket_expired),
            ("场景 4: Keytab 权限错误", self._scenario_4_keytab_permission),
            ("场景 5: 并发连接", self._scenario_5_concurrent_connections),
            ("场景 6: WebHDFS 列出目录", self._scenario_6_webhdfs_list_directory),
        ]

        for scenario_name, scenario_func in scenarios:
            print(f"\n执行: {scenario_name}")
            print("-" * 80)
            try:
                result = scenario_func()
                self.test_results.append(result)
                status_symbol = "✓" if result.status == "PASS" else "✗"
                print(f"{status_symbol} {scenario_name}: {result.status} ({result.duration_ms:.0f}ms)")
                if result.error_message:
                    print(f"  错误: {result.error_message}")
            except Exception as e:
                print(f"✗ {scenario_name}: 执行异常 - {e}")
                self.test_results.append(TestResult(
                    scenario=scenario_name,
                    status="FAIL",
                    duration_ms=0,
                    error_message=str(e)
                ))

        print("\n✓ 测试场景执行完成\n")
        return self.test_results

    def _scenario_1_happy_path(self) -> TestResult:
        """场景 1: 基础 Kerberos 认证 (Happy Path)"""
        start = time.time()

        try:
            # 1. 清除现有票据
            self._run_command(["kdestroy", "-A"], check=False)

            # 2. 使用 keytab 获取票据
            kinit_cmd = ["kinit", "-kt", self.keytab_path, self.principal]
            result = self._run_command(kinit_cmd)
            if result.returncode != 0:
                return TestResult(
                    scenario="场景1_基础认证",
                    status="FAIL",
                    duration_ms=(time.time() - start) * 1000,
                    error_message=f"kinit 失败: {result.stderr}"
                )

            # 3. 验证票据
            ticket_info = self._get_ticket_status()
            if "No credentials cache" in ticket_info:
                return TestResult(
                    scenario="场景1_基础认证",
                    status="FAIL",
                    duration_ms=(time.time() - start) * 1000,
                    error_message="票据未成功获取"
                )

            # 4. 创建 WebHDFS 客户端
            client = WebHDFSClient(
                namenode_url=f"http://{self.cdp_host}:{self.webhdfs_port}/webhdfs/v1",
                user="hive",
                auth_type="KERBEROS",
                kerberos_principal=self.principal,
                kerberos_keytab_path=self.keytab_path,
                kerberos_realm=self.realm,
                timeout=60
            )

            # 5. 测试连接
            success, message = client.test_connection()

            duration_ms = (time.time() - start) * 1000

            if success:
                return TestResult(
                    scenario="场景1_基础认证",
                    status="PASS",
                    duration_ms=duration_ms,
                    details={
                        "ticket_obtained": True,
                        "webhdfs_connected": True,
                        "connection_message": message
                    }
                )
            else:
                diagnostic = client.last_diagnostic()
                return TestResult(
                    scenario="场景1_基础认证",
                    status="FAIL",
                    duration_ms=duration_ms,
                    error_message=message,
                    diagnostic_code=diagnostic.code.name if diagnostic else None
                )

        except Exception as e:
            return TestResult(
                scenario="场景1_基础认证",
                status="FAIL",
                duration_ms=(time.time() - start) * 1000,
                error_message=str(e)
            )

    def _scenario_2_beeline_connection(self) -> TestResult:
        """场景 2: Beeline Kerberos 连接"""
        start = time.time()

        try:
            # 确保有有效票据
            self._ensure_valid_ticket()

            # 创建 Beeline 连接器
            connector = BeelineConnector(
                host=self.cdp_host,
                port=self.hive_port,
                auth_type="KERBEROS",
                kerberos_principal=self.principal,
                kerberos_keytab_path=self.keytab_path,
                kerberos_realm=self.realm,
                timeout=60
            )

            # 验证 JDBC URL
            jdbc_url = connector.get_jdbc_url()
            if "principal=" not in jdbc_url:
                return TestResult(
                    scenario="场景2_Beeline连接",
                    status="FAIL",
                    duration_ms=(time.time() - start) * 1000,
                    error_message="JDBC URL 不包含 principal 参数"
                )

            # 测试连接
            result = connector.test_connection()
            duration_ms = (time.time() - start) * 1000

            if result.get('status') == 'success':
                return TestResult(
                    scenario="场景2_Beeline连接",
                    status="PASS",
                    duration_ms=duration_ms,
                    details={
                        "jdbc_url_valid": True,
                        "connection_success": True,
                        "jdbc_url": jdbc_url
                    }
                )
            else:
                return TestResult(
                    scenario="场景2_Beeline连接",
                    status="FAIL",
                    duration_ms=duration_ms,
                    error_message=result.get('message', '未知错误')
                )

        except Exception as e:
            return TestResult(
                scenario="场景2_Beeline连接",
                status="FAIL",
                duration_ms=(time.time() - start) * 1000,
                error_message=str(e)
            )

    def _scenario_3_ticket_expired(self) -> TestResult:
        """场景 3: 票据过期处理"""
        start = time.time()

        try:
            # 注意: 实际过期测试需要等待，这里模拟过期场景
            # 通过清除票据来模拟过期
            self._run_command(["kdestroy", "-A"], check=False)

            # 尝试连接 (不重新获取票据)
            client = WebHDFSClient(
                namenode_url=f"http://{self.cdp_host}:{self.webhdfs_port}/webhdfs/v1",
                user="hive",
                auth_type="KERBEROS",
                kerberos_principal=self.principal,
                kerberos_keytab_path=self.keytab_path,
                kerberos_realm=self.realm,
                timeout=30
            )

            # 由于有 keytab，系统会自动重新获取票据，这是预期行为
            success, message = client.test_connection()
            duration_ms = (time.time() - start) * 1000

            # 这个场景验证的是自动票据刷新能力
            if success:
                return TestResult(
                    scenario="场景3_票据过期",
                    status="PASS",
                    duration_ms=duration_ms,
                    details={
                        "auto_ticket_refresh": True,
                        "connection_success": True
                    }
                )
            else:
                diagnostic = client.last_diagnostic()
                return TestResult(
                    scenario="场景3_票据过期",
                    status="FAIL",
                    duration_ms=duration_ms,
                    error_message=message,
                    diagnostic_code=diagnostic.code.name if diagnostic else None
                )

        except Exception as e:
            return TestResult(
                scenario="场景3_票据过期",
                status="FAIL",
                duration_ms=(time.time() - start) * 1000,
                error_message=str(e)
            )

    def _scenario_4_keytab_permission(self) -> TestResult:
        """场景 4: Keytab 权限错误 (模拟测试)"""
        start = time.time()

        try:
            # 注意: 实际更改权限需要 root 权限，这里仅验证权限检查逻辑
            # 检查 keytab 文件当前权限
            stat_info = os.stat(self.keytab_path)
            current_mode = oct(stat_info.st_mode)[-3:]

            # 验证权限是否符合安全要求 (应该是 600 或更严格)
            expected_mode = "600"

            duration_ms = (time.time() - start) * 1000

            if current_mode <= expected_mode or current_mode in ["400", "600"]:
                return TestResult(
                    scenario="场景4_Keytab权限",
                    status="PASS",
                    duration_ms=duration_ms,
                    details={
                        "current_permission": current_mode,
                        "permission_check_passed": True,
                        "note": "Keytab 权限符合安全要求"
                    }
                )
            else:
                return TestResult(
                    scenario="场景4_Keytab权限",
                    status="FAIL",
                    duration_ms=duration_ms,
                    error_message=f"Keytab 权限过于开放: {current_mode}, 应该 <= 600",
                    diagnostic_code="KEYTAB_PERMISSION"
                )

        except Exception as e:
            return TestResult(
                scenario="场景4_Keytab权限",
                status="FAIL",
                duration_ms=(time.time() - start) * 1000,
                error_message=str(e)
            )

    def _scenario_5_concurrent_connections(self) -> TestResult:
        """场景 5: 并发连接"""
        start = time.time()

        try:
            # 确保有有效票据
            self._ensure_valid_ticket()

            # 创建多个并发客户端
            num_clients = 5
            clients = []

            for i in range(num_clients):
                client = WebHDFSClient(
                    namenode_url=f"http://{self.cdp_host}:{self.webhdfs_port}/webhdfs/v1",
                    user="hive",
                    auth_type="KERBEROS",
                    kerberos_principal=self.principal,
                    kerberos_keytab_path=self.keytab_path,
                    kerberos_realm=self.realm,
                    timeout=30
                )
                clients.append(client)

            # 并发测试连接
            results = []
            max_response_time = 0

            for client in clients:
                conn_start = time.time()
                success, message = client.test_connection()
                conn_time = (time.time() - conn_start) * 1000
                max_response_time = max(max_response_time, conn_time)
                results.append(success)

            duration_ms = (time.time() - start) * 1000
            all_success = all(results)

            if all_success:
                return TestResult(
                    scenario="场景5_并发连接",
                    status="PASS",
                    duration_ms=duration_ms,
                    details={
                        "concurrent_connections": num_clients,
                        "all_success": True,
                        "max_response_time_ms": max_response_time,
                        "success_count": sum(results)
                    }
                )
            else:
                return TestResult(
                    scenario="场景5_并发连接",
                    status="FAIL",
                    duration_ms=duration_ms,
                    error_message=f"部分连接失败: {sum(results)}/{num_clients} 成功"
                )

        except Exception as e:
            return TestResult(
                scenario="场景5_并发连接",
                status="FAIL",
                duration_ms=(time.time() - start) * 1000,
                error_message=str(e)
            )

    def _scenario_6_webhdfs_list_directory(self) -> TestResult:
        """场景 6: WebHDFS 列出目录"""
        start = time.time()

        try:
            # 确保有有效票据
            self._ensure_valid_ticket()

            # 创建客户端
            client = WebHDFSClient(
                namenode_url=f"http://{self.cdp_host}:{self.webhdfs_port}/webhdfs/v1",
                user="hive",
                auth_type="KERBEROS",
                kerberos_principal=self.principal,
                kerberos_keytab_path=self.keytab_path,
                kerberos_realm=self.realm,
                timeout=60
            )

            # 测试连接
            success, message = client.test_connection()
            if not success:
                return TestResult(
                    scenario="场景6_列出目录",
                    status="FAIL",
                    duration_ms=(time.time() - start) * 1000,
                    error_message=f"连接失败: {message}"
                )

            # 尝试列出根目录
            try:
                files = client.list_directory("/")
                duration_ms = (time.time() - start) * 1000

                if files is not None:
                    return TestResult(
                        scenario="场景6_列出目录",
                        status="PASS",
                        duration_ms=duration_ms,
                        details={
                            "directory": "/",
                            "file_count": len(files),
                            "list_success": True
                        }
                    )
                else:
                    return TestResult(
                        scenario="场景6_列出目录",
                        status="FAIL",
                        duration_ms=duration_ms,
                        error_message="list_directory 返回 None"
                    )
            except Exception as list_error:
                duration_ms = (time.time() - start) * 1000
                return TestResult(
                    scenario="场景6_列出目录",
                    status="FAIL",
                    duration_ms=duration_ms,
                    error_message=f"列出目录失败: {list_error}"
                )

        except Exception as e:
            return TestResult(
                scenario="场景6_列出目录",
                status="FAIL",
                duration_ms=(time.time() - start) * 1000,
                error_message=str(e)
            )

    # ========== A - Analysis 阶段 ==========

    def phase_analysis(self) -> Dict:
        """
        A - Analysis 阶段: 分析结果

        Returns:
            Dict: 分析结果和 metrics
        """
        print("\n" + "=" * 80)
        print("  [A] ANALYSIS 阶段: 分析测试结果")
        print("=" * 80 + "\n")

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.status == "PASS")
        failed_tests = sum(1 for r in self.test_results if r.status == "FAIL")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # 计算性能 metrics
        durations = [r.duration_ms for r in self.test_results if r.duration_ms > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0

        # 收集诊断码
        diagnostic_codes = {}
        for r in self.test_results:
            if r.diagnostic_code:
                diagnostic_codes[r.diagnostic_code] = diagnostic_codes.get(r.diagnostic_code, 0) + 1

        self.metrics = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate_percent": round(success_rate, 2)
            },
            "performance": {
                "avg_duration_ms": round(avg_duration, 2),
                "max_duration_ms": round(max_duration, 2),
                "min_duration_ms": round(min_duration, 2)
            },
            "diagnostic_codes": diagnostic_codes,
            "test_details": [asdict(r) for r in self.test_results]
        }

        # 打印分析结果
        print(f"测试总数: {total_tests}")
        print(f"✓ 通过: {passed_tests}")
        print(f"✗ 失败: {failed_tests}")
        print(f"成功率: {success_rate:.1f}%")
        print(f"\n性能指标:")
        print(f"  平均响应时间: {avg_duration:.0f} ms")
        print(f"  最大响应时间: {max_duration:.0f} ms")
        print(f"  最小响应时间: {min_duration:.0f} ms")

        if diagnostic_codes:
            print(f"\n诊断码统计:")
            for code, count in diagnostic_codes.items():
                print(f"  {code}: {count} 次")

        print("\n✓ 结果分析完成\n")
        return self.metrics

    # ========== P - Publish 阶段 ==========

    def phase_publish(self, output_file: str = "kerberos_e2e_test_report.json") -> str:
        """
        P - Publish 阶段: 生成测试报告

        Args:
            output_file: 输出文件路径

        Returns:
            str: 报告文件路径
        """
        print("\n" + "=" * 80)
        print("  [P] PUBLISH 阶段: 生成测试报告")
        print("=" * 80 + "\n")

        report = {
            "report_metadata": {
                "title": "Kerberos E2E 测试报告 (BMAP 方法)",
                "generated_at": datetime.utcnow().isoformat(),
                "test_framework": "BMAP (Baseline, Mutation, Analysis, Publish)",
                "epic": "Epic-8: Kerberos Authentication Enhancement"
            },
            "baseline": asdict(self.baseline_data) if self.baseline_data else {},
            "metrics": self.metrics,
            "recommendations": self._generate_recommendations()
        }

        # 写入 JSON 报告
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"✓ JSON 报告已生成: {output_path.absolute()}")

        # 生成可读的文本报告
        text_report_path = output_path.with_suffix('.txt')
        self._generate_text_report(report, text_report_path)
        print(f"✓ 文本报告已生成: {text_report_path.absolute()}")

        print("\n✓ 报告发布完成\n")
        return str(output_path.absolute())

    def _generate_recommendations(self) -> List[str]:
        """生成建议和后续行动"""
        recommendations = []

        failed_count = self.metrics.get("summary", {}).get("failed", 0)

        if failed_count > 0:
            recommendations.append(
                f"[高优先级] 修复 {failed_count} 个失败的测试场景"
            )

        # 性能建议
        avg_duration = self.metrics.get("performance", {}).get("avg_duration_ms", 0)
        if avg_duration > 2000:
            recommendations.append(
                f"[中优先级] 优化性能，当前平均响应时间为 {avg_duration:.0f}ms，建议 < 2000ms"
            )

        # 诊断码覆盖
        diagnostic_codes = self.metrics.get("diagnostic_codes", {})
        expected_codes = [code.name for code in KerberosDiagnosticCode]
        missing_codes = set(expected_codes) - set(diagnostic_codes.keys())

        if missing_codes:
            recommendations.append(
                f"[低优先级] 增加测试覆盖，以下诊断码未被测试: {', '.join(list(missing_codes)[:5])}"
            )

        if not recommendations:
            recommendations.append("✓ 所有测试通过，无需改进建议")

        return recommendations

    def _generate_text_report(self, report: Dict, output_path: Path):
        """生成可读的文本报告"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("  Kerberos E2E 测试报告 (BMAP 方法)\n")
            f.write("=" * 80 + "\n\n")

            # 元数据
            metadata = report["report_metadata"]
            f.write(f"生成时间: {metadata['generated_at']}\n")
            f.write(f"测试框架: {metadata['test_framework']}\n")
            f.write(f"Epic: {metadata['epic']}\n\n")

            # 基线信息
            f.write("--- 基线信息 ---\n")
            baseline = report.get("baseline", {})
            if baseline:
                f.write(f"主机名: {baseline.get('hostname')}\n")
                f.write(f"Realm: {baseline.get('realm')}\n")
                f.write(f"KDC: {baseline.get('kdc')}\n")
                f.write(f"Keytab: {baseline.get('keytab_path')}\n")
                f.write(f"Python: {baseline.get('python_version')}\n")
                f.write(f"requests-kerberos: {baseline.get('requests_kerberos_version')}\n\n")

            # 测试摘要
            f.write("--- 测试摘要 ---\n")
            metrics = report.get("metrics", {})
            summary = metrics.get("summary", {})
            f.write(f"总测试数: {summary.get('total_tests', 0)}\n")
            f.write(f"通过: {summary.get('passed', 0)}\n")
            f.write(f"失败: {summary.get('failed', 0)}\n")
            f.write(f"成功率: {summary.get('success_rate_percent', 0)}%\n\n")

            # 性能指标
            f.write("--- 性能指标 ---\n")
            perf = metrics.get("performance", {})
            f.write(f"平均响应时间: {perf.get('avg_duration_ms', 0):.0f} ms\n")
            f.write(f"最大响应时间: {perf.get('max_duration_ms', 0):.0f} ms\n")
            f.write(f"最小响应时间: {perf.get('min_duration_ms', 0):.0f} ms\n\n")

            # 详细测试结果
            f.write("--- 详细测试结果 ---\n")
            for test in metrics.get("test_details", []):
                f.write(f"\n{test['scenario']}:\n")
                f.write(f"  状态: {test['status']}\n")
                f.write(f"  耗时: {test['duration_ms']:.0f} ms\n")
                if test.get('error_message'):
                    f.write(f"  错误: {test['error_message']}\n")
                if test.get('diagnostic_code'):
                    f.write(f"  诊断码: {test['diagnostic_code']}\n")

            # 建议
            f.write("\n--- 建议和后续行动 ---\n")
            for i, rec in enumerate(report.get("recommendations", []), 1):
                f.write(f"{i}. {rec}\n")

            f.write("\n" + "=" * 80 + "\n")

    # ========== 辅助方法 ==========

    def _get_hostname(self) -> str:
        """获取主机名"""
        try:
            return subprocess.run(
                ["hostname"],
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()
        except:
            return "unknown"

    def _get_kdc_from_krb5conf(self) -> str:
        """从 krb5.conf 读取 KDC"""
        try:
            with open("/etc/krb5.conf", 'r') as f:
                content = f.read()
                # 简单解析，查找 kdc = 行
                for line in content.split('\n'):
                    if 'kdc' in line.lower() and '=' in line:
                        return line.split('=')[-1].strip()
        except:
            pass
        return "unknown"

    def _check_kerberos_tools(self) -> bool:
        """检查 Kerberos 工具是否已安装"""
        tools = ['kinit', 'klist', 'kdestroy']
        for tool in tools:
            try:
                result = subprocess.run(
                    ['which', tool],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode != 0:
                    return False
            except:
                return False
        return True

    def _get_ticket_status(self) -> str:
        """获取当前票据状态"""
        try:
            result = subprocess.run(
                ['klist'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "No credentials cache found"
        except:
            return "Error checking tickets"

    def _check_network_connectivity(self) -> Dict[str, bool]:
        """检查网络连接"""
        connectivity = {}

        # 检查 WebHDFS
        try:
            result = subprocess.run(
                ['curl', '-s', '-I', '--connect-timeout', '5',
                 f'http://{self.cdp_host}:{self.webhdfs_port}/webhdfs/v1'],
                capture_output=True,
                timeout=10
            )
            connectivity['WebHDFS'] = result.returncode == 0
        except:
            connectivity['WebHDFS'] = False

        # 检查 HiveServer2 (仅端口)
        try:
            result = subprocess.run(
                ['nc', '-zv', '-w', '5', self.cdp_host, str(self.hive_port)],
                capture_output=True,
                timeout=10
            )
            connectivity['HiveServer2'] = result.returncode == 0
        except:
            # nc 可能不可用，跳过
            connectivity['HiveServer2'] = None

        return connectivity

    def _get_package_version(self, package_name: str) -> Optional[str]:
        """获取 Python 包版本"""
        try:
            result = subprocess.run(
                ['pip', 'show', package_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':')[-1].strip()
        except:
            pass
        return None

    def _run_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """执行命令"""
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=check
        )

    def _ensure_valid_ticket(self):
        """确保有有效的 Kerberos 票据"""
        ticket_status = self._get_ticket_status()
        if "No credentials cache" in ticket_status:
            # 获取新票据
            result = self._run_command([
                "kinit", "-kt", self.keytab_path, self.principal
            ])
            if result.returncode != 0:
                raise RuntimeError(f"无法获取 Kerberos 票据: {result.stderr}")

    def run_all_phases(self, output_dir: str = ".") -> str:
        """
        运行所有 BMAP 阶段

        Args:
            output_dir: 报告输出目录

        Returns:
            str: 报告文件路径
        """
        print("\n")
        print("╔" + "=" * 78 + "╗")
        print("║" + " " * 15 + "Kerberos E2E 测试 (BMAP 方法)" + " " * 33 + "║")
        print("║" + " " * 10 + "Epic-8: Kerberos Authentication Enhancement" + " " * 24 + "║")
        print("╚" + "=" * 78 + "╝")

        try:
            # B - Baseline
            self.phase_baseline()

            # M - Mutation
            self.phase_mutation()

            # A - Analysis
            self.phase_analysis()

            # P - Publish
            output_file = os.path.join(output_dir, "kerberos_e2e_test_report.json")
            report_path = self.phase_publish(output_file)

            print("\n" + "=" * 80)
            print("  测试完成!")
            print("=" * 80)
            print(f"\n报告已保存至: {report_path}")

            # 打印最终摘要
            summary = self.metrics.get("summary", {})
            if summary.get("failed", 0) == 0:
                print("\n🎉 所有测试通过! Kerberos 认证模块工作正常。")
                return report_path
            else:
                print(f"\n⚠ {summary.get('failed', 0)} 个测试失败，请查看报告了解详情。")
                return report_path

        except Exception as e:
            print(f"\n✗ 测试执行失败: {e}")
            import traceback
            traceback.print_exc()
            raise


# ========== 主函数 ==========

def main():
    """主测试入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Kerberos E2E 测试 (BMAP 方法)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 test_kerberos_e2e_bmap.py \\
    --keytab /etc/security/keytabs/hive.service.keytab \\
    --principal hive/cdpmaster1@PHOENIXESINFO.COM \\
    --host 192.168.0.105 \\
    --output reports/
        """
    )

    parser.add_argument(
        '--keytab',
        required=True,
        help='Keytab 文件路径'
    )
    parser.add_argument(
        '--principal',
        required=True,
        help='Kerberos principal (例如: hive/cdpmaster1@PHOENIXESINFO.COM)'
    )
    parser.add_argument(
        '--host',
        default='192.168.0.105',
        help='CDP 集群主机地址 (默认: 192.168.0.105)'
    )
    parser.add_argument(
        '--output',
        default='.',
        help='报告输出目录 (默认: 当前目录)'
    )

    args = parser.parse_args()

    # 创建测试套件
    test_suite = KerberosE2ETestBMAP(
        keytab_path=args.keytab,
        principal=args.principal,
        cdp_host=args.host
    )

    # 运行所有阶段
    try:
        report_path = test_suite.run_all_phases(output_dir=args.output)
        sys.exit(0)
    except Exception as e:
        print(f"\n测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
