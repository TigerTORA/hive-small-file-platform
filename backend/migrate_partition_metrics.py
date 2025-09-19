#!/usr/bin/env python3
"""
数据库迁移脚本：为partition_metrics表添加冷数据归档相关字段
"""
import sqlite3
import sys
from pathlib import Path

def migrate_partition_metrics():
    """为partition_metrics表添加新的归档相关字段"""

    # 获取数据库文件路径
    backend_dir = Path(__file__).parent
    db_path = backend_dir / "var/data/hive_small_file_db.db"

    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='partition_metrics'")
        if not cursor.fetchone():
            print("partition_metrics表不存在")
            return False

        # 获取当前表结构
        cursor.execute("PRAGMA table_info(partition_metrics)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"当前字段: {columns}")

        # 要添加的新字段列表
        new_columns = [
            ("scan_time", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
            ("last_access_time", "DATETIME"),
            ("days_since_last_access", "INTEGER"),
            ("is_cold_data", "INTEGER DEFAULT 0"),
            ("archive_status", "VARCHAR(50) DEFAULT 'active'"),
            ("archive_location", "VARCHAR(1000)"),
            ("archived_at", "DATETIME")
        ]

        # 添加缺失的字段
        added_columns = []
        for col_name, col_def in new_columns:
            if col_name not in columns:
                try:
                    sql = f"ALTER TABLE partition_metrics ADD COLUMN {col_name} {col_def}"
                    print(f"执行: {sql}")
                    cursor.execute(sql)
                    added_columns.append(col_name)
                except sqlite3.Error as e:
                    print(f"添加字段 {col_name} 失败: {e}")
                    continue

        if added_columns:
            # 创建索引
            index_sqls = [
                "CREATE INDEX IF NOT EXISTS ix_partition_metrics_scan_time ON partition_metrics (scan_time)",
                "CREATE INDEX IF NOT EXISTS ix_partition_metrics_last_access_time ON partition_metrics (last_access_time)",
                "CREATE INDEX IF NOT EXISTS ix_partition_metrics_archive_status ON partition_metrics (archive_status)",
                "CREATE INDEX IF NOT EXISTS ix_partition_metrics_archived_at ON partition_metrics (archived_at)"
            ]

            for sql in index_sqls:
                try:
                    print(f"执行: {sql}")
                    cursor.execute(sql)
                except sqlite3.Error as e:
                    print(f"创建索引失败: {e}")

        # 提交更改
        conn.commit()

        # 验证更新后的表结构
        cursor.execute("PRAGMA table_info(partition_metrics)")
        new_columns_list = [row[1] for row in cursor.fetchall()]
        print(f"更新后字段: {new_columns_list}")

        if added_columns:
            print(f"成功添加字段: {added_columns}")
        else:
            print("所有字段都已存在，无需添加")

        return True

    except sqlite3.Error as e:
        print(f"数据库操作失败: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("开始迁移partition_metrics表...")
    success = migrate_partition_metrics()
    if success:
        print("迁移完成")
        sys.exit(0)
    else:
        print("迁移失败")
        sys.exit(1)