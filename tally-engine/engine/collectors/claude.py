"""Claude Code collector.

Source: ``~/.claude/projects/<project>/<session>.jsonl`` (cross-platform; only
the HOME root differs). Each ``assistant`` message carries ``message.usage`` with
input/output/cache tokens; cost is computed from the canonical price table.
"""
from __future__ import annotations

import os

from .base import register
from ..core.paths import HOME, discover_dirs
from ..core.pricing import price_for
from ..core.ranges import parse_ts
from .jsonl import JsonlCollector


class ClaudeCollector(JsonlCollector):
    tool = "claude"
    recursive = True

    def candidate_dirs(self):
        return discover_dirs("TALLY_CLAUDE_DIR", os.path.join(HOME, ".claude", "projects"))

    def parse_record(self, obj, path):
        if obj.get("type") != "assistant":
            return None
        msg = obj.get("message") or {}
        u = msg.get("usage")
        if not u:
            return None
        dt = parse_ts(obj.get("timestamp", ""))
        if dt is None:
            return None
        dt = dt.astimezone()
        inp = int(u.get("input_tokens", 0) or 0)
        out = int(u.get("output_tokens", 0) or 0)
        cr = int(u.get("cache_read_input_tokens", 0) or 0)
        cw = int(u.get("cache_creation_input_tokens", 0) or 0)
        p = price_for(msg.get("model"))
        cc = u.get("cache_creation") or {}
        w5 = cc.get("ephemeral_5m_input_tokens")
        w1 = cc.get("ephemeral_1h_input_tokens")
        if w5 is None and w1 is None:
            write_cost = cw / 1e6 * p["write5m"]
        else:
            write_cost = (w5 or 0) / 1e6 * p["write5m"] + (w1 or 0) / 1e6 * p["write1h"]
        cost = (inp / 1e6 * p["in"] + out / 1e6 * p["out"]
                + cr / 1e6 * p["cache_read"] + write_cost)
        return {
            "dt": dt, "in": inp, "out": out, "cr": cr, "cw": cw, "cost": cost,
            "model": msg.get("model") or "unknown", "session": path,
        }

    def collect(self):
        result = super().collect()
        today = result["ranges"]["today"]
        result["cur"] = {
            "in": today["in"], "out": today["out"], "cr": today["cr"],
            "cw": today["cw"], "name": "-",
        }
        return result


register(ClaudeCollector())
