"""SQLite storage layer for TokenWatch usage records."""

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

from .models import UsageRecord

DEFAULT_DB_PATH = Path.home() / ".tokenwatch" / "usage.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    caller TEXT DEFAULT '',
    tags JSON DEFAULT '{}',
    prompt_hash TEXT DEFAULT ''
);
"""

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_model ON events(model);
CREATE INDEX IF NOT EXISTS idx_cost ON events(cost_usd);
CREATE INDEX IF NOT EXISTS idx_provider ON events(provider);
"""


class Storage:
    """SQLite-based storage for usage records."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(CREATE_TABLE_SQL + CREATE_INDEXES_SQL)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def record(self, usage: UsageRecord) -> None:
        """Insert a usage record into the database."""
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO events (id, timestamp, provider, model, input_tokens, output_tokens,
               total_tokens, cost_usd, caller, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                usage.id,
                usage.timestamp.isoformat(),
                usage.provider,
                usage.model,
                usage.input_tokens,
                usage.output_tokens,
                usage.total_tokens,
                usage.cost_usd,
                usage.caller,
                json.dumps(usage.tags),
            ),
        )
        conn.commit()

    def query_period(
        self,
        period_start: datetime,
        period_end: Optional[datetime] = None,
    ) -> list[UsageRecord]:
        """Query records within a time period."""
        if period_end is None:
            period_end = datetime.now(UTC)
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM events WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp DESC",
            (period_start.isoformat(), period_end.isoformat()),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_summary_by_model(
        self, period_start: datetime, period_end: Optional[datetime] = None
    ) -> list[dict]:
        """Get cost summary grouped by model."""
        if period_end is None:
            period_end = datetime.now(UTC)
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT model, SUM(cost_usd) as total_cost, COUNT(*) as request_count,
               SUM(input_tokens) as total_input, SUM(output_tokens) as total_output
               FROM events WHERE timestamp >= ? AND timestamp <= ?
               GROUP BY model ORDER BY total_cost DESC""",
            (period_start.isoformat(), period_end.isoformat()),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_summary_by_caller(
        self, period_start: datetime, period_end: Optional[datetime] = None
    ) -> list[dict]:
        """Get cost summary grouped by caller."""
        if period_end is None:
            period_end = datetime.now(UTC)
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT caller, SUM(cost_usd) as total_cost, COUNT(*) as request_count,
               SUM(input_tokens) as total_input, SUM(output_tokens) as total_output
               FROM events WHERE timestamp >= ? AND timestamp <= ?
               GROUP BY caller ORDER BY total_cost DESC""",
            (period_start.isoformat(), period_end.isoformat()),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_total_cost(
        self, period_start: datetime, period_end: Optional[datetime] = None
    ) -> float:
        """Get total cost for a period."""
        if period_end is None:
            period_end = datetime.now(UTC)
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) FROM events WHERE timestamp >= ? AND timestamp <= ?",
            (period_start.isoformat(), period_end.isoformat()),
        )
        return cursor.fetchone()[0]

    def get_daily_costs(
        self, period_start: datetime, period_end: Optional[datetime] = None
    ) -> list[dict]:
        """Get daily cost totals for a period."""
        if period_end is None:
            period_end = datetime.now(UTC)
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT DATE(timestamp) as day, SUM(cost_usd) as total_cost
               FROM events WHERE timestamp >= ? AND timestamp <= ?
               GROUP BY DATE(timestamp) ORDER BY day""",
            (period_start.isoformat(), period_end.isoformat()),
        )
        return [dict(row) for row in cursor.fetchall()]

    def _row_to_record(self, row: sqlite3.Row) -> UsageRecord:
        """Convert a database row to a UsageRecord."""
        return UsageRecord(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            provider=row["provider"],
            model=row["model"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            total_tokens=row["total_tokens"],
            cost_usd=row["cost_usd"],
            caller=row["caller"],
            tags=json.loads(row["tags"]) if row["tags"] else {},
        )

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
