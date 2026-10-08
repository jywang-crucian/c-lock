"""sqlite3 读写与统计查询。ui 层一律经此层，不直接写 SQL。"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import List, Tuple

from core.config import DB_PATH

_TIME_FMT = "%Y-%m-%d %H:%M:%S"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_connect()) as conn:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    task         TEXT    NOT NULL DEFAULT '未命名',
                    kind         TEXT    NOT NULL CHECK (kind IN ('focus','short_break','long_break')),
                    started_at   TEXT    NOT NULL,
                    ended_at     TEXT    NOT NULL,
                    duration_sec INTEGER NOT NULL,
                    completed    INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at)"
            )


def add_session(record) -> int:
    """插入一条记录，返回自增 id。record 为 SegmentRecord 或等价对象。"""
    with closing(_connect()) as conn:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO sessions (task, kind, started_at, ended_at, duration_sec, completed)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (record.task, record.kind, record.started_at, record.ended_at,
                 record.duration_sec, record.completed),
            )
            return cur.lastrowid


# ---- 时间范围 ----
def _today_range() -> Tuple[str, str]:
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.strftime(_TIME_FMT), (start + timedelta(days=1)).strftime(_TIME_FMT)


def _week_range() -> Tuple[str, str]:
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.strftime(_TIME_FMT), (start + timedelta(days=7)).strftime(_TIME_FMT)


# ---- 聚合查询 ----
def _focus_total(start: str, end: str) -> int:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(duration_sec), 0) AS s FROM sessions "
            "WHERE kind='focus' AND started_at >= ? AND started_at < ?",
            (start, end),
        ).fetchone()
        return int(row["s"])


def _focus_by_task(start: str, end: str) -> List[Tuple[str, int]]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT task, SUM(duration_sec) AS s FROM sessions "
            "WHERE kind='focus' AND started_at >= ? AND started_at < ? "
            "GROUP BY task ORDER BY s DESC",
            (start, end),
        ).fetchall()
        return [(r["task"], int(r["s"])) for r in rows]


# ---- 今日 ----
def today_total() -> int:
    return _focus_total(*_today_range())


def today_by_task() -> List[Tuple[str, int]]:
    return _focus_by_task(*_today_range())


# ---- 本周 ----
def week_total() -> int:
    return _focus_total(*_week_range())


def week_by_day() -> List[int]:
    """返回周一~周日 7 天的专注秒数。"""
    s, e = _week_range()
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT date(started_at) AS d, SUM(duration_sec) AS s FROM sessions "
            "WHERE kind='focus' AND started_at >= ? AND started_at < ? "
            "GROUP BY d",
            (s, e),
        ).fetchall()

    now = datetime.now()
    monday = now.replace(hour=0, minute=0, second=0, microsecond=0) \
        - timedelta(days=now.weekday())
    day_total = {monday.date() + timedelta(days=i): 0 for i in range(7)}
    for r in rows:
        try:
            d = datetime.strptime(r["d"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if d in day_total:
            day_total[d] = int(r["s"])
    return [day_total[monday.date() + timedelta(days=i)] for i in range(7)]


def week_by_task() -> List[Tuple[str, int]]:
    return _focus_by_task(*_week_range())
