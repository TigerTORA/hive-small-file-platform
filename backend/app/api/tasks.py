from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.merge_task import MergeTask
from app.models.cluster import Cluster
from app.schemas.merge_task import MergeTaskCreate, MergeTaskResponse
from datetime import datetime
import uuid
from app.config.settings import settings

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

@router.get("/cluster/{cluster_id}", response_model=list[MergeTaskResponse])
async def get_cluster_tasks(cluster_id: int, db: Session = Depends(get_db)):
    """Get tasks for a specific cluster"""
    tasks = db.query(MergeTask).filter(
        MergeTask.cluster_id == cluster_id
    ).order_by(MergeTask.created_time.desc()).all()
    return tasks

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
    
    # 执行合并任务（支持演示模式与真实执行）
    try:
        # 获取集群信息
        cluster = db.query(Cluster).filter(Cluster.id == task.cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        # 更新任务状态为运行中
        task.status = "running"
        task.started_time = datetime.utcnow()
        task.execution_phase = "initialization"
        task.progress_percentage = 5.0
        task.current_operation = "初始化合并任务"
        db.commit()
        
        # 引擎选择：DEMO_MODE 使用 DemoMergeEngine，本地即可验证全流程；否则走真实引擎
        if settings.DEMO_MODE:
            from app.engines.demo_merge_engine import DemoMergeEngine
            engine = DemoMergeEngine(cluster)
        else:
            # 使用引擎工厂，默认返回 SafeHiveMergeEngine（基于 HiveServer2/pyhive，兼容 LDAP）
            from app.engines.engine_factory import MergeEngineFactory
            engine = MergeEngineFactory.get_engine(cluster)
        
        # 执行合并
        result = engine.execute_merge(task, db)
        
        return {
            "message": "Task execution completed", 
            "task_id": task_id,
            "status": task.status,
            "result": result
        }
    except Exception as e:
        # 任务失败时更新状态
        task.status = "failed"
        task.error_message = str(e)
        task.execution_phase = "error"
        task.current_operation = f"执行失败: {str(e)}"
        db.commit()
        
        return {
            "message": f"Task execution failed: {str(e)}", 
            "task_id": task_id,
            "status": "failed",
            "error": str(e)
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

@router.get("/{task_id}/logs")
async def get_task_logs(task_id: int, db: Session = Depends(get_db)):
    """Get logs for a specific task"""
    # 验证任务是否存在
    task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 查询任务日志
    from app.models.task_log import TaskLog
    logs = db.query(TaskLog).filter(
        TaskLog.task_id == task_id
    ).order_by(TaskLog.timestamp.asc()).all()
    
    return [
        {
            "id": log.id,
            "log_level": log.log_level,
            "message": log.message,
            "details": log.details,
            "timestamp": log.timestamp,
            "phase": log.phase,
            "duration_ms": log.duration_ms,
            "sql_statement": log.sql_statement,
            "affected_rows": log.affected_rows,
            "files_before": log.files_before,
            "files_after": log.files_after,
            "hdfs_stats": log.hdfs_stats,
            "yarn_application_id": log.yarn_application_id,
            "progress_percentage": log.progress_percentage
        }
        for log in logs
    ]

@router.get("/{task_id}/preview")
async def get_task_preview(task_id: int, db: Session = Depends(get_db)):
    """Get merge preview for a specific task"""
    # 验证任务是否存在
    task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 获取集群信息
    cluster = db.query(Cluster).filter(Cluster.id == task.cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        # 导入引擎工厂
        from app.engines.engine_factory import MergeEngineFactory
        
        # 根据任务的合并策略选择引擎
        engine_type = None
        if task.merge_strategy == 'safe_merge':
            engine_type = 'safe_hive'
        elif task.merge_strategy in ['concatenate', 'insert_overwrite']:
            engine_type = 'hive'
        
        # 获取合并引擎
        engine = MergeEngineFactory.get_engine(cluster, engine_type)
        
        # 获取预览信息
        preview = engine.get_merge_preview(task)
        
        return {
            "task_id": task.id,
            "task_name": task.task_name,
            "table": f"{task.database_name}.{task.table_name}",
            "merge_strategy": task.merge_strategy,
            "preview": preview
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate preview: {str(e)}"
        )
