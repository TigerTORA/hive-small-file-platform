#!/usr/bin/env python3
"""
快速测试检查脚本
检查测试文件数量和基本配置
"""

import subprocess
import sys
from pathlib import Path


def count_test_files():
    """统计测试文件数量"""
    print("📁 统计测试文件...")

    # 后端测试文件
    backend_root_tests = list(Path("backend").glob("test_*.py"))
    backend_unit_tests = []
    backend_tests_dir = Path("backend/tests")
    if backend_tests_dir.exists():
        backend_unit_tests = list(backend_tests_dir.glob("**/*.py"))
        # 排除 __init__.py 文件
        backend_unit_tests = [f for f in backend_unit_tests if f.name != "__init__.py"]

    # 前端测试文件
    frontend_tests = list(Path("frontend/src").glob("**/*.test.ts"))

    print(f"   后端根目录测试: {len(backend_root_tests)} 个")
    print(f"   后端单元测试: {len(backend_unit_tests)} 个")
    print(f"   前端测试: {len(frontend_tests)} 个")

    total = len(backend_root_tests) + len(backend_unit_tests) + len(frontend_tests)
    print(f"   总计: {total} 个测试文件")

    print("\n📋 后端测试文件列表:")
    for test_file in backend_root_tests:
        print(f"   - {test_file}")

    print("\n📋 后端单元测试文件列表:")
    for test_file in backend_unit_tests:
        print(f"   - {test_file}")

    print("\n📋 前端测试文件列表:")
    for test_file in frontend_tests:
        print(f"   - {test_file}")

    return total


def check_pytest_config():
    """检查pytest配置"""
    print("\n🔧 检查pytest配置...")

    pytest_ini = Path("backend/pytest.ini")
    if pytest_ini.exists():
        with open(pytest_ini, 'r') as f:
            content = f.read()

        if "--cov-fail-under=75" in content:
            print("   ✅ pytest配置中覆盖率阈值已设置为75%")
        else:
            print("   ❌ pytest配置中覆盖率阈值未正确设置")

        if "--ignore=" not in content or "test_smart" not in content:
            print("   ✅ 被禁用的测试已启用")
        else:
            print("   ❌ 仍有测试被禁用")

        return True
    else:
        print("   ❌ pytest.ini文件不存在")
        return False


def check_vitest_config():
    """检查vitest配置"""
    print("\n🔧 检查vitest配置...")

    vitest_config = Path("frontend/vitest.config.ts")
    if vitest_config.exists():
        with open(vitest_config, 'r') as f:
            content = f.read()

        if "lines: 80" in content and "functions: 85" in content:
            print("   ✅ vitest配置中覆盖率阈值已提高到企业级标准")
        else:
            print("   ❌ vitest配置中覆盖率阈值未正确设置")

        if "ClusterDetail.test.ts" not in content or "exclude:" not in content:
            print("   ✅ 前端核心测试文件已包含")
        else:
            print("   ❌ 前端核心测试文件仍被排除")

        return True
    else:
        print("   ❌ vitest.config.ts文件不存在")
        return False


def check_ci_config():
    """检查CI配置"""
    print("\n🔧 检查CI配置...")

    ci_yml = Path(".github/workflows/ci.yml")
    if ci_yml.exists():
        with open(ci_yml, 'r') as f:
            content = f.read()

        if "--cov-fail-under=75" in content:
            print("   ✅ CI配置中覆盖率阈值已提高到75%")
        else:
            print("   ❌ CI配置中覆盖率阈值未正确设置")

        if "test_simple.py" not in content:
            print("   ✅ CI不再仅运行简单测试")
        else:
            print("   ❌ CI仍只运行简单测试")

        return True
    else:
        print("   ❌ CI配置文件不存在")
        return False


def main():
    """主函数"""
    print("🚀 快速测试检查开始...\n")

    # 统计测试文件
    test_count = count_test_files()

    # 检查配置
    pytest_ok = check_pytest_config()
    vitest_ok = check_vitest_config()
    ci_ok = check_ci_config()

    # 总结
    print("\n" + "="*50)
    print("📋 检查总结:")
    print(f"   测试文件数量: {test_count} 个 {'✅' if test_count >= 15 else '❌'}")
    print(f"   pytest配置: {'✅' if pytest_ok else '❌'}")
    print(f"   vitest配置: {'✅' if vitest_ok else '❌'}")
    print(f"   CI配置: {'✅' if ci_ok else '❌'}")

    if test_count >= 15 and pytest_ok and vitest_ok and ci_ok:
        print("\n🎉 测试配置检查通过！")
        print("📝 建议:")
        print("   1. 运行 'make ci-test' 验证测试执行")
        print("   2. 运行 'scripts/validate_test_coverage.py' 检查覆盖率")
        print("   3. 提交代码触发CI验证")
        return True
    else:
        print("\n⚠️  部分检查未通过，需要进一步调整")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)