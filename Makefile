# Makefile for Hive Small File Platform

.PHONY: help install-dev format check test status clean

help:
	@echo "Available commands:"
	@echo "  install-dev     Install development dependencies"
	@echo "  format          Auto-format code with Black and isort"
	@echo "  check           Run quality checks (Black, Flake8, isort, MyPy)"
	@echo "  test            Run tests"
	@echo "  status          Generate consolidated project status"
	@echo "  clean           Clean up cache files"

install-dev:
	@echo "Installing development dependencies..."
	cd backend && pip install -r requirements.txt

format:
	@echo "Formatting code..."
	python3 scripts/format_code.py

check:
	@echo "Running quality checks..."
	python3 scripts/quality_check.py

test:
	@echo "Running backend tests..."
	cd backend && python -m pytest
	@echo "Running frontend tests..."
	cd frontend && npm test

status:
	@echo "Generating consolidated project status..."
	python3 scripts/generate_project_status.py
	@echo "\nSummary written to PROJECT_STATUS.md and project_status.json"

clean:
	@echo "Cleaning up cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
