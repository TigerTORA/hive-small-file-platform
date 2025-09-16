from typing import Dict, Type, Optional
from app.engines.base_engine import BaseMergeEngine
from app.engines.safe_hive_engine import SafeHiveMergeEngine
from app.models.cluster import Cluster

class MergeEngineFactory:
    """
    简化的合并引擎工厂类
    统一使用SafeHiveMergeEngine，支持智能策略选择
    """
    
    # 统一使用SafeHiveMergeEngine，支持多种策略
    _default_engine: Type[BaseMergeEngine] = SafeHiveMergeEngine
    
    @classmethod
    def get_engine(cls, cluster: Cluster, engine_type: Optional[str] = None) -> BaseMergeEngine:
        """
        获取合并引擎实例
        统一使用SafeHiveMergeEngine，支持智能策略选择
        
        Args:
            cluster: 集群配置对象
            engine_type: 保留参数以维持向后兼容性（已弃用）
        
        Returns:
            SafeHiveMergeEngine实例
        """
        # 统一使用SafeHiveMergeEngine
        return cls._default_engine(cluster)
    
    @classmethod
    def get_engine_capabilities(cls) -> Dict[str, any]:
        """
        获取SafeHiveMergeEngine的能力信息
        
        Returns:
            引擎能力信息字典
        """
        return {
            'supported_strategies': ['concatenate', 'insert_overwrite', 'safe_merge'],
            'supported_formats': ['TEXTFILE', 'SEQUENCEFILE', 'RCFILE', 'PARQUET', 'ORC'],
            'supports_partitions': True,
            'supports_preview': True,
            'parallel_execution': False,
            'typical_performance': 'medium',
            'zero_downtime': True,
            'rollback_support': True,
            'smart_strategy_selection': True
        }
    
    @classmethod
    def recommend_strategy(cls, cluster: Cluster, table_format: str = None, 
                          file_count: int = 0, partition_count: int = 0, 
                          table_size: int = 0, is_production: bool = True) -> str:
        """
        智能推荐合并策略
        
        Args:
            cluster: 集群配置
            table_format: 表存储格式
            file_count: 文件数量
            partition_count: 分区数量  
            table_size: 表大小（字节）
            is_production: 是否为生产环境
            
        Returns:
            推荐的合并策略
        """
        # 生产环境优先使用安全合并策略
        # 大表优先选择零停机安全合并：生产环境 ≥1GB 直接使用 safe_merge
        if is_production and table_size >= 1024 * 1024 * 1024:  # 大于等于1GB
            return 'safe_merge'
        
        # 基于表格式和文件数量推荐策略
        format_upper = table_format.upper() if table_format else ''
        if format_upper in ['TEXTFILE', 'SEQUENCEFILE', 'RCFILE']:
            # 对于行存储格式
            if file_count < 100:
                return 'concatenate'  # 文件少时，CONCATENATE最快
            elif file_count < 1000:
                return 'insert_overwrite'  # 中等文件数，INSERT OVERWRITE更可靠
            else:
                return 'safe_merge'  # 文件太多时，使用安全合并
        elif format_upper in ['PARQUET', 'ORC']:
            # 对于列存储格式，INSERT OVERWRITE 通常更好
            if file_count < 500:
                return 'insert_overwrite'
            else:
                return 'safe_merge'  # 大量文件时使用安全合并
        else:
            # 未知格式，默认使用安全合并
            return 'safe_merge'
    
    @classmethod
    def validate_strategy_compatibility(cls, merge_strategy: str, 
                                      table_format: str = None) -> Dict[str, any]:
        """
        验证策略兼容性
        
        Args:
            merge_strategy: 合并策略
            table_format: 表格式
            
        Returns:
            验证结果字典
        """
        result = {
            'compatible': True,
            'valid': True,
            'warnings': [],
            'recommendations': []
        }
        
        capabilities = cls.get_engine_capabilities()
        
        # 检查引擎是否支持该策略
        if merge_strategy not in capabilities.get('supported_strategies', []):
            result['compatible'] = False
            result['valid'] = False
            result['warnings'].append(f"SafeHiveMergeEngine does not support strategy {merge_strategy}")
            return result
        
        # 检查策略和表格式的兼容性
        if table_format:
            format_upper = table_format.upper()
            if merge_strategy == 'concatenate' and format_upper not in ['TEXTFILE', 'SEQUENCEFILE', 'RCFILE']:
                result['warnings'].append(f"CONCATENATE strategy may not work optimally with {table_format} format")
                result['recommendations'].append("Consider using INSERT OVERWRITE or SAFE_MERGE strategy instead")

            if merge_strategy == 'insert_overwrite' and format_upper in ['PARQUET', 'ORC']:
                result['recommendations'].append("For large tables, consider using SAFE_MERGE for zero-downtime operation")
        
        return result
    
    @classmethod 
    def create_smart_merge_task(cls, cluster: Cluster, database_name: str, table_name: str,
                               table_format: str = None, file_count: int = 0,
                               table_size: int = 0, partition_count: int = 0) -> Dict[str, any]:
        """
        创建智能合并任务，自动选择最佳策略
        
        Args:
            cluster: 集群配置
            database_name: 数据库名
            table_name: 表名
            table_format: 表格式
            file_count: 文件数量
            table_size: 表大小
            partition_count: 分区数量
            
        Returns:
            任务配置字典
        """
        # 智能推荐策略
        recommended_strategy = cls.recommend_strategy(
            cluster=cluster,
            table_format=table_format,
            file_count=file_count,
            table_size=table_size,
            partition_count=partition_count,
            is_production=True
        )
        
        # 验证策略兼容性
        validation = cls.validate_strategy_compatibility(recommended_strategy, table_format)

        # 针对极端规模补充风险提示（不改变 valid 结论，仅加 warnings）
        try:
            if file_count and file_count > 5000:
                validation.setdefault('warnings', []).append(
                    f"文件数量过多({file_count})，建议分批处理或在低峰期执行")
            if partition_count and partition_count > 1000:
                validation.setdefault('warnings', []).append(
                    f"分区数量过多({partition_count})，建议限制并发或按分区批次合并")
        except Exception:
            # 不因指标计算失败影响任务创建
            pass
        
        return {
            'database_name': database_name,
            'table_name': table_name,
            'recommended_strategy': recommended_strategy,
            'validation': validation,
            'task_name': f"Smart merge for {database_name}.{table_name}",
            'strategy_reason': cls._get_strategy_reason(recommended_strategy, file_count, table_format, table_size)
        }
    
    @classmethod
    def _get_strategy_reason(cls, strategy: str, file_count: int, table_format: str, table_size: int) -> str:
        """
        获取策略选择原因
        """
        # 细化提示文案：小表/中等/大表
        size_mb = max(0, (table_size or 0) // (1024 * 1024))
        if strategy == 'concatenate':
            return f"小表/文件较少({file_count})且为行存储格式({table_format})，CONCATENATE最高效"
        if strategy == 'insert_overwrite':
            # 认为 <256MB 或文件数 <100 为小表场景
            if (table_size and table_size < 256 * 1024 * 1024) or (file_count and file_count < 100):
                return f"小表({size_mb}MB, {file_count}文件)，INSERT OVERWRITE在可靠性与性能间更均衡"
            return f"中等文件数量({file_count})，INSERT OVERWRITE平衡性能和可靠性"
        if strategy == 'safe_merge':
            return f"大量文件({file_count})或大表({size_mb}MB)，使用零停机安全合并"
        return f"根据表特征选择{strategy}策略"
