from typing import Dict, Type, Optional
from app.engines.base_engine import BaseMergeEngine
from app.engines.hive_engine import HiveMergeEngine
from app.models.cluster import Cluster

class MergeEngineFactory:
    """
    合并引擎工厂类
    根据集群配置和策略选择合适的合并引擎
    """
    
    # 注册的引擎类
    _engines: Dict[str, Type[BaseMergeEngine]] = {
        'hive': HiveMergeEngine,
        # 可以扩展其他引擎，如 Spark 引擎、Impala 引擎等
        # 'spark': SparkMergeEngine,
        # 'impala': ImpalaMergeEngine,
    }
    
    @classmethod
    def get_engine(cls, cluster: Cluster, engine_type: Optional[str] = None) -> BaseMergeEngine:
        """
        获取合并引擎实例
        
        Args:
            cluster: 集群配置对象
            engine_type: 指定的引擎类型，如果不指定则自动选择
        
        Returns:
            合并引擎实例
        
        Raises:
            ValueError: 当指定的引擎类型不存在时
        """
        if engine_type:
            # 使用指定的引擎类型
            if engine_type not in cls._engines:
                raise ValueError(f"Unknown engine type: {engine_type}")
            engine_class = cls._engines[engine_type]
        else:
            # 自动选择引擎类型
            engine_class = cls._auto_select_engine(cluster)
        
        return engine_class(cluster)
    
    @classmethod
    def _auto_select_engine(cls, cluster: Cluster) -> Type[BaseMergeEngine]:
        """
        根据集群配置自动选择合并引擎
        
        Args:
            cluster: 集群配置对象
            
        Returns:
            引擎类
        """
        # 目前默认使用 Hive 引擎
        # 将来可以根据集群的特征自动选择最佳引擎
        # 例如：
        # - 如果集群有 Spark，可以选择 Spark 引擎
        # - 如果集群有 Impala，可以选择 Impala 引擎
        # - 根据表的格式和大小选择最适合的引擎
        
        return cls._engines['hive']
    
    @classmethod
    def register_engine(cls, name: str, engine_class: Type[BaseMergeEngine]):
        """
        注册新的引擎类
        
        Args:
            name: 引擎名称
            engine_class: 引擎类
        """
        if not issubclass(engine_class, BaseMergeEngine):
            raise ValueError("Engine class must inherit from BaseMergeEngine")
        
        cls._engines[name] = engine_class
    
    @classmethod
    def list_engines(cls) -> Dict[str, str]:
        """
        列出所有可用的引擎
        
        Returns:
            引擎名称到描述的映射
        """
        return {
            'hive': 'Hive SQL Engine - 使用 Hive SQL 命令进行文件合并',
            # 'spark': 'Spark Engine - 使用 Spark 进行分布式文件合并',
            # 'impala': 'Impala Engine - 使用 Impala SQL 进行文件合并',
        }
    
    @classmethod
    def get_engine_capabilities(cls, engine_type: str) -> Dict[str, any]:
        """
        获取指定引擎的能力信息
        
        Args:
            engine_type: 引擎类型
            
        Returns:
            引擎能力信息字典
        """
        capabilities = {
            'hive': {
                'supported_strategies': ['concatenate', 'insert_overwrite'],
                'supported_formats': ['TEXTFILE', 'SEQUENCEFILE', 'RCFILE', 'PARQUET', 'ORC'],
                'supports_partitions': True,
                'supports_preview': True,
                'parallel_execution': False,
                'typical_performance': 'medium'
            }
            # 可以为其他引擎添加能力信息
        }
        
        return capabilities.get(engine_type, {})
    
    @classmethod
    def recommend_strategy(cls, cluster: Cluster, table_format: str, 
                          file_count: int, partition_count: int = 0) -> str:
        """
        推荐合并策略
        
        Args:
            cluster: 集群配置
            table_format: 表存储格式
            file_count: 文件数量
            partition_count: 分区数量
            
        Returns:
            推荐的合并策略
        """
        # 基于表格式和文件数量推荐策略
        if table_format in ['TEXTFILE', 'SEQUENCEFILE', 'RCFILE']:
            # 对于这些格式，CONCATENATE 通常更高效
            if file_count < 1000:
                return 'concatenate'
            else:
                return 'insert_overwrite'  # 文件太多时，INSERT OVERWRITE 更可靠
        else:
            # 对于列存储格式（Parquet、ORC），INSERT OVERWRITE 通常更好
            return 'insert_overwrite'
    
    @classmethod
    def validate_strategy_compatibility(cls, engine_type: str, merge_strategy: str, 
                                      table_format: str) -> Dict[str, any]:
        """
        验证策略兼容性
        
        Args:
            engine_type: 引擎类型
            merge_strategy: 合并策略
            table_format: 表格式
            
        Returns:
            验证结果字典
        """
        result = {
            'compatible': True,
            'warnings': [],
            'recommendations': []
        }
        
        capabilities = cls.get_engine_capabilities(engine_type)
        
        # 检查引擎是否支持该策略
        if merge_strategy not in capabilities.get('supported_strategies', []):
            result['compatible'] = False
            result['warnings'].append(f"Engine {engine_type} does not support strategy {merge_strategy}")
        
        # 检查策略和表格式的兼容性
        if merge_strategy == 'concatenate' and table_format not in ['TEXTFILE', 'SEQUENCEFILE', 'RCFILE']:
            result['warnings'].append(f"CONCATENATE strategy may not work well with {table_format} format")
            result['recommendations'].append("Consider using INSERT OVERWRITE strategy instead")
        
        return result