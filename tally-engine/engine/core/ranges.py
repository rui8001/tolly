"""Time-range bucketing shared by every collector."""
from __future__ import annotations

from datetime import datetime, timedelta

# Order matters only for display; logic reads membership, not position.
RANGE_KEYS = ["today", "yesterday", "week", "last_week", "month", "year", "all"]
TOKEN_FIELDS = ("in", "out", "cr", "cw", "reason")


def range_bounds():
    """Local start points for today/yesterday/this-week(Mon)/last-week/month/year."""
    now = datetime.now().astimezone()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    week = today - timedelta(days=today.weekday())          # Monday 00:00
    last_week_start = week - timedelta(days=7)
    month = today.replace(day=1)
    year = today.replace(month=1, day=1)
    return {"today": today, "yesterday": yesterday, "week": week,
            "last_week": last_week_start, "last_week_end": week,
            "month": month, "year": year}


def range_boundaries():
    """Explicit date boundaries per relative range (used by sync reconciliation)."""
    b = range_bounds()
    next_month = (b["month"].replace(day=28) + timedelta(days=4)).replace(day=1)
    next_year = b["year"].replace(year=b["year"].year + 1)

    def day_s(dt):
        return dt.date().isoformat()

    return {
        "today": {"start": day_s(b["today"]), "end": day_s(b["today"] + timedelta(days=1))},
        "yesterday": {"start": day_s(b["yesterday"]), "end": day_s(b["today"])},
        "week": {"start": day_s(b["week"]), "end": day_s(b["week"] + timedelta(days=7))},
        "last_week": {"start": day_s(b["last_week"]), "end": day_s(b["week"])},
        "month": {"start": day_s(b["month"]), "end": day_s(next_month)},
        "year": {"start": day_s(b["year"]), "end": day_s(next_year)},
        "all": {"start": None, "end": None},
    }


def classify_date(d, b):
    """Given a local date, return the range keys it falls into.

    Today is also in week/month/year (and last_week if applicable).
    """
    ks = ["all"]
    if d == b["today"].date():
        ks.append("today")
    if d == b["yesterday"].date():
        ks.append("yesterday")
    if d >= b["week"].date():
        ks.append("week")
    if b["last_week"].date() <= d < b["last_week_end"].date():
        ks.append("last_week")
    if d >= b["month"].date():
        ks.append("month")
    if d >= b["year"].date():
        ks.append("year")
    return ks


def classify(dt, b):
    return classify_date(dt.date(), b)


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def empty_bucket(extra_keys=None):
    b = {"in": 0, "out": 0, "cr": 0, "cw": 0, "reason": 0,
         "cost": 0.0, "models": {}, "sessions": set()}
    for k in (extra_keys or ()):
        b[k] = 0
    return b


def empty_ranges(extra_keys=None):
    return {k: empty_bucket(extra_keys) for k in RANGE_KEYS}
