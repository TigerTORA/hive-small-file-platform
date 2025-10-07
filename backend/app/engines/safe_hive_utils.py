"""
Hive合并引擎工具函数和常量定义
包含格式关键字、压缩配置等常量
"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class HiveEngineUtils:
    """Hive引擎工具类,提供常量和通用工具方法"""

    FORMAT_KEYWORDS = {
        "PARQUET": ["parquet"],
        "ORC": ["orc"],
        "AVRO": ["avro"],
        "RCFILE": ["rcfile"],
    }

    COMPRESSION_CODECS = {
        "SNAPPY": "org.apache.hadoop.io.compress.SnappyCodec",
        "GZIP": "org.apache.hadoop.io.compress.GzipCodec",
        "LZ4": "org.apache.hadoop.io.compress.Lz4Codec",
    }

    PARQUET_COMPRESSION = {
        "SNAPPY": "SNAPPY",
        "GZIP": "GZIP",
        "LZ4": "LZ4",
        "NONE": "UNCOMPRESSED",
    }

    ORC_COMPRESSION = {
        "SNAPPY": "SNAPPY",
        "GZIP": "ZLIB",
        "LZ4": "LZ4",
        "NONE": "NONE",
    }

    @staticmethod
    def extract_error_detail(exc: Exception) -> str:
        """提取底层异常的可读信息,优先展示Hive返回的真实报错"""
        from pyhive import exc as hive_exc
        from typing import List

        try:
            logger.info(
                "extract_error_detail input: %s %s",
                type(exc).__name__,
                getattr(exc, "args", None),
            )
            messages: List[str] = []

            def _append(raw: Any):
                if raw is None:
                    return
                text = str(raw).strip()
                if not text:
                    return
                # 只过滤纯粹的"EXECUTION",保留包含具体错误信息的内容
                if text.upper() == "EXECUTION" and len(text) <= 10:
                    return
                normalized = " ".join(text.split())
                if normalized not in messages:
                    messages.append(normalized)

            def _extract_from_response(resp: Any):
                status = getattr(resp, "status", None)
                if not status:
                    return
                _append(getattr(status, "errorMessage", None))
                info_messages = getattr(status, "infoMessages", None)
                if info_messages:
                    for info in info_messages:
                        if not info:
                            continue
                        cleaned = info
                        # Hive infoMessages 形如 "*org.apache...:message",取冒号后的内容
                        if "::" in cleaned:
                            cleaned = cleaned.split("::", 1)[-1]
                        if ":" in cleaned:
                            cleaned = cleaned.split(":", 1)[-1]
                        _append(cleaned)
                diagnostics = getattr(status, "diagnosticInfo", None)
                _append(diagnostics)

            _extract_from_response(exc)

            if isinstance(exc, hive_exc.Error):
                for arg in getattr(exc, "args", ()):  # OperationalError 将详细信息放在 args[1]
                    if hasattr(arg, "status"):
                        _extract_from_response(arg)
                        continue
                    _append(arg)

            if not messages and getattr(exc, "args", None):
                for arg in exc.args:
                    if hasattr(arg, "status"):
                        _extract_from_response(arg)
                        continue
                    _append(arg)

            if messages:
                detail = " | ".join(messages)
                logger.info("Extracted Hive error detail: %s", detail)
                return detail
            logger.warning(
                "extract_error_detail fallback: %s %s (%r)",
                type(exc).__name__,
                getattr(exc, "args", None),
                exc,
            )
        except Exception:
            pass
        return str(exc)

    @staticmethod
    def get_format_classes(storage_format: str) -> tuple:
        """
        根据存储格式返回对应的InputFormat和OutputFormat类

        Args:
            storage_format: 存储格式名称(PARQUET/ORC/TEXTFILE等)

        Returns:
            (input_format_class, output_format_class)元组
        """
        storage_format_upper = storage_format.upper()

        if storage_format_upper == "PARQUET":
            return (
                "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
            )
        elif storage_format_upper == "ORC":
            return (
                "org.apache.hadoop.hive.ql.io.orc.OrcInputFormat",
                "org.apache.hadoop.hive.ql.io.orc.OrcOutputFormat",
            )
        elif storage_format_upper == "TEXTFILE":
            return (
                "org.apache.hadoop.mapred.TextInputFormat",
                "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            )
        elif storage_format_upper == "SEQUENCEFILE":
            return (
                "org.apache.hadoop.mapred.SequenceFileInputFormat",
                "org.apache.hadoop.hive.ql.io.HiveSequenceFileOutputFormat",
            )
        elif storage_format_upper == "RCFILE":
            return (
                "org.apache.hadoop.hive.ql.io.RCFileInputFormat",
                "org.apache.hadoop.hive.ql.io.RCFileOutputFormat",
            )
        elif storage_format_upper == "AVRO":
            return (
                "org.apache.hadoop.hive.ql.io.avro.AvroContainerInputFormat",
                "org.apache.hadoop.hive.ql.io.avro.AvroContainerOutputFormat",
            )
        else:
            # 默认使用TEXTFILE格式
            logger.warning(f"未识别的存储格式: {storage_format}, 使用默认TEXTFILE格式")
            return (
                "org.apache.hadoop.mapred.TextInputFormat",
                "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            )
