"""Exchange-session freshness for mainland fund review data."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo


CHINA_TZ = ZoneInfo("Asia/Shanghai")


@lru_cache(maxsize=1)
def _calendar():
    import exchange_calendars as xcals

    return xcals.get_calendar("XSHG")


def expected_session(as_at: datetime, *, publication_hour: int) -> date | None:
    """Latest session expected to have published, or None if calendar is unavailable."""
    local = as_at.astimezone(CHINA_TZ)
    cutoff = local.date() if local.time() >= time(publication_hour) else local.date() - timedelta(days=1)
    try:
        return _calendar().date_to_session(cutoff.isoformat(), direction="previous").date()
    except (ImportError, ValueError, OverflowError):
        return None


def sessions_between(start: date, end: date) -> int | None:
    """Count actual exchange sessions after start through end."""
    if start >= end:
        return 0
    try:
        return len(_calendar().sessions_in_range(
            (start + timedelta(days=1)).isoformat(), end.isoformat(),
        ))
    except (ImportError, ValueError, OverflowError):
        return None
