from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.merge_task import MergeTask
from app.schemas.merge_task import MergeTaskCreate, MergeTaskResponse

router = APIRouter()

@router.get("/", response_model=list[MergeTaskResponse])
async def list_tasks(db: Session = Depends(get_db)):
    """List all merge tasks"""
    tasks = db.query(MergeTask).order_by(MergeTask.created_time.desc()).all()
    return tasks

@router.post("/", response_model=MergeTaskResponse)
async def create_task(task: MergeTaskCreate, db: Session = Depends(get_db)):
    """Create a new merge task"""
    db_task = MergeTask(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

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
    
    # TODO: Implement Celery task execution
    from app.scheduler.merge_tasks import execute_merge_task
    result = execute_merge_task.delay(task_id)
    
    task.status = "running"
    task.celery_task_id = result.id
    db.commit()
    
    return {"message": "Task execution started", "celery_task_id": result.id}