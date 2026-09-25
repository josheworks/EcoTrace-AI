"""Timestamp utilities."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Return the current UTC datetime as an ISO 8601 string."""
    return utc_now().isoformat()


def timestamp_ms() -> float:
    """Return the current UTC timestamp in milliseconds."""
    return utc_now().timestamp() * 1000
