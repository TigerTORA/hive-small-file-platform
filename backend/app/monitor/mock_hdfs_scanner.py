import logging
import random
import time
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class MockHDFSScanner:
    """
    模拟HDFS扫描器，用于演示小文件检测功能
    实际部署时需要替换为真实的HDFS客户端
    """
    
    def __init__(self, namenode_url: str, user: str = "hdfs"):
        self.namenode_url = namenode_url
        self.user = user
        self._connected = False
    
    def connect(self) -> bool:
        """模拟连接到HDFS"""
        try:
            # 模拟连接延迟
            time.sleep(0.1)
            self._connected = True
            logger.info(f"Mock connected to HDFS: {self.namenode_url}")
            return True
        except Exception as e:
            logger.error(f"Mock HDFS connection failed: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self._connected = False
        logger.info("Disconnected from mock HDFS")
    
    def test_connection(self) -> Dict[str, any]:
        """测试连接"""
        if self.connect():
            return {
                'status': 'success',
                'namenode': self.namenode_url,
                'user': self.user,
                'connected': True
            }
        else:
            return {
                'status': 'error', 
                'message': 'Failed to connect to HDFS',
                'connected': False
            }
    
    def scan_table_partitions(self, table_path: str, partitions: List[Dict], 
                            small_file_threshold: int) -> Tuple[Dict, List[Dict]]:
        """
        扫描表分区的文件分布情况
        返回: (表级统计, 分区级统计列表)
        """
        if not self._connected:
            raise ConnectionError("Not connected to HDFS")
        
        logger.info(f"Mock scanning table at {table_path}")
        
        # 模拟扫描延迟
        time.sleep(random.uniform(0.5, 2.0))
        
        # 生成模拟的表级统计
        total_files = random.randint(100, 10000)
        small_files = random.randint(int(total_files * 0.2), int(total_files * 0.8))
        total_size = random.randint(1024*1024*100, 1024*1024*1024*50)  # 100MB to 50GB
        
        table_stats = {
            'total_files': total_files,
            'small_files': small_files,
            'total_size': total_size,
            'avg_file_size': total_size / total_files if total_files > 0 else 0,
            'scan_duration': random.uniform(0.5, 3.0)
        }
        
        # 生成分区级统计
        partition_stats = []
        if partitions:
            # 有分区的表
            for partition in partitions:
                partition_files = random.randint(10, int(total_files / len(partitions)) * 2)
                partition_small_files = random.randint(0, partition_files)
                partition_size = random.randint(1024*1024*10, total_size // len(partitions) * 2)
                
                partition_stats.append({
                    'partition_name': partition['partition_name'],
                    'partition_path': partition['partition_path'],
                    'file_count': partition_files,
                    'small_file_count': partition_small_files,
                    'total_size': partition_size,
                    'avg_file_size': partition_size / partition_files if partition_files > 0 else 0
                })
        else:
            # 无分区的表，创建一个默认分区统计
            partition_stats.append({
                'partition_name': 'default',
                'partition_path': table_path,
                'file_count': total_files,
                'small_file_count': small_files,
                'total_size': total_size,
                'avg_file_size': table_stats['avg_file_size']
            })
        
        return table_stats, partition_stats
    
    def get_directory_stats(self, path: str) -> Dict:
        """获取目录的文件统计信息"""
        if not self._connected:
            raise ConnectionError("Not connected to HDFS")
        
        # 模拟目录扫描
        file_count = random.randint(1, 1000)
        total_size = random.randint(1024*1024, 1024*1024*1024*10)
        
        return {
            'path': path,
            'file_count': file_count,
            'total_size': total_size,
            'avg_file_size': total_size / file_count,
            'directories': random.randint(0, 20),
            'last_modified': time.time()
        }