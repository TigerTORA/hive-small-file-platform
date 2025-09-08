from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.merge_task import MergeTask
from app.models.cluster import Cluster
from app.schemas.merge_task import MergeTaskCreate, MergeTaskResponse
from datetime import datetime
import uuid

router = APIRouter()

@router.get("/", response_model=list[MergeTaskResponse])
async def list_tasks(
    cluster_id: int = Query(None),
    status: str = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    """List merge tasks with filtering"""
    query = db.query(MergeTask)
    
    if cluster_id:
        query = query.filter(MergeTask.cluster_id == cluster_id)
    if status:
        query = query.filter(MergeTask.status == status)
    
    tasks = query.order_by(MergeTask.created_time.desc()).limit(limit).all()
    return tasks

@router.post("/", response_model=MergeTaskResponse)
async def create_task(task: MergeTaskCreate, db: Session = Depends(get_db)):
    """Create a new merge task"""
    db_task = MergeTask(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.get("/stats")
async def get_task_stats(cluster_id: int = Query(None), db: Session = Depends(get_db)):
    """获取任务统计信息"""
    from sqlalchemy import func
    
    query = db.query(MergeTask)
    if cluster_id:
        query = query.filter(MergeTask.cluster_id == cluster_id)
    
    # 按状态分组统计
    status_stats = query.with_entities(
        MergeTask.status,
        func.count(MergeTask.id).label('count')
    ).group_by(MergeTask.status).all()
    
    # 总统计
    total_tasks = query.count()
    completed_tasks = query.filter(MergeTask.status == 'success').all()
    
    total_files_saved = sum(
        (task.files_before or 0) - (task.files_after or 0) 
        for task in completed_tasks 
        if task.files_before and task.files_after
    )
    
    total_size_saved = sum(task.size_saved or 0 for task in completed_tasks)
    
    return {
        "total_tasks": total_tasks,
        "status_distribution": {status: count for status, count in status_stats},
        "total_files_saved": total_files_saved,
        "total_size_saved": total_size_saved,
        "completed_tasks": len(completed_tasks)
    }

@router.get("/{task_id}", response_model=MergeTaskResponse)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get task by ID"""
    task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/{task_id}/execute")
async def execute_task(task_id: int, db: Session = Depends(get_db)):
    """Execute a merge task"""
    task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status in ["running", "success"]:
        raise HTTPException(status_code=400, detail=f"Task is already {task.status}")
    
    # 模拟任务执行
    task.status = "running"
    task.started_time = datetime.utcnow()
    task.celery_task_id = f"mock-{uuid.uuid4().hex[:8]}"
    db.commit()
    
    # 这里可以启动后台任务
    # result = execute_merge_task.delay(task_id)
    
    return {
        "message": "Task execution started", 
        "task_id": task_id,
        "celery_task_id": task.celery_task_id,
        "status": task.status
    }

@router.post("/{task_id}/cancel")
async def cancel_task(task_id: int, db: Session = Depends(get_db)):
    """Cancel a running task"""
    task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "running":
        raise HTTPException(status_code=400, detail="Task is not running")
    
    task.status = "cancelled"
    task.completed_time = datetime.utcnow()
    task.error_message = "Task cancelled by user"
    db.commit()
    
    return {"message": "Task cancelled successfully"}

@router.post("/{task_id}/simulate-complete")
async def simulate_complete_task(task_id: int, db: Session = Depends(get_db)):
    """模拟完成任务 (仅用于演示)"""
    task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "running":
        raise HTTPException(status_code=400, detail="Task is not running")
    
    # 模拟任务完成
    import random
    task.status = "success"
    task.completed_time = datetime.utcnow()
    task.files_before = random.randint(1000, 10000)
    task.files_after = random.randint(100, task.files_before // 5)
    task.size_saved = random.randint(1024*1024*100, 1024*1024*1024*10)  # 100MB to 10GB
    db.commit()
    
    return {
        "message": "Task completed successfully",
        "files_before": task.files_before,
        "files_after": task.files_after,
        "size_saved": task.size_saved
    }