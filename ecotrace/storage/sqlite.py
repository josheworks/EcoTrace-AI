"""SQLite storage backend."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ecotrace.exceptions import StorageError
from ecotrace.storage.base import BaseStorage
from ecotrace.storage.models import RequestEvent

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS request_events (
    request_id   TEXT PRIMARY KEY,
    session_id   TEXT,
    timestamp    TEXT NOT NULL,
    provider     TEXT NOT NULL,
    model        TEXT NOT NULL,
    prompt       TEXT NOT NULL,
    response     TEXT,
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens  INTEGER DEFAULT 0,
    latency_ms   REAL DEFAULT 0.0,
    request_hash TEXT,
    metadata     TEXT DEFAULT '{}'
);
"""

_CREATE_INDEX_SESSION = """
CREATE INDEX IF NOT EXISTS idx_session_id ON request_events(session_id);
"""

_CREATE_INDEX_PROVIDER = """
CREATE INDEX IF NOT EXISTS idx_provider ON request_events(provider);
"""


class SQLiteStorage(BaseStorage):
    """SQLite-backed persistent storage for request events."""

    def __init__(self, db_path: str = "ecotrace.db") -> None:
        self._db_path = db_path
        try:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute(_CREATE_TABLE)
            self._conn.execute(_CREATE_INDEX_SESSION)
            self._conn.execute(_CREATE_INDEX_PROVIDER)
            self._conn.commit()
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to initialize SQLite storage: {exc}") from exc

    def save_event(self, event: RequestEvent) -> None:
        """Insert or replace an event in the database."""
        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO request_events
                    (request_id, session_id, timestamp, provider, model,
                     prompt, response, input_tokens, output_tokens,
                     total_tokens, latency_ms, request_hash, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.request_id,
                    event.session_id,
                    event.timestamp.isoformat() if event.timestamp else None,
                    event.provider,
                    event.model,
                    json.dumps(event.prompt, default=str),
                    event.response,
                    event.input_tokens,
                    event.output_tokens,
                    event.total_tokens,
                    event.latency_ms,
                    event.request_hash,
                    json.dumps(event.metadata, default=str),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to save event: {exc}") from exc

    def _row_to_event(self, row: sqlite3.Row) -> RequestEvent:
        """Convert a database row to a RequestEvent."""
        prompt_raw = row["prompt"]
        try:
            prompt = json.loads(prompt_raw)
        except (json.JSONDecodeError, TypeError):
            prompt = prompt_raw

        metadata_raw = row["metadata"]
        try:
            metadata = json.loads(metadata_raw)
        except (json.JSONDecodeError, TypeError):
            metadata = {}

        ts = row["timestamp"]
        if ts:
            timestamp = datetime.fromisoformat(ts)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)

        return RequestEvent(
            request_id=row["request_id"],
            session_id=row["session_id"],
            timestamp=timestamp,
            provider=row["provider"],
            model=row["model"],
            prompt=prompt,
            response=row["response"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            total_tokens=row["total_tokens"],
            latency_ms=row["latency_ms"],
            request_hash=row["request_hash"],
            metadata=metadata,
        )

    def get_event(self, request_id: str) -> Optional[RequestEvent]:
        """Retrieve an event by request ID."""
        try:
            row = self._conn.execute(
                "SELECT * FROM request_events WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_event(row)
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to get event: {exc}") from exc

    def get_events(
        self,
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RequestEvent]:
        """Query events with optional filters."""
        clauses = []
        params: list = []
        if session_id is not None:
            clauses.append("session_id = ?")
            params.append(session_id)
        if provider is not None:
            clauses.append("provider = ?")
            params.append(provider)
        if model is not None:
            clauses.append("model = ?")
            params.append(model)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM request_events {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        try:
            rows = self._conn.execute(query, params).fetchall()
            return [self._row_to_event(r) for r in rows]
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to query events: {exc}") from exc

    def count_events(
        self,
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> int:
        """Count events matching filters."""
        clauses = []
        params: list = []
        if session_id is not None:
            clauses.append("session_id = ?")
            params.append(session_id)
        if provider is not None:
            clauses.append("provider = ?")
            params.append(provider)
        if model is not None:
            clauses.append("model = ?")
            params.append(model)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT COUNT(*) FROM request_events {where}"

        try:
            row = self._conn.execute(query, params).fetchone()
            return row[0] if row else 0
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to count events: {exc}") from exc

    def clear(self) -> None:
        """Delete all events."""
        try:
            self._conn.execute("DELETE FROM request_events")
            self._conn.commit()
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to clear events: {exc}") from exc

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
