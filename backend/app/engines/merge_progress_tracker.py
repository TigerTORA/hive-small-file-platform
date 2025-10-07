"""
合并进度追踪器模块
负责合并任务的进度追踪、预览和时间估算
"""

import logging
import time
from typing import Any, Dict, Optional

from app.engines.connection_manager import HiveConnectionManager
from app.models.merge_task import MergeTask

logger = logging.getLogger(__name__)


class MergeProgressTracker:
    """合并进度追踪器"""

    def __init__(self, connection_manager: HiveConnectionManager):
        self.connection_manager = connection_manager

    def get_merge_preview(self, task: MergeTask) -> Dict[str, Any]:
        """获取合并预览信息"""
        try:
            preview_data = {
                "table_info": {
                    "database": task.database_name,
                    "table": task.table_name,
                    "partition_filter": task.partition_filter,
                },
                "current_file_stats": {},
                "estimated_result": {},
                "risks": [],
                "recommendations": [],
            }

            # 获取当前文件统计
            current_stats = self._get_current_file_stats(task)
            preview_data["current_file_stats"] = current_stats

            # 估算合并结果
            estimated_result = self._estimate_merge_result(task, current_stats)
            preview_data["estimated_result"] = estimated_result

            # 风险评估
            risks = self._assess_merge_risks(task, current_stats)
            preview_data["risks"] = risks

            # 生成建议
            recommendations = self._generate_recommendations(task, current_stats, risks)
            preview_data["recommendations"] = recommendations

            return preview_data

        except Exception as e:
            logger.error(f"Failed to generate merge preview: {e}")
            return {
                "error": str(e),
                "table_info": {
                    "database": task.database_name,
                    "table": task.table_name,
                    "partition_filter": task.partition_filter,
                },
            }

    def estimate_duration(self, task: MergeTask) -> int:
        """估算合并任务执行时间（秒）"""
        try:
            # 获取表的基本信息
            file_count = self._get_file_count(
                task.database_name, task.table_name, task.partition_filter
            )
            if file_count is None:
                return 300  # 默认5分钟

            # 统一合并策略的时间估算
            base_time = 120  # 基础时间120秒
            per_file_time = 0.8  # 每个文件0.8秒

            estimated_time = base_time + (file_count * per_file_time)

            # 添加分区表的额外开销
            if task.partition_filter:
                estimated_time *= 1.2

            return int(estimated_time)

        except Exception as e:
            logger.error(f"Failed to estimate duration: {e}")
            return 300  # 默认5分钟

    def _get_current_file_stats(self, task: MergeTask) -> Dict[str, Any]:
        """获取当前文件统计信息"""
        try:
            stats = {
                "total_files": 0,
                "small_files": 0,
                "total_size": 0,
                "avg_file_size": 0,
                "partition_count": 0,
            }

            # 获取文件数量
            file_count = self._get_file_count(
                task.database_name, task.table_name, task.partition_filter
            )
            if file_count:
                stats["total_files"] = file_count

            # 使用WebHDFS获取更详细的统计信息
            try:
                table_location = self._get_table_location(
                    task.database_name, task.table_name
                )
                if table_location:
                    hdfs_stats = (
                        self.connection_manager.webhdfs_client.get_directory_stats(
                            table_location
                        )
                    )
                    if hdfs_stats:
                        stats.update(hdfs_stats)
            except Exception as e:
                logger.warning(f"Failed to get HDFS stats: {e}")

            return stats

        except Exception as e:
            logger.error(f"Failed to get current file stats: {e}")
            return {}

    def _estimate_merge_result(
        self, task: MergeTask, current_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """估算合并后的结果"""
        try:
            current_files = current_stats.get("total_files", 0)
            if current_files == 0:
                return {}

            estimated_result = {
                "estimated_files_after_merge": 0,
                "file_reduction_count": 0,
                "file_reduction_percentage": 0,
                "estimated_performance_improvement": 0,
            }

            # 统一合并策略的文件数量估算
            reduction_factor = 0.75  # 统一减少75%

            estimated_files = int(current_files * (1 - reduction_factor))
            estimated_result["estimated_files_after_merge"] = max(1, estimated_files)
            estimated_result["file_reduction_count"] = (
                current_files - estimated_result["estimated_files_after_merge"]
            )
            estimated_result["file_reduction_percentage"] = (
                estimated_result["file_reduction_count"] / current_files
            ) * 100

            # 性能改善估算（基于文件数量减少）
            estimated_result["estimated_performance_improvement"] = min(
                90, estimated_result["file_reduction_percentage"] * 1.2
            )

            return estimated_result

        except Exception as e:
            logger.error(f"Failed to estimate merge result: {e}")
            return {}

    def _assess_merge_risks(
        self, task: MergeTask, current_stats: Dict[str, Any]
    ) -> list:
        """评估合并风险"""
        risks = []

        try:
            # 检查文件数量风险
            total_files = current_stats.get("total_files", 0)
            if total_files > 10000:
                risks.append(
                    {
                        "level": "high",
                        "message": f"Large number of files ({total_files}). Merge operation may take significant time.",
                        "recommendation": "Consider running during low-traffic hours",
                    }
                )
            elif total_files > 1000:
                risks.append(
                    {
                        "level": "medium",
                        "message": f"Moderate number of files ({total_files}). Monitor progress carefully.",
                        "recommendation": "Ensure sufficient resources are available",
                    }
                )

            # 检查表大小风险
            total_size = current_stats.get("total_size", 0)
            if total_size > 100 * 1024 * 1024 * 1024:  # 100GB
                risks.append(
                    {
                        "level": "high",
                        "message": "Large table size detected. Merge operation may require significant resources.",
                        "recommendation": "Monitor cluster resources during merge",
                    }
                )

            # 检查分区风险
            if task.partition_filter and not task.partition_filter.strip():
                risks.append(
                    {
                        "level": "high",
                        "message": "Empty partition filter for partitioned table may affect all partitions.",
                        "recommendation": "Specify a valid partition filter to limit scope",
                    }
                )

            # 统一安全合并策略的风险评估
            risks.append(
                {
                    "level": "low",
                    "message": "Unified safe merge requires additional storage for shadow directories.",
                    "recommendation": "Ensure sufficient disk space is available",
                }
            )

        except Exception as e:
            logger.error(f"Failed to assess merge risks: {e}")

        return risks

    def _generate_recommendations(
        self, task: MergeTask, current_stats: Dict[str, Any], risks: list
    ) -> list:
        """生成合并建议"""
        recommendations = []

        try:
            total_files = current_stats.get("total_files", 0)

            # 基于文件数量的策略建议
            if total_files < 100:
                recommendations.append(
                    {
                        "type": "strategy",
                        "message": "Small number of files. CONCATENATE strategy is recommended for faster execution.",
                    }
                )
            elif total_files > 1000:
                recommendations.append(
                    {
                        "type": "strategy",
                        "message": "Large number of files. Consider using SAFE_MERGE for better reliability.",
                    }
                )

            # 基于风险的建议
            high_risks = [r for r in risks if r.get("level") == "high"]
            if high_risks:
                recommendations.append(
                    {
                        "type": "scheduling",
                        "message": "High risk detected. Schedule merge during maintenance window.",
                    }
                )

            # 通用建议
            recommendations.append(
                {
                    "type": "monitoring",
                    "message": "Monitor the merge progress and be prepared to cancel if issues arise.",
                }
            )

            if task.partition_filter:
                recommendations.append(
                    {
                        "type": "partition",
                        "message": "Verify partition filter matches intended partitions before execution.",
                    }
                )

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")

        return recommendations

    def _get_file_count(
        self,
        database_name: str,
        table_name: str,
        partition_filter: Optional[str] = None,
    ) -> Optional[int]:
        """获取文件数量"""
        try:
            # 使用HDFS API获取文件数量
            table_location = self._get_table_location(database_name, table_name)
            if not table_location:
                return None

            return self.connection_manager.webhdfs_client.get_file_count(table_location)

        except Exception as e:
            logger.error(f"Failed to get file count: {e}")
            return None

    def _get_table_location(self, database_name: str, table_name: str) -> Optional[str]:
        """获取表的HDFS位置"""
        try:
            with self.connection_manager.metastore_connector as connector:
                table_info = connector.get_table_info(database_name, table_name)
                return table_info.get("location")
        except Exception as e:
            logger.error(f"Failed to get table location: {e}")
            return None
