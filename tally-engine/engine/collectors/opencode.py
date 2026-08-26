"""OpenCode collector.

Source: ``~/.local/share/opencode/opencode.db`` (env ``OPENCODE_DATA_DIR``).
The ``message`` table stores each assistant turn as a JSON blob in ``data``;
token usage and cost are extracted per row and bucketed into time ranges.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from .base import register
from .sqlite import SqliteCollector
from ..core.paths import HOME, local_data_dir
from ..core.pricing import price_for, pricing_id
from ..core.ranges import empty_ranges, range_bounds
from ..core.usage import bucket_record


class OpenCodeCollector(SqliteCollector):
    tool = "opencode"

    def candidate_dbs(self):
        cands = []
        env = os.environ.get("OPENCODE_DATA_DIR")
        if env:
            env = os.path.expanduser(env)
            cands.append(os.path.join(env, "opencode.db"))
            cands.append(os.path.join(env, "opencode", "opencode.db"))
        base = local_data_dir()
        cands.append(os.path.join(base, "opencode", "opencode.db"))
        cands.append(local_data_dir("opencode", "opencode.db"))
        return cands

    @staticmethod
    def _message(message, session_id, created_ms):
        if message.get("role") != "assistant":
            return None
        timestamp = (message.get("time") or {}).get("created") or created_ms
        if not timestamp:
            return None
        tokens = message.get("tokens") or {}
        cache = tokens.get("cache") or {}
        model = message.get("modelID", "")
        try:
            created = datetime.fromtimestamp(int(timestamp) / 1000).astimezone()
        except (ValueError, OverflowError, OSError):
            return None
        cost = float(message.get("cost", 0) or 0)
        inp = int(tokens.get("input", 0) or 0)
        out = int(tokens.get("output", 0) or 0)
        reason = int(tokens.get("reasoning", 0) or 0)
        cr = int(cache.get("read", 0) or 0)
        cw = int(cache.get("write", 0) or 0)
        if not cost:
            pid = pricing_id(model)
            if pid:
                p = price_for(model)
                cost = (inp / 1e6 * p["in"]
                        + (out + reason) / 1e6 * p["out"]
                        + cr / 1e6 * p["cache_read"]
                        + cw / 1e6 * p["write5m"])
        return {
            "dt": created, "in": inp, "out": out, "reason": reason,
            "cr": cr, "cw": cw, "cost": cost,
            "model": model or "unknown",
            "session": message.get("sessionID") or session_id,
        }

    def query(self, conn):
        ranges = empty_ranges()
        bounds = range_bounds()
        try:
            rows = conn.execute(
                "SELECT id, session_id, time_created, data FROM message")
        except Exception:
            return {"ranges": ranges}
        for _mid, session_id, created_ms, raw in rows:
            try:
                message = json.loads(raw)
            except (TypeError, ValueError):
                continue
            rec = self._message(message, session_id or "", created_ms or 0)
            if not rec:
                continue
            bucket_record(
                ranges, bounds, rec["dt"],
                inp=rec["in"], out=rec["out"], cr=rec["cr"], cw=rec["cw"],
                reason=rec["reason"], cost=rec["cost"],
                model=rec["model"], session=rec["session"])
        return {"ranges": ranges}


register(OpenCodeCollector())
