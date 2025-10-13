"""
测试表生成相关的Pydantic模式
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator


class TestTableScenario(str, Enum):
    """测试场景枚举"""

    LIGHT = "light"  # 轻量: 5分区, 20文件/分区, 100文件
    DEFAULT = "default"  # 默认: 10分区, 100文件/分区, 1000文件
    HEAVY = "heavy"  # 重度: 20分区, 100文件/分区, 2000文件
    EXTREME = "extreme"  # 超大: 100分区, 100文件/分区, 10000文件
    CUSTOM = "custom"  # 自定义配置


class TestTableConfig(BaseModel):
    """测试表配置 - 统一使用Beeline模式生成数据"""

    table_name: str = Field(default="test_small_files_table", description="表名")
    database_name: str = Field(default="test_db", description="数据库名")
    hdfs_base_path: str = Field(
        default="/user/test/small_files_test",
        description="HDFS基础路径(仅供参考,实际由Hive管理)",
    )
    partition_count: int = Field(default=10, ge=1, le=1000, description="分区数量")
    files_per_partition: int = Field(
        default=100, ge=1, le=1000, description="每分区文件数"
    )
    file_size_kb: int = Field(default=50, ge=1, le=1024, description="单文件大小(KB)")
    scenario: TestTableScenario = Field(
        default=TestTableScenario.DEFAULT, description="测试场景"
    )

    @validator("partition_count", "files_per_partition")
    def validate_file_counts(cls, v, values):
        """验证文件数量不会过大"""
        partition_count = values.get(
            "partition_count", v if "partition_count" in values else 10
        )
        files_per_partition = values.get(
            "files_per_partition", v if "files_per_partition" in values else 100
        )

        total_files = partition_count * files_per_partition
        if total_files > 50000:
            raise ValueError(
                f"总文件数 {total_files} 超过限制 (50000)，请减少分区数或每分区文件数"
            )

        return v

    @validator("hdfs_base_path")
    def validate_hdfs_path(cls, v):
        """验证HDFS路径格式"""
        if not v.startswith("/"):
            raise ValueError("HDFS路径必须以 '/' 开头")
        if "/tmp/" in v:
            raise ValueError("不建议使用 /tmp/ 目录")
        return v

    def get_total_files(self) -> int:
        """获取总文件数"""
        return self.partition_count * self.files_per_partition

    def get_estimated_size_mb(self) -> float:
        """获取预估总大小(MB)"""
        return (self.get_total_files() * self.file_size_kb) / 1024

    def get_estimated_duration_minutes(self) -> int:
        """获取预估执行时间(分钟)"""
        total_files = self.get_total_files()
        if total_files <= 100:
            return 2
        elif total_files <= 500:
            return 5
        elif total_files <= 1000:
            return 10
        elif total_files <= 2000:
            return 20
        else:
            return max(30, total_files // 100)


class TestTableCreateRequest(BaseModel):
    """创建测试表请求"""

    cluster_id: int = Field(description="集群ID")
    config: TestTableConfig = Field(description="测试表配置")
    force_recreate: bool = Field(
        default=False, description="是否强制重新创建（删除已存在的表）"
    )


class TestTableTask(BaseModel):
    """测试表创建任务"""

    id: str = Field(description="任务ID")
    cluster_id: int = Field(description="集群ID")
    config: TestTableConfig = Field(description="配置信息")
    status: str = Field(
        description="任务状态", examples=["pending", "running", "success", "failed"]
    )
    progress_percentage: float = Field(default=0.0, description="进度百分比")
    current_phase: Optional[str] = Field(default=None, description="当前阶段")
    current_operation: Optional[str] = Field(default=None, description="当前操作")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    created_time: datetime = Field(description="创建时间")
    started_time: Optional[datetime] = Field(default=None, description="开始时间")
    completed_time: Optional[datetime] = Field(default=None, description="完成时间")

    # 执行结果
    hdfs_files_created: Optional[int] = Field(
        default=None, description="创建的HDFS文件数"
    )
    hive_partitions_added: Optional[int] = Field(
        default=None, description="添加的Hive分区数"
    )
    total_size_mb: Optional[float] = Field(default=None, description="总大小(MB)")


class TestTableTaskResponse(TestTableTask):
    """测试表任务响应"""

    class Config:
        from_attributes = True


class TestTableDeleteRequest(BaseModel):
    """删除测试表请求"""

    cluster_id: int = Field(description="集群ID")
    database_name: str = Field(description="数据库名")
    table_name: str = Field(description="表名")
    delete_hdfs_data: bool = Field(default=True, description="是否删除HDFS数据")


class TestTableVerifyRequest(BaseModel):
    """验证测试表请求"""

    cluster_id: int = Field(description="集群ID")
    database_name: str = Field(description="数据库名")
    table_name: str = Field(description="表名")


class TestTableVerifyResult(BaseModel):
    """验证结果"""

    table_exists: bool = Field(description="表是否存在")
    partitions_count: int = Field(description="分区数量")
    hdfs_files_count: int = Field(description="HDFS文件数量")
    total_size_mb: float = Field(description="总大小(MB)")
    data_rows_count: Optional[int] = Field(default=None, description="数据行数")
    verification_passed: bool = Field(description="验证是否通过")
    issues: list[str] = Field(default_factory=list, description="发现的问题")


# 预设场景配置
SCENARIO_CONFIGS = {
    TestTableScenario.LIGHT: TestTableConfig(
        partition_count=5,
        files_per_partition=20,
        file_size_kb=30,
        scenario=TestTableScenario.LIGHT,
    ),
    TestTableScenario.DEFAULT: TestTableConfig(
        partition_count=10,
        files_per_partition=100,
        file_size_kb=50,
        scenario=TestTableScenario.DEFAULT,
    ),
    TestTableScenario.HEAVY: TestTableConfig(
        partition_count=20,
        files_per_partition=100,
        file_size_kb=60,
        scenario=TestTableScenario.HEAVY,
    ),
    TestTableScenario.EXTREME: TestTableConfig(
        partition_count=100,
        files_per_partition=100,
        file_size_kb=64,
        scenario=TestTableScenario.EXTREME,
    ),
}
