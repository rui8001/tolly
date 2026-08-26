"""Kimi Code collector.

Source (cross-platform, env override first):
  ${TALLY_KIMI_CODE_DIR:-~/.kimi-code}/sessions/*/*/agents/*/wire.jsonl
  ${TALLY_KIMI_SHARE_DIR:-~/.kimi}/sessions/*/*/wire.jsonl

Each ``wire.jsonl`` line is either ``type == "usage.record"`` (carrying a
``usage`` block) or a ``StatusUpdate`` message whose ``payload.token_usage``
holds the token counts. Cost is derived from the canonical price table.
"""
from __future__ import annotations

import math
import os
from datetime import datetime

from .base import register
from ..core.paths import HOME, discover_dirs
from ..core.pricing import price_for
from ..core.ranges import parse_ts
from .jsonl import JsonlCollector


def _kimi_token(value):
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def _kimi_datetime(record, key):
    value = record.get(key) if isinstance(record, dict) else None
    try:
        epoch = float(value)
        if not math.isfinite(epoch):
            return None
        if epoch > 100_000_000_000:
            epoch /= 1000
        return datetime.fromtimestamp(epoch).astimezone()
    except (TypeError, ValueError, OverflowError, OSError):
        parsed = parse_ts(value) if isinstance(value, str) else None
        return parsed.astimezone() if parsed is not None else None


def _kimi_events(message, scope="main"):
    if not isinstance(message, dict):
        return
    msg_type = message.get("type")
    payload = message.get("payload")
    if not isinstance(payload, dict):
        return
    if msg_type == "SubagentEvent":
        agent = (payload.get("agent_id") or payload.get("parent_tool_call_id")
                 or payload.get("task_tool_call_id"))
        child_scope = f"{scope}/{agent}" if isinstance(agent, str) and agent else scope
        yield from _kimi_events(payload.get("event"), child_scope)
    elif msg_type == "StatusUpdate":
        yield scope, payload


def _kimi_record(dt, inp, out, cr, cw, model, path):
    price = price_for(model)
    cost = (inp / 1e6 * price["in"] + out / 1e6 * price["out"]
            + cr / 1e6 * price["cache_read"] + cw / 1e6 * price["write5m"])
    return {"dt": dt, "in": inp, "out": out, "cr": cr, "cw": cw,
            "cost": cost, "model": model, "session": path}


class KimiCodeCollector(JsonlCollector):
    tool = "kimicode"
    recursive = True

    def candidate_dirs(self):
        code = discover_dirs("TALLY_KIMI_CODE_DIR",
                             os.path.join(HOME, ".kimi-code", "sessions"))
        share = discover_dirs("TALLY_KIMI_SHARE_DIR",
                              os.path.join(HOME, ".kimi", "sessions"))
        return code + share

    def parse_record(self, obj, path):
        if not isinstance(obj, dict):
            return None

        if obj.get("type") == "usage.record":
            usage = obj.get("usage")
            if not isinstance(usage, dict):
                return None
            dt = _kimi_datetime(obj, "time")
            if dt is None:
                return None
            inp = _kimi_token(usage.get("inputOther"))
            out = _kimi_token(usage.get("output"))
            cr = _kimi_token(usage.get("inputCacheRead"))
            cw = _kimi_token(usage.get("inputCacheCreation"))
            if inp + out + cr + cw == 0:
                return None
            model = obj.get("model") or "unknown"
            return _kimi_record(dt, inp, out, cr, cw, model, path)

        # StatusUpdate path.
        dt = _kimi_datetime(obj, "timestamp")
        if dt is None:
            return None
        message = obj.get("message")
        for _scope, payload in _kimi_events(message):
            usage = payload.get("token_usage")
            if not isinstance(usage, dict):
                continue
            inp = _kimi_token(usage.get("input_other"))
            out = _kimi_token(usage.get("output"))
            cr = _kimi_token(usage.get("input_cache_read"))
            cw = _kimi_token(usage.get("input_cache_creation"))
            if inp + out + cr + cw == 0:
                continue
            model = obj.get("model") or "unknown"
            return _kimi_record(dt, inp, out, cr, cw, model, path)
        return None


register(KimiCodeCollector())
