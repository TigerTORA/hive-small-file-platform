#!/usr/bin/env python3
"""
Code formatting script for Hive Small File Platform.

This script automatically formats the codebase using:
- Black code formatter
- isort import sorter
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
        print(f"✅ {description} completed")
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
    """Main formatting function."""
    project_root = Path(__file__).parent.parent
    backend_path = project_root / "backend"
    
    print("🔧 Starting code formatting...")
    print(f"Project root: {project_root}")
    print(f"Backend path: {backend_path}")
    
    if not backend_path.exists():
        print("❌ Backend directory not found!")
        sys.exit(1)
    
    format_commands = [
        ("isort backend/app", "isort import sorting", project_root),
        ("black backend/app", "Black code formatting", project_root),
    ]
    
    failed_commands = []
    
    for command, description, cwd in format_commands:
        if not run_command(command, description, cwd):
            failed_commands.append(description)
    
    print("\n" + "="*50)
    
    if failed_commands:
        print("❌ Some formatting commands failed!")
        print("Failed commands:")
        for cmd in failed_commands:
            print(f"  - {cmd}")
        sys.exit(1)
    else:
        print("✅ Code formatting completed successfully!")
        print("You can now run 'python scripts/quality_check.py' to verify quality.")


if __name__ == "__main__":
    main()