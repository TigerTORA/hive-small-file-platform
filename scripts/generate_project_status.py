#!/usr/bin/env python3
"""
Generate a consolidated project status report for PMs.

Outputs:
 - PROJECT_STATUS.md (human-readable)
 - project_status.json (machine-readable)

The report aggregates:
 - Feature progress from FEATURE_LIST.md
 - API endpoint counts from backend/app/api
 - Test file counts (backend/frontend) and last known frontend test artifacts
 - Basic repo metrics (lines of code, last update timestamps)

Note: This script is read-only and does not execute tests. It summarizes
what's present in the repo so PMs can get a macro view quickly.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def parse_feature_list(feature_list_path: Path) -> dict:
    text = read_text(feature_list_path)
    if not text:
        return {"completed": 0, "pending": 0, "total": 0, "last_update": None}

    # Count completed and pending by markers used in the doc
    completed = len(re.findall(r"✅已完成|已完成", text))
    pending = len(re.findall(r"❌待开发|待开发", text))

    # Try to parse last update line
    m = re.search(r"最后更新\s*[:：]\s*([0-9\-]{8,}|[0-9]{4}-[0-9]{2}-[0-9]{2})", text)
    last_update = m.group(1) if m else None

    # Avoid overcounting from header lines by a simple heuristic: if header section mentions counts,
    # they may include numbers like (85个). Keep raw counts as an approximation.
    total = completed + pending
    return {
        "completed": completed,
        "pending": pending,
        "total": total,
        "last_update": last_update,
    }


def count_api_endpoints(api_dir: Path) -> dict:
    pattern = re.compile(r"@router\.(get|post|put|delete|patch)\(")
    counts = {"get": 0, "post": 0, "put": 0, "delete": 0, "patch": 0}
    files = sorted(api_dir.glob("*.py"))
    for f in files:
        text = read_text(f)
        matches = re.findall(pattern, text)
        for m in matches:
            if m in counts:
                counts[m] += 1
    counts["total"] = sum(counts.values())
    return counts


def count_backend_tests(backend_dir: Path) -> dict:
    py_tests = list(backend_dir.glob("test_*.py"))
    py_tests += list((backend_dir / "tests").rglob("test_*.py"))
    return {"files": len(py_tests), "paths": [str(p.relative_to(ROOT)) for p in py_tests]}


def count_frontend_tests(frontend_dir: Path) -> dict:
    vitest_dir = frontend_dir / "src" / "test"
    vitest_files = list(vitest_dir.rglob("*.test.ts"))
    # heuristic: also count top-level test-*.js utilities/specs
    misc = list(frontend_dir.glob("test-*.js")) + list(frontend_dir.glob("*.spec.js"))
    return {
        "vitest_files": len(vitest_files),
        "misc_files": len(misc),
        "paths": [str(p.relative_to(ROOT)) for p in (vitest_files + misc)],
    }


def read_frontend_test_artifacts(frontend_dir: Path) -> dict:
    artifacts = {}
    tr_dir = frontend_dir / "test-results"
    if tr_dir.exists():
        for name in ["dashboard-summary.json", "dashboard-data.json"]:
            p = tr_dir / name
            if p.exists():
                try:
                    artifacts[name] = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    artifacts[name] = {"error": "failed to parse"}
    return artifacts


def repo_loc(paths: list[Path]) -> int:
    total = 0
    exclude_dirs = {"node_modules", "dist", "build", ".playwright-mcp", ".pytest_cache", ".mypy_cache", ".venv", "venv"}
    for p in paths:
        if p.is_file():
            try:
                total += sum(1 for _ in p.open("r", encoding="utf-8", errors="ignore"))
            except Exception:
                pass
        else:
            for f in p.rglob("*"):
                if f.is_file() and f.suffix in {".py", ".ts", ".vue", ".js"}:
                    # skip files under excluded directories
                    parts = set(f.parts)
                    if parts & exclude_dirs:
                        continue
                    try:
                        total += sum(1 for _ in f.open("r", encoding="utf-8", errors="ignore"))
                    except Exception:
                        pass
    return total


def last_git_update_marker(root: Path) -> str | None:
    # Fall back to .last-dashboard-update or directory mtime as a heuristic
    marker = root / ".last-dashboard-update"
    if marker.exists():
        try:
            return marker.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    # directory mtime heuristic
    ts = datetime.fromtimestamp(root.stat().st_mtime)
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def generate_status() -> dict:
    feature_stats = parse_feature_list(ROOT / "FEATURE_LIST.md")
    api_stats = count_api_endpoints(ROOT / "backend" / "app" / "api")
    be_tests = count_backend_tests(ROOT / "backend")
    fe_tests = count_frontend_tests(ROOT / "frontend")
    fe_artifacts = read_frontend_test_artifacts(ROOT / "frontend")
    coverage = collect_coverage()

    status = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "last_repo_update": last_git_update_marker(ROOT),
        "features": feature_stats,
        "api": api_stats,
        "tests": {
            "backend": be_tests,
            "frontend": fe_tests,
            "frontend_artifacts": fe_artifacts,
            "coverage": coverage,
        },
        "metrics": {
            "loc_estimate": repo_loc([ROOT / "backend", ROOT / "frontend"]),
        },
        "hints": [
            "Run 'make test' for live test results.",
            "Consider enabling CI to persist coverage and status badges.",
        ],
    }
    return status


def write_markdown(status: dict) -> str:
    feat = status.get("features", {})
    api = status.get("api", {})
    tests = status.get("tests", {})
    be = tests.get("backend", {})
    fe = tests.get("frontend", {})
    loc = status.get("metrics", {}).get("loc_estimate")

    lines = []
    lines.append("# 项目健康报告 (自动生成)")
    lines.append("")
    lines.append(f"生成时间: {status.get('generated_at')}  ")
    if status.get("last_repo_update"):
        lines.append(f"仓库最近更新: {status['last_repo_update']}")
    lines.append("")
    lines.append("## 功能进度总览")
    lines.append(f"- 已完成: {feat.get('completed', 0)}")
    lines.append(f"- 待开发: {feat.get('pending', 0)}")
    lines.append(f"- 合计: {feat.get('total', 0)}")
    if feat.get("last_update"):
        lines.append(f"- 功能清单最后更新: {feat['last_update']}")
    lines.append("")
    lines.append("## API 概览")
    lines.append(f"- 路由总数: {api.get('total', 0)} (GET: {api.get('get', 0)}, POST: {api.get('post', 0)}, PUT: {api.get('put', 0)}, DELETE: {api.get('delete', 0)}, PATCH: {api.get('patch', 0)})")
    lines.append("")
    lines.append("## 测试概览 (静态统计)")
    lines.append(f"- 后端测试文件: {be.get('files', 0)}")
    lines.append(f"- 前端 Vitest 测试文件: {fe.get('vitest_files', 0)}；其它脚本: {fe.get('misc_files', 0)}")
    if tests.get("frontend_artifacts"):
        lines.append("- 前端历史测试产物: 存在 (frontend/test-results)")
    else:
        lines.append("- 前端历史测试产物: 未检测到")
    cov = tests.get("coverage", {})
    if cov:
        be_pct = cov.get("backend", {}).get("lines_pct")
        fe_pct = cov.get("frontend", {}).get("lines_pct")
        cov_line = "- 覆盖率: "
        cov_parts = []
        if be_pct is not None:
            cov_parts.append(f"后端 {be_pct:.1f}%")
        if fe_pct is not None:
            cov_parts.append(f"前端 {fe_pct:.1f}%")
        if cov_parts:
            cov_line += "，".join(cov_parts)
            lines.append(cov_line)
    lines.append("")
    lines.append("## 代码规模 (估算)")
    lines.append(f"- 代码行数 (py/ts/vue/js): ~{loc}")
    lines.append("")
    lines.append("## 下一步建议 (PM 视角)")
    lines.append("- 在 CI 中汇总后端 pytest 与前端 vitest/playwright 结果，产出覆盖率与状态徽章。")
    lines.append("- 固化每周自动生成报告流程（本脚本）并提交到仓库，便于宏观跟踪。")
    lines.append("- 将功能清单、里程碑与风险在一页可视化（前端新增 Project Status 页面或静态站点）。")
    lines.append("")

    return "\n".join(lines)


def collect_coverage() -> dict:
    """Collect coverage metrics if coverage reports exist.
    - Backend: look for coverage.xml in backend/ or root
    - Frontend: look for frontend/coverage/coverage-summary.json
    """
    result: dict = {}

    # Backend coverage (coverage.xml)
    backend_xml_candidates = [
        ROOT / "backend" / "coverage.xml",
        ROOT / "coverage-backend.xml",
        ROOT / "backend-coverage.xml",
    ]
    for p in backend_xml_candidates:
        if p.exists():
            xml = read_text(p)
            # Try to parse line-rate or compute from lines-covered/lines-valid
            m = re.search(r"line-rate=\"([0-9.]+)\"", xml)
            if m:
                result.setdefault("backend", {})["lines_pct"] = float(m.group(1)) * 100.0
                break
            m2 = re.search(r"lines-covered=\"(\d+)\".*lines-valid=\"(\d+)\"", xml)
            if m2:
                covered, valid = int(m2.group(1)), int(m2.group(2))
                if valid:
                    result.setdefault("backend", {})["lines_pct"] = covered / valid * 100.0
                break

    # Frontend coverage (vitest summary)
    fe_summary = ROOT / "frontend" / "coverage" / "coverage-summary.json"
    if fe_summary.exists():
        try:
            data = json.loads(fe_summary.read_text(encoding="utf-8"))
            total = data.get("total", {})
            lines = total.get("lines", {})
            pct = lines.get("pct")
            if isinstance(pct, (int, float)):
                result.setdefault("frontend", {})["lines_pct"] = float(pct)
        except Exception:
            pass

    return result


def main() -> None:
    status = generate_status()
    (ROOT / "project_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = write_markdown(status)
    (ROOT / "PROJECT_STATUS.md").write_text(md, encoding="utf-8")
    print("Generated PROJECT_STATUS.md and project_status.json")


if __name__ == "__main__":
    main()
