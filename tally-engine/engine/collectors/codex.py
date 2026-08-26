"""Codex CLI collector.

Source
------
``~/.codex/sessions/**/rollout-*.jsonl`` and
``~/.codex/archived_sessions/**/rollout-*.jsonl`` (cross-platform; only the
HOME root differs).

Each rollout JSONL line is one of two shapes relevant here:

* a *model* event (``type`` in ``{turn_context, session_meta}``) whose payload
  carries the active model; we track it per file so token events can be priced;
* a *token_count* event (``type == "event_msg"`` and
  ``payload.type == "token_count"``) whose ``payload.info.last_token_usage``
  holds the *incremental* token usage of the last request.

Cost is computed from the canonical price table. ``last_token_usage`` is already
incremental (not cumulative), so each event is bucketed directly.
"""
from __future__ import annotations

import os

from .base import register
from ..core.paths import HOME, discover_dirs
from ..core.pricing import price_for, _has_known_price
from ..core.ranges import parse_ts
from .jsonl import JsonlCollector


class CodexCollector(JsonlCollector):
    tool = "codex"
    recursive = True

    def __init__(self):
        super().__init__()
        # Active model per file, set by model events and reused for token events.
        self._model_by_path: dict[str, str] = {}

    def candidate_dirs(self):
        return discover_dirs(
            "TALLY_CODEX_DIR",
            os.path.join(HOME, ".codex", "sessions"),
            os.path.join(HOME, ".codex", "archived_sessions"),
        )

    @staticmethod
    def _extract_model(obj: dict) -> str | None:
        payload = obj.get("payload") or {}
        model = payload.get("model")
        if not model and isinstance(payload.get("info"), dict):
            model = payload.get("info", {}).get("model")
        if not model:
            model = obj.get("model")
        return model or None

    def parse_record(self, obj, path):
        if not isinstance(obj, dict):
            return None

        rtype = obj.get("type")
        # Model-carrying events: track the active model for this file, no usage.
        if rtype in ("turn_context", "session_meta"):
            model = self._extract_model(obj)
            if model:
                self._model_by_path[path] = model
            return None

        # Token usage events only.
        if rtype != "event_msg":
            return None
        payload = obj.get("payload") or {}
        if payload.get("type") != "token_count":
            return None
        info = payload.get("info") or {}
        last = info.get("last_token_usage")
        if not isinstance(last, dict):
            return None

        dt = parse_ts(obj.get("timestamp", ""))
        if dt is None:
            return None
        dt = dt.astimezone()

        li = int(last.get("input_tokens", 0) or 0)
        lc = int(last.get("cached_input_tokens", 0) or 0)
        lo = int(last.get("output_tokens", 0) or 0)
        lr = int(last.get("reasoning_output_tokens", 0) or 0)
        if li == 0 and lc == 0 and lo == 0 and lr == 0:
            return None

        report_model = self._extract_model(obj) or self._model_by_path.get(path) or "unknown"
        price_model = report_model if _has_known_price(report_model) else "openai/gpt-5.5"
        p = price_for(price_model)
        cost = (li / 1e6 * p["in"] + lo / 1e6 * p["out"] + lc / 1e6 * p["cache_read"])

        return {
            "dt": dt, "in": li, "out": lo, "cr": lc, "cw": 0, "reason": lr,
            "cost": cost, "model": report_model, "session": path,
        }


register(CodexCollector())
