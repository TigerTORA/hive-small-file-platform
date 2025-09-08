import logging
import requests
import time
from typing import Dict, List, Tuple, Optional
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

logger = logging.getLogger(__name__)

class WebHDFSScanner:
    """
    WebHDFS REST API版本的文件扫描器，兼容性更好
    使用HTTP协议连接HDFS，无需安装特殊的Python库
    """
    
    def __init__(self, namenode_url: str, user: str = "hdfs", webhdfs_port: int = 9870):
        """
        初始化WebHDFS扫描器
        Args:
            namenode_url: NameNode URL, e.g., hdfs://nameservice1 or http://namenode:9870
            user: HDFS用户名
            webhdfs_port: WebHDFS端口，默认9870
        """
        self.user = user
        self._connected = False
        
        # 解析URL并构造WebHDFS基础URL
        if namenode_url.startswith('hdfs://'):
            # 从HDFS URL推断WebHDFS URL
            parsed = urlparse(namenode_url)
            if parsed.hostname:
                self.webhdfs_base_url = f"http://{parsed.hostname}:{webhdfs_port}/webhdfs/v1"
            else:
                # 处理nameservice情况，尝试常见的WebHDFS端口
                # 这里需要根据实际环境配置
                self.webhdfs_base_url = f"http://192.168.0.105:{webhdfs_port}/webhdfs/v1"
        elif namenode_url.startswith('http://'):
            # 直接使用HTTP URL
            parsed = urlparse(namenode_url)
            self.webhdfs_base_url = f"http://{parsed.netloc}/webhdfs/v1"
        else:
            # 假设是主机名
            self.webhdfs_base_url = f"http://{namenode_url}:{webhdfs_port}/webhdfs/v1"
        
        logger.info(f"WebHDFS base URL: {self.webhdfs_base_url}")
        
        # HTTP会话
        self.session = requests.Session()
        self.session.timeout = 30
    
    def connect(self) -> bool:
        """测试WebHDFS连接"""
        try:
            # 测试根目录访问
            response = self._get_request("/", "LISTSTATUS")
            if response.status_code == 200:
                self._connected = True
                logger.info(f"Connected to WebHDFS: {self.webhdfs_base_url}")
                return True
            else:
                logger.error(f"WebHDFS connection failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to WebHDFS: {e}")
            return False
    
    def disconnect(self):
        """关闭连接"""
        self._connected = False
        self.session.close()
        logger.info("Disconnected from WebHDFS")
    
    def _get_request(self, path: str, operation: str, **params) -> requests.Response:
        """发送WebHDFS GET请求"""
        url = urljoin(self.webhdfs_base_url, path.lstrip('/'))
        params.update({
            'op': operation,
            'user.name': self.user
        })
        return self.session.get(url, params=params)
    
    def test_connection(self) -> Dict[str, any]:
        """测试WebHDFS连接"""
        if not self.connect():
            return {'status': 'error', 'message': 'Failed to connect to WebHDFS'}
        
        try:
            # 测试根目录列出
            response = self._get_request("/", "LISTSTATUS")
            if response.status_code == 200:
                data = response.json()
                file_statuses = data.get('FileStatuses', {}).get('FileStatus', [])
                sample_files = [f['pathSuffix'] for f in file_statuses[:5]]
                
                return {
                    'status': 'success',
                    'webhdfs_url': self.webhdfs_base_url,
                    'user': self.user,
                    'sample_paths': sample_files
                }
            else:
                return {
                    'status': 'error', 
                    'message': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            self.disconnect()
    
    def scan_directory(self, path: str, small_file_threshold: int = 128*1024*1024) -> Dict:
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
            'path': path,
            'total_files': 0,
            'small_files': 0,
            'total_size': 0,
            'avg_file_size': 0.0,
            'file_size_distribution': {},
            'scan_time': start_time,
            'scan_duration': 0.0,
            'error': None
        }
        
        try:
            # 检查路径是否存在
            response = self._get_request(path, "GETFILESTATUS")
            if response.status_code != 200:
                stats['error'] = f"Path does not exist or inaccessible: {path}"
                return stats
            
            # 递归遍历目录获取所有文件
            file_sizes = []
            for file_info in self._walk_directory(path):
                if file_info['type'] == 'FILE':
                    size = file_info['length']
                    file_sizes.append(size)
                    
                    # 统计小文件
                    if size < small_file_threshold:
                        stats['small_files'] += 1
                    
                    # 文件大小分布统计
                    size_range = self._get_size_range(size)
                    stats['file_size_distribution'][size_range] = \
                        stats['file_size_distribution'].get(size_range, 0) + 1
            
            # 计算统计信息
            stats['total_files'] = len(file_sizes)
            stats['total_size'] = sum(file_sizes)
            stats['avg_file_size'] = stats['total_size'] / stats['total_files'] if file_sizes else 0.0
            stats['scan_duration'] = time.time() - start_time
            
            logger.info(f"Scanned {path}: {stats['total_files']} files, "
                       f"{stats['small_files']} small files, "
                       f"{stats['total_size'] / (1024**3):.2f} GB total")
            
        except Exception as e:
            logger.error(f"Failed to scan directory {path}: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def _walk_directory(self, path: str) -> List[Dict]:
        """递归遍历目录获取所有文件信息"""
        files = []
        try:
            response = self._get_request(path, "LISTSTATUS")
            if response.status_code != 200:
                logger.warning(f"Cannot list directory {path}: HTTP {response.status_code}")
                return files
            
            data = response.json()
            file_statuses = data.get('FileStatuses', {}).get('FileStatus', [])
            
            for file_status in file_statuses:
                file_path = path.rstrip('/') + '/' + file_status['pathSuffix']
                
                if file_status['type'] == 'FILE':
                    files.append(file_status)
                elif file_status['type'] == 'DIRECTORY':
                    # 递归遍历子目录
                    files.extend(self._walk_directory(file_path))
                    
        except Exception as e:
            logger.error(f"Error walking directory {path}: {e}")
        
        return files
    
    def scan_table_partitions(self, table_path: str, partitions: List[Dict], 
                            small_file_threshold: int = 128*1024*1024,
                            max_workers: int = 4) -> Tuple[Dict, List[Dict]]:
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
            'table_path': table_path,
            'total_files': 0,
            'small_files': 0,
            'total_size': 0,
            'avg_file_size': 0.0,
            'partition_count': len(partitions),
            'scan_duration': 0.0
        }
        
        partition_stats = []
        
        if not partitions:
            # 非分区表，直接扫描表路径
            stats = self.scan_directory(table_path, small_file_threshold)
            table_stats.update({
                'total_files': stats['total_files'],
                'small_files': stats['small_files'],
                'total_size': stats['total_size'],
                'avg_file_size': stats['avg_file_size'],
                'scan_duration': time.time() - start_time
            })
            
            # 为非分区表创建一个默认分区统计
            if stats['total_files'] > 0:
                partition_stats.append({
                    'partition_name': 'default',
                    'partition_path': table_path,
                    'file_count': stats['total_files'],
                    'small_file_count': stats['small_files'],
                    'total_size': stats['total_size'],
                    'avg_file_size': stats['avg_file_size']
                })
            
            return table_stats, partition_stats
        
        # 并行扫描分区
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交扫描任务
            future_to_partition = {}
            for partition in partitions:
                future = executor.submit(
                    self.scan_directory, 
                    partition['partition_path'], 
                    small_file_threshold
                )
                future_to_partition[future] = partition
            
            # 收集结果
            for future in as_completed(future_to_partition):
                partition = future_to_partition[future]
                try:
                    result = future.result()
                    if not result.get('error'):
                        # 累计到表级统计
                        table_stats['total_files'] += result['total_files']
                        table_stats['small_files'] += result['small_files']
                        table_stats['total_size'] += result['total_size']
                        
                        # 添加分区级统计
                        partition_stats.append({
                            'partition_name': partition['partition_name'],
                            'partition_path': partition['partition_path'],
                            'file_count': result['total_files'],
                            'small_file_count': result['small_files'],
                            'total_size': result['total_size'],
                            'avg_file_size': result['avg_file_size']
                        })
                    else:
                        logger.error(f"Failed to scan partition {partition['partition_name']}: {result['error']}")
                
                except Exception as e:
                    logger.error(f"Exception scanning partition {partition['partition_name']}: {e}")
        
        # 计算平均文件大小
        if table_stats['total_files'] > 0:
            table_stats['avg_file_size'] = table_stats['total_size'] / table_stats['total_files']
        
        table_stats['scan_duration'] = time.time() - start_time
        
        logger.info(f"Scanned table {table_path}: "
                   f"{table_stats['total_files']} files, "
                   f"{table_stats['small_files']} small files, "
                   f"{len(partition_stats)} partitions scanned")
        
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