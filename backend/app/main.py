from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from app.api import clusters, tables, tasks, errors, dashboard
from app.api import scan_tasks as scan_tasks_api
from app.config.database import engine, Base
from app.config.settings import settings
from app.models import Cluster, TableMetric, PartitionMetric, MergeTask, TaskLog, ScanTask, ScanTaskLogDB

# Initialize Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(auto_enabling_integrations=True),
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
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clusters.router, prefix="/api/v1/clusters", tags=["clusters"])
app.include_router(tables.router, prefix="/api/v1/tables", tags=["tables"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(errors.router, prefix="/api/v1/errors", tags=["errors"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(scan_tasks_api.router, prefix="/api/v1/scan-tasks", tags=["scan-tasks"])

@app.get("/")
async def root():
    return {"message": "Hive Small File Management Platform API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
