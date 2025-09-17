"""
增强的连接检测服务
提供连接超时控制、重试机制、故障识别和连接池管理功能
"""
import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from urllib.parse import urlparse
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from app.models.cluster import Cluster
from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
from app.monitor.hive_connector import HiveMetastoreConnector
from app.monitor.webhdfs_scanner import WebHDFSScanner

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """连接类型枚举"""
    METASTORE = "metastore"
    HDFS = "hdfs"
    HIVESERVER2 = "hiveserver2"


class FailureType(Enum):
    """故障类型枚举"""
    NETWORK_TIMEOUT = "network_timeout"
    CONNECTION_REFUSED = "connection_refused"
    AUTHENTICATION_FAILED = "authentication_failed"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DNS_RESOLUTION_FAILED = "dns_resolution_failed"
    SSL_ERROR = "ssl_error"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ConnectionResult:
    """连接测试结果"""
    connection_type: ConnectionType
    status: str  # success, failed, timeout
    response_time_ms: float
    failure_type: Optional[FailureType] = None
    error_message: Optional[str] = None
    attempt_count: int = 1
    retry_count: int = 0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ConnectionConfig:
    """连接配置"""
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0  # 指数退避倍数
    health_check_interval: int = 300  # 5分钟
    circuit_breaker_threshold: int = 5  # 连续失败阈值


class EnhancedConnectionService:
    """增强的连接检测服务"""

    def __init__(self, config: ConnectionConfig = None):
        self.config = config or ConnectionConfig()
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="conn-test")
        self._connection_history: Dict[int, List[ConnectionResult]] = {}
        self._circuit_breakers: Dict[Tuple[int, ConnectionType], int] = {}  # 熔断器状态
        self._last_successful_check: Dict[Tuple[int, ConnectionType], datetime] = {}
        self._lock = threading.Lock()

    def _classify_error(self, error: Exception, connection_type: ConnectionType) -> FailureType:
        """分类连接错误类型"""
        error_str = str(error).lower()

        # 网络超时
        if "timeout" in error_str or "timed out" in error_str:
            return FailureType.NETWORK_TIMEOUT

        # 连接被拒绝
        if "connection refused" in error_str or "refused" in error_str:
            return FailureType.CONNECTION_REFUSED

        # DNS解析失败
        if "name resolution" in error_str or "getaddrinfo" in error_str:
            return FailureType.DNS_RESOLUTION_FAILED

        # 认证失败
        if any(keyword in error_str for keyword in ["authentication", "login", "password", "unauthorized"]):
            return FailureType.AUTHENTICATION_FAILED

        # 权限拒绝
        if "permission denied" in error_str or "access denied" in error_str:
            return FailureType.PERMISSION_DENIED

        # SSL错误
        if "ssl" in error_str or "certificate" in error_str:
            return FailureType.SSL_ERROR

        # 服务不可用
        if any(keyword in error_str for keyword in ["service unavailable", "bad gateway", "not found"]):
            return FailureType.SERVICE_UNAVAILABLE

        return FailureType.UNKNOWN_ERROR

    def _generate_failure_suggestions(self, failure_type: FailureType, connection_type: ConnectionType) -> List[str]:
        """根据故障类型生成修复建议"""
        suggestions = []

        if failure_type == FailureType.NETWORK_TIMEOUT:
            suggestions.extend([
                "检查网络连接是否正常",
                "验证目标服务器是否可达",
                "考虑增加连接超时时间",
                "检查防火墙设置"
            ])

        elif failure_type == FailureType.CONNECTION_REFUSED:
            suggestions.extend([
                "确认目标服务正在运行",
                "检查端口配置是否正确",
                "验证服务监听地址配置"
            ])

        elif failure_type == FailureType.DNS_RESOLUTION_FAILED:
            suggestions.extend([
                "检查域名配置是否正确",
                "验证DNS服务器设置",
                "尝试使用IP地址代替域名"
            ])

        elif failure_type == FailureType.AUTHENTICATION_FAILED:
            suggestions.extend([
                "检查用户名和密码是否正确",
                "验证用户权限设置",
                "确认认证方式配置"
            ])

        elif failure_type == FailureType.PERMISSION_DENIED:
            suggestions.extend([
                "检查用户访问权限",
                "验证文件系统权限设置",
                "确认服务账户配置"
            ])

        elif failure_type == FailureType.SSL_ERROR:
            suggestions.extend([
                "检查SSL证书配置",
                "验证证书有效期",
                "确认SSL协议版本兼容性"
            ])

        elif failure_type == FailureType.SERVICE_UNAVAILABLE:
            suggestions.extend([
                "检查目标服务状态",
                "验证服务配置",
                "确认服务依赖是否正常"
            ])

        # 连接类型特定建议
        if connection_type == ConnectionType.METASTORE:
            suggestions.append("检查Hive MetaStore服务状态")
            suggestions.append("验证数据库连接配置")
        elif connection_type == ConnectionType.HDFS:
            suggestions.append("检查HDFS NameNode状态")
            suggestions.append("验证WebHDFS服务配置")
        elif connection_type == ConnectionType.HIVESERVER2:
            suggestions.append("检查HiveServer2服务状态")
            suggestions.append("验证Hive服务配置")

        return suggestions[:5]  # 限制建议数量

    def _is_circuit_breaker_open(self, cluster_id: int, connection_type: ConnectionType) -> bool:
        """检查熔断器是否开启"""
        key = (cluster_id, connection_type)
        with self._lock:
            failures = self._circuit_breakers.get(key, 0)
            return failures >= self.config.circuit_breaker_threshold

    def _update_circuit_breaker(self, cluster_id: int, connection_type: ConnectionType, success: bool):
        """更新熔断器状态"""
        key = (cluster_id, connection_type)
        with self._lock:
            if success:
                self._circuit_breakers[key] = 0
                self._last_successful_check[key] = datetime.now()
            else:
                self._circuit_breakers[key] = self._circuit_breakers.get(key, 0) + 1

    def _record_connection_result(self, cluster_id: int, result: ConnectionResult):
        """记录连接测试结果"""
        with self._lock:
            if cluster_id not in self._connection_history:
                self._connection_history[cluster_id] = []

            history = self._connection_history[cluster_id]
            history.append(result)

            # 只保留最近100条记录
            if len(history) > 100:
                self._connection_history[cluster_id] = history[-100:]

    def _test_metastore_connection(self, cluster: Cluster) -> ConnectionResult:
        """测试MetaStore连接"""
        start_time = time.time()
        connection_type = ConnectionType.METASTORE

        try:
            # 创建连接器
            parsed = urlparse(cluster.hive_metastore_url)
            scheme = (parsed.scheme or '').lower()

            if scheme.startswith('mysql'):
                connector = MySQLHiveMetastoreConnector(cluster.hive_metastore_url)
            else:
                connector = HiveMetastoreConnector(cluster.hive_metastore_url)

            # 测试连接
            test_result = connector.test_connection()
            response_time = (time.time() - start_time) * 1000

            if test_result.get('status') == 'success':
                return ConnectionResult(
                    connection_type=connection_type,
                    status="success",
                    response_time_ms=response_time
                )
            else:
                error_msg = test_result.get('message', 'Unknown error')
                return ConnectionResult(
                    connection_type=connection_type,
                    status="failed",
                    response_time_ms=response_time,
                    failure_type=FailureType.SERVICE_UNAVAILABLE,
                    error_message=error_msg
                )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            failure_type = self._classify_error(e, connection_type)

            return ConnectionResult(
                connection_type=connection_type,
                status="failed",
                response_time_ms=response_time,
                failure_type=failure_type,
                error_message=str(e)
            )

    def _test_hdfs_connection(self, cluster: Cluster) -> ConnectionResult:
        """测试HDFS连接"""
        start_time = time.time()
        connection_type = ConnectionType.HDFS

        try:
            scanner = WebHDFSScanner(
                cluster.hdfs_namenode_url,
                user=getattr(cluster, 'hdfs_user', 'hdfs') or 'hdfs'
            )

            # 测试连接
            success = scanner.connect()
            response_time = (time.time() - start_time) * 1000

            try:
                scanner.disconnect()
            except:
                pass  # 忽略断开连接的错误

            if success:
                return ConnectionResult(
                    connection_type=connection_type,
                    status="success",
                    response_time_ms=response_time
                )
            else:
                return ConnectionResult(
                    connection_type=connection_type,
                    status="failed",
                    response_time_ms=response_time,
                    failure_type=FailureType.SERVICE_UNAVAILABLE,
                    error_message="HDFS connection failed"
                )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            failure_type = self._classify_error(e, connection_type)

            return ConnectionResult(
                connection_type=connection_type,
                status="failed",
                response_time_ms=response_time,
                failure_type=failure_type,
                error_message=str(e)
            )

    def _test_hiveserver2_connection(self, cluster: Cluster) -> ConnectionResult:
        """测试HiveServer2连接"""
        start_time = time.time()
        connection_type = ConnectionType.HIVESERVER2

        try:
            # 首先进行TCP连接测试
            host = cluster.hive_host
            port = cluster.hive_port

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.timeout_seconds)

            result = sock.connect_ex((host, port))
            sock.close()

            if result != 0:
                response_time = (time.time() - start_time) * 1000
                return ConnectionResult(
                    connection_type=connection_type,
                    status="failed",
                    response_time_ms=response_time,
                    failure_type=FailureType.CONNECTION_REFUSED,
                    error_message=f"Cannot connect to {host}:{port}"
                )

            # TCP连接成功，尝试真实的Hive连接测试
            try:
                from pyhive import hive

                # 根据认证类型构建连接参数
                conn_params = {
                    "host": host,
                    "port": port,
                    "timeout": self.config.timeout_seconds,
                }

                if cluster.auth_type == "LDAP" and cluster.hive_username:
                    # LDAP认证
                    conn_params["username"] = cluster.hive_username
                    if cluster.hive_password:
                        conn_params["password"] = cluster.hive_password
                    conn_params["auth"] = "LDAP"
                else:
                    # 无认证或匿名访问
                    conn_params["username"] = cluster.hive_username or "anonymous"

                conn = hive.Connection(**conn_params)

                # 尝试执行一个简单的查询来验证服务可用性
                cursor = conn.cursor()
                cursor.execute("SHOW DATABASES")
                cursor.fetchone()  # 尝试获取结果
                cursor.close()
                conn.close()

                response_time = (time.time() - start_time) * 1000
                return ConnectionResult(
                    connection_type=connection_type,
                    status="success",
                    response_time_ms=response_time
                )

            except Exception as hive_error:
                response_time = (time.time() - start_time) * 1000
                # 虽然TCP连接成功，但Hive服务不可用
                return ConnectionResult(
                    connection_type=connection_type,
                    status="failed",
                    response_time_ms=response_time,
                    failure_type=FailureType.SERVICE_UNAVAILABLE,
                    error_message=f"HiveServer2 service unavailable: {str(hive_error)}"
                )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            failure_type = self._classify_error(e, connection_type)

            return ConnectionResult(
                connection_type=connection_type,
                status="failed",
                response_time_ms=response_time,
                failure_type=failure_type,
                error_message=str(e)
            )

    def _test_connection_with_retry(self, cluster: Cluster, connection_type: ConnectionType) -> ConnectionResult:
        """带重试机制的连接测试"""
        last_result = None
        total_attempts = 1 + self.config.max_retries

        for attempt in range(total_attempts):
            try:
                # 执行连接测试
                if connection_type == ConnectionType.METASTORE:
                    future = self.executor.submit(self._test_metastore_connection, cluster)
                elif connection_type == ConnectionType.HDFS:
                    future = self.executor.submit(self._test_hdfs_connection, cluster)
                elif connection_type == ConnectionType.HIVESERVER2:
                    future = self.executor.submit(self._test_hiveserver2_connection, cluster)
                else:
                    raise ValueError(f"Unsupported connection type: {connection_type}")

                # 等待结果，带超时
                result = future.result(timeout=self.config.timeout_seconds)
                result.attempt_count = attempt + 1
                result.retry_count = attempt

                # 如果成功，直接返回
                if result.status == "success":
                    return result

                last_result = result

                # 如果不是最后一次尝试，等待后重试
                if attempt < total_attempts - 1:
                    delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    time.sleep(delay)

            except FutureTimeoutError:
                last_result = ConnectionResult(
                    connection_type=connection_type,
                    status="timeout",
                    response_time_ms=self.config.timeout_seconds * 1000,
                    failure_type=FailureType.NETWORK_TIMEOUT,
                    error_message=f"Connection timeout after {self.config.timeout_seconds}s",
                    attempt_count=attempt + 1,
                    retry_count=attempt
                )

                if attempt < total_attempts - 1:
                    delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    time.sleep(delay)

            except Exception as e:
                last_result = ConnectionResult(
                    connection_type=connection_type,
                    status="failed",
                    response_time_ms=0,
                    failure_type=self._classify_error(e, connection_type),
                    error_message=str(e),
                    attempt_count=attempt + 1,
                    retry_count=attempt
                )
                break  # 非超时错误不重试

        return last_result or ConnectionResult(
            connection_type=connection_type,
            status="failed",
            response_time_ms=0,
            failure_type=FailureType.UNKNOWN_ERROR,
            error_message="All connection attempts failed"
        )

    async def test_cluster_connections(
        self,
        cluster: Cluster,
        connection_types: List[ConnectionType] = None
    ) -> Dict[str, Any]:
        """异步测试集群连接"""
        if connection_types is None:
            connection_types = [ConnectionType.METASTORE, ConnectionType.HDFS, ConnectionType.HIVESERVER2]

        start_time = time.time()
        results = {}
        logs = []
        suggestions = []

        # 并发测试所有连接类型
        tasks = []
        for conn_type in connection_types:
            # 检查熔断器
            if self._is_circuit_breaker_open(cluster.id, conn_type):
                last_success = self._last_successful_check.get((cluster.id, conn_type))
                if last_success and datetime.now() - last_success < timedelta(minutes=5):
                    # 熔断器开启且最近没有成功，跳过测试
                    result = ConnectionResult(
                        connection_type=conn_type,
                        status="circuit_breaker_open",
                        response_time_ms=0,
                        error_message="Circuit breaker is open due to consecutive failures"
                    )
                    results[conn_type.value] = result
                    continue

            # 创建异步任务
            task = asyncio.get_event_loop().run_in_executor(
                None, self._test_connection_with_retry, cluster, conn_type
            )
            tasks.append((conn_type, task))

        # 等待所有任务完成
        for conn_type, task in tasks:
            try:
                result = await task
                results[conn_type.value] = result

                # 更新熔断器状态
                self._update_circuit_breaker(cluster.id, conn_type, result.status == "success")

                # 记录结果
                self._record_connection_result(cluster.id, result)

                # 生成日志
                if result.status == "success":
                    logs.append({
                        "level": "INFO",
                        "message": f"{conn_type.value}: Connected successfully ({result.response_time_ms:.1f}ms)"
                    })
                else:
                    logs.append({
                        "level": "ERROR",
                        "message": f"{conn_type.value}: {result.error_message} (attempts: {result.attempt_count})"
                    })

                    # 生成修复建议
                    if result.failure_type:
                        conn_suggestions = self._generate_failure_suggestions(result.failure_type, conn_type)
                        suggestions.extend(conn_suggestions)

            except Exception as e:
                logs.append({
                    "level": "ERROR",
                    "message": f"{conn_type.value}: Unexpected error - {str(e)}"
                })

        # 计算整体状态
        successful_connections = sum(1 for r in results.values() if r.status == "success")
        total_connections = len(results)

        if successful_connections == total_connections:
            overall_status = "success"
        elif successful_connections > 0:
            overall_status = "partial"
        else:
            overall_status = "failed"

        total_time = time.time() - start_time

        return {
            "overall_status": overall_status,
            "test_time": datetime.now().isoformat(),
            "total_test_time_ms": total_time * 1000,
            "tests": {
                conn_type: {
                    "status": result.status,
                    "response_time_ms": result.response_time_ms,
                    "failure_type": result.failure_type.value if result.failure_type else None,
                    "error_message": result.error_message,
                    "attempt_count": result.attempt_count,
                    "retry_count": result.retry_count
                }
                for conn_type, result in results.items()
            },
            "logs": logs,
            "suggestions": list(set(suggestions))  # 去重
        }

    def get_connection_history(self, cluster_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """获取连接历史记录"""
        with self._lock:
            history = self._connection_history.get(cluster_id, [])
            recent_history = history[-limit:] if limit > 0 else history

            return [
                {
                    "connection_type": result.connection_type.value,
                    "status": result.status,
                    "response_time_ms": result.response_time_ms,
                    "failure_type": result.failure_type.value if result.failure_type else None,
                    "error_message": result.error_message,
                    "attempt_count": result.attempt_count,
                    "retry_count": result.retry_count,
                    "timestamp": result.timestamp.isoformat()
                }
                for result in recent_history
            ]

    def get_connection_statistics(self, cluster_id: int, hours: int = 24) -> Dict[str, Any]:
        """获取连接统计信息"""
        since_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            history = self._connection_history.get(cluster_id, [])
            recent_history = [r for r in history if r.timestamp >= since_time]

            if not recent_history:
                return {
                    "total_tests": 0,
                    "success_rate": 0,
                    "average_response_time_ms": 0,
                    "failure_types": {},
                    "period_hours": hours
                }

            # 计算统计指标
            total_tests = len(recent_history)
            successful_tests = sum(1 for r in recent_history if r.status == "success")
            success_rate = (successful_tests / total_tests) * 100

            # 平均响应时间（只计算成功的连接）
            successful_results = [r for r in recent_history if r.status == "success"]
            avg_response_time = (
                sum(r.response_time_ms for r in successful_results) / len(successful_results)
                if successful_results else 0
            )

            # 故障类型统计
            failure_types = {}
            for result in recent_history:
                if result.failure_type:
                    failure_type = result.failure_type.value
                    failure_types[failure_type] = failure_types.get(failure_type, 0) + 1

            return {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": round(success_rate, 2),
                "average_response_time_ms": round(avg_response_time, 2),
                "failure_types": failure_types,
                "period_hours": hours
            }


# 全局服务实例
enhanced_connection_service = EnhancedConnectionService()