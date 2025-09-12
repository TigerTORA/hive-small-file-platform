"""
Lightweight compatibility shim for HybridTableScanner.

Some API modules import `HybridTableScanner` for connection tests and scanning.
In the refactor, this module may be absent or renamed. This shim preserves
the expected interface used by the API and tests without requiring real
cluster connectivity. It returns safe mock-style results and exposes the
attributes/methods that API code references.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class _DummyConnector:
    def __init__(self) -> None:
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False


class HybridTableScanner:
    """Compatibility scanner that returns mock results with required shape."""

    def __init__(self, cluster: Any) -> None:
        self.cluster = cluster
        # Attributes referenced by APIs
        self.hive_connector = _DummyConnector()
        self.hdfs_scanner = _DummyConnector()

    # API code may call this before using hdfs_scanner
    def _initialize_hdfs_scanner(self) -> None:
        self.hdfs_scanner = _DummyConnector()

    def test_connections(self) -> Dict[str, Any]:
        return {
            "overall_status": "success",
            "test_time": None,
            "tests": {
                "metastore": {"status": "success", "mode": "mock", "message": "OK"},
                "hdfs": {"status": "success", "mode": "mock", "message": "OK"},
            },
            "logs": [{"level": "INFO", "message": "Mock connection test"}],
            "suggestions": [],
        }

    def scan_database_tables(
        self,
        db: Any,
        database_name: str,
        table_filter: Optional[str] = None,
        max_tables: int = 10,
    ) -> Dict[str, Any]:
        """Return an empty but well-formed scan result for a database."""
        return {
            "database": database_name,
            "tables_scanned": 0,
            "total_files": 0,
            "total_small_files": 0,
            "scan_duration": 0.0,
            "hdfs_mode": "mock",
            "errors": [],
        }

    def scan_table(self, db: Any, database_name: str, table_info: Dict[str, Any]) -> Dict[str, Any]:
        """Return an empty but well-formed scan result for a single table."""
        return {
            "table_name": table_info.get("table_name") if isinstance(table_info, dict) else None,
            "total_files": 0,
            "small_files": 0,
            "small_file_ratio": 0.0,
            "avg_file_size": 0,
            "total_size": 0,
            "is_partitioned": False,
            "partition_count": 0,
            "scan_mode": "mock",
            "scan_time": None,
            "scan_duration": 0.0,
        }

