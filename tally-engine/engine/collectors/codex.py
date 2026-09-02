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
import time

from .base import register
from ..core.paths import HOME, discover_dirs
from ..core.pricing import price_for, _has_known_price
from ..core.ranges import parse_ts
from .jsonl import JsonlCollector
from .codex_app_server import read_account_rate_limits


class CodexCollector(JsonlCollector):
    tool = "codex"
    recursive = True

    def __init__(self):
        super().__init__()
        # Active model per file, set by model events and reused for token events.
        self._model_by_path: dict[str, str] = {}
        self._project_by_path: dict[str, str] = {}
        self._latest_codex_quota: dict | None = None
        self._latest_codex_quota_timestamp: float = float("-inf")
        self._previous_total_by_path: dict[str, tuple] = {}

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

    @staticmethod
    def _percent(value) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return min(max(number, 0.0), 100.0)

    @classmethod
    def _quota_from_rate_limits(
        cls, rate_limits: dict, source: str = "local_log"
    ) -> dict | None:
        """Normalize trustworthy provider quota fields written by Codex itself."""
        quota = {"source": source}
        # Codex has changed which slot carries the weekly window. Classify by
        # duration rather than assuming that `secondary` always means weekly.
        for window in (rate_limits.get("primary"), rate_limits.get("secondary")):
            if not isinstance(window, dict):
                continue
            used = cls._percent(window.get("used_percent", window.get("usedPercent")))
            try:
                window_minutes = int(
                    window.get("window_minutes", window.get("windowDurationMins")) or 0
                )
            except (TypeError, ValueError):
                window_minutes = 0
            # Codex currently records the weekly window as 10080 minutes. Keep
            # a narrow tolerance so a monthly/other window is never mislabeled.
            if used is not None and 6 * 24 * 60 <= window_minutes <= 8 * 24 * 60:
                weekly = {
                    "used_percent": used,
                    "remaining_percent": 100.0 - used,
                    "window_minutes": window_minutes,
                }
                try:
                    resets_at = int(window.get("resets_at", window.get("resetsAt")) or 0)
                except (TypeError, ValueError):
                    resets_at = 0
                if resets_at > 0:
                    weekly["resets_at"] = resets_at
                quota["weekly"] = weekly

        credits = rate_limits.get("credits")
        if isinstance(credits, dict) and (
            credits.get("has_credits", credits.get("hasCredits")) is True
            or credits.get("unlimited") is True
        ):
            normalized = {"unlimited": credits.get("unlimited") is True}
            balance = credits.get("balance")
            if balance is not None:
                try:
                    normalized["remaining"] = float(balance)
                except (TypeError, ValueError):
                    pass
            if normalized.get("unlimited") or "remaining" in normalized:
                quota["credits"] = normalized

        return quota if len(quota) > 1 else None

    def _observe_quota(self, obj: dict) -> None:
        payload = obj.get("payload") or {}
        rate_limits = payload.get("rate_limits")
        if not isinstance(rate_limits, dict):
            return
        quota = self._quota_from_rate_limits(rate_limits)
        if quota is None:
            return
        dt = parse_ts(obj.get("timestamp", ""))
        timestamp = dt.timestamp() if dt is not None else 0.0
        limit_id = str(rate_limits.get("limit_id") or "")
        if limit_id == "codex" and timestamp >= self._latest_codex_quota_timestamp:
            quota["updated_at"] = obj.get("timestamp") or None
            quota["limit_id"] = "codex"
            limit_name = rate_limits.get("limit_name")
            if limit_name:
                quota["limit_name"] = str(limit_name)
            self._latest_codex_quota = quota
            self._latest_codex_quota_timestamp = timestamp

    def _read_live_account_quota(self) -> dict | None:
        snapshot = read_account_rate_limits()
        if not isinstance(snapshot, dict):
            return None
        quota = self._quota_from_rate_limits(snapshot, source="codex_app_server")
        if quota is None:
            return None
        quota["limit_id"] = "codex"
        limit_name = snapshot.get("limitName")
        if limit_name:
            quota["limit_name"] = str(limit_name)
        return quota

    def collect(self):
        self._latest_codex_quota = None
        self._latest_codex_quota_timestamp = float("-inf")
        self._previous_total_by_path.clear()
        self._project_by_path.clear()
        result = super().collect()
        # The live app-server value matches Codex Settings' "general usage
        # limit". Local logs are only a fallback and only their account-wide
        # `codex` bucket is eligible. Model-specific buckets are never shown.
        quota = self._read_live_account_quota() or self._latest_codex_quota
        weekly = (quota or {}).get("weekly") or {}
        reset = weekly.get("resets_at")
        if reset and reset < time.time():
            quota = None
        if quota is not None:
            result["quota"] = quota
        return result

    def parse_record(self, obj, path):
        if not isinstance(obj, dict):
            return None

        # Quota metadata is useful even on token_count events with no request
        # delta, so observe it before the usage-specific early returns below.
        self._observe_quota(obj)

        rtype = obj.get("type")
        payload = obj.get("payload") or {}
        # Model-carrying events: track the active model for this file, no usage.
        if rtype in ("turn_context", "session_meta"):
            model = self._extract_model(obj)
            if model:
                self._model_by_path[path] = model
            project = payload.get("cwd")
            if project:
                self._project_by_path[path] = str(project)
            return None

        # Token usage events only.
        if rtype != "event_msg":
            return None
        if payload.get("type") != "token_count":
            return None
        info = payload.get("info") or {}
        last = info.get("last_token_usage")
        if not isinstance(last, dict):
            return None

        total = info.get("total_token_usage")
        if isinstance(total, dict):
            total_key = tuple(int(total.get(key, 0) or 0) for key in (
                "input_tokens", "cached_input_tokens", "output_tokens",
                "reasoning_output_tokens",
            ))
            if self._previous_total_by_path.get(path) == total_key:
                return None
            self._previous_total_by_path[path] = total_key

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
        # Codex input_tokens already includes cached_input_tokens. Split it so
        # totals, costs, and cache-hit percentage never count cached input twice.
        uncached_input = max(li - lc, 0)
        cost = (uncached_input / 1e6 * p["in"] + lo / 1e6 * p["out"]
                + lc / 1e6 * p["cache_read"])

        return {
            "dt": dt, "in": uncached_input, "out": lo, "cr": lc, "cw": 0, "reason": lr,
            "cost": cost, "model": report_model, "session": path,
            "project": self._project_by_path.get(path),
        }


register(CodexCollector())
