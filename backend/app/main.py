import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.api import clusters, dashboard, errors, partition_archiving
from app.api import scan_tasks as scan_tasks_api
from app.api import storage_admin, tables_archive, tables_cold_data, tables_refactored, tasks, test_tables, websocket
from app.config.database import Base, engine
from app.config.settings import settings
from app.models import (
    Cluster,
    MergeTask,
    PartitionMetric,
    ScanTask,
    ScanTaskLogDB,
    TableMetric,
    TaskLog,
)
from app.models.cluster_status_history import ClusterStatusHistory

# Initialize Sentry
if settings.SENTRY_DSN and settings.SENTRY_DSN.startswith("http"):
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=1.0,
    )

if settings.AUTO_CREATE_SCHEMA:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hive Small File Management Platform",
    description="A platform for monitoring and managing small files in Hive/Impala clusters",
    version="1.0.0",
)

# CORS configuration
# Prefer explicit whitelist via env var ALLOWED_ORIGINS; default to local dev hosts
_origins_raw = (settings.ALLOWED_ORIGINS or "").strip()
if _origins_raw:
    _allowed_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
else:
    _allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

# If wildcard is present, disable credentials to avoid insecure combination
_allow_credentials = "*" not in _allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clusters.router, prefix="/api/v1/clusters", tags=["clusters"])
app.include_router(tables_refactored.router, prefix="/api/v1/tables", tags=["tables"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(errors.router, prefix="/api/v1/errors", tags=["errors"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(
    scan_tasks_api.router, prefix="/api/v1/scan-tasks", tags=["scan-tasks"]
)
app.include_router(
    tables_cold_data.router, prefix="/api/v1/table-archiving", tags=["cold-data"]
)
app.include_router(
    tables_archive.router, prefix="/api/v1/table-archiving", tags=["table-archiving"]
)
app.include_router(
    partition_archiving.router,
    prefix="/api/v1/partition-archiving",
    tags=["partition-archiving"],
)
app.include_router(storage_admin.router, prefix="/api/v1", tags=["storage-admin"])
app.include_router(test_tables.router, prefix="/api/v1/test-tables", tags=["test-tables"])
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])


@app.get("/")
async def root():
    return {"message": "Hive Small File Management Platform API"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "server_config": {
            "host": settings.SERVER_HOST,
            "port": settings.SERVER_PORT,
            "environment": settings.SENTRY_ENVIRONMENT,
        },
    }


# Uvicorn server启动配置
if __name__ == "__main__":
    import uvicorn

    print(f"🚀 启动 Hive Small File Platform 后端服务")
    print(f"📍 服务地址: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}")
    print(f"🔄 热重载: {'开启' if settings.RELOAD else '关闭'}")
    print(f"🌍 环境: {settings.SENTRY_ENVIRONMENT}")
    print(f"💾 数据库: {settings.DATABASE_URL}")
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.RELOAD,
    )
