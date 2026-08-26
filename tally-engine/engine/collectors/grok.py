"""Grok collector.

Source: ``~/.grok/logs/unified.jsonl`` (env ``GROK_HOME`` overrides the ``~/.grok``
root). Each ``shell.turn.inference_done`` event carries a ``ctx`` block with token
counts. Cost follows the same published-token pricing formula as other tools.

Live quota fetching is kept outside the collector and behind an explicit opt-in
flag, so a network request never blocks or crashes a normal usage scan.
"""
from __future__ import annotations

import os

from .base import register
from ..core.paths import HOME, discover_dirs
from ..core.pricing import price_for
from ..core.ranges import parse_ts
from .jsonl import JsonlCollector


def _grok_home() -> str:
    return os.path.expanduser(os.environ.get("GROK_HOME", os.path.join(HOME, ".grok")))


class GrokCollector(JsonlCollector):
    tool = "grok"
    recursive = True

    def candidate_dirs(self):
        return discover_dirs("TALLY_GROK_DIR", os.path.join(_grok_home(), "logs"))

    def parse_record(self, obj, path):
        if not isinstance(obj, dict):
            return None
        if obj.get("msg") != "shell.turn.inference_done":
            return None
        ctx = obj.get("ctx") or {}
        if not isinstance(ctx, dict):
            return None
        token_keys = ("prompt_tokens", "cached_prompt_tokens",
                      "completion_tokens", "reasoning_tokens")
        if not any(k in ctx for k in token_keys):
            return None
        ts = str(obj.get("ts") or "")
        dt = parse_ts(ts)
        if dt is None:
            return None
        dt = dt.astimezone()
        try:
            prompt = max(int(ctx.get("prompt_tokens") or 0), 0)
            cached = max(int(ctx.get("cached_prompt_tokens") or 0), 0)
            completion = max(int(ctx.get("completion_tokens") or 0), 0)
            reasoning = max(int(ctx.get("reasoning_tokens") or 0), 0)
        except (TypeError, ValueError, OverflowError):
            return None
        cached = min(cached, prompt)
        reasoning = min(reasoning, completion)
        rec_in = prompt - cached
        cr = cached
        out = completion - reasoning
        reason = reasoning

        # Best-effort model; fall back to the canonical grok default so cost is meaningful.
        model = (obj.get("model") or ctx.get("model")
                 or obj.get("model_name") or "x-ai/grok-4.5")
        p = price_for(model)
        cost = (rec_in / 1e6 * p["in"]
                + cr / 1e6 * p["cache_read"]
                + (out + reason) / 1e6 * p["out"])

        return {
            "dt": dt, "in": rec_in, "out": out, "cr": cr, "cw": 0,
            "reason": reason, "cost": cost, "model": model,
            "session": str(obj.get("sid") or path),
        }


register(GrokCollector())
