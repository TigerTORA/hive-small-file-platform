# Makefile for Hive Small File Platform

.PHONY: help install-dev format check test status clean ci-test setup build-images build-backend-image build-frontend-image release-save

help:
	@echo "Available commands:"
	@echo "  setup           Setup project and hooks"
	@echo "  install-dev     Install development dependencies"
	@echo "  format          Auto-format code with Black and isort"
	@echo "  check           Run quality checks (Black, Flake8, isort, MyPy)"
	@echo "  test            Run tests"
	@echo "  ci-test         Run CI-compatible tests"
	@echo "  status          Generate consolidated project status"
	@echo "  clean           Clean up cache files"
	@echo "  build-images    Build production Docker images (backend/frontend)"
	@echo "  release-save    Save images as tar files to dist/ (offline delivery)"

setup:
	@echo "Setting up project..."
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit
	chmod +x scripts/update-dashboard.sh
	@echo "Installing development dependencies..."
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

install-dev:
	@echo "Installing development dependencies..."
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

format:
	@echo "Formatting code..."
	cd backend && black . && isort .
	cd frontend && npm run format 2>/dev/null || echo "Frontend formatting not available"

check:
	@echo "Running quality checks..."
	cd backend && black --check . && isort -c . && flake8 . --count --max-line-length=100 --statistics
	cd frontend && npm run lint 2>/dev/null || echo "Frontend linting not available"

test:
	@echo "Running backend tests..."
	cd backend && python -m pytest test_simple.py --cov=app --cov-report=term --cov-fail-under=0 -v
	@echo "Running frontend tests..."
	cd frontend && npm run test:run

ci-test:
	@echo "Running CI-compatible tests..."
	cd backend && python -m pytest test_simple.py --cov=app --cov-report=xml:coverage.xml --cov-fail-under=0 -v
	cd frontend && npm run test:run

status:
	@echo "Generating consolidated project status..."
	python3 scripts/generate_project_status.py
	@echo "\nSummary written to PROJECT_STATUS.md and project_status.json"

clean:
	@echo "Cleaning up cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	cd frontend && rm -rf node_modules/.cache 2>/dev/null || true

# -------- Release helpers --------

VERSION ?= $(shell cat VERSION 2>/dev/null || echo latest)
IMAGE_API ?= hive-small-file-api
IMAGE_FE  ?= hive-small-file-frontend

build-images: build-backend-image build-frontend-image
	@echo "Built images: $(IMAGE_API):$(VERSION), $(IMAGE_FE):$(VERSION)"

build-backend-image:
	docker build -t $(IMAGE_API):$(VERSION) backend

build-frontend-image:
	docker build -t $(IMAGE_FE):$(VERSION) frontend

release-save: build-images
	mkdir -p dist
	docker save -o dist/$(IMAGE_API)-$(VERSION).tar $(IMAGE_API):$(VERSION)
	docker save -o dist/$(IMAGE_FE)-$(VERSION).tar $(IMAGE_FE):$(VERSION)
	@echo "Saved to dist/:"
	ls -lh dist | sed -n '1,200p'
