"""MiMo Code (Xiaomi) collector.

MiMo CLI writes per-session JSONL logs under its platform data directory. Each
assistant message record carries a ``tokens`` block (opencode/MiMo shape:
``tokens{input,output,reasoning,cache{read,write}}``) plus a ``modelID`` and a
timestamp. Cost is derived from the canonical price table (mimo family).

Cross-platform via ``discover_dirs`` (env override first), with ``MIMOCODE_HOME``
and the standard XDG / Application-Support / LOCALAPPDATA locations as defaults.
"""
from __future__ import annotations

import os
from datetime import datetime

from .base import register
from ..core.paths import HOME, IS_WIN, discover_dirs, app_support_dir, local_data_dir
from ..core.pricing import price_for
from ..core.ranges import parse_ts
from .jsonl import JsonlCollector


def _mimocode_number(value):
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def _mimocode_dt(value):
    if isinstance(value, str):
        dt = parse_ts(value)
        return dt.astimezone() if dt else None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            secs = float(value) / 1000 if value > 10_000_000_000 else float(value)
            return datetime.fromtimestamp(secs).astimezone()
        except (OSError, OverflowError, ValueError):
            return None
    return None


class MimocodeCollector(JsonlCollector):
    tool = "mimocode"
    recursive = True

    def candidate_dirs(self):
        defaults = []
        configured = os.environ.get("MIMOCODE_HOME")
        if configured:
            defaults.append(os.path.join(os.path.expanduser(configured), "data"))
        defaults.append(local_data_dir("mimocode"))
        defaults.append(app_support_dir("mimocode"))
        if IS_WIN:
            local = os.environ.get("LOCALAPPDATA", "")
            app = os.environ.get("APPDATA", "")
            if local:
                defaults.insert(0, os.path.join(local, "mimocode"))
            if app:
                defaults.insert(0, os.path.join(app, "mimocode"))
        else:
            defaults.append(os.path.join(HOME, ".local", "share", "mimocode"))
            defaults.append(os.path.join(HOME, "Library", "Application Support", "mimocode"))
        return discover_dirs("TALLY_MIMOCODE_DIR", *defaults)

    def parse_record(self, obj, path):
        if not isinstance(obj, dict):
            return None
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else obj
        tokens = obj.get("tokens") or (msg.get("tokens")
                                       if isinstance(msg, dict) else None)
        if not isinstance(tokens, dict):
            tokens = {}
        if not tokens:
            # Also accept a flat usage block.
            usage = obj.get("usage") or (msg.get("usage")
                                         if isinstance(msg, dict) else None)
            if isinstance(usage, dict):
                tokens = usage
        if not isinstance(tokens, dict) or not tokens:
            return None

        inp = _mimocode_number(tokens.get("input") or tokens.get("inputTokens")
                               or tokens.get("prompt_tokens"))
        out = _mimocode_number(tokens.get("output") or tokens.get("outputTokens")
                               or tokens.get("completion_tokens"))
        reason = _mimocode_number(tokens.get("reasoning")
                                  or tokens.get("reasoningTokens")
                                  or tokens.get("thoughts"))
        cache = tokens.get("cache") if isinstance(tokens.get("cache"), dict) else {}
        if cache:
            cr = _mimocode_number(cache.get("read") or cache.get("readTokens"))
            cw = _mimocode_number(cache.get("write") or cache.get("writeTokens"))
        else:
            cr = _mimocode_number(tokens.get("cacheRead") or tokens.get("cache_read"))
            cw = _mimocode_number(tokens.get("cacheWrite") or tokens.get("cache_write"))

        if inp + out + cr + cw + reason == 0:
            return None

        ts = (obj.get("time") or obj.get("timestamp")
              or (msg.get("timestamp") if isinstance(msg, dict) else None))
        dt = _mimocode_dt(ts)
        if dt is None:
            return None
        dt = dt.astimezone()

        model = (obj.get("modelID") or obj.get("model")
                 or (msg.get("modelID") if isinstance(msg, dict) else None)
                 or (msg.get("model") if isinstance(msg, dict) else None)
                 or (tokens.get("model") if isinstance(tokens, dict) else None)
                 or "unknown")
        price = price_for(model)
        cost = (inp / 1e6 * price["in"] + out / 1e6 * price["out"]
                + reason / 1e6 * price["out"]
                + cr / 1e6 * price["cache_read"] + cw / 1e6 * price["write5m"])
        return {
            "dt": dt, "in": inp, "out": out, "cr": cr, "cw": cw,
            "reason": reason, "cost": cost, "model": model, "session": path,
        }


register(MimocodeCollector())
