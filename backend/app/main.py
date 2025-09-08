from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import clusters, tables, tasks
from app.config.database import engine, Base
from app.models import Cluster, TableMetric, PartitionMetric, MergeTask, TaskLog

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

@app.get("/")
async def root():
    return {"message": "Hive Small File Management Platform API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}