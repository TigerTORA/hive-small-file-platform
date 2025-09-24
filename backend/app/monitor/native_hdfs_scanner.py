import json
import logging
import re
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class NativeHDFSScanner:
    """
    原生HDFS扫描器 - 直接使用hdfs命令获取真实数据

    在HDFS节点上运行，通过原生hdfs dfs命令获取100%真实的文件统计信息
    彻底替换Mock模式，提供准确的小文件分析
    """

    def __init__(self, namenode_url: str = None, user: str = "hdfs"):
        self.namenode_url = namenode_url or "hdfs://nameservice1"
        self.user = user
        self.connection_status = {}

        logger.info(f"初始化原生HDFS扫描器: 用户={user}")

    def test_connection(self) -> Dict[str, any]:
        """测试HDFS命令可用性和权限"""
        try:
            # 测试hdfs命令是否可用
            version_result = subprocess.run(
                ["hdfs", "version"], capture_output=True, text=True, timeout=10
            )

            if version_result.returncode != 0:
                return {
                    "status": "error",
                    "error_type": "hdfs_command_unavailable",
                    "message": "hdfs命令不可用",
                    "suggestion": "请确认Hadoop已正确安装且在PATH中",
                }

            # 解析Hadoop版本信息
            version_info = (
                version_result.stdout.split("\n")[0]
                if version_result.stdout
                else "Unknown"
            )

            # 测试HDFS根目录访问
            ls_result = subprocess.run(
                ["hdfs", "dfs", "-ls", "/"], capture_output=True, text=True, timeout=15
            )

            if ls_result.returncode != 0:
                return {
                    "status": "error",
                    "error_type": "hdfs_permission",
                    "message": f"HDFS访问失败: {ls_result.stderr}",
                    "suggestion": "请检查HDFS权限或尝试使用sudo -u hdfs",
                }

            # 解析根目录内容
            root_dirs = []
            for line in ls_result.stdout.split("\n"):
                if line.strip() and not line.startswith("Found"):
                    parts = line.split()
                    if len(parts) >= 8:
                        root_dirs.append(parts[-1])  # 目录名

            self.connection_status = {
                "status": "success",
                "hadoop_version": version_info,
                "user": self.user,
                "namenode": self.namenode_url,
                "root_directories": root_dirs[:10],
                "access_method": "native_hdfs_command",
            }

            return {
                "status": "success",
                "service_type": "Native HDFS",
                "hadoop_version": version_info,
                "user": self.user,
                "namenode": self.namenode_url,
                "sample_root_dirs": root_dirs[:5],
                "message": "成功连接到原生HDFS服务",
                "access_method": "direct_hdfs_commands",
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error_type": "timeout",
                "message": "HDFS命令执行超时",
                "suggestion": "请检查HDFS服务状态",
            }
        except FileNotFoundError:
            return {
                "status": "error",
                "error_type": "hdfs_not_found",
                "message": "hdfs命令未找到",
                "suggestion": "请确认Hadoop已安装且在PATH中",
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": "exception",
                "message": f"连接测试异常: {str(e)}",
                "suggestion": "请检查HDFS服务状态和权限配置",
            }

    def scan_path(self, path: str) -> Dict[str, any]:
        """使用原生hdfs命令扫描指定路径获取真实文件数据"""
        try:
            start_time = time.time()

            logger.info(f"开始扫描HDFS路径: {path}")

            # 使用hdfs dfs -ls -R获取递归文件列表
            ls_result = subprocess.run(
                ["hdfs", "dfs", "-ls", "-R", path],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if ls_result.returncode != 0:
                error_msg = ls_result.stderr.strip()
                if "No such file or directory" in error_msg:
                    return {
                        "status": "error",
                        "message": f"路径不存在: {path}",
                        "error_type": "path_not_found",
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"HDFS扫描失败: {error_msg}",
                        "path": path,
                        "error_type": "hdfs_command_failed",
                    }

            # 解析hdfs ls输出获取文件信息
            files = []
            total_size = 0
            small_files_count = 0
            small_file_threshold = 128 * 1024 * 1024  # 128MB

            for line in ls_result.stdout.split("\n"):
                line = line.strip()
                if not line or line.startswith("Found"):
                    continue

                # 解析hdfs ls输出格式
                # -rw-r--r--   3 hdfs hdfs    1234567 2024-01-01 12:00 /path/to/file
                parts = line.split()
                if len(parts) >= 8 and parts[0].startswith("-"):  # 确保是文件而不是目录
                    try:
                        permissions = parts[0]
                        replication = int(parts[1])
                        owner = parts[2]
                        group = parts[3]
                        file_size = int(parts[4])
                        date_part = parts[5]
                        time_part = parts[6]
                        file_path = " ".join(parts[7:])  # 处理文件名中可能包含空格

                        # 解析修改时间
                        try:
                            modification_time = int(
                                datetime.strptime(
                                    f"{date_part} {time_part}", "%Y-%m-%d %H:%M"
                                ).timestamp()
                                * 1000
                            )
                        except:
                            modification_time = int(
                                time.time() * 1000
                            )  # 使用当前时间作为后备

                        files.append(
                            {
                                "path": file_path,
                                "size": file_size,
                                "modification_time": modification_time,
                                "replication": replication,
                                "owner": owner,
                                "group": group,
                                "permissions": permissions,
                            }
                        )

                        total_size += file_size
                        if file_size < small_file_threshold:
                            small_files_count += 1

                    except (ValueError, IndexError) as e:
                        logger.warning(f"解析文件信息失败: {line}, 错误: {e}")
                        continue

            scan_duration = time.time() - start_time

            logger.info(
                f"扫描完成: {len(files)}个文件, {small_files_count}个小文件, 耗时{scan_duration:.2f}秒"
            )

            return {
                "status": "success",
                "path": path,
                "scan_mode": "native_hdfs_real",
                "total_files": len(files),
                "small_files_count": small_files_count,
                "total_size": total_size,
                "files": files[:200],  # 返回前200个文件作为样本
                "scan_duration": scan_duration,
                "metadata": {
                    "data_source": "native_hdfs_commands",
                    "scan_timestamp": datetime.now().isoformat(),
                    "small_file_threshold_mb": small_file_threshold // (1024 * 1024),
                    "avg_file_size": total_size / max(len(files), 1),
                    "largest_file_size": max([f["size"] for f in files], default=0),
                    "smallest_file_size": min([f["size"] for f in files], default=0),
                },
                "note": "这是通过原生HDFS命令获取的100%真实数据",
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": f"扫描路径 {path} 超时（120秒）",
                "suggestion": "路径包含大量文件，请考虑分批扫描或增加超时时间",
                "error_type": "scan_timeout",
            }
        except Exception as e:
            logger.error(f"扫描路径 {path} 时发生异常: {e}")
            return {
                "status": "error",
                "message": f"扫描异常: {str(e)}",
                "path": path,
                "error_type": "scan_exception",
            }

    def get_directory_summary(self, path: str) -> Dict[str, any]:
        """获取目录的快速摘要信息（不递归）"""
        try:
            # 使用hdfs dfs -count获取快速统计
            count_result = subprocess.run(
                ["hdfs", "dfs", "-count", path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if count_result.returncode == 0:
                # 解析hdfs dfs -count输出
                # 格式: DIR_COUNT FILE_COUNT CONTENT_SIZE PATHNAME
                parts = count_result.stdout.strip().split()
                if len(parts) >= 4:
                    dir_count = int(parts[0])
                    file_count = int(parts[1])
                    content_size = int(parts[2])

                    return {
                        "status": "success",
                        "path": path,
                        "directory_count": dir_count,
                        "file_count": file_count,
                        "total_size": content_size,
                        "avg_file_size": content_size / max(file_count, 1),
                    }

            return {"status": "error", "message": "Failed to get directory summary"}

        except Exception as e:
            return {"status": "error", "message": f"Summary failed: {str(e)}"}

    def connect(self) -> bool:
        """兼容性方法：连接测试"""
        result = self.test_connection()
        return result["status"] == "success"

    def disconnect(self):
        """兼容性方法：断开连接"""
        # 原生命令不需要显式断开连接
        pass

    def scan_table_partitions(
        self, table_path: str, partitions: List[Dict], small_file_threshold: int
    ) -> Tuple[Dict, List[Dict]]:
        """
        兼容性方法：扫描表分区
        返回 (table_stats, partition_stats)
        """
        # 使用scan_path方法获取真实文件信息
        scan_result = self.scan_path(table_path)

        if scan_result["status"] != "success":
            # 扫描失败，返回空数据
            table_stats = {
                "total_files": 0,
                "total_size": 0,
                "small_files": 0,
                "avg_file_size": 0.0,
                "path": table_path,
                "scan_mode": "native_hdfs_failed",
                "scan_duration": 0.0,
            }
            return table_stats, []

        # 构建表统计信息
        table_stats = {
            "total_files": scan_result["total_files"],
            "total_size": scan_result["total_size"],
            "small_files": scan_result["small_files_count"],
            "avg_file_size": scan_result["total_size"]
            / max(scan_result["total_files"], 1),
            "path": table_path,
            "scan_mode": scan_result["scan_mode"],
            "scan_duration": scan_result["scan_duration"],
        }

        # 构建分区统计信息
        # 如果有真实分区信息，可以进一步优化为按分区扫描
        partition_stats = [
            {
                "partition_path": table_path,
                "partition_name": "main",  # 主分区
                "file_count": scan_result["total_files"],
                "total_size": scan_result["total_size"],
                "small_file_count": scan_result["small_files_count"],
                "avg_file_size": scan_result["total_size"]
                / max(scan_result["total_files"], 1),
                "files": scan_result.get("files", []),
            }
        ]

        return table_stats, partition_stats

    def get_connection_info(self) -> Dict[str, any]:
        """获取连接信息"""
        return {
            "namenode": self.namenode_url,
            "user": self.user,
            "method": "native_hdfs_commands",
            "status": self.connection_status,
            "scanner_type": "NativeHDFSScanner",
        }
