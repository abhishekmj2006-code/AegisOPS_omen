"""Timestamp helper functions ensuring strict UTC ISO 8601 formatting."""

from datetime import datetime, timezone


def get_utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def get_iso_utc_now() -> str:
    """Return current UTC time in strict ISO 8601 format with Z suffix.
    
    Example: 2026-11-20T09:45:00.123456Z
    """
    dt = get_utc_now()
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def format_iso_utc(dt: datetime) -> str:
    """Format any datetime to UTC ISO 8601 string with Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
