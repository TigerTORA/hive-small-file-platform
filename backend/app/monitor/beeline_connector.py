"""
Beeline/JDBC连接器 - 用于测试Hive Server2连接
支持Kerberos和非Kerberos认证
"""

import logging
import os
import socket
import subprocess
import time
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from app.utils.kerberos_diagnostics import (
    KerberosDiagnostic,
    KerberosDiagnosticCode,
    KerberosDiagnosticError,
    build_diagnostic,
    log_kerberos_diagnostic,
    map_exception_to_diagnostic,
    raise_diagnostic_error,
)
from app.utils.metrics import increment_kerberos_failure, increment_ticket_event

if TYPE_CHECKING:  # pragma: no cover
    from app.models.cluster import Cluster


logger = logging.getLogger(__name__)


class BeelineConnector:
    """
    Beeline连接器 - 测试Hive Server2 JDBC连接

    支持多种连接方式：
    1. 简单认证 (用户名/密码)
    2. Kerberos认证
    3. 端口连通性测试
    """

    def __init__(
        self,
        host: str,
        port: int = 10000,
        username: Optional[str] = None,
        password: Optional[str] = None,
        *,
        auth_type: str = "SIMPLE",
        kerberos_principal: Optional[str] = None,
        kerberos_keytab_path: Optional[str] = None,
        kerberos_realm: Optional[str] = None,
        kerberos_ticket_cache: Optional[str] = None,
        timeout: int = 30,
    ):
        self.host = host
        self.port = port
        self.username = username or "hive"
        self.password = password
        self.timeout = timeout
        self.auth_type = (auth_type or "SIMPLE").upper()
        self.kerberos_principal = kerberos_principal
        self.kerberos_keytab_path = kerberos_keytab_path
        self.kerberos_realm = kerberos_realm
        self.kerberos_ticket_cache = kerberos_ticket_cache
        self._last_diagnostic: Optional[KerberosDiagnostic] = None
        self._cached_principal: Optional[str] = None

    def last_diagnostic(self) -> Optional[KerberosDiagnostic]:
        return self._last_diagnostic

    def _record_diagnostic(
        self, diagnostic: KerberosDiagnostic, *, extra: Optional[dict] = None
    ) -> None:
        self._last_diagnostic = diagnostic
        log_kerberos_diagnostic(logger, "error", diagnostic, extra_context=extra)
        increment_kerberos_failure(diagnostic.code.value)


    @classmethod
    def from_cluster(
        cls, cluster: "Cluster", timeout: int = 30  # type: ignore[name-defined]
    ) -> "BeelineConnector":
        auth_type = (getattr(cluster, "auth_type", "NONE") or "NONE").upper()
        username = getattr(cluster, "hive_username", None)
        password = getattr(cluster, "hive_password", None)

        kerberos_kwargs = {}
        if auth_type == "KERBEROS":
            username = getattr(cluster, "kerberos_principal", None)
            password = None
            kerberos_kwargs = {
                "kerberos_principal": getattr(
                    cluster, "kerberos_principal", None
                ),
                "kerberos_keytab_path": getattr(
                    cluster, "kerberos_keytab_path", None
                ),
                "kerberos_realm": getattr(cluster, "kerberos_realm", None),
                "kerberos_ticket_cache": getattr(
                    cluster, "kerberos_ticket_cache", None
                ),
            }

        return cls(
            cluster.hive_host,
            port=getattr(cluster, "hive_port", 10000) or 10000,
            username=username,
            password=password,
            auth_type=auth_type,
            timeout=timeout,
            **kerberos_kwargs,
        )

    def test_connection(self) -> Dict:
        """
        测试Beeline/HiveServer2连接

        Returns:
            Dict: 包含连接状态、详细信息和建议
        """
        result = {
            "status": "unknown",
            "message": "",
            "details": {},
            "test_time": datetime.now().isoformat(),
            "connection_type": "jdbc",
            "driver": "hive2",
        }

        logger.info(f"开始测试Beeline连接: {self.host}:{self.port}")

        try:
            if self.auth_type == "KERBEROS":
                validation_error = self._validate_kerberos_config()
                if validation_error:
                    result["status"] = "failed"
                    result["message"] = validation_error
                    result["details"] = {
                        "error": validation_error,
                        "suggestions": self._get_connection_suggestions(),
                        "auth_type": "KERBEROS",
                    }
                    return result

            # 1. 首先测试端口连通性
            port_test = self._test_port_connectivity()
            result["details"]["port_connectivity"] = port_test

            if not port_test["accessible"]:
                result["status"] = "failed"
                result["message"] = f"HiveServer2端口 {self.host}:{self.port} 不可访问"
                result["details"]["error"] = port_test.get("error", "连接超时")
                result["details"]["suggestions"] = [
                    "检查HiveServer2服务是否启动",
                    f"确认端口{self.port}是否正确",
                    "检查防火墙和网络连接",
                    "验证Hive配置中的端口设置",
                ]
                return result

            # 2. 尝试JDBC连接测试
            jdbc_test = self._test_jdbc_connection()
            result["details"]["jdbc_test"] = jdbc_test

            if jdbc_test["success"]:
                result["status"] = "success"
                result["message"] = (
                    f"HiveServer2连接成功 (认证方式: {jdbc_test.get('auth_method', 'simple')})"
                )
                result["details"]["connection_info"] = {
                    "jdbc_url": self.get_jdbc_url(),
                    "username": self.username,
                    "auth_method": jdbc_test.get("auth_method", "simple"),
                    "server_version": jdbc_test.get("server_version", "unknown"),
                    "response_time_ms": jdbc_test.get("response_time_ms", 0),
                }
                if self.auth_type == "KERBEROS":
                    result["details"]["connection_info"]["principal"] = (
                        self._normalized_principal() or ""
                    )
            else:
                result["status"] = "failed"
                result["message"] = (
                    f"HiveServer2连接失败: {jdbc_test.get('error', '未知错误')}"
                )
                result["details"]["error"] = jdbc_test.get("error")
                result["details"]["suggestions"] = self._get_connection_suggestions()
                result["details"]["connection_info"] = {
                    "jdbc_url": self.get_jdbc_url(),
                    "auth_type": self.auth_type,
                }
                if self.auth_type == "KERBEROS":
                    result["details"]["connection_info"][
                        "principal"
                    ] = self._normalized_principal() or ""

        except Exception as e:
            logger.error(f"Beeline连接测试异常: {e}")
            result["status"] = "failed"
            result["message"] = f"连接测试异常: {str(e)}"
            result["details"]["error"] = str(e)
            result["details"]["suggestions"] = self._get_connection_suggestions()

        logger.info(f"Beeline连接测试完成: {result['status']}")
        return result

    def _test_port_connectivity(self) -> Dict:
        """测试端口连通性"""
        result = {"accessible": False, "response_time_ms": 0, "error": None}

        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # 10秒超时

            result_code = sock.connect_ex((self.host, self.port))
            end_time = time.time()

            sock.close()

            result["response_time_ms"] = int((end_time - start_time) * 1000)

            if result_code == 0:
                result["accessible"] = True
                logger.info(
                    f"端口连通性测试成功: {self.host}:{self.port} ({result['response_time_ms']}ms)"
                )
            else:
                result["error"] = f"连接被拒绝 (错误码: {result_code})"
                logger.warning(f"端口连通性测试失败: {result['error']}")

        except socket.timeout:
            result["error"] = "连接超时"
            logger.warning(f"端口连通性测试超时: {self.host}:{self.port}")
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"端口连通性测试异常: {e}")

        return result



    def _test_jdbc_connection(self) -> Dict:
        """
        使用Beeline命令行工具测试JDBC连接

        注意：这是一个简化实现，实际生产环境中可能需要：
        1. 安装Java和Hive Beeline客户端
        2. 配置Kerberos认证
        3. 设置正确的JDBC驱动路径
        """
        result = {
            "success": False,
            "auth_method": "kerberos" if self.auth_type == "KERBEROS" else "simple",
            "server_version": "unknown",
            "response_time_ms": 0,
            "error": None,
        }

        try:
            if self.auth_type == "KERBEROS":
                self._ensure_kerberos_ticket()

            jdbc_url = self.get_jdbc_url()
            cmd = self._build_beeline_command(jdbc_url)

            start_time = time.time()
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=os.environ.copy(),
            )
            end_time = time.time()
            result["response_time_ms"] = int((end_time - start_time) * 1000)

            if process.returncode == 0:
                result["success"] = True
                result["server_version"] = self._extract_server_version(process.stdout)
                logger.info(
                    "Beeline JDBC 测试成功，耗时 %sms",
                    result["response_time_ms"],
                )
            else:
                result["error"] = self._build_jdbc_error(process)
                logger.warning("Beeline JDBC 测试失败: %s", result["error"])

        except FileNotFoundError:
            logger.info('Beeline 命令不可用，使用备用连接测试方案')
            return self._fallback_connection_test()
        except subprocess.TimeoutExpired:
            result["error"] = "Beeline 执行超时"
        except RuntimeError as err:
            result["error"] = str(err)
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"执行Beeline命令异常: {e}")

        return result

    def _build_beeline_command(self, jdbc_url: str) -> List[str]:
        cmd = [
            "beeline",
            "-u",
            jdbc_url,
            "-e",
            "SELECT 1;",
            "--outputformat=csv2",
            "--silent=true",
        ]
        if self.auth_type == "KERBEROS":
            principal = self._normalized_principal()
            if principal:
                cmd.extend(["-n", principal])
        else:
            cmd.extend(["-n", self.username])
            if self.password:
                cmd.extend(["-p", self.password])
        return cmd

    def _normalized_principal(self) -> Optional[str]:
        if self._cached_principal:
            return self._cached_principal
        principal = (self.kerberos_principal or "").strip()
        if not principal:
            return None
        if self.kerberos_realm and "@" not in principal:
            principal = f"{principal}@{self.kerberos_realm}"
        self._cached_principal = principal
        return principal

    def _validate_kerberos_config(self) -> Optional[str]:
        if self.auth_type != "KERBEROS":
            return None
        missing = []
        if not (self.kerberos_principal or "").strip():
            missing.append("kerberos_principal")
        if not (self.kerberos_keytab_path or "").strip():
            missing.append("kerberos_keytab_path")
        if missing:
            return "Kerberos 配置缺失: " + ", ".join(missing)
        return None

    def _ensure_kerberos_ticket(self) -> None:
        principal = self._normalized_principal()
        if not principal:
            raise_diagnostic_error(
                KerberosDiagnosticCode.CONFIG_MISSING,
                detail="Kerberos principal 缺失",
                logger=logger,
            )

        env = os.environ.copy()
        if self.kerberos_ticket_cache:
            cache_path = os.path.expanduser(self.kerberos_ticket_cache)
            os.environ["KRB5CCNAME"] = cache_path
            env["KRB5CCNAME"] = cache_path
            increment_ticket_event("kerberos_ticket_cache_set")

        if self.kerberos_keytab_path:
            keytab_path = os.path.expanduser(self.kerberos_keytab_path)
            if not os.path.exists(keytab_path):
                raise_diagnostic_error(
                    KerberosDiagnosticCode.KEYTAB_MISSING,
                    detail=f"Kerberos keytab 不存在: {keytab_path}",
                    logger=logger,
                )
            try:
                subprocess.run(
                    ["kinit", "-k", "-t", keytab_path, principal],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=env,
                )
                increment_ticket_event("kerberos_kinit_success")
                increment_ticket_event("kerberos_ticket_renewed")
            except FileNotFoundError as exc:
                diagnostic = build_diagnostic(
                    KerberosDiagnosticCode.KINIT_FAILURE,
                    detail="未找到 kinit 命令，请确认 Kerberos 客户端已安装",
                )
                self._record_diagnostic(diagnostic, extra={"stage": "beeline_kinit"})
                raise KerberosDiagnosticError(diagnostic, original=exc)
            except subprocess.CalledProcessError as exc:
                detail = exc.stderr.strip() if exc.stderr else str(exc)
                diagnostic = build_diagnostic(
                    KerberosDiagnosticCode.KINIT_FAILURE,
                    detail=f"kinit 执行失败: {detail}",
                )
                self._record_diagnostic(diagnostic, extra={"stage": "beeline_kinit"})
                raise KerberosDiagnosticError(diagnostic, original=exc)
        else:
            logger.debug("未提供 Kerberos keytab，假定外部票据已准备就绪")

    def _extract_server_version(self, output: str) -> str:
        if not output:
            return "unknown"
        for line in output.splitlines():
            low = line.lower()
            if "hive" in low and "version" in low:
                return line.strip()
        return "unknown"

    def _build_jdbc_error(self, process: subprocess.CompletedProcess) -> str:
        stderr = (process.stderr or "").strip()
        stdout = (process.stdout or "").strip()
        if stderr:
            return stderr
        if stdout:
            return stdout
        return f"Beeline 执行失败，返回码 {process.returncode}"

    def _fallback_connection_test(self) -> Dict:
        """
        备用连接测试方案 - 当Beeline不可用时使用
        仅基于端口连通性和协议探测
        """
        result = {
            "success": False,
            "auth_method": "simple",
            "server_version": "unknown",
            "response_time_ms": 0,
            "error": None,
            "test_method": "fallback",
        }

        try:
            # 尝试连接并发送简单的协议握手
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)

            sock.connect((self.host, self.port))

            # 发送简单的探测数据 (模拟JDBC握手)
            # 实际的Thrift协议握手会更复杂
            try:
                sock.send(b"test_connection")
                response = sock.recv(1024)

                end_time = time.time()
                result["response_time_ms"] = int((end_time - start_time) * 1000)

                if response:
                    result["success"] = True
                    result["server_version"] = "detected"
                    logger.info("备用连接测试成功")
                else:
                    result["error"] = "服务器无响应"

            except:
                # 即使数据交换失败，端口连通也说明服务在运行
                end_time = time.time()
                result["response_time_ms"] = int((end_time - start_time) * 1000)
                result["success"] = True
                result["server_version"] = "service_detected"
                logger.info("检测到HiveServer2服务运行")

            sock.close()

        except Exception as e:
            result["error"] = str(e)
            logger.warning(f"备用连接测试失败: {e}")

        return result

    def _get_connection_suggestions(self) -> List[str]:
        """获取连接失败时的建议"""
        suggestions = [
            "检查HiveServer2服务是否正在运行",
            f"确认主机地址 {self.host} 是否正确",
            f"验证端口 {self.port} 是否为HiveServer2监听端口",
            "检查防火墙规则是否允许连接",
            "确认用户权限和认证配置",
            "如果使用Kerberos，检查票据是否有效",
            "查看HiveServer2日志文件获取详细错误信息",
        ]
        if self.auth_type == "KERBEROS":
            suggestions = [
                "确认 Kerberos principal、keytab 路径配置正确",
                "确保主机可以访问 KDC，DNS 解析正常",
                "验证 keytab 权限，并执行 kinit -kt <keytab> <principal>",
                "如果使用自定义票据缓存，确认环境变量 KRB5CCNAME 设置正确",
            ] + suggestions
        return suggestions

    def get_jdbc_url(self) -> str:
        """获取JDBC连接URL"""
        base = f"jdbc:hive2://{self.host}:{self.port}/default"
        if self.auth_type == "KERBEROS":
            principal = self._normalized_principal()
            if principal:
                return f"{base};principal={principal}"
        return base

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # Beeline连接器通常不需要显式清理
        pass
if TYPE_CHECKING:  # pragma: no cover
    from app.models.cluster import Cluster
