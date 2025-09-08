import logging
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os
from urllib.parse import urlparse
from hdfs3 import HDFileSystem

logger = logging.getLogger(__name__)

class HDFSScanner:
    """
    HDFS 文件扫描器，用于收集文件分布和大小统计
    """
    
    def __init__(self, hdfs_url: str, user: str = "hdfs"):
        """
        初始化 HDFS 扫描器
        Args:
            hdfs_url: HDFS NameNode URL, e.g., hdfs://namenode:9000
            user: HDFS 用户名
        """
        self.hdfs_url = hdfs_url
        self.user = user
        self._fs = None
        
        # 解析 HDFS URL
        parsed = urlparse(hdfs_url)
        self.namenode_host = parsed.hostname
        self.namenode_port = parsed.port or 9000
    
    def connect(self) -> bool:
        """建立 HDFS 连接"""
        try:
            self._fs = HDFileSystem(
                host=self.namenode_host,
                port=self.namenode_port,
                user=self.user
            )
            logger.info(f"Connected to HDFS: {self.hdfs_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to HDFS: {e}")
            return False
    
    def disconnect(self):
        """关闭 HDFS 连接"""
        if self._fs:
            # hdfs3 doesn't have explicit close method
            self._fs = None
    
    def scan_directory(self, path: str, small_file_threshold: int = 128*1024*1024) -> Dict:
        """
        扫描指定目录的文件分布
        Args:
            path: HDFS 路径
            small_file_threshold: 小文件阈值（字节）
        Returns:
            文件统计信息字典
        """
        if not self._fs:
            raise ConnectionError("Not connected to HDFS")
        
        start_time = time.time()
        stats = {
            'path': path,
            'total_files': 0,
            'small_files': 0,
            'total_size': 0,
            'avg_file_size': 0.0,
            'file_size_distribution': {},  # size_range -> count
            'scan_time': start_time,
            'scan_duration': 0.0,
            'error': None
        }
        
        try:
            if not self._fs.exists(path):
                stats['error'] = f"Path does not exist: {path}"
                return stats
            
            # 递归遍历目录获取所有文件
            file_sizes = []
            for file_path in self._walk_directory(path):
                try:
                    file_info = self._fs.info(file_path)
                    if file_info['kind'] == 'file':
                        size = file_info['size']
                        file_sizes.append(size)
                        
                        # 统计小文件
                        if size < small_file_threshold:
                            stats['small_files'] += 1
                        
                        # 文件大小分布统计
                        size_range = self._get_size_range(size)
                        stats['file_size_distribution'][size_range] = \
                            stats['file_size_distribution'].get(size_range, 0) + 1
                            
                except Exception as e:
                    logger.warning(f"Failed to get info for file {file_path}: {e}")
                    continue
            
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
        if not self._fs:
            raise ConnectionError("Not connected to HDFS")
        
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
            return table_stats, []
        
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
    
    def _walk_directory(self, path: str) -> List[str]:
        """递归遍历目录获取所有文件路径"""
        file_paths = []
        try:
            for item in self._fs.walk(path):
                if self._fs.info(item)['kind'] == 'file':
                    file_paths.append(item)
        except Exception as e:
            logger.error(f"Error walking directory {path}: {e}")
        return file_paths
    
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
    
    def test_connection(self) -> Dict[str, any]:
        """测试 HDFS 连接"""
        if not self.connect():
            return {'status': 'error', 'message': 'Failed to connect to HDFS'}
        
        try:
            # 测试基本操作
            home_dir = f"/user/{self.user}"
            if self._fs.exists(home_dir):
                file_list = self._fs.ls(home_dir, detail=False)[:5]  # 只获取前5个文件
                return {
                    'status': 'success',
                    'namenode': f"{self.namenode_host}:{self.namenode_port}",
                    'user': self.user,
                    'sample_files': file_list
                }
            else:
                return {
                    'status': 'success',
                    'namenode': f"{self.namenode_host}:{self.namenode_port}",
                    'user': self.user,
                    'message': f"Home directory {home_dir} does not exist"
                }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            self.disconnect()

    def __enter__(self):
        """Context manager entry"""
        if not self.connect():
            raise ConnectionError("Failed to connect to HDFS")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()