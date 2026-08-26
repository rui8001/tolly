"""Gemini (Google AI Studio CLI) collector.

Source: ``~/.gemini/tmp/<hash>/chats/*.jsonl`` plus session jsonl. Each record
with ``type == "gemini"`` carries ``tokens{input,output,cached,thoughts}``.
Cost uses the Gemini price table. Cross-platform via ``discover_dirs``.
"""
from __future__ import annotations

import os

from .base import register
from ..core.paths import HOME, discover_dirs
from ..core.pricing import gemini_price
from ..core.ranges import parse_ts
from .jsonl import JsonlCollector


class GeminiCollector(JsonlCollector):
    tool = "gemini"
    recursive = True

    def candidate_dirs(self):
        return discover_dirs("TALLY_GEMINI_DIR", os.path.join(HOME, ".gemini", "tmp"))

    def parse_record(self, obj, path):
        if obj.get("type") != "gemini":
            return None
        tokens = obj.get("tokens")
        if not isinstance(tokens, dict):
            return None
        dt = parse_ts(obj.get("timestamp", ""))
        if dt is None:
            return None
        dt = dt.astimezone()
        inp = int(tokens.get("input", 0) or 0)
        out = int(tokens.get("output", 0) or 0)
        cached = int(tokens.get("cached", 0) or 0)
        thoughts = int(tokens.get("thoughts", 0) or 0)
        model = obj.get("model") or "unknown"
        price = gemini_price(model)
        cost = (max(inp - cached, 0) / 1e6 * price["in"]
                + cached / 1e6 * price["cache_read"]
                + (out + thoughts) / 1e6 * price["out"])
        return {
            "dt": dt, "in": inp, "out": out, "cr": cached, "cw": 0,
            "cost": cost, "model": model, "session": path,
        }


register(GeminiCollector())
