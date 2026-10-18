"""Local XNYS session dates, including exchange holidays and special closures."""
from datetime import timedelta
from functools import lru_cache


@lru_cache(maxsize=16)
def _year_sessions(first, last):
    import exchange_calendars as xcals
    start, end = f"{first}-01-01", f"{last}-12-31"
    calendar = xcals.get_calendar("XNYS", start=start, end=end)
    return frozenset(stamp.date().isoformat() for stamp in calendar.sessions)


def session_dates(start, end):
    return sorted(day for day in _year_sessions(start.year, end.year)
                  if start.isoformat() <= day <= end.isoformat())


def last_trading_dates(ending, count=5):
    return session_dates(ending-timedelta(days=60), ending)[-count:]
