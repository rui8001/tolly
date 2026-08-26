"""ZCode collector.

Source: ``~/.zcode/cli/db/db.sqlite`` (env ``TALLY_ZCODE_DB``).
The ``model_usage`` table stores per-request token counts with epoch-millisecond
timestamps; cache tokens are split out and fresh input is recomputed.
"""
from __future__ import annotations

import os

from .base import register
from .sqlite import SqliteCollector
from ..core.paths import HOME
from ..core.pricing import price_for, pricing_id
from ..core.ranges import empty_ranges, range_bounds
from ..core.usage import bucket_record
from datetime import datetime


def _number(value):
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError, OverflowError):
        return 0


class ZCodeCollector(SqliteCollector):
    tool = "zcode"

    def candidate_dbs(self):
        cands = []
        env = os.environ.get("TALLY_ZCODE_DB")
        if env:
            cands.append(os.path.expanduser(env))
        cands.append(os.path.expanduser(
            os.path.join(HOME, ".zcode", "cli", "db", "db.sqlite")))
        return cands

    def query(self, conn):
        ranges = empty_ranges()
        bounds = range_bounds()
        try:
            rows = conn.execute("""
                SELECT id, session_id, model_id, input_tokens, output_tokens,
                       reasoning_tokens, cache_creation_input_tokens,
                       cache_read_input_tokens, started_at, completed_at
                FROM model_usage
                ORDER BY started_at ASC
            """)
        except Exception:
            return {"ranges": ranges}
        for _rid, session_id, model, input_total, output_total, reasoning, \
                cache_write, cache_read, started_at, completed_at in rows:
            ts = _number(completed_at) or _number(started_at)
            if not ts:
                continue
            try:
                created = datetime.fromtimestamp(ts / 1000).astimezone()
            except (OSError, OverflowError, ValueError):
                continue
            input_total = _number(input_total)
            output_total = _number(output_total)
            reasoning = _number(reasoning)
            cache_write = _number(cache_write)
            cache_read = _number(cache_read)
            fresh_input = max(input_total - cache_read - cache_write, 0)
            visible_output = max(output_total - reasoning, 0)
            if fresh_input + output_total + cache_read + cache_write <= 0:
                continue
            display_model = pricing_id(model) or str(model or "unknown")
            cost = 0.0
            pid = pricing_id(model)
            if pid:
                p = price_for(model)
                cost = (fresh_input / 1e6 * p["in"]
                        + output_total / 1e6 * p["out"]
                        + cache_read / 1e6 * p["cache_read"]
                        + cache_write / 1e6 * p["write5m"])
            bucket_record(
                ranges, bounds, created,
                inp=fresh_input, out=visible_output, cr=cache_read, cw=cache_write,
                reason=reasoning, cost=cost, model=display_model,
                session=str(session_id or _rid or "unknown"))
        return {"ranges": ranges}


register(ZCodeCollector())
