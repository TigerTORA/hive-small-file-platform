from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List
from app.config.database import get_db
from app.models.cluster import Cluster
from app.models.table_metric import TableMetric
from app.schemas.cluster import ClusterCreate, ClusterResponse, ClusterUpdate
from app.monitor.hybrid_table_scanner import HybridTableScanner
from app.services.cluster_status_service import cluster_status_service
from app.services.enhanced_connection_service import enhanced_connection_service

router = APIRouter()

@router.get("/", response_model=list[ClusterResponse])
async def list_clusters(db: Session = Depends(get_db)):
    """List all clusters"""
    clusters = db.query(Cluster).all()
    return clusters

@router.post("/", response_model=ClusterResponse)
async def create_cluster(cluster: ClusterCreate, validate_connection: bool = False, db: Session = Depends(get_db)):
    """Create a new cluster
    Args:
        validate_connection: If True, test connections before creating the cluster
    """
    # 检查集群名称是否已存在
    existing = db.query(Cluster).filter(Cluster.name == cluster.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Cluster name '{cluster.name}' already exists")
    
    # 验证URL格式
    if not cluster.hive_metastore_url.startswith(('mysql://', 'postgresql://', 'sqlite://')):
        raise HTTPException(status_code=400, detail="Invalid MetaStore URL format. Must start with mysql://, postgresql://, or sqlite://")
    
    if not cluster.hdfs_namenode_url.startswith(('hdfs://', 'http://', 'https://')):
        raise HTTPException(status_code=400, detail="Invalid HDFS URL format. Must start with hdfs://, http://, or https://")
    
    # 可选的连接验证
    validation_results = None
    if validate_connection:
        try:
            # 创建临时集群对象用于连接测试
            temp_cluster = Cluster(**cluster.dict())
            scanner = HybridTableScanner(temp_cluster)
            validation_results = scanner.test_connections()
            
            # 检查连接结果
            overall_status = validation_results.get('overall_status', 'unknown')
            tests = validation_results.get('tests', {})
            metastore_test = tests.get('metastore', {})
            hdfs_test = tests.get('hdfs', {})
            
            metastore_ok = metastore_test.get('status') == 'success'
            hdfs_ok = hdfs_test.get('status') == 'success'
            
            if not metastore_ok:
                # MetaStore连接失败是致命的，不能创建集群
                error_msg = metastore_test.get('message', 'Unknown error')
                logs = validation_results.get('logs', [])
                suggestions = validation_results.get('suggestions', [])
                
                raise HTTPException(
                    status_code=400, 
                    detail={
                        "error": f"MetaStore connection failed: {error_msg}",
                        "validation_results": validation_results,
                        "logs": logs,
                        "suggestions": suggestions
                    }
                )
            
            if not hdfs_ok and hdfs_test.get('mode') != 'mock':
                # HDFS连接失败会记录警告但不阻止创建
                validation_results['warning'] = f"HDFS connection failed but cluster will be created: {hdfs_test.get('message', 'Unknown error')}"
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": f"Connection validation failed: {str(e)}",
                    "logs": [{"level": "ERROR", "message": str(e)}],
                    "suggestions": [
                        "请检查集群配置是否正确",
                        "确认网络连接正常",
                        "验证用户权限设置"
                    ]
                }
            )
    
    try:
        db_cluster = Cluster(**cluster.dict())
        db.add(db_cluster)
        db.commit()
        db.refresh(db_cluster)
        
        # 如果有验证结果，包含在响应中
        if validation_results:
            response_data = {
                "id": db_cluster.id,
                "name": db_cluster.name,
                "description": db_cluster.description,
                "hive_metastore_url": db_cluster.hive_metastore_url,
                "hdfs_namenode_url": db_cluster.hdfs_namenode_url,
                "created_at": db_cluster.created_at.isoformat() if db_cluster.created_at else None,
                "updated_at": db_cluster.updated_at.isoformat() if db_cluster.updated_at else None,
                "validation_results": validation_results
            }
            return response_data
        
        return db_cluster
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create cluster: {str(e)}")

@router.get("/health-metrics")
async def get_health_metrics(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """获取集群健康指标统计"""
    try:
        metrics = cluster_status_service.get_cluster_health_metrics(db, days)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health metrics: {str(e)}")

@router.post("/batch-health-check")
async def batch_health_check(
    cluster_ids: List[int] = None,
    parallel_limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """批量健康检查"""
    try:
        results = await cluster_status_service.batch_health_check(
            db, cluster_ids, parallel_limit
        )

        successful_checks = sum(1 for r in results.values() if r.get('overall_status') != 'error')
        total_checks = len(results)

        return {
            "total_clusters": total_checks,
            "successful_checks": successful_checks,
            "failed_checks": total_checks - successful_checks,
            "parallel_limit": parallel_limit,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch health check failed: {str(e)}")

@router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(cluster_id: int, db: Session = Depends(get_db)):
    """Get cluster by ID"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster

@router.get("/{cluster_id}/stats")
async def get_cluster_stats(cluster_id: int, db: Session = Depends(get_db)):
    """Get cluster statistics"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        # 统计数据库数量 (通过distinct database_name)
        total_databases = db.query(func.count(func.distinct(TableMetric.database_name)))\
            .filter(TableMetric.cluster_id == cluster_id).scalar() or 0
        
        # 统计总表数
        total_tables = db.query(func.count(TableMetric.id))\
            .filter(TableMetric.cluster_id == cluster_id).scalar() or 0
        
        # 统计有小文件的表数
        small_file_tables = db.query(func.count(TableMetric.id))\
            .filter(TableMetric.cluster_id == cluster_id)\
            .filter(TableMetric.small_files > 0).scalar() or 0
        
        # 统计小文件总数
        total_small_files = db.query(func.sum(TableMetric.small_files))\
            .filter(TableMetric.cluster_id == cluster_id).scalar() or 0
        
        return {
            "total_databases": total_databases,
            "total_tables": total_tables,
            "small_file_tables": small_file_tables,
            "total_small_files": total_small_files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cluster stats: {str(e)}")

@router.get("/{cluster_id}/databases")
async def get_cluster_databases(cluster_id: int, db: Session = Depends(get_db)):
    """Get databases for cluster"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        # 从已扫描的表指标中获取数据库列表
        databases = db.query(TableMetric.database_name.distinct())\
            .filter(TableMetric.cluster_id == cluster_id)\
            .all()
        
        # 转换为字符串列表
        database_list = [db_row[0] for db_row in databases]
        
        # 如果没有扫描过的数据库，尝试连接MetaStore获取
        if not database_list:
            try:
                scanner = HybridTableScanner(cluster)
                from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
                with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as metastore_connector:
                    database_list = metastore_connector.get_databases()
            except Exception as e:
                # 如果连接失败，返回空列表和警告
                return {
                    "databases": [],
                    "warning": f"Failed to fetch databases from MetaStore: {str(e)}",
                    "suggestion": "Please run a database scan first"
                }
        
        return database_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cluster databases: {str(e)}")

@router.put("/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(cluster_id: int, cluster_update: ClusterUpdate, db: Session = Depends(get_db)):
    """Update cluster configuration"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    # 只更新提供的字段
    update_data = cluster_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cluster, field, value)
    
    try:
        db.commit()
        db.refresh(cluster)
        return cluster
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update cluster: {str(e)}")

@router.delete("/{cluster_id}")
async def delete_cluster(cluster_id: int, db: Session = Depends(get_db)):
    """Delete cluster and all related data"""
    # 首先检查集群是否存在，但不加载关系
    cluster_result = db.execute("SELECT name FROM clusters WHERE id = :cluster_id", {"cluster_id": cluster_id}).fetchone()
    if not cluster_result:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster_name = cluster_result[0]

    try:
        # 检查关联数据数量
        table_count_result = db.execute("SELECT COUNT(*) FROM table_metrics WHERE cluster_id = :cluster_id", {"cluster_id": cluster_id}).fetchone()
        scan_task_count_result = db.execute("SELECT COUNT(*) FROM scan_tasks WHERE cluster_id = :cluster_id", {"cluster_id": cluster_id}).fetchone()

        table_count = table_count_result[0] if table_count_result else 0
        scan_task_count = scan_task_count_result[0] if scan_task_count_result else 0

        # 使用原生SQL进行级联删除，避免SQLAlchemy的关系管理干扰
        db.execute("DELETE FROM scan_tasks WHERE cluster_id = :cluster_id", {"cluster_id": cluster_id})
        db.execute("DELETE FROM table_metrics WHERE cluster_id = :cluster_id", {"cluster_id": cluster_id})
        db.execute("DELETE FROM clusters WHERE id = :cluster_id", {"cluster_id": cluster_id})

        db.commit()

        total_deleted = table_count + scan_task_count
        return {"message": f"Cluster '{cluster_name}' and {total_deleted} related records deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete cluster: {str(e)}")

@router.post("/{cluster_id}/test")
async def test_cluster_connection(
    cluster_id: int,
    mode: str = "mock",
    force_refresh: bool = False,
    db: Session = Depends(get_db)
):
    """Test cluster connections with detailed diagnostics and caching
    Args:
        mode: 'mock' for mock testing, 'real' for real connection testing
        force_refresh: If True, bypass cache and perform fresh test
    """
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        if mode == "real":
            # 使用状态管理服务进行连接测试（支持缓存）
            results = await cluster_status_service.test_cluster_connections(
                db, cluster_id, force_refresh=force_refresh
            )

            return {
                "cluster_id": cluster_id,
                "cluster_name": cluster.name,
                "test_mode": "real",
                "overall_status": results.get("overall_status", "unknown"),
                "test_time": results.get("test_time"),
                "tests": results.get("tests", {}),
                "logs": results.get("logs", []),
                "suggestions": results.get("suggestions", []),
                "cached": results.get("cached", False),
                "connections": results  # 保持向后兼容
            }
        else:
            # Mock模式
            mock_results = {
                "overall_status": "success",
                "test_time": datetime.now().isoformat(),
                "tests": {
                    "metastore": {"status": "success", "mode": "mock"},
                    "hdfs": {"status": "success", "mode": "mock"},
                    "hiveserver2": {"status": "success", "mode": "mock"}
                },
                "logs": [{"level": "INFO", "message": "Mock test completed successfully"}],
                "suggestions": [],
                "cached": False
            }

            return {
                "cluster_id": cluster_id,
                "cluster_name": cluster.name,
                "test_mode": "mock",
                **mock_results,
                "connections": mock_results  # 保持向后兼容
            }
    except Exception as e:
        # 记录测试失败状态
        cluster_status_service.record_status_change(
            db, cluster_id, cluster.status,
            reason="connection_test_failed",
            message=f"Connection test failed: {str(e)}"
        )

        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "test_mode": mode,
            "overall_status": "failed",
            "test_time": datetime.now().isoformat(),
            "tests": {},
            "logs": [
                {"level": "ERROR", "message": f"Connection test failed: {str(e)}"}
            ],
            "suggestions": [
                "请检查集群配置是否正确",
                "确认网络连接正常",
                "验证用户权限设置"
            ],
            "cached": False,
            "error": str(e)
        }

@router.post("/{cluster_id}/test-real")
async def test_cluster_connection_real(cluster_id: int, db: Session = Depends(get_db)):
    """Test real cluster connections with intelligent fallback"""
    return await test_cluster_connection(cluster_id, mode="real", db=db)

@router.get("/{cluster_id}/test-connection")
async def get_cluster_test_connection(cluster_id: int, mode: str = "mock", db: Session = Depends(get_db)):
    """Legacy GET endpoint for cluster connection testing (for backward compatibility)"""
    return await test_cluster_connection(cluster_id, mode=mode, db=db)

@router.post("/test-connection")
async def test_connection_without_cluster(cluster: ClusterCreate):
    """Test connection to cluster configuration without creating a cluster
    
    This endpoint allows testing cluster connectivity before actually creating the cluster.
    It provides detailed diagnostic information and suggestions for connection issues.
    """
    # 验证URL格式
    if not cluster.hive_metastore_url.startswith(('mysql://', 'postgresql://', 'sqlite://')):
        return {
            "overall_status": "failed",
            "test_time": datetime.now().isoformat(),
            "tests": {},
            "logs": [{"level": "ERROR", "message": "Invalid MetaStore URL format"}],
            "suggestions": ["MetaStore URL must start with mysql://, postgresql://, or sqlite://"],
            "error": "Invalid MetaStore URL format"
        }
    
    if not cluster.hdfs_namenode_url.startswith(('hdfs://', 'http://', 'https://')):
        return {
            "overall_status": "failed", 
            "test_time": datetime.now().isoformat(),
            "tests": {},
            "logs": [{"level": "ERROR", "message": "Invalid HDFS URL format"}],
            "suggestions": ["HDFS URL must start with hdfs://, http://, or https://"],
            "error": "Invalid HDFS URL format"
        }
    
    try:
        # 创建临时集群对象用于连接测试
        temp_cluster = Cluster(**cluster.dict())
        scanner = HybridTableScanner(temp_cluster)
        results = scanner.test_connections()
        
        return {
            "cluster_name": cluster.name,
            "test_mode": "real",
            "overall_status": results.get("overall_status", "unknown"),
            "test_time": results.get("test_time"),
            "tests": results.get("tests", {}),
            "logs": results.get("logs", []),
            "suggestions": results.get("suggestions", []),
            "connections": results  # 保持向后兼容
        }
    except Exception as e:
        return {
            "cluster_name": cluster.name,
            "test_mode": "real",
            "overall_status": "failed",
            "test_time": datetime.now().isoformat(),
            "tests": {},
            "logs": [
                {"level": "ERROR", "message": f"Connection test failed: {str(e)}"}
            ],
            "suggestions": [
                "请检查集群配置是否正确",
                "确认网络连接正常",
                "验证用户权限设置",
                "检查防火墙设置是否允许连接"
            ],
            "error": str(e)
        }

@router.get("/health-check")
async def check_all_clusters_health(db: Session = Depends(get_db)):
    """Check health of all clusters - DRAFT VERSION"""
    all_clusters = db.query(Cluster).all()
    health_results = []
    
    for cluster in all_clusters:
        try:
            scanner = HybridTableScanner(cluster)
            test_results = scanner.test_connections()
            
            # Simple logic to determine health
            metastore_healthy = test_results.get("metastore_connection", False)
            hdfs_healthy = test_results.get("hdfs_connection", False)
            overall_healthy = metastore_healthy and hdfs_healthy
            
            health_status = {
                "cluster_id": cluster.id,
                "cluster_name": cluster.name,
                "overall_health": "healthy" if overall_healthy else "unhealthy",
                "metastore_status": "ok" if metastore_healthy else "failed",
                "hdfs_status": "ok" if hdfs_healthy else "failed",
                "last_check": "2025-01-08T10:00:00Z",  # hardcoded for now
                "details": test_results
            }
            
        except Exception as e:
            health_status = {
                "cluster_id": cluster.id,
                "cluster_name": cluster.name,
                "overall_health": "error",
                "metastore_status": "error",
                "hdfs_status": "error", 
                "last_check": "2025-01-08T10:00:00Z",
                "error_message": str(e)
            }
            
        health_results.append(health_status)
    
    return {
        "total_clusters": len(all_clusters),
        "healthy_count": len([r for r in health_results if r["overall_health"] == "healthy"]),
        "clusters": health_results
    }

@router.post("/{cluster_id}/scan-all")
async def scan_all_cluster_tables(
    cluster_id: int,
    max_tables_per_db: int = Query(20, description="Maximum tables to scan per database"),
    max_databases: int = Query(10, description="Maximum databases to scan"),
    db: Session = Depends(get_db)
):
    """
    批量扫描集群中的所有数据库和表
    
    这个端点会:
    1. 获取集群的所有数据库列表
    2. 对每个数据库扫描指定数量的表
    3. 将扫描结果存储到table_metrics表中，用于时序数据分析
    4. 返回扫描进度和统计信息
    """
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    try:
        from datetime import datetime
        import time
        
        scan_start_time = datetime.now()
        scanner = HybridTableScanner(cluster)
        
        # 获取所有数据库
        with MySQLHiveMetastoreConnector(cluster.hive_metastore_url) as metastore_connector:
            databases = metastore_connector.get_databases()
            
        if len(databases) > max_databases:
            databases = databases[:max_databases]
        
        scan_results = {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "scan_start_time": scan_start_time.isoformat(),
            "total_databases": len(databases),
            "scanned_databases": 0,
            "total_tables_scanned": 0,
            "total_files_found": 0,
            "total_small_files": 0,
            "databases": [],
            "errors": []
        }
        
        # 扫描每个数据库
        for db_name in databases:
            try:
                print(f"扫描数据库: {db_name}")
                
                # 扫描数据库中的表
                db_result = scanner.scan_database_tables(
                    db, db_name, 
                    table_filter=None,
                    max_tables=max_tables_per_db
                )
                
                if db_result.get("status") == "completed":
                    scan_results["scanned_databases"] += 1
                    scan_results["total_tables_scanned"] += db_result.get("tables_scanned", 0)
                    scan_results["total_files_found"] += db_result.get("total_files", 0)
                    scan_results["total_small_files"] += db_result.get("total_small_files", 0)
                    
                    scan_results["databases"].append({
                        "database_name": db_name,
                        "tables_scanned": db_result.get("tables_scanned", 0),
                        "total_files": db_result.get("total_files", 0),
                        "small_files": db_result.get("total_small_files", 0),
                        "scan_time": db_result.get("scan_duration", 0),
                        "status": "completed"
                    })
                else:
                    scan_results["databases"].append({
                        "database_name": db_name,
                        "status": "failed",
                        "error": db_result.get("error", "Unknown error")
                    })
                    scan_results["errors"].append(f"Database {db_name}: {db_result.get('error', 'Unknown error')}")
                    
            except Exception as db_error:
                error_msg = f"Failed to scan database {db_name}: {str(db_error)}"
                scan_results["errors"].append(error_msg)
                scan_results["databases"].append({
                    "database_name": db_name,
                    "status": "error",
                    "error": str(db_error)
                })
                print(f"数据库扫描错误: {error_msg}")
        
        scan_end_time = datetime.now()
        scan_duration = (scan_end_time - scan_start_time).total_seconds()
        
        scan_results.update({
            "scan_end_time": scan_end_time.isoformat(),
            "total_scan_duration": round(scan_duration, 2),
            "status": "completed",
            "summary": {
                "databases_scanned": scan_results["scanned_databases"],
                "databases_failed": len(databases) - scan_results["scanned_databases"],
                "total_tables": scan_results["total_tables_scanned"],
                "total_files": scan_results["total_files_found"],
                "small_files": scan_results["total_small_files"],
                "small_file_ratio": round(
                    (scan_results["total_small_files"] / scan_results["total_files_found"] * 100) 
                    if scan_results["total_files_found"] > 0 else 0, 2
                )
            }
        })
        
        return scan_results

    except Exception as e:
        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "status": "failed",
            "error": str(e),
            "scan_start_time": datetime.now().isoformat(),
            "total_databases": 0,
            "scanned_databases": 0,
            "total_tables_scanned": 0,
            "databases": [],
            "errors": [str(e)]
        }

@router.get("/{cluster_id}/status")
async def get_cluster_status(cluster_id: int, db: Session = Depends(get_db)):
    """获取集群状态信息"""
    try:
        status_info = cluster_status_service.get_cluster_connection_summary(db, cluster_id)
        return status_info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cluster status: {str(e)}")

@router.get("/{cluster_id}/status-history")
async def get_cluster_status_history(
    cluster_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取集群状态变更历史"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        history = cluster_status_service.get_cluster_status_history(db, cluster_id, limit)
        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "total_records": len(history),
            "history": [
                {
                    "id": record.id,
                    "from_status": record.from_status,
                    "to_status": record.to_status,
                    "reason": record.reason,
                    "message": record.message,
                    "created_at": record.created_at.isoformat(),
                    "connection_test_result": record.connection_test_result
                }
                for record in history
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status history: {str(e)}")

@router.post("/{cluster_id}/status")
async def update_cluster_status(
    cluster_id: int,
    new_status: str,
    reason: str = None,
    message: str = None,
    db: Session = Depends(get_db)
):
    """手动更新集群状态"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # 验证状态值
    valid_statuses = ['active', 'inactive', 'error', 'testing', 'maintenance']
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    try:
        history_record = cluster_status_service.record_status_change(
            db, cluster_id, new_status, reason or "manual", message
        )

        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "old_status": history_record.from_status,
            "new_status": history_record.to_status,
            "reason": history_record.reason,
            "message": history_record.message,
            "updated_at": history_record.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update cluster status: {str(e)}")

@router.delete("/{cluster_id}/cache")
async def clear_cluster_cache(cluster_id: int, db: Session = Depends(get_db)):
    """清除集群连接状态缓存"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster_status_service.clear_connection_cache(cluster_id)

    return {
        "cluster_id": cluster_id,
        "cluster_name": cluster.name,
        "message": "Connection cache cleared successfully"
    }

@router.get("/{cluster_id}/connection-history")
async def get_connection_history(
    cluster_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """获取集群连接历史记录"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        history = enhanced_connection_service.get_connection_history(cluster_id, limit)
        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "total_records": len(history),
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connection history: {str(e)}")

@router.get("/{cluster_id}/connection-statistics")
async def get_connection_statistics(
    cluster_id: int,
    hours: int = Query(24, ge=1, le=168),  # 最多7天
    db: Session = Depends(get_db)
):
    """获取集群连接统计信息"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        statistics = enhanced_connection_service.get_connection_statistics(cluster_id, hours)
        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            **statistics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connection statistics: {str(e)}")

@router.post("/{cluster_id}/test-enhanced")
async def test_cluster_connection_enhanced(
    cluster_id: int,
    connection_types: List[str] = Query(
        default=None,
        description="Connection types to test: metastore, hdfs, hiveserver2"
    ),
    force_refresh: bool = Query(False, description="Force refresh, bypass cache"),
    db: Session = Depends(get_db)
):
    """增强的集群连接测试，支持指定连接类型和详细诊断"""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # 验证连接类型参数
    valid_types = ['metastore', 'hdfs', 'hiveserver2']
    if connection_types:
        invalid_types = [t for t in connection_types if t not in valid_types]
        if invalid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid connection types: {invalid_types}. Valid types: {valid_types}"
            )

    try:
        results = await cluster_status_service.test_cluster_connections(
            db, cluster_id, force_refresh, connection_types
        )

        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "test_mode": "enhanced",
            "force_refresh": force_refresh,
            "requested_types": connection_types or valid_types,
            **results
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced connection test failed: {str(e)}")

