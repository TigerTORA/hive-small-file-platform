"""
后端性能基准测试
建立后端API和引擎的性能基准线，用于持续监控性能变化
"""

import asyncio
import gc
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mock the problematic imports before importing the actual modules
with patch.dict(
    "sys.modules",
    {
        "pyhive": MagicMock(),
        "pyhive.hive": MagicMock(),
        "app.monitor.hdfs_scanner": MagicMock(),
        "app.monitor.hive_connector": MagicMock(),
        "app.engines.base_engine": MagicMock(),
        "app.engines.safe_hive_engine": MagicMock(),
    },
):
    from app.engines.engine_factory import MergeEngineFactory
    from app.models.cluster import Cluster
    from app.models.merge_task import MergeTask


class TestPerformanceBaseline:
    """后端性能基准测试套件"""

    def setup_method(self):
        """测试前准备"""
        self.cluster = Cluster(
            id=1,
            name="test-cluster",
            hive_metastore_url="mysql://test:test@localhost:3306/hive",
            hdfs_namenode_url="hdfs://localhost:9000",
            hive_host="localhost",
            hive_port=10000,
        )

        # 性能基准指标（毫秒）
        self.performance_baselines = {
            "engine_factory_init": 5.0,
            "strategy_recommendation": 2.0,
            "task_validation": 10.0,
            "smart_task_creation": 15.0,
            "batch_processing": 100.0,
            "concurrent_operations": 50.0,
        }

    def test_engine_factory_initialization_performance(self):
        """测试引擎工厂初始化性能"""
        start_time = time.perf_counter()

        # 执行100次初始化
        for _ in range(100):
            engine = MergeEngineFactory.get_engine(self.cluster)
            assert engine is not None

        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / 100) * 1000

        # 单次初始化应在基准时间内完成
        assert (
            avg_time_ms < self.performance_baselines["engine_factory_init"]
        ), f"引擎初始化平均时间 {avg_time_ms:.2f}ms 超过基准 {self.performance_baselines['engine_factory_init']}ms"

    def test_strategy_recommendation_performance(self):
        """测试策略推荐性能"""
        test_cases = [
            # (table_format, file_count, partition_count, table_size, is_production)
            ("parquet", 50, 0, 100 * 1024 * 1024, True),
            ("orc", 5000, 100, 50 * 1024 * 1024 * 1024, True),
            ("textfile", 200, 10, 1024 * 1024 * 1024, True),
            ("parquet", 1000, 5, 10 * 1024 * 1024 * 1024, False),
        ]

        start_time = time.perf_counter()

        # 执行1000次策略推荐
        for _ in range(250):
            for (
                table_format,
                file_count,
                partition_count,
                table_size,
                is_production,
            ) in test_cases:
                strategy = MergeEngineFactory.recommend_strategy(
                    cluster=self.cluster,
                    table_format=table_format,
                    file_count=file_count,
                    partition_count=partition_count,
                    table_size=table_size,
                    is_production=is_production,
                )
                assert strategy in ["concatenate", "insert_overwrite", "safe_merge"]

        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / 1000) * 1000

        assert (
            avg_time_ms < self.performance_baselines["strategy_recommendation"]
        ), f"策略推荐平均时间 {avg_time_ms:.3f}ms 超过基准 {self.performance_baselines['strategy_recommendation']}ms"

    def test_task_validation_performance(self):
        """测试任务验证性能"""
        strategies = ["concatenate", "insert_overwrite", "safe_merge"]
        table_formats = ["TEXTFILE", "PARQUET", "ORC", "SEQUENCEFILE"]

        start_time = time.perf_counter()

        # 执行大量验证操作
        validation_count = 0
        for _ in range(100):
            for strategy in strategies:
                for table_format in table_formats:
                    result = MergeEngineFactory.validate_strategy_compatibility(
                        merge_strategy=strategy, table_format=table_format
                    )
                    assert "compatible" in result
                    assert "warnings" in result
                    assert "recommendations" in result
                    validation_count += 1

        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / validation_count) * 1000

        assert (
            avg_time_ms < self.performance_baselines["task_validation"]
        ), f"任务验证平均时间 {avg_time_ms:.3f}ms 超过基准 {self.performance_baselines['task_validation']}ms"

    def test_smart_task_creation_performance(self):
        """测试智能任务创建性能"""
        test_scenarios = [
            {
                "database_name": "prod_db",
                "table_name": "user_events",
                "table_format": "parquet",
                "file_count": 150,
                "table_size": 500 * 1024 * 1024,
                "partition_count": 5,
            },
            {
                "database_name": "analytics_db",
                "table_name": "daily_reports",
                "table_format": "orc",
                "file_count": 3000,
                "table_size": 30 * 1024 * 1024 * 1024,
                "partition_count": 50,
            },
            {
                "database_name": "temp_db",
                "table_name": "staging_data",
                "table_format": "textfile",
                "file_count": 50,
                "table_size": 100 * 1024 * 1024,
                "partition_count": 0,
            },
        ]

        start_time = time.perf_counter()

        # 执行多次智能任务创建
        for _ in range(100):
            for scenario in test_scenarios:
                task_config = MergeEngineFactory.create_smart_merge_task(
                    cluster=self.cluster, **scenario
                )

                assert "recommended_strategy" in task_config
                assert "validation" in task_config
                assert "task_name" in task_config
                assert "strategy_reason" in task_config
                assert task_config["validation"]["valid"] is True

        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / (100 * len(test_scenarios))) * 1000

        assert (
            avg_time_ms < self.performance_baselines["smart_task_creation"]
        ), f"智能任务创建平均时间 {avg_time_ms:.2f}ms 超过基准 {self.performance_baselines['smart_task_creation']}ms"

    def test_batch_processing_performance(self):
        """测试批量处理性能"""
        # 生成大量任务数据
        tasks_data = []
        for i in range(1000):
            tasks_data.append(
                {
                    "database_name": f"db_{i % 10}",
                    "table_name": f"table_{i}",
                    "table_format": ["parquet", "orc", "textfile"][i % 3],
                    "file_count": (i % 500) + 100,
                    "table_size": (i % 1000) * 1024 * 1024,
                    "partition_count": i % 20,
                }
            )

        start_time = time.perf_counter()

        # 批量处理
        results = []
        for task_data in tasks_data:
            result = MergeEngineFactory.create_smart_merge_task(
                cluster=self.cluster, **task_data
            )
            results.append(result)

        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_ms = total_time_ms / len(tasks_data)

        assert (
            total_time_ms < self.performance_baselines["batch_processing"]
        ), f"批量处理总时间 {total_time_ms:.2f}ms 超过基准 {self.performance_baselines['batch_processing']}ms"

        assert len(results) == 1000
        assert all("recommended_strategy" in result for result in results)

    def test_concurrent_operations_performance(self):
        """测试并发操作性能"""

        def create_task_batch(batch_id, batch_size=50):
            """创建一批任务"""
            results = []
            for i in range(batch_size):
                task_config = MergeEngineFactory.create_smart_merge_task(
                    cluster=self.cluster,
                    database_name=f"concurrent_db_{batch_id}",
                    table_name=f"table_{i}",
                    table_format="parquet",
                    file_count=100 + i,
                    table_size=1024 * 1024 * (100 + i),
                    partition_count=i % 10,
                )
                results.append(task_config)
            return results

        start_time = time.perf_counter()

        # 使用线程池执行并发操作
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_task_batch, i) for i in range(10)]

            all_results = []
            for future in as_completed(futures):
                batch_results = future.result()
                all_results.extend(batch_results)

        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000

        assert (
            total_time_ms < self.performance_baselines["concurrent_operations"]
        ), f"并发操作总时间 {total_time_ms:.2f}ms 超过基准 {self.performance_baselines['concurrent_operations']}ms"

        assert len(all_results) == 500  # 10 batches * 50 tasks each
        assert all("recommended_strategy" in result for result in all_results)

    def test_memory_usage_baseline(self):
        """测试内存使用基准"""
        tracemalloc.start()

        # 执行大量操作
        results = []
        for i in range(500):
            # 创建多个引擎实例
            engine = MergeEngineFactory.get_engine(self.cluster)

            # 执行策略推荐
            strategy = MergeEngineFactory.recommend_strategy(
                cluster=self.cluster,
                table_format="parquet",
                file_count=100 + i,
                table_size=1024 * 1024 * i,
                partition_count=i % 20,
                is_production=True,
            )

            # 创建智能任务
            task_config = MergeEngineFactory.create_smart_merge_task(
                cluster=self.cluster,
                database_name=f"memory_test_db",
                table_name=f"table_{i}",
                table_format="parquet",
                file_count=100 + i,
                table_size=1024 * 1024 * i,
                partition_count=i % 20,
            )

            results.append((engine, strategy, task_config))

            # 定期清理
            if i % 100 == 0:
                gc.collect()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 内存使用应在合理范围内（小于50MB）
        assert (
            peak < 50 * 1024 * 1024
        ), f"峰值内存使用 {peak / 1024 / 1024:.2f}MB 超过50MB基准"
        assert len(results) == 500

    def test_error_handling_performance(self):
        """测试错误处理性能"""
        start_time = time.perf_counter()

        # 测试各种错误场景的处理速度
        error_scenarios = [
            {"merge_strategy": "invalid_strategy", "table_format": "parquet"},
            {"merge_strategy": "concatenate", "table_format": None},
            {"merge_strategy": "", "table_format": "orc"},
            {"merge_strategy": "safe_merge", "table_format": "unknown_format"},
        ]

        results = []
        for _ in range(250):  # 1000 total tests
            for scenario in error_scenarios:
                result = MergeEngineFactory.validate_strategy_compatibility(**scenario)
                results.append(result)

        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / len(results)) * 1000

        # 错误处理应该很快
        assert avg_time_ms < 0.5, f"错误处理平均时间 {avg_time_ms:.3f}ms 过慢"
        assert len(results) == 1000

    def test_cpu_intensive_operations(self):
        """测试CPU密集型操作性能"""
        start_time = time.perf_counter()

        # 执行大量计算密集型操作
        for i in range(1000):
            # 多重嵌套的策略推荐
            for format_type in ["parquet", "orc", "textfile"]:
                for file_count in [100, 500, 1000, 5000]:
                    for is_prod in [True, False]:
                        strategy = MergeEngineFactory.recommend_strategy(
                            cluster=self.cluster,
                            table_format=format_type,
                            file_count=file_count,
                            table_size=file_count * 1024 * 1024,
                            partition_count=file_count // 100,
                            is_production=is_prod,
                        )
                        assert strategy in [
                            "concatenate",
                            "insert_overwrite",
                            "safe_merge",
                        ]

        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000

        # CPU密集型操作应在合理时间内完成（2秒内）
        assert (
            total_time_ms < 2000
        ), f"CPU密集型操作时间 {total_time_ms:.2f}ms 超过2秒基准"

    def test_performance_regression_detection(self):
        """测试性能回归检测"""
        # 执行标准性能测试套件
        performance_results = {}

        # 测试1: 引擎初始化
        start = time.perf_counter()
        for _ in range(50):
            MergeEngineFactory.get_engine(self.cluster)
        performance_results["engine_init"] = ((time.perf_counter() - start) / 50) * 1000

        # 测试2: 策略推荐
        start = time.perf_counter()
        for _ in range(100):
            MergeEngineFactory.recommend_strategy(
                cluster=self.cluster,
                table_format="parquet",
                file_count=1000,
                table_size=1024 * 1024 * 1024,
                partition_count=10,
                is_production=True,
            )
        performance_results["strategy_recommend"] = (
            (time.perf_counter() - start) / 100
        ) * 1000

        # 测试3: 任务创建
        start = time.perf_counter()
        for i in range(50):
            MergeEngineFactory.create_smart_merge_task(
                cluster=self.cluster,
                database_name=f"test_db",
                table_name=f"table_{i}",
                table_format="parquet",
                file_count=100 + i,
                table_size=1024 * 1024 * (100 + i),
                partition_count=i % 10,
            )
        performance_results["task_creation"] = (
            (time.perf_counter() - start) / 50
        ) * 1000

        # 检查性能指标是否在预期范围内
        for metric, value in performance_results.items():
            if metric in self.performance_baselines:
                baseline = self.performance_baselines.get(metric, float("inf"))
                assert (
                    value < baseline
                ), f"性能回归检测: {metric} 当前值 {value:.3f}ms 超过基准 {baseline}ms"

        # 输出性能报告
        print("\n=== 性能基准报告 ===")
        for metric, value in performance_results.items():
            baseline = self.performance_baselines.get(metric, 0)
            status = "✓" if value < baseline else "✗"
            print(f"{status} {metric}: {value:.3f}ms (基准: {baseline}ms)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
