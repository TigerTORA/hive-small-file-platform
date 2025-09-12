from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.config.database import get_db
from app.models.scan_task import ScanTask
from app.schemas.scan_task import ScanTaskResponse, ScanTaskLog
from app.models.scan_task_log import ScanTaskLogDB
from app.models.scan_task import ScanTask as ScanTaskModel
from app.services.scan_service import scan_task_manager

router = APIRouter()


@router.get("/", response_model=List[ScanTaskResponse])
async def list_scan_tasks(
    cluster_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List scan tasks with optional filtering by cluster and status."""
    query = db.query(ScanTask)
    if cluster_id is not None:
        query = query.filter(ScanTask.cluster_id == cluster_id)
    if status:
        query = query.filter(ScanTask.status == status)

    tasks = (
        query.order_by(ScanTask.start_time.desc()).limit(limit).all()
    )
    return tasks


@router.get("/{task_id}", response_model=ScanTaskResponse)
async def get_scan_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(ScanTask).filter(ScanTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/logs", response_model=List[ScanTaskLog])
async def get_scan_task_logs(task_id: str, db: Session = Depends(get_db)):
    """Get logs for a specific scan task.
    Prefer persisted logs; if task is running and in-memory has newer logs, append them.
    """
    # Resolve scan_task id
    task = db.query(ScanTaskModel).filter(ScanTaskModel.task_id == task_id).first()
    if not task:
        # fall back to in-memory only
        return scan_task_manager.get_task_logs(task_id)

    # Fetch persisted logs
    rows = (
        db.query(ScanTaskLogDB)
        .filter(ScanTaskLogDB.scan_task_id == task.id)
        .order_by(ScanTaskLogDB.timestamp.asc())
        .all()
    )
    persisted = [
        ScanTaskLog(
            timestamp=r.timestamp,
            level=r.level,
            message=r.message,
            database_name=r.database_name,
            table_name=r.table_name,
        )
        for r in rows
    ]

    # Append in-memory logs that might not be persisted yet
    mem_logs = scan_task_manager.get_task_logs(task_id)
    if mem_logs:
        # Only append logs that are newer than the last persisted timestamp
        last_ts = persisted[-1].timestamp if persisted else None
        for ml in mem_logs:
            if last_ts is None or (ml.timestamp and ml.timestamp > last_ts):
                persisted.append(ml)

    return persisted
