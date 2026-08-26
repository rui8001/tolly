"""Qwen Code (qwencode) collector.

Source
------
``~/.qwen/usage/token-usage-*.jsonl`` (the Qwen Code runtime output dir,
resolved cross-platform; env override first, then platform defaults).

Each request record (``schemaVersion == 1``) carries the model plus
``inputTokens`` / ``cachedTokens`` / ``outputTokens`` / ``thoughtsTokens``.
Cached input is split out from input (matching the engine's ``cr`` bucket) and
cost is computed from the canonical price table. Cumulative ``usage_record.jsonl``
summary entries (which use ``version``, not ``schemaVersion``) are ignored to
avoid double counting.
"""
from __future__ import annotations

import os
from datetime import datetime

from .base import register
from ..core.paths import HOME, discover_dirs
from ..core.pricing import price_for
from ..core.ranges import parse_ts
from .jsonl import JsonlCollector


def _qwen_number(value) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def _qwen_datetime(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            seconds = float(value) / 1000 if value > 10_000_000_000 else float(value)
            return datetime.fromtimestamp(seconds).astimezone()
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        dt = parse_ts(value)
        return dt.astimezone() if dt else None
    return None


class QwenCodeCollector(JsonlCollector):
    tool = "qwencode"
    recursive = False

    def candidate_dirs(self):
        return discover_dirs("TALLY_QWEN_DIR", os.path.join(HOME, ".qwen", "usage"))

    def parse_record(self, obj, path):
        if not isinstance(obj, dict):
            return None

        if _qwen_number(obj.get("schemaVersion")) != 1:
            return None
        record_id = str(obj.get("id") or "").strip()
        session = str(obj.get("sessionId") or "").strip()
        if not record_id or not session:
            return None

        model = str(obj.get("model") or "unknown")
        dt = _qwen_datetime(obj.get("timestamp"))
        if dt is None:
            return None

        input_total = _qwen_number(obj.get("inputTokens"))
        cached = _qwen_number(obj.get("cachedTokens"))
        if input_total == 0 and cached > 0:
            input_total = cached
        cached = min(cached, input_total)
        inp = max(input_total - cached, 0)
        out = _qwen_number(obj.get("outputTokens"))
        reason = _qwen_number(obj.get("thoughtsTokens"))
        if inp == 0 and cached == 0 and out == 0 and reason == 0:
            return None

        p = price_for(model)
        cost = (inp * p["in"] + cached * p["cache_read"]
                + (out + reason) * p["out"]) / 1e6

        return {
            "dt": dt, "in": inp, "out": out, "cr": cached, "cw": 0,
            "reason": reason, "cost": cost, "model": model, "session": session,
        }


register(QwenCodeCollector())
