import pytest
from app.engines.engine_factory import MergeEngineFactory
from app.models.cluster import Cluster


def make_cluster() -> Cluster:
    return Cluster(
        id=1,
        name="test-cluster",
        hive_metastore_url="mysql://test:test@localhost:3306/hive",
        hdfs_namenode_url="hdfs://localhost:9000",
        hive_host="localhost",
        hive_port=10000,
    )


def test_unknown_format_defaults_to_safe_merge():
    c = make_cluster()
    strategy = MergeEngineFactory.recommend_strategy(
        cluster=c,
        table_format="unknownfmt",
        file_count=10,
        table_size=10 * 1024 * 1024,
        partition_count=0,
        is_production=True,
    )
    assert strategy == "safe_merge"


def test_validate_strategy_compatibility_concatenate_on_parquet_warns():
    result = MergeEngineFactory.validate_strategy_compatibility(
        merge_strategy="concatenate", table_format="parquet"
    )
    assert result["compatible"] is True
    assert result["valid"] is True
    assert any("CONCATENATE" in w for w in result["warnings"])


def test_get_strategy_reason_texts_small_medium_large():
    # 小表 insert_overwrite 文案包含“小表”
    reason_small = MergeEngineFactory._get_strategy_reason(
        "insert_overwrite", file_count=10, table_format="parquet", table_size=10 * 1024 * 1024
    )
    assert "小表" in reason_small

    # 大量文件/大表 safe_merge 文案包含“大表/大量文件”
    reason_large = MergeEngineFactory._get_strategy_reason(
        "safe_merge", file_count=5000, table_format="orc", table_size=5 * 1024 * 1024 * 1024
    )
    assert ("大量文件" in reason_large) or ("大表" in reason_large)

