"""SQLite persistence for historian records, prediction execution logs, alarms, and audit events."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Iterable, List, Optional


class SqliteRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS historian_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag_id TEXT NOT NULL,
                    ts_ms INTEGER NOT NULL,
                    ts_iso TEXT NOT NULL,
                    value REAL NOT NULL,
                    quality TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_hist_tag_ts ON historian_points(tag_id, ts_ms);

                CREATE TABLE IF NOT EXISTS prediction_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    eval_time TEXT NOT NULL,
                    tag_id TEXT NOT NULL,
                    system_id TEXT NOT NULL,
                    submain_id TEXT NOT NULL,
                    measurement_type TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    base_avg_60 REAL NOT NULL,
                    m60 INTEGER NOT NULL,
                    m10 INTEGER NOT NULL,
                    n10 REAL NOT NULL,
                    slope REAL NOT NULL,
                    slope_ols REAL NOT NULL,
                    r2 REAL NOT NULL,
                    fcst10 REAL NOT NULL,
                    fcst20 REAL NOT NULL,
                    fcst30 REAL NOT NULL,
                    ttl_minutes REAL,
                    state TEXT NOT NULL,
                    detector TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    trigger_path TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_pred_tag_time ON prediction_logs(tag_id, eval_time);

                CREATE TABLE IF NOT EXISTS alarm_logs (
                    alarm_id TEXT PRIMARY KEY,
                    tag_id TEXT NOT NULL,
                    system_id TEXT NOT NULL,
                    submain_id TEXT NOT NULL,
                    alarm_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    state TEXT NOT NULL,
                    message TEXT NOT NULL,
                    value REAL NOT NULL,
                    limit_val REAL NOT NULL,
                    unit TEXT NOT NULL,
                    activated_at TEXT NOT NULL,
                    acknowledged_at TEXT,
                    cleared_at TEXT,
                    acknowledged_by TEXT,
                    source TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    detail TEXT
                );
                """
            )

    def insert_historian_batch(self, rows: Iterable[tuple]) -> None:
        data = list(rows)
        if not data:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                "INSERT INTO historian_points (tag_id, ts_ms, ts_iso, value, quality) VALUES (?, ?, ?, ?, ?)",
                data,
            )

    def insert_prediction_batch(self, rows: Iterable[tuple]) -> None:
        data = list(rows)
        if not data:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO prediction_logs (
                    eval_time, tag_id, system_id, submain_id, measurement_type, scenario,
                    current_value, base_avg_60, m60, m10, n10, slope, slope_ols, r2,
                    fcst10, fcst20, fcst30, ttl_minutes, state, detector, risk_score, trigger_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data,
            )

    def upsert_alarms(self, rows: Iterable[tuple]) -> None:
        data = list(rows)
        if not data:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO alarm_logs (
                    alarm_id, tag_id, system_id, submain_id, alarm_type, priority, state,
                    message, value, limit_val, unit, activated_at, acknowledged_at, cleared_at,
                    acknowledged_by, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(alarm_id) DO UPDATE SET
                    state=excluded.state,
                    value=excluded.value,
                    limit_val=excluded.limit_val,
                    message=excluded.message,
                    priority=excluded.priority,
                    acknowledged_at=excluded.acknowledged_at,
                    cleared_at=excluded.cleared_at,
                    acknowledged_by=excluded.acknowledged_by
                """,
                data,
            )

    def append_audit(self, ts: str, actor: str, action: str, target: str, detail: Optional[str] = None) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (ts, actor, action, target, detail) VALUES (?, ?, ?, ?, ?)",
                (ts, actor, action, target, detail),
            )

    def query_prediction_logs(
        self,
        tag_id: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 500,
    ) -> List[dict]:
        clauses = []
        params: list = []
        if tag_id:
            clauses.append("tag_id = ?")
            params.append(tag_id)
        if state:
            clauses.append("state = ?")
            params.append(state)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM prediction_logs {where} ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._lock, self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def count_prediction_logs(self) -> dict:
        with self._lock, self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM prediction_logs").fetchone()[0]
            unique_tags = conn.execute("SELECT COUNT(DISTINCT tag_id) FROM prediction_logs").fetchone()[0]
            non_normal = conn.execute(
                "SELECT COUNT(*) FROM prediction_logs WHERE state IN ('T-30','T-20','T-10','EVENT')"
            ).fetchone()[0]
            return {"totalRows": total, "uniqueTags": unique_tags, "nonNormalRows": non_normal}

    def clear_runtime_tables(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                DELETE FROM historian_points;
                DELETE FROM prediction_logs;
                DELETE FROM alarm_logs;
                """
            )

