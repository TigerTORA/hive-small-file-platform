import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests

from app.utils.webhdfs_client import WebHDFSClient

logger = logging.getLogger(__name__)

# 尝试导入Kerberos相关模块
try:
    from requests_gssapi import OPTIONAL, HTTPSPNEGOAuth

    KERBEROS_AVAILABLE = True
    logger.info("Kerberos authentication support available (via GSSAPI)")
except ImportError:
    logger.warning(
        "Kerberos authentication not available - install requests-gssapi for Kerberos support"
    )
    KERBEROS_AVAILABLE = False


class WebHDFSScanner:
    """
    WebHDFS REST API版本的文件扫描器，兼容性更好
    使用HTTP协议连接HDFS，无需安装特殊的Python库
    """

    def __init__(
        self,
        namenode_url: str,
        user: str = "hdfs",
        webhdfs_port: int = 9870,
        password: str = None,
    ):
        """
        初始化WebHDFS/HttpFS扫描器
        Args:
            namenode_url: NameNode URL, e.g., hdfs://nameservice1, http://namenode:9870, or http://httpfs:14000
            user: HDFS用户名
            webhdfs_port: WebHDFS/HttpFS端口，默认9870
            password: 用户密码（用于Kerberos认证）
        """
        self.user = user
        self.password = password
        self._connected = False
        self.auth = None
        self.is_httpfs = False

        # 解析URL并构造WebHDFS/HttpFS基础URL
        if namenode_url.startswith("hdfs://"):
            # 从HDFS URL推断WebHDFS URL
            parsed = urlparse(namenode_url)
            if parsed.hostname:
                self.webhdfs_base_url = (
                    f"http://{parsed.hostname}:{webhdfs_port}/webhdfs/v1"
                )
            else:
                # 处理nameservice情况
                self.webhdfs_base_url = (
                    f"http://192.168.0.105:{webhdfs_port}/webhdfs/v1"
                )
        elif namenode_url.startswith("http://"):
            # 直接使用HTTP URL
            parsed = urlparse(namenode_url)
            # 检查是否是HttpFS（端口14000）
            if parsed.port == 14000:
                self.is_httpfs = True
                self.webhdfs_base_url = f"http://{parsed.netloc}/webhdfs/v1"
            else:
                self.webhdfs_base_url = f"http://{parsed.netloc}/webhdfs/v1"
        else:
            # 假设是主机名，检查端口判断类型
            if webhdfs_port == 14000:
                self.is_httpfs = True
            self.webhdfs_base_url = f"http://{namenode_url}:{webhdfs_port}/webhdfs/v1"

        # 统一客户端（带路径归一与多端口回退）
        self._client = WebHDFSClient(self.webhdfs_base_url, user=self.user)

        # 设置认证方式
        if KERBEROS_AVAILABLE:
            try:
                # 尝试使用GSSAPI Kerberos认证
                self.auth = HTTPSPNEGOAuth(mutual_authentication=OPTIONAL)
                logger.info(
                    f"Using Kerberos authentication (GSSAPI) for {'HttpFS' if self.is_httpfs else 'WebHDFS'}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Kerberos auth: {e}")
                self.auth = None

        logger.info(
            f"{'HttpFS' if self.is_httpfs else 'WebHDFS'} base URL: {self.webhdfs_base_url}"
        )

        # HTTP会话
        self.session = requests.Session()
        self.session.timeout = 30

    def connect(self) -> bool:
        """测试WebHDFS连接"""
        try:
            ok, msg = self._client.test_connection()
            self._connected = ok
            if ok:
                logger.info(f"Connected to WebHDFS via {self.webhdfs_base_url}")
            else:
                logger.error(f"WebHDFS connection failed: {msg}")
            return ok
        except Exception as e:
            logger.error(f"Failed to connect to WebHDFS: {e}")
            return False

    def disconnect(self):
        """关闭连接"""
        self._connected = False
        try:
            self.session.close()
        except Exception:
            pass
        try:
            self._client.close()
        except Exception:
            pass
        logger.info("Disconnected from WebHDFS")

    def _normalize_path(self, path: str) -> str:
        """将HDFS URI转换为HTTP路径"""
        if path.startswith("hdfs://"):
            # 从HDFS URI中提取路径部分
            parsed = urlparse(path)
            return parsed.path
        else:
            # 已经是路径格式，直接返回
            return path

    def _get_request(self, path: str, operation: str, **params) -> requests.Response:
        """发送WebHDFS/HttpFS GET请求"""
        # 先转换HDFS URI为HTTP路径
        normalized_path = self._normalize_path(path)
        # 确保路径正确拼接
        if not normalized_path.startswith("/"):
            normalized_path = "/" + normalized_path
        url = self.webhdfs_base_url + normalized_path

        logger.debug(f"WebHDFS请求URL: {url}")

        params.update({"op": operation, "user.name": self.user})

        # 使用认证（如果可用）
        if self.auth:
            return self.session.get(url, params=params, auth=self.auth)
        else:
            return self.session.get(url, params=params)

    def test_connection(self) -> Dict[str, any]:
        """测试WebHDFS/HttpFS连接"""
        service_type = "HttpFS" if self.is_httpfs else "WebHDFS"

        if not self.connect():
            return {
                "status": "error",
                "message": f"Failed to connect to {service_type}",
            }

        try:
            # 测试根目录列出
            response = self._get_request("/", "LISTSTATUS")
            if response.status_code == 200:
                data = response.json()
                file_statuses = data.get("FileStatuses", {}).get("FileStatus", [])
                sample_files = [f["pathSuffix"] for f in file_statuses[:5]]

                return {
                    "status": "success",
                    "message": f"{service_type} 连接成功，发现 {len(sample_files)} 个目录/文件",
                    "service_type": service_type,
                    "webhdfs_url": self.webhdfs_base_url,
                    "user": self.user,
                    "auth_method": "Kerberos" if self.auth else "Simple",
                    "sample_paths": sample_files,
                }
            else:
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text}",
                    "service_type": service_type,
                }
        except Exception as e:
            return {"status": "error", "message": str(e), "service_type": service_type}
        finally:
            self.disconnect()

    def scan_directory(
        self, path: str, small_file_threshold: int = 128 * 1024 * 1024
    ) -> Dict:
        """
        扫描指定目录的文件分布
        Args:
            path: HDFS路径
            small_file_threshold: 小文件阈值（字节）
        Returns:
            文件统计信息字典
        """
        if not self._connected:
            raise ConnectionError("Not connected to WebHDFS")

        start_time = time.time()
        stats = {
            "path": path,
            "total_files": 0,
            "small_files": 0,
            "total_size": 0,
            "avg_file_size": 0.0,
            "file_size_distribution": {},
            "scan_time": start_time,
            "scan_duration": 0.0,
            "error": None,
        }

        try:
            # 使用统一客户端做快速统计（优先 GETCONTENTSUMMARY，失败回退递归）
            res = self._client.get_table_hdfs_stats(path, small_file_threshold)
            if res.get("success"):
                stats["total_files"] = int(res.get("total_files") or 0)
                stats["small_files"] = int(res.get("small_files_count") or 0)
                stats["total_size"] = int(res.get("total_size") or 0)
                stats["avg_file_size"] = float(res.get("average_file_size") or 0.0)
            else:
                stats["error"] = res.get("error")
                logger.warning(f"WebHDFS stats failed for {path}: {stats['error']}")

        except Exception as e:
            logger.error(f"Failed to scan directory {path}: {e}")
            stats["error"] = str(e)

        return stats

    def _walk_directory(self, path: str) -> List[Dict]:
        """递归遍历目录获取所有文件信息"""
        files = []
        try:
            response = self._get_request(path, "LISTSTATUS")
            if response.status_code != 200:
                logger.warning(
                    f"Cannot list directory {path}: HTTP {response.status_code}"
                )
                return files

            data = response.json()
            file_statuses = data.get("FileStatuses", {}).get("FileStatus", [])

            for file_status in file_statuses:
                file_path = path.rstrip("/") + "/" + file_status["pathSuffix"]

                if file_status["type"] == "FILE":
                    files.append(file_status)
                elif file_status["type"] == "DIRECTORY":
                    # 递归遍历子目录
                    files.extend(self._walk_directory(file_path))

        except Exception as e:
            logger.error(f"Error walking directory {path}: {e}")

        return files

    def scan_table_partitions(
        self,
        table_path: str,
        partitions: List[Dict],
        small_file_threshold: int = 128 * 1024 * 1024,
        max_workers: int = 4,
    ) -> Tuple[Dict, List[Dict]]:
        """
        并行扫描表的所有分区
        Args:
            table_path: 表的根路径
            partitions: 分区信息列表
            small_file_threshold: 小文件阈值
            max_workers: 最大并发数
        Returns:
            (表级统计, 分区级统计列表)
        """
        if not self._connected:
            raise ConnectionError("Not connected to WebHDFS")

        start_time = time.time()

        # 表级统计
        table_stats = {
            "table_path": table_path,
            "total_files": 0,
            "small_files": 0,
            "total_size": 0,
            "avg_file_size": 0.0,
            "partition_count": len(partitions),
            "scan_duration": 0.0,
        }

        partition_stats = []

        if not partitions:
            # 非分区表，直接扫描表路径
            stats = self.scan_directory(table_path, small_file_threshold)
            table_stats.update(
                {
                    "total_files": stats["total_files"],
                    "small_files": stats["small_files"],
                    "total_size": stats["total_size"],
                    "avg_file_size": stats["avg_file_size"],
                    "scan_duration": time.time() - start_time,
                }
            )

            # 为非分区表创建一个默认分区统计
            if stats["total_files"] > 0:
                partition_stats.append(
                    {
                        "partition_name": "default",
                        "partition_path": table_path,
                        "file_count": stats["total_files"],
                        "small_file_count": stats["small_files"],
                        "total_size": stats["total_size"],
                        "avg_file_size": stats["avg_file_size"],
                    }
                )

            return table_stats, partition_stats

        # 并行扫描分区
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交扫描任务
            future_to_partition = {}
            for partition in partitions:
                future = executor.submit(
                    self.scan_directory,
                    partition["partition_path"],
                    small_file_threshold,
                )
                future_to_partition[future] = partition

            # 收集结果
            for future in as_completed(future_to_partition):
                partition = future_to_partition[future]
                try:
                    result = future.result()
                    if not result.get("error"):
                        # 累计到表级统计
                        table_stats["total_files"] += result["total_files"]
                        table_stats["small_files"] += result["small_files"]
                        table_stats["total_size"] += result["total_size"]

                        # 添加分区级统计
                        partition_stats.append(
                            {
                                "partition_name": partition["partition_name"],
                                "partition_path": partition["partition_path"],
                                "file_count": result["total_files"],
                                "small_file_count": result["small_files"],
                                "total_size": result["total_size"],
                                "avg_file_size": result["avg_file_size"],
                            }
                        )
                    else:
                        logger.error(
                            f"Failed to scan partition {partition['partition_name']}: {result['error']}"
                        )

                except Exception as e:
                    logger.error(
                        f"Exception scanning partition {partition['partition_name']}: {e}"
                    )

        # 计算平均文件大小
        if table_stats["total_files"] > 0:
            table_stats["avg_file_size"] = (
                table_stats["total_size"] / table_stats["total_files"]
            )

        table_stats["scan_duration"] = time.time() - start_time

        logger.info(
            f"Scanned table {table_path}: "
            f"{table_stats['total_files']} files, "
            f"{table_stats['small_files']} small files, "
            f"{len(partition_stats)} partitions scanned"
        )

        return table_stats, partition_stats

    def _get_size_range(self, size: int) -> str:
        """获取文件大小范围标签"""
        if size < 1024:  # < 1KB
            return "< 1KB"
        elif size < 1024 * 1024:  # < 1MB
            return "1KB-1MB"
        elif size < 128 * 1024 * 1024:  # < 128MB (small file)
            return "1MB-128MB"
        elif size < 1024 * 1024 * 1024:  # < 1GB
            return "128MB-1GB"
        else:  # >= 1GB
            return "> 1GB"

    def __enter__(self):
        """Context manager entry"""
        if not self.connect():
            raise ConnectionError("Failed to connect to WebHDFS")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
