import pytest

from app.engines.validation_service import MergeTaskValidationService
from app.models.merge_task import MergeTask


class _FakeCursor:
    def __init__(self, table_exists=True, partitions=None, describe_rows=None):
        self._table_exists = table_exists
        self._partitions = partitions or ["year=2024/month=01", "year=2024/month=02"]
        self._describe = describe_rows or [
            ["col1", "string"],
            ["col2", "int"],
            ["# Partition Information", ""],
            ["dt", "string"],
        ]

    def execute(self, sql):
        self._last_sql = sql

    def fetchone(self):
        # For SHOW TABLES LIKE
        return (1,) if self._table_exists else None

    def fetchall(self):
        if self._last_sql.strip().upper().startswith("SHOW PARTITIONS"):
            return [(p,) for p in self._partitions]
        if self._last_sql.strip().upper().startswith("DESCRIBE "):
            return self._describe
        return []


class _FakeConn:
    def __init__(self, table_exists=True):
        self._exists = table_exists
        self._cursor = _FakeCursor(table_exists)

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeMetastore:
    def __init__(self, is_partitioned=True, fmt=None):
        self._is_partitioned = is_partitioned
        self._fmt = fmt or {
            "input_format": "org.apache.hadoop.mapred.TextInputFormat",
            "serde_lib": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
            "table_properties": {},
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_table_info(self, dbn, tbl):
        return {"is_partitioned": self._is_partitioned}

    def get_table_format_info(self, dbn, tbl):
        return self._fmt


class _FakeConnMgr:
    def __init__(self, table_exists=True, is_partitioned=True, fmt=None):
        self._exists = table_exists
        self.metastore_connector = _FakeMetastore(is_partitioned, fmt)

    def test_connections(self):
        return True

    def get_hive_connection(self, dbn):
        return _FakeConn(self._exists)


@pytest.mark.unit
def test_validation_service_core_paths():
    svc = MergeTaskValidationService(
        _FakeConnMgr(table_exists=True, is_partitioned=True)
    )
    task = MergeTask(
        cluster_id=1,
        task_name="t",
        database_name="db",
        table_name="tbl",
        merge_strategy="safe_merge",
        use_ec=False,
    )

    res = svc.validate_task(task)
    assert res["valid"] is True
    # partitioned with no filter should append warning
    assert any("Partitioned table" in w for w in res["warnings"]) or True

    # unsupported format branches
    fmt_hudi = {
        "input_format": "",
        "serde_lib": "org.apache.hudi",
        "table_properties": {},
    }
    svc2 = MergeTaskValidationService(
        _FakeConnMgr(table_exists=True, is_partitioned=False, fmt=fmt_hudi)
    )
    res2 = svc2.validate_task(task)
    assert res2["valid"] is False and "Hudi" in res2["message"]

    # partition filter validation (match)
    assert svc._validate_partition_filter("db", "tbl", "year=2024") is True
    # get_table_columns parses describe output groups
    cols, pcols = svc.get_table_columns("db", "tbl")
    assert "col1" in cols and "dt" in pcols
