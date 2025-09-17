"""
Hybrid scanner that bridges Hive Metastore and WebHDFS to compute table metrics.

For CI/empty envs it degrades gracefully and returns structured empty results,
but when given real cluster config it will attempt real connections.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, List
from urllib.parse import urlparse

from app.models.table_metric import TableMetric
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.monitor.hive_connector import HiveMetastoreConnector
from app.monitor.webhdfs_scanner import WebHDFSScanner
from app.monitor.cold_data_scanner import SimpleColdDataScanner


class HybridTableScanner:
    def __init__(self, cluster: Any) -> None:
        self.cluster = cluster
        self.hive_connector = self._create_metastore_connector(cluster.hive_metastore_url)
        self.hdfs_scanner: Optional[WebHDFSScanner] = None

    def _create_metastore_connector(self, url: str):
        parsed = urlparse(url)
        scheme = (parsed.scheme or '').lower()
        if scheme.startswith('mysql'):
            return MySQLHiveMetastoreConnector(url)
        elif scheme.startswith('postgres'):
            return HiveMetastoreConnector(url)
        else:
            # default to MySQL connector
            return MySQLHiveMetastoreConnector(url)

    def _initialize_hdfs_scanner(self) -> None:
        self.hdfs_scanner = WebHDFSScanner(
            self.cluster.hdfs_namenode_url,
            user=getattr(self.cluster, 'hdfs_user', 'hdfs') or 'hdfs',
        )

    def test_connections(self) -> Dict[str, Any]:
        logs: List[Dict[str, str]] = []
        suggestions: List[str] = []

        # MetaStore test
        try:
            meta_result = self.hive_connector.test_connection()
            logs.append({"level": "INFO", "message": f"MetaStore: {meta_result.get('status')}"})
        except Exception as e:
            meta_result = {"status": "error", "message": str(e)}
            suggestions.append("检查 MetaStore 连接字符串与网络可达性")

        # HDFS test
        try:
            self._initialize_hdfs_scanner()
            hdfs_ok = self.hdfs_scanner.connect() if self.hdfs_scanner else False
            hdfs_result = {"status": "success" if hdfs_ok else "error", "mode": "real"}
            if self.hdfs_scanner:
                self.hdfs_scanner.disconnect()
        except Exception as e:
            hdfs_result = {"status": "error", "message": str(e), "mode": "real"}
            suggestions.append("核对 HDFS/HttpFS 地址与权限；必要时采用 HttpFS")

        overall = "success" if meta_result.get("status") == "success" else "failed"
        return {
            "overall_status": overall,
            "tests": {"metastore": meta_result, "hdfs": hdfs_result},
            "logs": logs,
            "suggestions": suggestions,
        }

    def scan_database_tables(
        self,
        db: Any,
        database_name: str,
        table_filter: Optional[str] = None,
        max_tables: Optional[int] = None,
        strict_real: bool = False,
    ) -> Dict[str, Any]:
        start = time.time()
        errors: List[str] = []
        total_files = 0
        total_small = 0
        tables_scanned = 0

        try:
            # Get table list from metastore
            metastore_query_start = time.time()
            with self.hive_connector as meta:
                tables = meta.get_tables(database_name)
            metastore_query_time = time.time() - metastore_query_start
            
            # 记录MetaStore查询的详细信息
            original_table_count = len(tables)
            
        except Exception as e:
            return {
                "database": database_name,
                "tables_scanned": 0,
                "total_files": 0,
                "total_small_files": 0,
                "scan_duration": round(time.time() - start, 2),
                "hdfs_mode": "real",
                "errors": [f"MetaStore查询失败: {e}"],
                "metastore_query_time": 0,
                "original_table_count": 0,
                "filtered_table_count": 0,
            }

        # filter and limit
        filtered_by_name = 0
        if table_filter:
            original_count = len(tables)
            tables = [t for t in tables if table_filter in t.get('table_name', '')]
            filtered_by_name = original_count - len(tables)
        
        limited_by_count = 0
        if max_tables and len(tables) > max_tables:
            limited_by_count = len(tables) - max_tables
            tables = tables[:max_tables]
        
        filtered_table_count = len(tables)

        # HDFS scanner initialization with detailed logging
        self._initialize_hdfs_scanner()
        hdfs_ok = False
        hdfs_mode = "error"
        hdfs_connect_time = 0
        
        hdfs_connect_start = time.time()
        try:
            if self.hdfs_scanner:
                hdfs_ok = self.hdfs_scanner.connect()
                hdfs_connect_time = time.time() - hdfs_connect_start
                if hdfs_ok:
                    hdfs_mode = "real"
                else:
                    if strict_real:
                        raise Exception("HDFS连接失败，严格模式已开启，终止扫描")
                    hdfs_mode = "mock"
                    # 如果真实HDFS连接失败，尝试使用Mock模式
                    from app.monitor.mock_hdfs_scanner import MockHDFSScanner
                    self.hdfs_scanner.disconnect()
                    # 传入必要的参数以正确初始化 Mock 扫描器
                    self.hdfs_scanner = MockHDFSScanner(
                        self.cluster.hdfs_namenode_url,
                        user=getattr(self.cluster, 'hdfs_user', 'hdfs') or 'hdfs',
                    )
                    try:
                        self.hdfs_scanner.connect()
                    except Exception:
                        pass
                    hdfs_ok = True
            else:
                # 如果没有HDFS扫描器，直接使用Mock模式
                if strict_real:
                    raise Exception("未初始化HDFS扫描器，严格模式已开启，终止扫描")
                from app.monitor.mock_hdfs_scanner import MockHDFSScanner
                self.hdfs_scanner = MockHDFSScanner(
                    self.cluster.hdfs_namenode_url,
                    user=getattr(self.cluster, 'hdfs_user', 'hdfs') or 'hdfs',
                )
                try:
                    self.hdfs_scanner.connect()
                except Exception:
                    pass
                hdfs_ok = True
                hdfs_mode = "mock"
        except Exception as e:
            hdfs_connect_time = time.time() - hdfs_connect_start
            if strict_real:
                # 严格模式直接抛出错误
                raise
            errors.append(f"HDFS连接错误: {e}")
            # 降级到Mock模式
            try:
                from app.monitor.mock_hdfs_scanner import MockHDFSScanner
                self.hdfs_scanner = MockHDFSScanner(
                    self.cluster.hdfs_namenode_url,
                    user=getattr(self.cluster, 'hdfs_user', 'hdfs') or 'hdfs',
                )
                try:
                    self.hdfs_scanner.connect()
                except Exception:
                    pass
                hdfs_ok = True
                hdfs_mode = "mock"
            except Exception as mock_error:
                errors.append(f"Mock HDFS初始化失败: {mock_error}")

        # 记录扫描统计
        successful_tables = 0
        failed_tables = 0
        partitioned_tables = 0
        total_partitions = 0
        total_scan_time_per_table = 0

        for i, t in enumerate(tables, 1):
            table_start_time = time.time()
            table_name = t.get('table_name', f'table_{i}')
            
            try:
                metrics = {
                    'database_name': database_name,
                    'table_name': table_name,
                    'table_path': t.get('table_path'),
                    'table_type': t.get('table_type'),
                    'storage_format': t.get('storage_format'),
                    'input_format': t.get('input_format'),
                    'output_format': t.get('output_format'),
                    'serde_lib': t.get('serde_lib'),
                    'table_owner': t.get('table_owner'),
                    'table_create_time': t.get('table_create_time'),
                    'is_partitioned': bool(t.get('is_partitioned')),
                    'partition_count': int(t.get('partition_count') or 0),
                }

                # 统计分区表信息
                if metrics['is_partitioned']:
                    partitioned_tables += 1
                    total_partitions += metrics['partition_count']

                files = 0
                small = 0
                total_size = 0
                avg_size = 0.0

                # HDFS文件扫描
                if hdfs_ok and t.get('table_path'):
                    file_scan_start = time.time()
                    try:
                        stat = self.hdfs_scanner.scan_directory(
                            t['table_path'],
                            small_file_threshold=getattr(self.cluster, 'small_file_threshold', None) or 128*1024*1024,
                        )  # type: ignore
                        files = int(stat.get('total_files') or 0)
                        small = int(stat.get('small_files') or 0)
                        total_size = int(stat.get('total_size') or 0)
                        avg_size = float(stat.get('avg_file_size') or 0.0)
                        file_scan_time = time.time() - file_scan_start
                        
                        # 记录每个表的扫描详情（只记录有问题的表）
                        if files == 0:
                            errors.append(f"表{table_name}: 未发现文件数据")
                        elif small / files > 0.8 if files > 0 else False:  # 小文件比例超过80%
                            errors.append(f"表{table_name}: 小文件比例过高({small}/{files}, {small/files*100:.1f}%)")
                            
                    except Exception as scan_error:
                        errors.append(f"表{table_name}文件扫描失败: {scan_error}")

                # persist metric
                from datetime import datetime
                tm = TableMetric(
                    cluster_id=self.cluster.id,
                    database_name=metrics['database_name'],
                    table_name=metrics['table_name'],
                    table_path=metrics['table_path'],
                    table_type=metrics.get('table_type'),
                    storage_format=metrics.get('storage_format'),
                    input_format=metrics.get('input_format'),
                    output_format=metrics.get('output_format'),
                    serde_lib=metrics.get('serde_lib'),
                    table_owner=metrics.get('table_owner'),
                    table_create_time=metrics.get('table_create_time'),
                    total_files=files,
                    small_files=small,
                    total_size=total_size,
                    avg_file_size=avg_size,
                    is_partitioned=1 if metrics['is_partitioned'] else 0,
                    partition_count=metrics['partition_count'],
                    scan_time=datetime.utcnow(),
                )
                db.add(tm)
                db.commit()
                
                tables_scanned += 1
                successful_tables += 1
                total_files += files
                total_small += small
                
                table_scan_time = time.time() - table_start_time
                total_scan_time_per_table += table_scan_time
                
            except Exception as e:
                failed_tables += 1
                db.rollback()
                table_scan_time = time.time() - table_start_time
                error_msg = f"表{table_name}处理失败: {e} (耗时: {table_scan_time:.2f}秒)"
                errors.append(error_msg)

        # 清理HDFS连接
        if self.hdfs_scanner:
            try:
                self.hdfs_scanner.disconnect()
            except Exception:
                pass

        # 计算性能指标
        total_scan_time = time.time() - start
        avg_table_scan_time = total_scan_time_per_table / max(successful_tables, 1)
        
        return {
            "database": database_name,
            "tables_scanned": tables_scanned,
            "successful_tables": successful_tables,
            "failed_tables": failed_tables,
            "partitioned_tables": partitioned_tables,
            "total_partitions": total_partitions,
            "total_files": total_files,
            "total_small_files": total_small,
            "scan_duration": round(total_scan_time, 2),
            "avg_table_scan_time": round(avg_table_scan_time, 3),
            "hdfs_mode": hdfs_mode,
            "hdfs_connect_time": round(hdfs_connect_time, 2),
            "metastore_query_time": round(metastore_query_time, 2),
            "original_table_count": original_table_count,
            "filtered_table_count": filtered_table_count,
            "filtered_by_name": filtered_by_name,
            "limited_by_count": limited_by_count,
            "errors": errors,
        }

    def scan_table(self, db: Any, database_name: str, table_info: Dict[str, Any], strict_real: bool = False) -> Dict[str, Any]:
        start = time.time()
        self._initialize_hdfs_scanner()
        hdfs_ok = False
        try:
            hdfs_ok = self.hdfs_scanner.connect() if self.hdfs_scanner else False
        except Exception:
            pass
        if strict_real and not hdfs_ok:
            raise Exception("HDFS连接失败，严格模式已开启，终止扫描")
        files = small = total_size = 0
        avg_size = 0.0
        try:
            path = table_info.get('table_path') if isinstance(table_info, dict) else None
            if hdfs_ok and path:
                stat = self.hdfs_scanner.scan_directory(
                    path,
                    small_file_threshold=getattr(self.cluster, 'small_file_threshold', None) or 128*1024*1024,
                )  # type: ignore
                files = int(stat.get('total_files') or 0)
                small = int(stat.get('small_files') or 0)
                total_size = int(stat.get('total_size') or 0)
                avg_size = float(stat.get('avg_file_size') or 0.0)
        finally:
            if self.hdfs_scanner:
                try:
                    self.hdfs_scanner.disconnect()
                except Exception:
                    pass

        return {
            "table_name": table_info.get("table_name") if isinstance(table_info, dict) else None,
            "total_files": files,
            "small_files": small,
            "small_file_ratio": round((small / files * 100) if files else 0.0, 2),
            "avg_file_size": avg_size,
            "total_size": total_size,
            "is_partitioned": bool(table_info.get('is_partitioned')) if isinstance(table_info, dict) else False,
            "partition_count": int(table_info.get('partition_count') or 0) if isinstance(table_info, dict) else 0,
            "scan_mode": "real" if hdfs_ok else "error",
            "scan_time": None,
            "scan_duration": round(time.time() - start, 2),
        }

    def scan_table_with_coldness_check(self, db: Any, database_name: str, table_info: Dict[str, Any], strict_real: bool = False, cold_threshold_days: int = 90) -> Dict[str, Any]:
        """
        在现有表扫描中同时检查冷数据
        Args:
            db: 数据库会话
            database_name: 数据库名
            table_info: 表信息字典
            strict_real: 严格实连模式
            cold_threshold_days: 冷数据天数阈值
        Returns:
            包含冷数据信息的扫描结果
        """
        # 1. 执行原有的小文件扫描
        result = self.scan_table(db, database_name, table_info, strict_real)

        # 2. 新增：冷数据检查
        try:
            coldness_info = self._check_table_coldness(database_name, table_info['table_name'], cold_threshold_days)

            # 将冷数据信息添加到结果中
            result.update({
                'last_access_time': coldness_info['last_access_time'],
                'days_since_access': coldness_info['days_since_access'],
                'is_cold_data': coldness_info['is_cold'],
                'cold_threshold_days': cold_threshold_days
            })

        except Exception as e:
            # 冷数据检查失败时记录错误，但不影响主扫描结果
            result.update({
                'last_access_time': None,
                'days_since_access': None,
                'is_cold_data': False,
                'cold_data_error': str(e)
            })

        return result

    def _check_table_coldness(self, database_name: str, table_name: str, cold_threshold_days: int = 90) -> Dict[str, Any]:
        """
        检查单个表的冷热程度
        Args:
            database_name: 数据库名
            table_name: 表名
            cold_threshold_days: 冷数据天数阈值
        Returns:
            冷数据检查结果
        """
        from datetime import datetime

        try:
            # 获取表的最后访问时间
            last_access_time = None
            if hasattr(self.hive_connector, 'get_table_last_access_time'):
                last_access_time = self.hive_connector.get_table_last_access_time(database_name, table_name)

            current_time = datetime.now()

            if last_access_time:
                days_since_access = (current_time - last_access_time).days
            else:
                # 如果没有访问时间记录，标记为很久未访问
                days_since_access = 999

            is_cold = days_since_access > cold_threshold_days

            return {
                'last_access_time': last_access_time.isoformat() if last_access_time else None,
                'days_since_access': days_since_access,
                'is_cold': is_cold
            }

        except Exception as e:
            raise Exception(f"冷数据检查失败: {str(e)}")

    def scan_cold_data_for_cluster(self, db: Any, cold_threshold_days: int = 90) -> Dict[str, Any]:
        """
        为整个集群执行冷数据扫描
        Args:
            db: 数据库会话
            cold_threshold_days: 冷数据天数阈值
        Returns:
            集群冷数据扫描结果
        """
        try:
            cold_scanner = SimpleColdDataScanner(self.cluster, cold_threshold_days)
            return cold_scanner.scan_cold_tables(db)

        except Exception as e:
            return {
                'error': f'集群冷数据扫描失败: {str(e)}',
                'cluster_id': getattr(self.cluster, 'id', None),
                'cluster_name': getattr(self.cluster, 'name', 'Unknown'),
                'scan_timestamp': time.time()
            }
