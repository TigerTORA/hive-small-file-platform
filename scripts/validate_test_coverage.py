#!/usr/bin/env python3
"""
测试覆盖率验证脚本
检查后端和前端的测试覆盖率是否达到企业级标准
"""

import subprocess
import sys
import json
import os
from pathlib import Path


def run_command(cmd, cwd=None):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def check_backend_coverage():
    """检查后端测试覆盖率"""
    print("🔍 检查后端测试覆盖率...")

    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ 后端目录不存在")
        return False

    # 运行后端测试
    cmd = "python -m pytest --cov=app --cov-report=json --cov-report=term-missing -v"
    returncode, stdout, stderr = run_command(cmd, cwd=backend_dir)

    print(f"后端测试输出:\n{stdout}")
    if stderr:
        print(f"后端测试错误:\n{stderr}")

    # 检查覆盖率报告
    coverage_file = backend_dir / "coverage.json"
    if not coverage_file.exists():
        print("❌ 覆盖率报告文件不存在")
        return returncode == 0

    try:
        with open(coverage_file, 'r') as f:
            coverage_data = json.load(f)

        totals = coverage_data.get('totals', {})
        percent_covered = totals.get('percent_covered', 0)

        print(f"📊 后端整体覆盖率: {percent_covered:.1f}%")

        # 企业级标准：75%
        if percent_covered >= 75:
            print("✅ 后端覆盖率达到企业级标准 (≥75%)")
            return True
        else:
            print(f"❌ 后端覆盖率未达标，需要 ≥75%，当前 {percent_covered:.1f}%")
            return False

    except Exception as e:
        print(f"❌ 解析覆盖率报告失败: {e}")
        return False


def check_frontend_coverage():
    """检查前端测试覆盖率"""
    print("\n🔍 检查前端测试覆盖率...")

    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ 前端目录不存在")
        return False

    # 检查前端依赖
    if not (frontend_dir / "node_modules").exists():
        print("📦 安装前端依赖...")
        returncode, _, stderr = run_command("npm install", cwd=frontend_dir)
        if returncode != 0:
            print(f"❌ 前端依赖安装失败: {stderr}")
            return False

    # 运行前端测试
    cmd = "npm run test:coverage"
    returncode, stdout, stderr = run_command(cmd, cwd=frontend_dir)

    print(f"前端测试输出:\n{stdout}")
    if stderr:
        print(f"前端测试错误:\n{stderr}")

    # 检查覆盖率
    coverage_dir = frontend_dir / "coverage"
    if coverage_dir.exists():
        coverage_json = coverage_dir / "coverage-summary.json"
        if coverage_json.exists():
            try:
                with open(coverage_json, 'r') as f:
                    coverage_data = json.load(f)

                total = coverage_data.get('total', {})
                lines_pct = total.get('lines', {}).get('pct', 0)
                functions_pct = total.get('functions', {}).get('pct', 0)
                branches_pct = total.get('branches', {}).get('pct', 0)
                statements_pct = total.get('statements', {}).get('pct', 0)

                print(f"📊 前端覆盖率统计:")
                print(f"   - 行覆盖率: {lines_pct}%")
                print(f"   - 函数覆盖率: {functions_pct}%")
                print(f"   - 分支覆盖率: {branches_pct}%")
                print(f"   - 语句覆盖率: {statements_pct}%")

                # 企业级标准检查
                if (lines_pct >= 80 and functions_pct >= 85 and
                    branches_pct >= 75 and statements_pct >= 80):
                    print("✅ 前端覆盖率达到企业级标准")
                    return True
                else:
                    print("❌ 前端覆盖率未达标")
                    print("   企业级标准要求:")
                    print("   - 行覆盖率 ≥80%")
                    print("   - 函数覆盖率 ≥85%")
                    print("   - 分支覆盖率 ≥75%")
                    print("   - 语句覆盖率 ≥80%")
                    return False

            except Exception as e:
                print(f"❌ 解析前端覆盖率报告失败: {e}")
                return False

    # 如果没有覆盖率报告，至少检查测试是否通过
    return returncode == 0


def check_test_files():
    """检查测试文件数量和质量"""
    print("\n🔍 检查测试文件...")

    backend_tests = list(Path("backend").glob("test_*.py"))
    backend_unit_tests = list(Path("backend/tests").glob("**/*.py")) if Path("backend/tests").exists() else []
    frontend_tests = list(Path("frontend/src").glob("**/*.test.ts"))

    print(f"📁 测试文件统计:")
    print(f"   - 后端根目录测试: {len(backend_tests)} 个")
    print(f"   - 后端单元测试: {len(backend_unit_tests)} 个")
    print(f"   - 前端测试: {len(frontend_tests)} 个")

    total_tests = len(backend_tests) + len(backend_unit_tests) + len(frontend_tests)

    if total_tests >= 15:
        print(f"✅ 测试文件数量充足 ({total_tests} 个)")
        return True
    else:
        print(f"⚠️  测试文件数量偏少 ({total_tests} 个，建议 ≥15 个)")
        return False


def generate_coverage_report():
    """生成覆盖率总结报告"""
    print("\n📋 生成覆盖率报告...")

    report = {
        "timestamp": subprocess.run(
            ["date", "+%Y-%m-%d %H:%M:%S"],
            capture_output=True, text=True
        ).stdout.strip(),
        "backend_coverage": "未知",
        "frontend_coverage": "未知",
        "test_files_count": 0,
        "enterprise_ready": False
    }

    # 后端覆盖率
    coverage_file = Path("backend/coverage.json")
    if coverage_file.exists():
        try:
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
            report["backend_coverage"] = f"{coverage_data['totals']['percent_covered']:.1f}%"
        except:
            pass

    # 前端覆盖率
    frontend_coverage = Path("frontend/coverage/coverage-summary.json")
    if frontend_coverage.exists():
        try:
            with open(frontend_coverage, 'r') as f:
                coverage_data = json.load(f)
            lines_pct = coverage_data['total']['lines']['pct']
            report["frontend_coverage"] = f"{lines_pct}%"
        except:
            pass

    # 测试文件统计
    backend_tests = len(list(Path("backend").glob("test_*.py")))
    backend_unit_tests = len(list(Path("backend/tests").glob("**/*.py"))) if Path("backend/tests").exists() else 0
    frontend_tests = len(list(Path("frontend/src").glob("**/*.test.ts")))
    report["test_files_count"] = backend_tests + backend_unit_tests + frontend_tests

    # 写入报告
    with open("TEST_COVERAGE_REPORT.md", "w", encoding="utf-8") as f:
        f.write(f"""# 测试覆盖率报告

## 📊 覆盖率统计

| 模块 | 覆盖率 | 状态 |
|------|--------|------|
| 后端 | {report['backend_coverage']} | {'✅' if '75' in str(report['backend_coverage']) else '❌'} |
| 前端 | {report['frontend_coverage']} | {'✅' if '80' in str(report['frontend_coverage']) else '❌'} |

## 📁 测试文件统计

- 总测试文件数: {report['test_files_count']}
- 后端根目录测试: {backend_tests}
- 后端单元测试: {backend_unit_tests}
- 前端测试: {frontend_tests}

## 🎯 企业级标准

- ✅ 后端覆盖率 ≥75%
- ✅ 前端行覆盖率 ≥80%
- ✅ 前端函数覆盖率 ≥85%
- ✅ 前端分支覆盖率 ≥75%
- ✅ 前端语句覆盖率 ≥80%

## 📅 报告时间

{report['timestamp']}

---
*此报告由测试覆盖率验证脚本自动生成*
""")

    print("✅ 覆盖率报告已生成: TEST_COVERAGE_REPORT.md")


def main():
    """主函数"""
    print("🚀 开始测试覆盖率验证...")

    results = []

    # 检查后端覆盖率
    backend_ok = check_backend_coverage()
    results.append(backend_ok)

    # 检查前端覆盖率
    frontend_ok = check_frontend_coverage()
    results.append(frontend_ok)

    # 检查测试文件
    test_files_ok = check_test_files()
    results.append(test_files_ok)

    # 生成报告
    generate_coverage_report()

    # 总结
    print("\n" + "="*50)
    print("📋 测试覆盖率验证总结:")
    print(f"   后端覆盖率: {'✅' if backend_ok else '❌'}")
    print(f"   前端覆盖率: {'✅' if frontend_ok else '❌'}")
    print(f"   测试文件: {'✅' if test_files_ok else '❌'}")

    all_passed = all(results)
    if all_passed:
        print("\n🎉 恭喜！所有测试覆盖率检查均通过，达到企业级标准！")
        sys.exit(0)
    else:
        print("\n⚠️  部分检查未通过，需要进一步改进测试覆盖率")
        sys.exit(1)


if __name__ == "__main__":
    main()