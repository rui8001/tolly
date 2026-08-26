"""Base collector for JSONL session logs (the most common source type).

Subclasses implement :meth:`candidate_dirs` and :meth:`parse_record`. The base
handles directory walking, optional ``.zstd`` decompression (via the *optional*
``zstandard`` dependency — a missing import yields a clear warning, never a
silent data drop), JSON parsing, and range bucketing.
"""
from __future__ import annotations

import json
import os

from .base import Collector
from ..core.io_util import iter_jsonl_files
from ..core.log import warn
from ..core.ranges import empty_ranges, range_bounds
from ..core.usage import bucket_record

_ZSTD_WARNED = False


def _maybe_decompress_zstd(raw: bytes):
    """Decompress ``.zstd`` bytes if zstandard is available, else warn + return None."""
    global _ZSTD_WARNED
    try:
        import zstandard  # optional dependency
    except ImportError:
        if not _ZSTD_WARNED:
            warn("zstandard not installed; .zstd logs (DeepSeek harness, Claude quota) "
                 "will be skipped. Run: pip install zstandard")
            _ZSTD_WARNED = True
        return None
    try:
        return zstandard.ZstdDecompressor().decompress(raw, max_output_size=len(raw) * 50)
    except Exception:
        return None


class JsonlCollector(Collector):
    recursive: bool = True
    handle_zstd: bool = False  # when True, *.zstd files are decompressed

    def candidate_dirs(self) -> list[str]:
        raise NotImplementedError

    def parse_record(self, obj: dict, path: str) -> dict | None:
        """Return a flat record ``{dt, in, out, cr, cw, reason, cost, model, session}``
        or ``None`` to skip the line."""
        raise NotImplementedError

    def project_for(self, path: str) -> str:
        """Return a stable local project key without exposing the full path."""
        parent = os.path.dirname(path)
        name = os.path.basename(parent) or "未知项目"
        if name in {"subagents", "archived_sessions", "agents"}:
            name = os.path.basename(os.path.dirname(parent)) or name
        return name

    def record_identity(self, obj: dict, record: dict):
        """Optional replay identity. Subclasses can return a hashable value."""
        return record.get("_dedupe")

    def _read_lines(self, path: str):
        if self.handle_zstd and path.endswith(".zstd"):
            with open(path, "rb") as f:
                data = _maybe_decompress_zstd(f.read())
            if data is None:
                return
            text = data.decode("utf-8", errors="replace")
            for line in text.splitlines():
                line = line.strip()
                if line:
                    yield line
            return
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield line

    def collect(self) -> dict:
        ranges = empty_ranges()
        daily = {}
        projects = {}
        seen = set()
        bounds = range_bounds()
        for path in iter_jsonl_files(self.candidate_dirs(), recursive=self.recursive):
            try:
                lines = self._read_lines(path)
            except Exception as e:
                warn(f"{self.tool}: cannot read {path}: {e}")
                continue
            project = self.project_for(path)
            project_data = projects.setdefault(
                project, {"ranges": empty_ranges(), "tools": set(), "last": None}
            )
            try:
                for raw in lines:
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
                    bucket_record(
                        ranges, bounds, dt,
                        inp=rec.get("in", 0), out=rec.get("out", 0),
                        cr=rec.get("cr", 0), cw=rec.get("cw", 0),
                        reason=rec.get("reason", 0), cost=rec.get("cost", 0),
                        model=rec.get("model"), session=rec.get("session"), daily=daily,
                    )
                    project_data["tools"].add(self.tool)
                    bucket_record(
                        project_data["ranges"], bounds, dt,
                        inp=rec.get("in", 0), out=rec.get("out", 0),
                        cr=rec.get("cr", 0), cw=rec.get("cw", 0),
                        reason=rec.get("reason", 0), cost=rec.get("cost", 0),
                        model=rec.get("model"), session=rec.get("session"),
                    )
                    if dt is not None:
                        day = dt.date().isoformat()
                        if project_data["last"] is None or day > project_data["last"]:
                            project_data["last"] = day
            except Exception as e:
                warn(f"{self.tool}: cannot scan {path}: {e}")
                continue
        result = {"ranges": ranges, "daily": daily}
        if projects:
            result["projects"] = {
                key: {"ranges": value["ranges"],
                      "tools": sorted(value["tools"]), "last": value["last"]}
                for key, value in projects.items()
            }
        return result
