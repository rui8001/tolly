"""WorkBuddy collector.

Source: ``~/.workbuddy/projects/**/*.jsonl``. Each record may carry a
``message.usage`` block, possibly mirrored in ``providerData.usage`` /
``providerData.rawUsage``. We pick the richest source and compute cost from the
canonical price table. Cross-platform via ``discover_dirs``.
"""
from __future__ import annotations

import os
from datetime import datetime

from .base import register
from ..core.paths import HOME, discover_dirs
from ..core.pricing import _raw_price
from ..core.ranges import parse_ts
from .jsonl import JsonlCollector


def _workbuddy_number(obj, *keys):
    if not isinstance(obj, dict):
        return None
    for key in keys:
        if key not in obj:
            continue
        value = obj.get(key)
        if isinstance(value, bool):
            continue
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            continue
    return None


def _workbuddy_decimal(obj, *keys):
    if not isinstance(obj, dict):
        return None
    for key in keys:
        if key not in obj:
            continue
        value = obj.get(key)
        if isinstance(value, bool):
            continue
        try:
            return max(float(value), 0.0)
        except (TypeError, ValueError):
            continue
    return None


def _workbuddy_detail_total(value, *keys):
    if isinstance(value, dict):
        return _workbuddy_number(value, *keys) or 0
    if isinstance(value, list):
        return sum(_workbuddy_number(item, *keys) or 0
                   for item in value if isinstance(item, dict))
    return 0


def _workbuddy_timestamp(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = float(value) / 1000 if value > 10_000_000_000 else float(value)
        try:
            return datetime.fromtimestamp(seconds).astimezone()
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        dt = parse_ts(value)
        return dt.astimezone() if dt else None
    return None


class WorkBuddyCollector(JsonlCollector):
    tool = "workbuddy"
    recursive = True
    extra_fields = ("credits_used",)

    def candidate_dirs(self):
        return discover_dirs("TALLY_WORKBUDDY_DIR",
                             os.path.join(HOME, ".workbuddy", "projects"))

    def parse_record(self, obj, path):
        message = obj.get("message") or {}
        if not isinstance(message, dict):
            message = {}
        provider = obj.get("providerData") or message.get("providerData") or {}
        if not isinstance(provider, dict):
            provider = {}

        message_usage = message.get("usage") or {}
        normalized = provider.get("usage") or {}
        raw = provider.get("rawUsage") or {}
        sources = [x for x in (message_usage, normalized, raw)
                   if isinstance(x, dict) and x]
        credit_candidates = [
            _workbuddy_decimal(source, "credit", "credits", "credits_used", "creditsUsed")
            for source in sources
        ]
        credits_used = max((value for value in credit_candidates if value is not None),
                           default=0.0)

        selected = None
        input_total = output = 0
        for source in sources:
            inp = _workbuddy_number(source, "input_tokens", "inputTokens",
                                    "input", "prompt_tokens")
            out = _workbuddy_number(source, "output_tokens", "outputTokens",
                                    "output", "completion_tokens")
            if (inp or 0) + (out or 0) > 0:
                selected = source
                input_total = inp or 0
                output = out or 0
                break
        if selected is None and credits_used <= 0:
            return None

        if selected is None:
            selected = {}

        cache_read_candidates = []
        cache_write_candidates = []
        total_candidates = []
        for source in sources:
            cr_cands = [
                _workbuddy_number(source, "cache_read_input_tokens",
                                  "cacheReadInputTokens", "cache_read", "cacheRead",
                                  "cached_tokens", "cachedTokens"),
                _workbuddy_number(source, "prompt_cache_hit_tokens"),
                _workbuddy_detail_total(source.get("inputTokensDetails"),
                                        "cached_tokens", "cachedTokens"),
                _workbuddy_detail_total(source.get("input_tokens_details"),
                                        "cached_tokens", "cachedTokens"),
                _workbuddy_detail_total(source.get("prompt_tokens_details"),
                                        "cached_tokens", "cachedTokens"),
            ]
            cache_read_candidates.extend(v or 0 for v in cr_cands)
            cache_write_candidates.append(_workbuddy_number(
                source, "cache_creation_input_tokens", "cacheCreationInputTokens",
                "cache_write_input_tokens", "cacheWriteInputTokens",
                "prompt_cache_write_tokens", "cache_write", "cacheWrite") or 0)
            total = _workbuddy_number(source, "total_tokens",
                                      "totalTokens", "total")
            if total is not None:
                total_candidates.append(total)

        cache_read = max(cache_read_candidates) if cache_read_candidates else 0
        cache_write = max(cache_write_candidates) if cache_write_candidates else 0
        inclusive_input = any(total == input_total + output
                              for total in total_candidates)
        if inclusive_input:
            cache_read = min(cache_read, input_total)
            cache_write = min(cache_write, max(input_total - cache_read, 0))
            input_tokens = max(input_total - cache_read - cache_write, 0)
        else:
            input_tokens = input_total

        timestamp_value = obj.get("timestamp") or message.get("timestamp")
        dt = _workbuddy_timestamp(timestamp_value)
        if dt is None:
            return None

        model = (provider.get("requestModelName")
                 or provider.get("requestModelId")
                 or provider.get("model")
                 or message.get("model")
                 or obj.get("model")
                 or "unknown")
        session_id = (obj.get("sessionId") or message.get("sessionId")
                      or os.path.basename(path))
        item_id = (obj.get("id") or message.get("id")
                   or provider.get("messageId"))
        price = _raw_price(str(model))
        cost = (input_tokens / 1e6 * price["in"] + output / 1e6 * price["out"]
                + cache_read / 1e6 * price["cache_read"]
                + cache_write / 1e6 * price["cache_write"])
        return {
            "dt": dt, "in": input_tokens, "out": output,
            "cr": cache_read, "cw": cache_write,
            "cost": cost, "model": str(model), "session": path,
            "credits_used": credits_used,
            "_dedupe": (str(session_id), str(item_id)) if item_id else None,
        }


register(WorkBuddyCollector())
