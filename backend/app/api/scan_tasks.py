from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.scan_task import ScanTask
from app.models.scan_task import ScanTask as ScanTaskModel
from app.models.scan_task_log import ScanTaskLogDB
from app.schemas.scan_task import ScanTaskLog, ScanTaskResponse
from app.services.scan_service import _sanitize_log_text  # 使用统一的日志清洗函数
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

    tasks = query.order_by(ScanTask.start_time.desc()).limit(limit).all()

    # 附加最近日志时间（last_update）
    if tasks:
        task_ids = [t.id for t in tasks]
        rows = (
            db.query(ScanTaskLogDB.scan_task_id, func.max(ScanTaskLogDB.timestamp))
            .filter(ScanTaskLogDB.scan_task_id.in_(task_ids))
            .group_by(ScanTaskLogDB.scan_task_id)
            .all()
        )
        last_map = {scan_task_id: ts for scan_task_id, ts in rows}
        for t in tasks:
            # 优先日志时间，其次 end_time，最后 start_time
            setattr(t, "last_update", last_map.get(t.id) or t.end_time or t.start_time)

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
    persisted = []
    for r in rows:
        try:
            msg = _sanitize_log_text(r.message)
        except Exception:
            msg = r.message
        persisted.append(
            ScanTaskLog(
                timestamp=r.timestamp,
                level=r.level,
                message=msg,
                database_name=r.database_name,
                table_name=r.table_name,
            )
        )

    # Append in-memory logs that might not be persisted yet
    mem_logs = scan_task_manager.get_task_logs(task_id)
    if mem_logs:
        # Only append logs that are newer than the last persisted timestamp
        last_ts = persisted[-1].timestamp if persisted else None
        for ml in mem_logs:
            if last_ts is None or (ml.timestamp and ml.timestamp > last_ts):
                persisted.append(ml)

    return persisted


@router.post("/{task_id}/cancel")
async def cancel_scan_task(task_id: str, db: Session = Depends(get_db)):
    """请求取消正在运行的扫描任务。若任务已完成或不存在，返回相应提示。"""
    db_task = db.query(ScanTaskModel).filter(ScanTaskModel.task_id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.status not in ("running", "pending"):
        return {
            "status": "ignored",
            "message": f"Task is {db_task.status}, cannot cancel",
        }

    # 标记取消并由执行线程尽快中止
    scan_task_manager.request_cancel(db, task_id)
    return {"status": "ok", "message": "Cancel signal sent"}
