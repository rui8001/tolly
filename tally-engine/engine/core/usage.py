"""Token/cost aggregation helpers shared by collectors.

These operate on plain dicts so the final output stays JSON-compatible.
"""
from __future__ import annotations

from .ranges import RANGE_KEYS, TOKEN_FIELDS, classify, range_bounds


def add_model_usage(models, model, inp=0, out=0, cr=0, cw=0, reason=0, cost=0.0):
    if not model:
        return
    mm = models.setdefault(model, {"in": 0, "out": 0, "cr": 0, "cw": 0, "reason": 0, "cost": 0.0})
    mm["in"] += int(inp or 0)
    mm["out"] += int(out or 0)
    mm["cr"] += int(cr or 0)
    mm["cw"] += int(cw or 0)
    mm["reason"] += int(reason or 0)
    mm["cost"] += float(cost or 0)


def add_token_usage(target, inp=0, out=0, cr=0, cw=0, reason=0, cost=0.0, model=None):
    target["in"] += int(inp or 0)
    target["out"] += int(out or 0)
    target["cr"] += int(cr or 0)
    target["cw"] += int(cw or 0)
    target["reason"] += int(reason or 0)
    target["cost"] += float(cost or 0)
    add_model_usage(target.get("models", {}), model, inp, out, cr, cw, reason, cost)


def token_total(day):
    return sum(day.get(k, 0) for k in TOKEN_FIELDS)


def empty_bucket(extra_keys=None):
    b = {"in": 0, "out": 0, "cr": 0, "cw": 0, "reason": 0,
         "cost": 0.0, "models": {}, "sessions": set()}
    for k in (extra_keys or ()):
        b[k] = 0
    return b


def empty_ranges(extra_keys=None):
    return {k: empty_bucket(extra_keys) for k in RANGE_KEYS}


def daily_record(daily, dt, *, inp=0, out=0, cr=0, cw=0,
                 reason=0, cost=0.0, model=None):
    """Accumulate one record into a calendar-day bucket."""
    if dt is None:
        return
    key = dt.date().isoformat()
    bucket = daily.setdefault(
        key,
        {"in": 0, "out": 0, "cr": 0, "cw": 0, "reason": 0,
         "cost": 0.0, "models": {}},
    )
    add_token_usage(bucket, inp, out, cr, cw, reason, cost, model)


def bucket_record(ranges, bounds, dt, *, inp=0, out=0, cr=0, cw=0,
                  reason=0, cost=0.0, model=None, session=None, daily=None):
    """Add one usage record into every range bucket it classifies into.

    ``bounds`` should be computed once per collector via ``range_bounds()``.
    """
    if dt is None:
        return
    for k in classify(dt, bounds):
        bucket = ranges[k]
        if session is not None:
            bucket["sessions"].add(session)
        add_token_usage(bucket, inp, out, cr, cw, reason, cost, model)
    if daily is not None:
        daily_record(daily, dt, inp=inp, out=out, cr=cr, cw=cw,
                     reason=reason, cost=cost, model=model)


def merge_token_day(bucket, day, session=None):
    if session is not None:
        bucket["sessions"].add(session)
    add_token_usage(bucket, day.get("in", 0), day.get("out", 0), day.get("cr", 0),
                    day.get("cw", 0), day.get("reason", 0), day.get("cost", 0))
    for model, mv in day.get("models", {}).items():
        add_model_usage(bucket["models"], model, mv.get("in", 0), mv.get("out", 0),
                        mv.get("cr", 0), mv.get("cw", 0), mv.get("reason", 0), mv.get("cost", 0))


def bucketize_days(ranges, bounds, days, session=None):
    """Bucket a list of ``{date, in, out, cr, cw, reason, cost, model}`` dicts."""
    for day in days:
        dt = day.get("dt")
        if dt is None:
            continue
        bucket_record(ranges, bounds, dt,
                      inp=day.get("in", 0), out=day.get("out", 0),
                      cr=day.get("cr", 0), cw=day.get("cw", 0),
                      reason=day.get("reason", 0), cost=day.get("cost", 0),
                      model=day.get("model"), session=session)
