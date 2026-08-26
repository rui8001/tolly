"""Qoder CLI collector.

Source
------
``~/.qoder/projects/<project>/*.jsonl`` plus its ``transcript/`` and
``*/subagents/`` subdirectories (cross-platform; only the HOME root differs).

Each line is a transcript event (``type`` in ``{runtime-config, user,
assistant}``). Qoder's logs expose **no real token accounting**, so this
collector uses a CJK-aware token *estimate* (``est``). We map that estimate
into the ``in`` bucket (total estimated tokens) and leave ``out``/``cr``/``cw``/
``cost`` at zero. Model is read from the
``runtime-config`` event and tracked per file.
"""
from __future__ import annotations

import json as _json
import os

from .base import register
from ..core.paths import HOME, discover_dirs
from ..core.ranges import parse_ts
from .jsonl import JsonlCollector


def _est_tokens(text) -> float:
    """CJK-aware estimate: CJK/fullwidth ~= 1 token; other chars ~= 1/4 token."""
    if not text:
        return 0.0
    cjk = sum(1 for ch in text
              if "\u3000" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef")
    return cjk + (len(text) - cjk) / 4


class QoderCliCollector(JsonlCollector):
    tool = "qodercli"
    recursive = True

    def __init__(self):
        super().__init__()
        self._model_by_path: dict[str, str] = {}

    def candidate_dirs(self):
        return discover_dirs("TALLY_QODERCLI_DIR", os.path.join(HOME, ".qoder", "projects"))

    def parse_record(self, obj, path):
        if not isinstance(obj, dict):
            return None

        typ = obj.get("type")
        if typ == "runtime-config":
            m = obj.get("model")
            if m:
                self._model_by_path[path] = m
            return None
        if typ not in ("user", "assistant"):
            return None

        dt = parse_ts(obj.get("timestamp") or "")
        if dt is None:
            return None
        dt = dt.astimezone()

        model = self._model_by_path.get(path) or "unknown"
        content = (obj.get("message") or {}).get("content")
        est = 0.0
        if typ == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                bt = block.get("type")
                if bt == "tool_use":
                    try:
                        est += _est_tokens(_json.dumps(block.get("input") or {},
                                                       ensure_ascii=False))
                    except (TypeError, ValueError):
                        pass
                elif bt in ("text", "thinking"):
                    est += _est_tokens(block.get(bt))
        elif typ == "user" and not obj.get("isMeta") and not obj.get("isSidechain"):
            if isinstance(content, str) and content and not content.startswith("<"):
                est += _est_tokens(content)

        if est <= 0:
            return None
        return {
            "dt": dt, "in": int(round(est)), "out": 0, "cr": 0, "cw": 0,
            "reason": 0, "cost": 0.0, "model": model, "session": path,
        }


register(QoderCliCollector())
