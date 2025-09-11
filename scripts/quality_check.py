#!/usr/bin/env python3
"""
Code quality checking script for Hive Small File Platform.

This script runs various code quality checks including:
- Black code formatting
- Flake8 linting 
- isort import sorting
- MyPy type checking
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description, cwd=None):
    """Run a command and return success status."""
    print(f"Running {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=cwd
        )
        print(f"✅ {description} passed")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main():
    """Main quality check function."""
    project_root = Path(__file__).parent.parent
    backend_path = project_root / "backend"
    
    print("🔍 Starting code quality checks...")
    print(f"Project root: {project_root}")
    print(f"Backend path: {backend_path}")
    
    if not backend_path.exists():
        print("❌ Backend directory not found!")
        sys.exit(1)
    
    checks = [
        ("black --check --diff backend/app", "Black formatting check", project_root),
        ("isort --check-only --diff backend/app", "isort import order check", project_root),
        ("flake8 backend/app", "Flake8 linting", project_root),
        ("mypy backend/app", "MyPy type checking", project_root),
    ]
    
    failed_checks = []
    
    for command, description, cwd in checks:
        if not run_command(command, description, cwd):
            failed_checks.append(description)
    
    print("\n" + "="*50)
    
    if failed_checks:
        print("❌ Quality checks failed!")
        print("Failed checks:")
        for check in failed_checks:
            print(f"  - {check}")
        print("\nRun 'python scripts/format_code.py' to auto-fix formatting issues.")
        sys.exit(1)
    else:
        print("✅ All quality checks passed!")
        print("Code is ready for commit.")


if __name__ == "__main__":
    main()