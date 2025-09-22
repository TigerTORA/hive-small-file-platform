"""
WebHDFS客户端工具类
通过REST API与HDFS交互，支持Simple认证
"""
import os
import json
import logging
import requests
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class HDFSFileInfo:
    """HDFS文件信息"""
    path: str
    size: int
    modification_time: int
    is_directory: bool
    block_size: int
    replication: int
    permission: str
    owner: str
    group: str

@dataclass
class HDFSDirectoryStats:
    """HDFS目录统计信息"""
    total_files: int
    total_size: int
    small_files_count: int
    small_files_size: int
    large_files_count: int
    large_files_size: int
    average_file_size: int
    directory_count: int

class WebHDFSClient:
    """WebHDFS客户端"""
    
    def __init__(self, namenode_url: str, user: str = "hdfs", timeout: int = 30):
        """
        初始化WebHDFS客户端
        
        Args:
            namenode_url: NameNode的WebHDFS URL (如: http://192.168.0.100:50070)
            user: HDFS用户名，默认hdfs
            timeout: 请求超时时间（秒）
        """
        self.namenode_url = namenode_url.rstrip('/')
        self.user = user
        self.timeout = timeout
        self.session = requests.Session()
        
        # WebHDFS API基础路径
        if namenode_url.endswith("/webhdfs/v1"):
            self.webhdfs_base = self.namenode_url
        else:
            self.webhdfs_base = f"{self.namenode_url}/webhdfs/v1"
        
        logger.info(f"Initialized WebHDFS client: {self.namenode_url}, user: {self.user}")
    
    def _build_url(self, path: str, operation: str, **params) -> str:
        """构建WebHDFS API URL（自动归一化 hdfs:// 路径为 HTTP 路径）"""
        # 归一化：将 hdfs://nameservice1/... 转为 /... 路径
        try:
            normalized = self._normalize_path(path)
        except Exception:
            normalized = path
        normalized = normalized.lstrip('/')
        url = f"{self.webhdfs_base}/{normalized}?op={operation}&user.name={self.user}"

        # 添加其他参数
        for key, value in params.items():
            if value is not None:
                url += f"&{key}={value}"

        return url

    def _normalize_path(self, path: str) -> str:
        """将 hdfs:// 或 viewfs:// 开头的 URI 归一为纯路径 /..."""
        try:
            if not path:
                return '/'
            if isinstance(path, str) and (path.startswith('hdfs://') or path.startswith('viewfs://')):
                p = urlparse(path)
                return p.path or '/'
            return path
        except Exception:
            return path

    def _alt_bases(self) -> list:
        """生成备选的 WebHDFS 基础地址（用于 HttpFS 不支持深路径时回退到 NN 9870/50070）。"""
        bases = [self.webhdfs_base]
        try:
            parsed = urlparse(self.webhdfs_base)
            host = parsed.hostname
            if host:
                # 常见 NN 端口
                for port in (9870, 50070):
                    alt = f"{parsed.scheme}://{host}:{port}/webhdfs/v1"
                    if alt not in bases:
                        bases.append(alt)
        except Exception:
            pass
        return bases
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        测试WebHDFS连接
        
        Returns:
            (是否连接成功, 错误信息或成功信息)
        """
        try:
            url = self._build_url("/", "LISTSTATUS")
            logger.info(f"Testing WebHDFS connection: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if 'FileStatuses' in data:
                    logger.info("WebHDFS connection successful")
                    return True, "WebHDFS连接成功"
                else:
                    error_msg = f"WebHDFS响应格式异常: {data}"
                    logger.error(error_msg)
                    return False, error_msg
            else:
                error_msg = f"WebHDFS连接失败: HTTP {response.status_code}, {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = f"WebHDFS连接超时 ({self.timeout}秒)"
            logger.error(error_msg)
            return False, error_msg
        except requests.exceptions.ConnectionError as e:
            error_msg = f"WebHDFS连接错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"WebHDFS连接异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    # ---- Storage policy helpers ----
    def set_storage_policy(self, path: str, policy: str) -> Tuple[bool, str]:
        """设置目录或文件的存储策略（如: HOT, COLD, WARM, ALL_SSD, ONE_SSD, LAZY_PERSIST）。

        Returns: (ok, message)
        """
        try:
            last_err = None
            for base in self._alt_bases():
                # Hadoop WebHDFS OP name is SETSTORAGEPOLICY; parameter key is 'storagepolicy'
                url = self._build_url(path, "SETSTORAGEPOLICY", storagepolicy=policy).replace(self.webhdfs_base, base, 1)
                try:
                    resp = self.session.put(url, timeout=self.timeout)
                    if resp.status_code in (200, 201):
                        return True, f"Set storage policy to {policy}"
                    last_err = f"HTTP {resp.status_code}: {resp.text}"
                except Exception as e:
                    last_err = str(e)
                    continue
            return False, last_err or "Unknown error"
        except Exception as e:
            return False, str(e)

    def get_storage_policy(self, path: str) -> Tuple[bool, Optional[str], str]:
        """获取路径的存储策略。Returns: (ok, policy|None, message)"""
        try:
            last_err = None
            for base in self._alt_bases():
                url = self._build_url(path, "GETSTORAGEPOLICY").replace(self.webhdfs_base, base, 1)
                try:
                    resp = self.session.get(url, timeout=self.timeout)
                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                            # Different Hadoop versions return different shapes; try common keys
                            policy = None
                            if isinstance(data, dict):
                                if 'StoragePolicy' in data and isinstance(data['StoragePolicy'], dict):
                                    policy = data['StoragePolicy'].get('type') or data['StoragePolicy'].get('policyName')
                                elif 'storagePolicy' in data:
                                    policy = data.get('storagePolicy')
                            return True, policy, "ok"
                        except Exception:
                            return True, None, "ok"
                    last_err = f"HTTP {resp.status_code}: {resp.text}"
                except Exception as e:
                    last_err = str(e)
                    continue
            return False, None, last_err or "Unknown error"
        except Exception as e:
            return False, None, str(e)

    def set_storage_policy_recursive(self, path: str, policy: str, max_entries: int = 5000) -> Tuple[int, int, List[str]]:
        """递归设置存储策略（简易版）。返回: (success_count, fail_count, errors)。
        为避免遍历过大目录导致 OOM，设置一个最大遍历条目数。
        """
        ok, msg = self.set_storage_policy(path, policy)
        success = 1 if ok else 0
        fail = 0 if ok else 1
        errors: List[str] = [] if ok else [msg]

        try:
            # 广度优先遍历子目录（仅目录）
            queue = [path]
            visited = 0
            while queue:
                cur = queue.pop(0)
                if visited > max_entries:
                    errors.append("reach_max_entries")
                    break
                try:
                    items = self.list_directory(cur)
                except Exception as e:
                    errors.append(str(e))
                    continue
                for it in items:
                    if it.is_directory:
                        visited += 1
                        # 应用策略
                        ok2, msg2 = self.set_storage_policy(it.path, policy)
                        if ok2:
                            success += 1
                        else:
                            fail += 1
                            errors.append(f"{it.path}: {msg2}")
                        queue.append(it.path)
            return success, fail, errors
        except Exception as e:
            errors.append(str(e))
            return success, fail, errors
    
    def get_file_status(self, path: str) -> Optional[HDFSFileInfo]:
        """
        获取文件或目录状态
        
        Args:
            path: HDFS路径
            
        Returns:
            文件信息对象，失败返回None
        """
        try:
            logger.debug(f"Getting file status: {path}")
            last_err = None
            for base in self._alt_bases():
                url = self._build_url(path, "GETFILESTATUS").replace(self.webhdfs_base, base, 1)
                try:
                    response = self.session.get(url, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        if 'FileStatus' in data:
                            fs = data['FileStatus']
                            return HDFSFileInfo(
                                path=path,
                                size=fs['length'],
                                modification_time=fs['modificationTime'],
                                is_directory=fs['type'] == 'DIRECTORY',
                                block_size=fs.get('blockSize', 0),
                                replication=fs.get('replication', 0),
                                permission=fs['permission'],
                                owner=fs['owner'],
                                group=fs['group']
                            )
                    last_err = f"HTTP {response.status_code}"
                except Exception as e:
                    last_err = str(e)
                    continue
            logger.error(f"Failed to get file status for {path}: {last_err}")
            return None
        except Exception as e:
            logger.error(f"Error getting file status for {path}: {str(e)}")
            return None
    
    def list_directory(self, path: str) -> List[HDFSFileInfo]:
        """
        列出目录内容
        
        Args:
            path: 目录路径
            
        Returns:
            文件信息列表
        """
        try:
            logger.debug(f"Listing directory: {path}")
            last_err = None
            for base in self._alt_bases():
                url = self._build_url(path, "LISTSTATUS").replace(self.webhdfs_base, base, 1)
                try:
                    response = self.session.get(url, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        file_statuses = data['FileStatuses']['FileStatus']
                        files = []
                        for file_status in file_statuses:
                            file_path = os.path.join(path, file_status['pathSuffix']).replace('\\', '/')
                            files.append(HDFSFileInfo(
                                path=file_path,
                                size=file_status['length'],
                                modification_time=file_status['modificationTime'],
                                is_directory=file_status['type'] == 'DIRECTORY',
                                block_size=file_status.get('blockSize', 0),
                                replication=file_status.get('replication', 0),
                                permission=file_status['permission'],
                                owner=file_status['owner'],
                                group=file_status['group']
                            ))
                        logger.debug(f"Listed {len(files)} items in {path}")
                        return files
                    last_err = f"HTTP {response.status_code}"
                except Exception as e:
                    last_err = str(e)
                    continue
            logger.error(f"Failed to list directory {path}: {last_err}")
            return []
        except Exception as e:
            logger.error(f"Error listing directory {path}: {str(e)}")
            return []
    
    def scan_directory_stats(self, path: str, small_file_threshold: int = 128 * 1024 * 1024,
                           max_depth: int = 10, current_depth: int = 0) -> HDFSDirectoryStats:
        """
        扫描目录统计信息（递归）
        
        Args:
            path: 目录路径
            small_file_threshold: 小文件阈值（字节）
            max_depth: 最大递归深度
            current_depth: 当前递归深度
            
        Returns:
            目录统计信息
        """
        logger.info(f"Scanning directory stats: {path} (depth: {current_depth})")
        
        stats = HDFSDirectoryStats(
            total_files=0,
            total_size=0,
            small_files_count=0,
            small_files_size=0,
            large_files_count=0,
            large_files_size=0,
            average_file_size=0,
            directory_count=0
        )
        
        if current_depth >= max_depth:
            logger.warning(f"Max depth {max_depth} reached for path: {path}")
            return stats
        
        try:
            files = self.list_directory(path)
            
            for file_info in files:
                if file_info.is_directory:
                    stats.directory_count += 1
                    # 递归扫描子目录
                    sub_stats = self.scan_directory_stats(
                        file_info.path, small_file_threshold, max_depth, current_depth + 1
                    )
                    # 累加子目录统计
                    stats.total_files += sub_stats.total_files
                    stats.total_size += sub_stats.total_size
                    stats.small_files_count += sub_stats.small_files_count
                    stats.small_files_size += sub_stats.small_files_size
                    stats.large_files_count += sub_stats.large_files_count
                    stats.large_files_size += sub_stats.large_files_size
                    stats.directory_count += sub_stats.directory_count
                else:
                    # 处理文件
                    stats.total_files += 1
                    stats.total_size += file_info.size
                    
                    if file_info.size <= small_file_threshold:
                        stats.small_files_count += 1
                        stats.small_files_size += file_info.size
                    else:
                        stats.large_files_count += 1
                        stats.large_files_size += file_info.size
            
            # 计算平均文件大小
            if stats.total_files > 0:
                stats.average_file_size = stats.total_size // stats.total_files
            
            logger.info(f"Directory {path} stats: {stats.total_files} files, "
                       f"{stats.small_files_count} small files, {stats.directory_count} directories")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error scanning directory stats for {path}: {str(e)}")
            return stats
    
    def get_table_hdfs_stats(self, table_location: str, small_file_threshold: int = 128 * 1024 * 1024,
                             estimate_on_summary: bool = True) -> Dict:
        """
        获取Hive表的HDFS统计信息
        
        Args:
            table_location: 表的HDFS位置
            small_file_threshold: 小文件阈值
            
        Returns:
            包含统计信息的字典
        """
        logger.info(f"Getting HDFS stats for table location: {table_location}")
        
        # 验证路径是否存在
        file_info = self.get_file_status(table_location)
        if not file_info:
            logger.error(f"Table location not found: {table_location}")
            return {
                "success": False,
                "error": f"表路径不存在: {table_location}",
                "total_files": 0,
                "small_files_count": 0,
                "total_size": 0
            }
        
        if not file_info.is_directory:
            logger.error(f"Table location is not a directory: {table_location}")
            return {
                "success": False,
                "error": f"表路径不是目录: {table_location}",
                "total_files": 0,
                "small_files_count": 0,
                "total_size": 0
            }
        
        # 优先使用 GETCONTENTSUMMARY（更快）
        try:
            cs = self.get_content_summary(table_location)
            if cs.get('success'):
                summary = cs.get('content_summary', {})
                total_files = summary.get('fileCount', 0)
                total_size = summary.get('length', 0)
                avg = int(total_size // total_files) if total_files else 0
                # 默认直接返回摘要，但为了避免小文件数长时间为0/1，
                # 在文件数量不大或平均文件大小低于阈值时进行浅层采样估算小文件数量
                estimated_small = 0
                if estimate_on_summary and total_files > 0:
                    # 触发估算条件：文件数较少或平均大小明显小于阈值
                    if total_files <= 5000 or (avg and avg < small_file_threshold):
                        try:
                            max_samples = 2000  # 采样上限，避免深度递归导致开销过大
                            sampled = 0
                            small_sampled = 0

                            # 遍历顶层目录；如遇到子目录，仅深入一层采样
                            top_items = self.list_directory(table_location)
                            for it in top_items:
                                if sampled >= max_samples:
                                    break
                                if it.is_directory:
                                    sub = self.list_directory(it.path)
                                    for subit in sub:
                                        if subit.is_directory:
                                            continue
                                        sampled += 1
                                        if subit.size <= small_file_threshold:
                                            small_sampled += 1
                                        if sampled >= max_samples:
                                            break
                                else:
                                    sampled += 1
                                    if it.size <= small_file_threshold:
                                        small_sampled += 1
                            if sampled > 0:
                                ratio = small_sampled / sampled
                                estimated_small = int(total_files * ratio)
                        except Exception as est_err:
                            logger.warning(f"Small-file estimation skipped due to error: {est_err}")

                # 如果没有估算结果，则保持0（未知）；否则使用估算值
                small_files_count = estimated_small if estimated_small > 0 else 0

                return {
                    "success": True,
                    "table_location": table_location,
                    "total_files": total_files,
                    "total_size": total_size,
                    "small_files_count": small_files_count,
                    "small_files_size": 0,
                    "large_files_count": max(total_files - small_files_count, 0),
                    "large_files_size": total_size,
                    "average_file_size": avg,
                    "directory_count": summary.get('directoryCount', 0),
                    "small_file_threshold": small_file_threshold
                }
        except Exception as e:
            logger.warning(f"GETCONTENTSUMMARY failed: {e}, fallback to LISTSTATUS")

        # 回退到递归扫描（可能较慢）
        stats = self.scan_directory_stats(table_location, small_file_threshold)
        
        return {
            "success": True,
            "table_location": table_location,
            "total_files": stats.total_files,
            "total_size": stats.total_size,
            "small_files_count": stats.small_files_count,
            "small_files_size": stats.small_files_size,
            "large_files_count": stats.large_files_count,
            "large_files_size": stats.large_files_size,
            "average_file_size": stats.average_file_size,
            "directory_count": stats.directory_count,
            "small_file_threshold": small_file_threshold
        }
    
    def get_content_summary(self, path: str) -> Dict:
        """使用 WebHDFS GETCONTENTSUMMARY 获取目录快速统计"""
        try:
            last_err = None
            for base in self._alt_bases():
                url = self._build_url(path, "GETCONTENTSUMMARY").replace(self.webhdfs_base, base, 1)
                try:
                    resp = self.session.get(url, timeout=self.timeout)
                    if resp.status_code == 200:
                        data = resp.json()
                        if 'ContentSummary' in data:
                            return {"success": True, "content_summary": data['ContentSummary']}
                        else:
                            last_err = 'Malformed response'
                            continue
                    last_err = f"HTTP {resp.status_code}"
                except Exception as e:
                    last_err = str(e)
                    continue
            return {"success": False, "error": last_err or 'Unknown error'}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_directory(self, path: str, permission: str = "755") -> Tuple[bool, str]:
        """
        创建目录

        Args:
            path: 目录路径
            permission: 目录权限，默认755

        Returns:
            (是否成功, 错误信息或成功信息)
        """
        try:
            logger.info(f"Creating directory: {path}")
            last_err = None
            for base in self._alt_bases():
                url = self._build_url(path, "MKDIRS", permission=permission).replace(self.webhdfs_base, base, 1)
                try:
                    response = self.session.put(url, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('boolean'):
                            logger.info(f"Directory created successfully: {path}")
                            return True, f"目录创建成功: {path}"
                        else:
                            return False, f"目录创建失败: {path}"
                    last_err = f"HTTP {response.status_code}: {response.text}"
                except Exception as e:
                    last_err = str(e)
                    continue
            logger.error(f"Failed to create directory {path}: {last_err}")
            return False, last_err or "未知错误"
        except Exception as e:
            error_msg = f"创建目录异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def copy_file(self, source_path: str, dest_path: str, overwrite: bool = False) -> Tuple[bool, str]:
        """
        复制文件（通过读取和写入实现）

        Args:
            source_path: 源文件路径
            dest_path: 目标文件路径
            overwrite: 是否覆盖现有文件

        Returns:
            (是否成功, 错误信息或成功信息)
        """
        try:
            logger.info(f"Copying file from {source_path} to {dest_path}")

            # 检查源文件是否存在
            source_info = self.get_file_status(source_path)
            if not source_info:
                return False, f"源文件不存在: {source_path}"

            if source_info.is_directory:
                return False, f"源路径是目录，不能复制: {source_path}"

            # 检查目标文件是否存在
            if not overwrite:
                dest_info = self.get_file_status(dest_path)
                if dest_info:
                    return False, f"目标文件已存在: {dest_path}"

            # 读取源文件内容
            read_success, content = self.read_file(source_path)
            if not read_success:
                return False, f"读取源文件失败: {content}"

            # 写入目标文件
            write_success, write_msg = self.write_file(dest_path, content, overwrite)
            if not write_success:
                return False, f"写入目标文件失败: {write_msg}"

            logger.info(f"File copied successfully from {source_path} to {dest_path}")
            return True, f"文件复制成功: {source_path} -> {dest_path}"

        except Exception as e:
            error_msg = f"文件复制异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def move_file(self, source_path: str, dest_path: str) -> Tuple[bool, str]:
        """
        移动/重命名文件

        Args:
            source_path: 源文件路径
            dest_path: 目标文件路径

        Returns:
            (是否成功, 错误信息或成功信息)
        """
        try:
            logger.info(f"Moving file from {source_path} to {dest_path}")
            last_err = None
            for base in self._alt_bases():
                url = self._build_url(source_path, "RENAME", destination=dest_path).replace(self.webhdfs_base, base, 1)
                try:
                    response = self.session.put(url, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('boolean'):
                            logger.info(f"File moved successfully from {source_path} to {dest_path}")
                            return True, f"文件移动成功: {source_path} -> {dest_path}"
                        else:
                            return False, f"文件移动失败: {source_path} -> {dest_path}"
                    last_err = f"HTTP {response.status_code}: {response.text}"
                except Exception as e:
                    last_err = str(e)
                    continue
            logger.error(f"Failed to move file from {source_path} to {dest_path}: {last_err}")
            return False, last_err or "未知错误"
        except Exception as e:
            error_msg = f"文件移动异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def delete_file(self, path: str, recursive: bool = False) -> Tuple[bool, str]:
        """
        删除文件或目录

        Args:
            path: 文件或目录路径
            recursive: 是否递归删除目录

        Returns:
            (是否成功, 错误信息或成功信息)
        """
        try:
            logger.info(f"Deleting {'recursively' if recursive else ''}: {path}")
            last_err = None
            for base in self._alt_bases():
                url = self._build_url(path, "DELETE", recursive="true" if recursive else "false").replace(self.webhdfs_base, base, 1)
                try:
                    response = self.session.delete(url, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('boolean'):
                            logger.info(f"Deleted successfully: {path}")
                            return True, f"删除成功: {path}"
                        else:
                            return False, f"删除失败: {path}"
                    last_err = f"HTTP {response.status_code}: {response.text}"
                except Exception as e:
                    last_err = str(e)
                    continue
            logger.error(f"Failed to delete {path}: {last_err}")
            return False, last_err or "未知错误"
        except Exception as e:
            error_msg = f"删除异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def read_file(self, path: str, offset: int = 0, length: Optional[int] = None) -> Tuple[bool, bytes]:
        """
        读取文件内容

        Args:
            path: 文件路径
            offset: 读取偏移量
            length: 读取长度

        Returns:
            (是否成功, 文件内容或错误信息)
        """
        try:
            logger.debug(f"Reading file: {path}")
            last_err = None
            for base in self._alt_bases():
                params = {"offset": offset}
                if length is not None:
                    params["length"] = length
                url = self._build_url(path, "OPEN", **params).replace(self.webhdfs_base, base, 1)
                try:
                    response = self.session.get(url, timeout=self.timeout)
                    if response.status_code == 200:
                        logger.debug(f"File read successfully: {path}")
                        return True, response.content
                    last_err = f"HTTP {response.status_code}: {response.text}"
                except Exception as e:
                    last_err = str(e)
                    continue
            logger.error(f"Failed to read file {path}: {last_err}")
            return False, last_err or "未知错误"
        except Exception as e:
            error_msg = f"读取文件异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def write_file(self, path: str, content: bytes, overwrite: bool = False,
                   blocksize: Optional[int] = None, replication: Optional[int] = None,
                   permission: str = "644") -> Tuple[bool, str]:
        """
        写入文件内容

        Args:
            path: 文件路径
            content: 文件内容
            overwrite: 是否覆盖现有文件
            blocksize: 块大小
            replication: 副本数
            permission: 文件权限

        Returns:
            (是否成功, 错误信息或成功信息)
        """
        try:
            logger.info(f"Writing file: {path}")
            last_err = None
            for base in self._alt_bases():
                params = {
                    "overwrite": "true" if overwrite else "false",
                    "permission": permission
                }
                if blocksize:
                    params["blocksize"] = blocksize
                if replication:
                    params["replication"] = replication

                # 第一步：创建文件
                create_url = self._build_url(path, "CREATE", **params).replace(self.webhdfs_base, base, 1)
                try:
                    create_response = self.session.put(create_url, timeout=self.timeout, allow_redirects=False)
                    if create_response.status_code == 307:
                        # 第二步：写入数据到重定向的DataNode
                        redirect_url = create_response.headers.get('Location')
                        if redirect_url:
                            write_response = self.session.put(redirect_url, data=content, timeout=self.timeout)
                            if write_response.status_code == 201:
                                logger.info(f"File written successfully: {path}")
                                return True, f"文件写入成功: {path}"
                            else:
                                last_err = f"Write failed - HTTP {write_response.status_code}: {write_response.text}"
                        else:
                            last_err = "No redirect location in response"
                    else:
                        last_err = f"Create failed - HTTP {create_response.status_code}: {create_response.text}"
                except Exception as e:
                    last_err = str(e)
                    continue
            logger.error(f"Failed to write file {path}: {last_err}")
            return False, last_err or "未知错误"
        except Exception as e:
            error_msg = f"写入文件异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def archive_directory(self, source_path: str, archive_path: str,
                         create_archive_dir: bool = True) -> Tuple[bool, str]:
        """
        归档目录（移动到归档位置）

        Args:
            source_path: 源目录路径
            archive_path: 归档目录路径
            create_archive_dir: 是否创建归档目录

        Returns:
            (是否成功, 错误信息或成功信息)
        """
        try:
            logger.info(f"Archiving directory from {source_path} to {archive_path}")

            # 检查源目录是否存在
            source_info = self.get_file_status(source_path)
            if not source_info:
                return False, f"源目录不存在: {source_path}"

            if not source_info.is_directory:
                return False, f"源路径不是目录: {source_path}"

            # 创建归档目录的父目录
            if create_archive_dir:
                import os
                archive_parent = os.path.dirname(archive_path)
                if archive_parent and archive_parent != '/':
                    create_success, create_msg = self.create_directory(archive_parent)
                    if not create_success and "已存在" not in create_msg:
                        return False, f"创建归档父目录失败: {create_msg}"

            # 移动目录
            move_success, move_msg = self.move_file(source_path, archive_path)
            if move_success:
                return True, f"目录归档成功: {source_path} -> {archive_path}"
            else:
                return False, f"目录归档失败: {move_msg}"

        except Exception as e:
            error_msg = f"目录归档异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def restore_directory(self, archive_path: str, restore_path: str) -> Tuple[bool, str]:
        """
        恢复目录（从归档位置移动回原位置）

        Args:
            archive_path: 归档目录路径
            restore_path: 恢复目录路径

        Returns:
            (是否成功, 错误信息或成功信息)
        """
        try:
            logger.info(f"Restoring directory from {archive_path} to {restore_path}")

            # 检查归档目录是否存在
            archive_info = self.get_file_status(archive_path)
            if not archive_info:
                return False, f"归档目录不存在: {archive_path}"

            if not archive_info.is_directory:
                return False, f"归档路径不是目录: {archive_path}"

            # 检查恢复位置是否已存在
            restore_info = self.get_file_status(restore_path)
            if restore_info:
                return False, f"恢复位置已存在: {restore_path}"

            # 移动目录
            move_success, move_msg = self.move_file(archive_path, restore_path)
            if move_success:
                return True, f"目录恢复成功: {archive_path} -> {restore_path}"
            else:
                return False, f"目录恢复失败: {move_msg}"

        except Exception as e:
            error_msg = f"目录恢复异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def close(self):
        """关闭客户端连接"""
        if hasattr(self, 'session'):
            self.session.close()
            logger.info("WebHDFS client session closed")


# 测试函数
if __name__ == "__main__":
    # 测试WebHDFS客户端
    namenode_url = "http://192.168.0.100:50070"  # 替换为实际的NameNode URL
    
    client = WebHDFSClient(namenode_url, user="hdfs")
    
    print("Testing WebHDFS connection...")
    success, message = client.test_connection()
    print(f"Connection test: {success}, Message: {message}")
    
    if success:
        # 测试获取根目录状态
        root_info = client.get_file_status("/")
        print(f"Root directory info: {root_info}")
        
        # 测试列出目录
        files = client.list_directory("/")
        print(f"Root directory contains {len(files)} items")
        
        # 测试扫描统计
        if files:
            test_path = files[0].path if files[0].is_directory else "/"
            stats = client.scan_directory_stats(test_path, max_depth=2)
            print(f"Directory stats for {test_path}: {stats}")
    
    client.close()
