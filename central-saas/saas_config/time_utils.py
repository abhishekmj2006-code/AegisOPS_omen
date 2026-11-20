"""Timezone conversion and 12-hour AM/PM formatting utilities for AegisOPS."""

from datetime import datetime, timezone
from typing import Optional, Union


def to_local_datetime(dt: Optional[Union[datetime, str]]) -> Optional[datetime]:
    """Convert any UTC datetime or ISO timestamp string into system local datetime."""
    if not dt:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()


def format_local_12h(dt: Optional[Union[datetime, str]]) -> str:
    """Format datetime in 12-hour format with AM/PM in local system timezone (e.g. 04:01:51 AM)."""
    loc = to_local_datetime(dt)
    return loc.strftime("%I:%M:%S %p") if loc else "None"


def format_local_full(dt: Optional[Union[datetime, str]]) -> str:
    """Format full date and time in 12-hour AM/PM local time (e.g. 2026-11-21 04:01:51 AM)."""
    loc = to_local_datetime(dt)
    return loc.strftime("%Y-%m-%d %I:%M:%S %p") if loc else ""


def format_iso_utc_offset(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime with explicit UTC offset suffix (+00:00) so JS Date parses as UTC."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
