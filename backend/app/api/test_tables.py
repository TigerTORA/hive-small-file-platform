"""
测试表管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.test_table import (
    SCENARIO_CONFIGS,
    TestTableConfig,
    TestTableCreateRequest,
    TestTableDeleteRequest,
    TestTableScenario,
    TestTableTaskResponse,
    TestTableVerifyRequest,
    TestTableVerifyResult,
)
from app.services.test_table_service import test_table_service

router = APIRouter()


@router.post("/check-timeout")
async def check_timeout_tasks(db: Session = Depends(get_db)):
    """检测并标记超时任务"""
    marked_count = test_table_service.check_and_mark_timeout_tasks(db, timeout_minutes=30)
    return {
        "marked_timeout_tasks": marked_count,
        "message": f"已标记 {marked_count} 个超时任务为失败状态"
    }


@router.get("/scenarios")
async def get_test_scenarios():
    """获取预设测试场景"""
    scenarios = {}
    for scenario, config in SCENARIO_CONFIGS.items():
        scenarios[scenario.value] = {
            "name": scenario.value,
            "description": _get_scenario_description(scenario),
            "config": config.dict(),
            "estimated_files": config.get_total_files(),
            "estimated_size_mb": config.get_estimated_size_mb(),
            "estimated_duration_minutes": config.get_estimated_duration_minutes(),
        }

    return {
        "scenarios": scenarios,
        "recommendations": {
            "development": "light",
            "testing": "default",
            "performance_test": "heavy",
            "stress_test": "extreme"
        }
    }


@router.post("/create", response_model=TestTableTaskResponse)
async def create_test_table(
    request: TestTableCreateRequest,
    db: Session = Depends(get_db)
):
    """创建测试表"""
    try:
        # 如果使用预设场景，应用场景配置
        if request.config.scenario != TestTableScenario.CUSTOM:
            scenario_config = SCENARIO_CONFIGS.get(request.config.scenario)
            if scenario_config:
                # 使用copy()创建副本,避免污染全局单例
                config_copy = scenario_config.copy(update={
                    'table_name': request.config.table_name,
                    'database_name': request.config.database_name,
                    'hdfs_base_path': request.config.hdfs_base_path,
                    'data_generation_mode': request.config.data_generation_mode
                })
                request.config = config_copy

        task = await test_table_service.create_test_table(request, db)
        return task

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建测试表失败: {str(e)}")


@router.get("/tasks", response_model=list[TestTableTaskResponse])
async def list_test_table_tasks(db: Session = Depends(get_db)):
    """获取测试表任务列表"""
    return test_table_service.list_active_tasks(db)


@router.get("/tasks/{task_id}", response_model=TestTableTaskResponse)
async def get_test_table_task(task_id: str, db: Session = Depends(get_db)):
    """获取指定任务详情"""
    task = test_table_service.get_task(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("/delete")
async def delete_test_table(
    request: TestTableDeleteRequest,
    db: Session = Depends(get_db)
):
    """删除测试表"""
    try:
        result = await test_table_service.delete_test_table(request, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除测试表失败: {str(e)}")


@router.post("/verify", response_model=TestTableVerifyResult)
async def verify_test_table(
    request: TestTableVerifyRequest,
    db: Session = Depends(get_db)
):
    """验证测试表"""
    try:
        result = await test_table_service.verify_test_table(request, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证测试表失败: {str(e)}")


@router.get("/config/validate")
async def validate_test_config(
    table_name: str = Query(..., description="表名"),
    database_name: str = Query(..., description="数据库名"),
    hdfs_base_path: str = Query(..., description="HDFS路径"),
    partition_count: int = Query(..., ge=1, le=1000, description="分区数"),
    files_per_partition: int = Query(..., ge=1, le=1000, description="每分区文件数"),
    file_size_kb: int = Query(..., ge=1, le=1024, description="文件大小KB")
):
    """验证测试配置"""
    try:
        config = TestTableConfig(
            table_name=table_name,
            database_name=database_name,
            hdfs_base_path=hdfs_base_path,
            partition_count=partition_count,
            files_per_partition=files_per_partition,
            file_size_kb=file_size_kb,
            scenario=TestTableScenario.CUSTOM
        )

        return {
            "valid": True,
            "config": config.dict(),
            "estimated_files": config.get_total_files(),
            "estimated_size_mb": config.get_estimated_size_mb(),
            "estimated_duration_minutes": config.get_estimated_duration_minutes(),
            "warnings": _get_config_warnings(config)
        }

    except ValueError as e:
        return {
            "valid": False,
            "error": str(e),
            "config": None
        }


@router.get("/cluster/{cluster_id}/existing-tables")
async def get_cluster_test_tables(
    cluster_id: int,
    db: Session = Depends(get_db)
):
    """获取集群中的测试表"""
    from app.models.cluster import Cluster

    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="集群不存在")

    try:
        # 这里可以查询集群中以 test_ 开头的表
        # 暂时返回模拟数据，实际实现需要连接Hive MetaStore
        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "test_tables": [
                {
                    "database_name": "test_db",
                    "table_name": "test_small_files_table",
                    "partition_count": 10,
                    "estimated_files": 1000,
                    "created_time": "2024-01-01T00:00:00Z",
                    "size_mb": 50.0
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询测试表失败: {str(e)}")


def _get_scenario_description(scenario: TestTableScenario) -> str:
    """获取场景描述"""
    descriptions = {
        TestTableScenario.LIGHT: "轻量测试 - 适合开发环境验证基本功能",
        TestTableScenario.DEFAULT: "默认测试 - 适合完整功能测试",
        TestTableScenario.HEAVY: "重度测试 - 适合性能测试，大量小文件场景",
        TestTableScenario.EXTREME: "极限测试 - 仅限高性能测试环境，慎用！",
        TestTableScenario.CUSTOM: "自定义配置 - 根据需求自定义参数"
    }
    return descriptions.get(scenario, "未知场景")


def _get_config_warnings(config: TestTableConfig) -> list[str]:
    """获取配置警告"""
    warnings = []

    total_files = config.get_total_files()
    total_size_mb = config.get_estimated_size_mb()

    if total_files > 5000:
        warnings.append(f"文件数量较大 ({total_files})，可能影响集群性能")

    if total_files > 10000:
        warnings.append("⚠️ 极大文件数量！建议仅在专用测试环境使用")

    if total_size_mb > 500:
        warnings.append(f"预估大小较大 ({total_size_mb:.1f}MB)，请确保有足够磁盘空间")

    if config.hdfs_base_path.startswith('/user/'):
        if 'prod' in config.hdfs_base_path.lower():
            warnings.append("⚠️ 路径包含 'prod'，请确认不是生产环境路径")

    if config.partition_count > 50:
        warnings.append("分区数较多，创建时间可能较长")

    return warnings
