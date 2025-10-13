#!/usr/bin/env python3
"""
Remove local-only caches, tmp files, and dev logs so the workspace stays tidy.

Usage:
  python3 scripts/cleanup_workspace.py          # dry-run (default)
  python3 scripts/cleanup_workspace.py --apply  # delete matched paths
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

FILE_GLOBS = [
    ".tmp_scan*.json",
    ".tmp_tasklogs*.json",
    ".tmp_smallfiles/*.json",
    ".tmp-backend-pid",
    ".tmp-frontend-pid",
    "backend_dev*.log",
    "frontend_dev*.log",
    "backend_final.log",
    "frontend_clean.log",
]

DIR_GLOBS = [
    ".tmp_smallfiles",
    ".pytest_cache",
    "backend/.pytest_cache",
    ".playwright-mcp",
    "frontend/.vite",
    "frontend/.temp",
    "frontend/.cache",
    "frontend/playwright-report",
    "frontend/test-results",
    "frontend/coverage",
    "frontend/node_modules/.cache",
]


def iter_matches(globs: Iterable[str]) -> list[Path]:
    matches: list[Path] = []
    for pattern in globs:
        for path in ROOT.glob(pattern):
            matches.append(path)
    return matches


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="delete matched paths")
    args = parser.parse_args()

    targets = iter_matches(FILE_GLOBS) + iter_matches(DIR_GLOBS)
    if not targets:
        print("[cleanup] nothing to do")
        return

    for path in sorted({t.resolve() for t in targets}):
        rel = path.relative_to(ROOT)
        if args.apply:
            remove_path(path)
            print(f"[cleanup] removed {rel}")
        else:
            print(f"[cleanup] would remove {rel}")

    if not args.apply:
        print("[cleanup] dry-run complete (pass --apply to delete)")


if __name__ == "__main__":
    main()
