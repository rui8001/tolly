"""DeepSeek Harness collector.

Source: decompressed ``*.jsonl.zstd`` (and plain ``*.jsonl``) under
``TALLY_DSH_DECOMPRESSED_DIR`` or ``~/.tally/cache/dsh-sessions``.

``handle_zstd = True`` makes the Jsonl base auto-decompress ``.zstd`` files, so
we never import zstandard directly. Each record is ``assistant/message`` (with a
final ``usage``) or ``assistant/chunk`` (a ``usage`` chunk). Cost uses the
official DeepSeek direct prices when available, otherwise the canonical table.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from .base import register
from ..core.log import warn
from ..core.paths import HOME, discover_dirs
from ..core.pricing import _deepseek_official_price, _raw_price
from ..core.ranges import empty_ranges, range_bounds
from ..core.usage import bucket_record
from .jsonl import JsonlCollector


class DeepSeekHarnessCollector(JsonlCollector):
    tool = "deepseek_harness"
    recursive = True
    handle_zstd = True  # base auto-decompresses *.zstd

    def candidate_dirs(self):
        return discover_dirs("TALLY_DSH_DECOMPRESSED_DIR",
                             os.path.join(HOME, ".tally", "cache", "dsh-sessions"))

    def parse_record(self, obj, path):
        if not isinstance(obj, dict):
            return None
        event_type = obj.get("type")
        data = obj.get("data") or {}
        if not isinstance(data, dict):
            return None

        usage = None
        model = ""
        if event_type == "assistant/message":
            usage = data.get("usage")
            message = data.get("message") or {}
            source = message.get("source") or {} if isinstance(message, dict) else {}
            if isinstance(source, dict):
                model = source.get("model") or model
        elif event_type == "assistant/chunk":
            chunk = data.get("chunk") or {}
            if isinstance(chunk, dict) and chunk.get("type") == "usage":
                usage = chunk.get("usage")
        if not isinstance(usage, dict):
            return None

        timestamp = obj.get("time")
        try:
            dt = datetime.fromtimestamp(int(timestamp) / 1000).astimezone()
        except (TypeError, ValueError, OSError, OverflowError):
            return None
        try:
            int(data.get("turn") or 0)
            int(data.get("step") or 0)
        except (TypeError, ValueError):
            return None

        inp = max(int(usage.get("inputTokens", 0) or 0), 0)
        raw_out = max(int(usage.get("outputTokens", 0) or 0), 0)
        cr = max(int(usage.get("cacheReadTokens", 0) or 0), 0)
        cw = max(int(usage.get("cacheWriteTokens", 0) or 0), 0)
        reason = min(max(int(usage.get("reasoningTokens", 0) or 0), 0), raw_out)
        out = raw_out - reason
        if inp + raw_out + cr + cw <= 0:
            return None

        model = str(model or "deepseek-v4-pro")
        price = _deepseek_official_price(model)
        if price is None:
            price = _raw_price(model)
        cost = 0.0
        if price:
            cost = (inp / 1e6 * price["in"] + raw_out / 1e6 * price["out"]
                    + cr / 1e6 * price["cache_read"]
                    + cw / 1e6 * price["cache_write"])
        return {
            "dt": dt, "in": inp, "out": out, "cr": cr, "cw": cw,
            "reason": reason, "cost": cost, "model": model, "session": path,
        }

    def collect(self):
        # iter_jsonl_files only matches ".jsonl"; DeepSeek logs are ".jsonl.zstd",
        # so we walk once here and reuse the base line-reader + bucketing.
        ranges = empty_ranges()
        daily = {}
        projects = {}
        seen = set()
        bounds = range_bounds()
        for d in self.candidate_dirs():
            if not os.path.isdir(d):
                continue
            for root, _dirs, fns in os.walk(d):
                for fn in fns:
                    if not (fn.endswith(".jsonl") or fn.endswith(".zstd")):
                        continue
                    path = os.path.join(root, fn)
                    project = self.project_for(path)
                    project_data = projects.setdefault(
                        project,
                        {"ranges": empty_ranges(), "tools": set(), "last": None},
                    )
                    try:
                        for raw in self._read_lines(path):
                            try:
                                obj = json.loads(raw)
                            except Exception:
                                continue
                            if not isinstance(obj, dict):
                                continue
                            rec = self.parse_record(obj, path)
                            if not rec:
                                continue
                            identity = self.record_identity(obj, rec)
                            if identity is not None:
                                if identity in seen:
                                    continue
                                seen.add(identity)
                            dt = rec.get("dt")
                            kwargs = {
                                "inp": rec.get("in", 0), "out": rec.get("out", 0),
                                "cr": rec.get("cr", 0), "cw": rec.get("cw", 0),
                                "reason": rec.get("reason", 0),
                                "cost": rec.get("cost", 0),
                                "model": rec.get("model"),
                                "session": rec.get("session"),
                            }
                            bucket_record(ranges, bounds, dt, daily=daily, **kwargs)
                            project_data["tools"].add(self.tool)
                            bucket_record(project_data["ranges"], bounds, dt, **kwargs)
                            if dt is not None:
                                day = dt.date().isoformat()
                                if (project_data["last"] is None
                                        or day > project_data["last"]):
                                    project_data["last"] = day
                    except Exception as e:
                        warn(f"{self.tool}: cannot scan {path}: {e}")
        return {
            "ranges": ranges,
            "daily": daily,
            "projects": {
                key: {"ranges": value["ranges"],
                      "tools": sorted(value["tools"]), "last": value["last"]}
                for key, value in projects.items()
            },
        }


register(DeepSeekHarnessCollector())
