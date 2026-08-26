"""Prime Agent collector (Pi-family usage shape).

Source: ``~/.prime/agent/sessions/*.jsonl`` plus ``session-artifacts/**/**/*.jsonl``.
Prime Agent reuses the Pi Coding Agent usage shape, so the per-record parsing is
shared. Cross-platform via ``discover_dirs`` (env override first).
"""
from __future__ import annotations

import os

from .base import register
from ..core.paths import HOME, discover_dirs
from ..core.pricing import _raw_price
from ..core.ranges import parse_ts
from .jsonl import JsonlCollector


def _pi_model_id(msg):
    msg = msg or {}
    model = msg.get("model", "") or ""
    provider = msg.get("provider", "") or ""
    if provider and model and "/" not in model:
        return f"{provider}/{model}"
    return model or provider or "unknown"


def _pi_usage_int(usage, *fields):
    for field in fields:
        if field in usage and usage[field] is not None:
            return int(usage[field] or 0)
    return 0


def _pi_usage_cost(u, model):
    cost_obj = u.get("cost") or {}
    total = float(cost_obj.get("total", 0) or 0)
    if total > 0:
        return total
    parts = sum(float(cost_obj.get(k, 0) or 0)
                for k in ("input", "output", "cacheRead", "cacheWrite"))
    if parts > 0:
        return parts
    p = _raw_price(model)
    inp = _pi_usage_int(u, "input")
    out = _pi_usage_int(u, "output")
    cr = _pi_usage_int(u, "cacheRead", "cache_read")
    cw = _pi_usage_int(u, "cacheWrite", "cache_write")
    return (inp / 1e6 * p["in"] + out / 1e6 * p["out"]
            + cr / 1e6 * p["cache_read"] + cw / 1e6 * p["cache_write"])


class PrimeAgentCollector(JsonlCollector):
    tool = "prime_agent"
    recursive = True

    def candidate_dirs(self):
        sess = discover_dirs("TALLY_PRIME_AGENT_SESSION_DIR",
                             os.path.join(HOME, ".prime", "agent", "sessions"))
        art = discover_dirs("TALLY_PRIME_AGENT_ARTIFACTS_DIR",
                            os.path.join(HOME, ".prime", "agent", "session-artifacts"))
        return sess + art

    def parse_record(self, obj, path):
        # session / model_change lines carry no token usage -> skip.
        if obj.get("type") in ("session", "model_change"):
            return None
        if obj.get("type") != "message":
            return None
        msg = obj.get("message") or {}
        if msg.get("role") != "assistant":
            return None
        u = msg.get("usage")
        if not isinstance(u, dict) or not u:
            return None
        dt = parse_ts(obj.get("timestamp") or msg.get("timestamp") or "")
        if dt is None:
            return None
        dt = dt.astimezone()
        inp = _pi_usage_int(u, "input")
        out = _pi_usage_int(u, "output")
        cr = _pi_usage_int(u, "cacheRead", "cache_read")
        cw = _pi_usage_int(u, "cacheWrite", "cache_write")
        reason = _pi_usage_int(u, "reasoning", "reason", "reasoningTokens")
        model = _pi_model_id(msg)
        cost = _pi_usage_cost(u, model)
        if inp + out + cr + cw + reason == 0 and cost <= 0:
            return None
        return {
            "dt": dt, "in": inp, "out": out, "cr": cr, "cw": cw,
            "reason": reason, "cost": cost, "model": model, "session": path,
        }


register(PrimeAgentCollector())
