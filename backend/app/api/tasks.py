import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import SessionLocal, get_db
from app.config.settings import settings
from app.models.cluster import Cluster
from app.models.merge_task import MergeTask
from app.models.test_table_task_log import TestTableTaskLog
from app.schemas.merge_task import MergeTaskCreate, MergeTaskResponse

router = APIRouter()
# Reload hint: retry endpoint added; ensure router includes it


@router.get("/")
async def list_tasks(
    cluster_id: int = Query(None),
    status: str = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db),
):
    """List all types of tasks (merge, scan, archive, test-table-generation) with filtering"""
    from app.models.scan_task import ScanTask
    from app.schemas.test_table import TestTableTask

    all_tasks = []

    # 获取合并任务
    merge_query = db.query(MergeTask)
    if cluster_id:
        merge_query = merge_query.filter(MergeTask.cluster_id == cluster_id)
    if status:
        merge_query = merge_query.filter(MergeTask.status == status)

    merge_tasks = merge_query.order_by(MergeTask.created_time.desc()).limit(limit).all()
    for task in merge_tasks:
        all_tasks.append({
            "id": task.id,
            "type": "merge",
            "task_name": task.task_name,
            "database_name": task.database_name,
            "table_name": task.table_name,
            "cluster_id": task.cluster_id,
            "status": task.status,
            "created_time": task.created_time,
            "started_time": task.started_time,
            "completed_time": task.completed_time,
            "error_message": task.error_message,
            "progress": task.progress,
            "current_phase": task.current_phase
        })

    # 获取扫描任务
    scan_query = db.query(ScanTask)
    if cluster_id:
        scan_query = scan_query.filter(ScanTask.cluster_id == cluster_id)
    if status:
        scan_query = scan_query.filter(ScanTask.status == status)

    scan_tasks = scan_query.order_by(ScanTask.start_time.desc()).limit(limit).all()
    for task in scan_tasks:
        # 根据task_type确定显示类型
        display_type = "archive" if task.task_type and task.task_type.startswith('archive') else "scan"

        # 计算进度
        progress = 0.0
        if task.total_items and task.total_items > 0:
            progress = (task.completed_items or 0) / task.total_items * 100

        all_tasks.append({
            "id": task.id,
            "type": display_type,
            "subtype": task.task_type,
            "task_name": task.task_name,
            "database_name": getattr(task, 'database_name', ''),
            "table_name": getattr(task, 'table_name', ''),
            "cluster_id": task.cluster_id,
            "status": task.status,
            "created_time": task.start_time,
            "started_time": task.start_time,
            "completed_time": task.end_time,
            "error_message": task.error_message,
            "progress": progress,
            "current_phase": task.current_item or task.task_type
        })

    # 获取测试表生成任务
    try:
        from app.models.test_table_task import TestTableTask as TestTableTaskModel

        test_tasks_query = db.query(TestTableTaskModel)
        if cluster_id:
            test_tasks_query = test_tasks_query.filter(TestTableTaskModel.cluster_id == cluster_id)
        if status:
            test_tasks_query = test_tasks_query.filter(TestTableTaskModel.status == status)

        test_tasks = test_tasks_query.order_by(TestTableTaskModel.created_time.desc()).limit(limit).all()
        for task in test_tasks:
            all_tasks.append({
                "id": task.id,
                "type": "test-table-generation",
                "task_name": task.task_name,
                "database_name": task.database_name,
                "table_name": task.table_name,
                "cluster_id": task.cluster_id,
                "status": task.status,
                "created_time": task.created_time,
                "started_time": task.started_time,
                "completed_time": task.completed_time,
                "error_message": task.error_message,
                "progress": task.progress_percentage,
                "current_phase": task.current_phase,
                "current_operation": task.current_operation
            })
    except Exception as e:
        # 测试表任务表可能不存在，忽略错误
        print(f"Warning: Could not load test table tasks: {e}")

    # 按创建时间排序并限制数量
    from datetime import datetime
    all_tasks.sort(
        key=lambda x: x["created_time"] if x["created_time"] else datetime.min,
        reverse=True
    )
    return all_tasks[:limit]


@router.post("/", response_model=MergeTaskResponse)
async def create_task(task: MergeTaskCreate, db: Session = Depends(get_db)):
    """Create a new merge task"""
    payload = task.dict()
    fmt = payload.get("target_storage_format")
    if fmt:
        fmt_upper = fmt.upper()
        payload["target_storage_format"] = fmt_upper
    comp = payload.get("target_compression")
    if comp:
        comp_upper = comp.upper()
        if comp_upper in {"DEFAULT", "ORIGINAL"}:
            payload["target_compression"] = "KEEP"
        else:
            payload["target_compression"] = comp_upper
    db_task = MergeTask(**payload)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.get("/cluster/{cluster_id}", response_model=list[MergeTaskResponse])
async def get_cluster_tasks(cluster_id: int, db: Session = Depends(get_db)):
    """Get tasks for a specific cluster"""
    tasks = (
        db.query(MergeTask)
        .filter(MergeTask.cluster_id == cluster_id)
        .order_by(MergeTask.created_time.desc())
        .all()
    )
    return tasks


@router.get("/stats")
async def get_task_stats(cluster_id: int = Query(None), db: Session = Depends(get_db)):
    """获取任务统计信息"""
    from sqlalchemy import func

    query = db.query(MergeTask)
    if cluster_id:
        query = query.filter(MergeTask.cluster_id == cluster_id)

    # 按状态分组统计
    status_stats = (
        query.with_entities(MergeTask.status, func.count(MergeTask.id).label("count"))
        .group_by(MergeTask.status)
        .all()
    )

    # 总统计
    total_tasks = query.count()
    completed_tasks = query.filter(MergeTask.status == "success").all()

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
        "completed_tasks": len(completed_tasks),
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
    """Execute a merge task in background to avoid blocking the API worker."""
    task = db.query(MergeTask).filter(MergeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in ["running", "success"]:
        raise HTTPException(status_code=400, detail=f"Task is already {task.status}")

    # Mark as running and return immediately
    cluster = db.query(Cluster).filter(Cluster.id == task.cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    task.status = "running"
    task.started_time = datetime.utcnow()
    task.execution_phase = "initialization"
    task.progress_percentage = 5.0
    task.current_operation = "初始化合并任务"
    db.commit()

    # Run merge in a dedicated thread with its own DB session
    import threading

    def _run_merge(tid: int, cluster_id: int):
        s = SessionLocal()
        try:
            t = s.query(MergeTask).filter(MergeTask.id == tid).first()
            c = s.query(Cluster).filter(Cluster.id == cluster_id).first()
            if not (t and c):
                return

            if settings.DEMO_MODE:
                from app.engines.demo_merge_engine import DemoMergeEngine
                engine = DemoMergeEngine(c)
            else:
                from app.engines.engine_factory import MergeEngineFactory
                engine = MergeEngineFactory.get_engine(c)

            result = engine.execute_merge(t, s)

            # 根据execute_merge的返回值更新任务状态
            if result and result.get('success'):
                t.status = 'completed'
                t.progress_percentage = 100
                t.completed_time = datetime.now()
                # 映射result中的数据到MergeTask字段
                if 'files_before' in result:
                    t.files_before = result['files_before']
                if 'files_after' in result:
                    t.files_after = result['files_after']
                if 'size_saved' in result:
                    t.size_saved = result['size_saved']
            else:
                t.status = 'failed'
                t.error_message = result.get('message', '合并失败') if result else '合并失败:无返回值'
            s.commit()
        except Exception as e:
            try:
                import traceback
                t = s.query(MergeTask).filter(MergeTask.id == tid).first()
                if t:
                    t.status = "failed"
                    # 保存完整错误信息
                    full_error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                    t.error_message = full_error[:5000]
                    t.execution_phase = "error"
                    t.current_operation = f"执行失败: {type(e).__name__}: {str(e)}"
                    s.commit()
            except Exception:
                s.rollback()
        finally:
            s.close()

    threading.Thread(target=_run_merge, args=(task_id, cluster.id), daemon=True).start()

    return {
        "message": "Task started",
        "task_id": task_id,
        "status": "running",
    }


@router.post("/{task_id}/retry")
async def retry_task(task_id: int, db: Session = Depends(get_db)):
    """Retry a failed or cancelled merge task by delegating to execute."""
    # 直接复用执行逻辑；若任务已在运行或已成功，execute_task 会返回相应错误
    return await execute_task(task_id, db)


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
async def get_task_logs(task_id: str, db: Session = Depends(get_db)):
    """Get logs for a specific task"""
    # 先检查是否是测试表任务（UUID格式）
    from app.models.test_table_task import TestTableTask as TestTableTaskModel

    # 尝试作为UUID查找测试表任务
    test_task = db.query(TestTableTaskModel).filter(TestTableTaskModel.id == task_id).first()
    if test_task:
        # 读取持久化日志
        persisted_logs = (
            db.query(TestTableTaskLog)
            .filter(TestTableTaskLog.task_id == task_id)
            .order_by(TestTableTaskLog.timestamp.asc())
            .all()
        )

        if persisted_logs:
            normalized = []
            for row in persisted_logs:
                normalized.append(
                    {
                        "id": row.id,
                        "log_level": row.log_level,
                        "message": _sanitize_log_text(row.message),
                        "details": row.details,
                        "timestamp": row.timestamp,
                        "phase": row.phase,
                        "progress_percentage": row.progress_percentage,
                    }
                )
            return normalized

        # 兼容老任务：没有持久化日志时返回基础信息
        fallback_logs = []
        if test_task.started_time:
            fallback_logs.append({
                "id": 1,
                "log_level": "INFO",
                "message": _sanitize_log_text(f"任务开始执行: {test_task.task_name}"),
                "details": None,
                "timestamp": test_task.started_time,
                "phase": test_task.current_phase,
                "progress_percentage": test_task.progress_percentage,
            })

        if test_task.error_message:
            fallback_logs.append({
                "id": 2,
                "log_level": "ERROR",
                "message": _sanitize_log_text(f"任务执行失败: {test_task.error_message}"),
                "details": test_task.current_operation,
                "timestamp": test_task.completed_time or test_task.started_time,
                "phase": test_task.current_phase,
                "progress_percentage": test_task.progress_percentage,
            })

        if test_task.status == "success" and test_task.completed_time:
            fallback_logs.append({
                "id": 3,
                "log_level": "INFO",
                "message": _sanitize_log_text(
                    f"任务执行成功 - 创建文件: {test_task.hdfs_files_created}, 分区: {test_task.hive_partitions_added}, 大小: {test_task.total_size_mb:.2f}MB"
                ),
                "details": test_task.current_operation,
                "timestamp": test_task.completed_time,
                "phase": test_task.current_phase,
                "progress_percentage": test_task.progress_percentage,
            })

        return fallback_logs

    # 如果不是测试表任务，尝试作为整数ID查找合并任务
    try:
        merge_task_id = int(task_id)
        task = db.query(MergeTask).filter(MergeTask.id == merge_task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # 查询任务日志
        from app.models.task_log import TaskLog

        logs = (
            db.query(TaskLog)
            .filter(TaskLog.task_id == merge_task_id)
            .order_by(TaskLog.timestamp.asc())
            .all()
        )
    except ValueError:
        # 既不是UUID也不是有效的整数ID
        raise HTTPException(status_code=404, detail="Task not found")

    sanitized = []
    for log in logs:
        sanitized.append(
            {
                "id": log.id,
                "log_level": log.log_level,
                "message": _sanitize_log_text(log.message),
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
                "progress_percentage": log.progress_percentage,
            }
        )
    return sanitized


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

        # 统一使用安全合并引擎
        engine = MergeEngineFactory.get_engine(cluster, "safe_hive")

        # 获取预览信息
        preview = engine.get_merge_preview(task)

        return {
            "task_id": task.id,
            "task_name": task.task_name,
            "table": f"{task.database_name}.{task.table_name}",
            "merge_strategy": "unified_safe_merge",
            "preview": preview,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate preview: {str(e)}"
        )


from app.services.scan_service import _sanitize_log_text
