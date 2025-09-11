# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Hive/Impala small file management platform consisting of a FastAPI backend and Vue 3 frontend. The platform monitors and manages small files in CDH/CDP clusters by connecting directly to Hive MetaStore databases and HDFS APIs.

## Development Commands

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --reload --port 8000

# Start Celery worker (for task processing)
celery -A app.scheduler.celery_app worker --loglevel=info

# Start Celery beat (for scheduled tasks)
celery -A app.scheduler.celery_app beat --loglevel=info

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Code Quality and Formatting

```bash
# Install quality tools (included in requirements.txt)
pip install black flake8 isort mypy pre-commit

# Auto-format code
python scripts/format_code.py

# Check code quality
python scripts/quality_check.py

# Set up pre-commit hooks (optional)
pre-commit install
pre-commit run --all-files

# Manual quality checks
black --check backend/app
flake8 backend/app
isort --check-only backend/app
mypy backend/app
```

### Frontend Development

```bash
cd frontend

# Install dependencies  
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check
```

### Testing the Platform

```bash
# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/clusters/

# Test cluster connections
curl http://localhost:8000/api/v1/tables/test-connection/1

# Scan tables
curl -X POST http://localhost:8000/api/v1/tables/scan-table/1/default/table_name
```

## Architecture Overview

### Backend Architecture (app/)

- **main.py**: FastAPI application entry point with CORS and router setup
- **config/**: Settings management using Pydantic Settings, supports .env files
- **models/**: SQLAlchemy ORM models for clusters, table metrics, partition metrics, merge tasks
- **schemas/**: Pydantic schemas for request/response validation
- **api/**: FastAPI routers organized by domain (clusters, tables, tasks)
- **monitor/**: Core monitoring functionality with pluggable connectors
- **engines/**: File merge engines with factory pattern for extensibility
- **scheduler/**: Celery task definitions for background processing

### Frontend Architecture (src/)

- **main.ts**: Vue 3 application bootstrap with Element Plus
- **App.vue**: Root component with routing and layout
- **router/**: Vue Router configuration
- **views/**: Page-level components
- **api/**: Axios-based API client modules

### Key Design Patterns

**Connector Pattern**: The monitor module uses interchangeable connectors:
- `MySQLHiveMetastoreConnector` for CDP clusters with MySQL MetaStore
- `HiveMetastoreConnector` for PostgreSQL-based MetaStores
- `MockHDFSScanner` for development/testing
- `HDFSScanner` for production HDFS access

**Factory Pattern**: Engine factory (`engines/engine_factory.py`) allows pluggable merge engines:
- Hive CONCATENATE engine for compatible file formats
- INSERT OVERWRITE engine for all formats
- Extensible for custom merge strategies

**Context Manager Pattern**: All connectors implement `__enter__`/`__exit__` for resource management.

## Database Configuration

The platform supports multiple database backends via SQLAlchemy:

- **Development**: SQLite (configured in settings.py)
- **Production**: PostgreSQL or MySQL

Database models use relationships with proper back_populates for bidirectional mapping:
- Cluster → TableMetric (one-to-many)  
- TableMetric → PartitionMetric (one-to-many)
- Cluster → MergeTask (one-to-many)

## CDP/CDH Cluster Integration

### MetaStore Connection Patterns

```python
# For MySQL MetaStore (CDP)
mysql_url = "mysql://user:pass@host:port/hive"
connector = MySQLHiveMetastoreConnector(mysql_url)

# For PostgreSQL MetaStore (CDH) 
postgres_url = "postgresql://user:pass@host:port/hive_metastore"
connector = HiveMetastoreConnector(postgres_url)
```

### HDFS Integration Challenges

The project includes both real and mock HDFS scanners:
- `hdfs_scanner.py` - Production HDFS integration (may have dependency issues)
- `mock_hdfs_scanner.py` - Development/demo version with simulated data
- Use mock version for development when HDFS libraries have compatibility issues

## API Design Patterns

### RESTful Resource Organization

- `/api/v1/clusters/` - Cluster CRUD and connection testing
- `/api/v1/tables/` - Table discovery and scanning operations  
- `/api/v1/tasks/` - Merge task management and execution

### Scanning Operations

```python
# Database scanning
POST /api/v1/tables/scan/{cluster_id}/{database_name}

# Single table scanning
POST /api/v1/tables/scan-table/{cluster_id}/{database_name}/{table_name}

# Get scan results
GET /api/v1/tables/metrics?cluster_id=1
GET /api/v1/tables/small-files?cluster_id=1
```

## Common Development Patterns

### Adding New Connectors

1. Inherit from base connector interface
2. Implement `connect()`, `disconnect()`, `test_connection()` methods
3. Add context manager support (`__enter__`, `__exit__`)
4. Register in appropriate factory or scanner class

### Extending Merge Engines

1. Inherit from `BaseMergeEngine` 
2. Implement abstract methods for validation and execution
3. Register in `engine_factory.py`
4. Add corresponding UI options in frontend

### Database Schema Changes

1. Modify SQLAlchemy models in `models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`  
3. Review and apply: `alembic upgrade head`

## Configuration Management

Settings use Pydantic Settings with environment variable override:

```python
# app/config/settings.py
DATABASE_URL: str = "sqlite:///./hive_small_file_db.db"  # Default
# Override with .env file or environment variables
```

Critical settings:
- `DATABASE_URL` - Main database connection
- `CELERY_BROKER_URL` - Redis for task queue
- `SMALL_FILE_THRESHOLD` - File size threshold (default 128MB)

## Known Issues and Workarounds

### Python Dependencies

- **hdfs3/hdfs libraries**: May have compatibility issues with Python 3.13
- **Pydantic v2**: Use `pattern` instead of `regex` in Field definitions
- **SQLAlchemy relationships**: Import all models in main.py to avoid circular dependency issues

### HDFS Integration

- Use `MockHDFSScanner` for development when real HDFS libraries fail
- Real HDFS integration requires network access to cluster NameNode
- Consider WebHDFS API as alternative to native HDFS clients

### Database Relationships

Ensure proper model imports in main.py to resolve SQLAlchemy relationships:

```python
from app.models import Cluster, TableMetric, PartitionMetric, MergeTask, TaskLog
```

Use `lazy="dynamic"` for relationships that may have performance issues with large datasets.