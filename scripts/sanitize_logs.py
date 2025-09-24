#!/usr/bin/env python3
"""
Sanitize existing persisted log messages by removing emoji/icon characters.

Targets tables:
 - scan_task_logs.message
 - task_logs.message

Usage:
  python3 scripts/sanitize_logs.py           # dry-run, show counts only
  python3 scripts/sanitize_logs.py --apply   # apply updates

It uses backend/app configuration (DATABASE_URL) with the same SQLite
path normalization as the application.
"""
from __future__ import annotations

import sys
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.config.database import engine  # type: ignore  # pylint: disable=import-error


_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]")
_COMBINERS_RE = re.compile(r"[\u200D\uFE0F\u20E3]")


def sanitize(text: str) -> str:
    try:
        if not isinstance(text, str):
            text = str(text)
        s = _EMOJI_RE.sub("", text)
        s = _COMBINERS_RE.sub("", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s
    except Exception:
        return text


def run(apply: bool = False) -> None:
    from sqlalchemy import text  # lazy import

    total_scans = 0
    total_tasks = 0
    updated_scans = 0
    updated_tasks = 0

    with engine.begin() as conn:
        # scan_task_logs
        rows = conn.execute(text("SELECT id, message FROM scan_task_logs")).fetchall()
        total_scans = len(rows)
        for rid, msg in rows:
            new_msg = sanitize(msg)
            if new_msg != msg:
                updated_scans += 1
                if apply:
                    conn.execute(text("UPDATE scan_task_logs SET message = :m WHERE id = :id"), {"m": new_msg, "id": rid})

        # task_logs
        rows = conn.execute(text("SELECT id, message FROM task_logs")).fetchall()
        total_tasks = len(rows)
        for rid, msg in rows:
            new_msg = sanitize(msg)
            if new_msg != msg:
                updated_tasks += 1
                if apply:
                    conn.execute(text("UPDATE task_logs SET message = :m WHERE id = :id"), {"m": new_msg, "id": rid})

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"[sanitize_logs] mode={mode}")
    print(f" scan_task_logs: total={total_scans}, to_update={updated_scans}")
    print(f" task_logs    : total={total_tasks}, to_update={updated_tasks}")
    if not apply:
        print("Run with --apply to commit changes.")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    run(apply)

