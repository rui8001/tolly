"""Collector protocol and the run orchestration.

Each AI-coding tool is a :class:`Collector` that returns its own result dict
(with a ``ranges`` key). ``run_all`` executes every registered collector in
isolation so one tool's failure never blanks the whole report.
"""
from __future__ import annotations

from ..core.ranges import empty_ranges
from ..core.log import warn


class Collector:
    tool: str = "unknown"

    def collect(self) -> dict:
        raise NotImplementedError

    # Convenience for subclasses that only produce token ranges.
    def empty_result(self, extra=None):
        return {"ranges": empty_ranges(extra), "daily": {}, "projects": {}}


# Registry filled by importing collector modules (they self-register).
REGISTRY: list["Collector"] = []


def register(instance: "Collector") -> "Collector":
    REGISTRY.append(instance)
    return instance


def run_all(errors: dict) -> dict:
    """Run every collector; capture per-tool failures into *errors*."""
    out: dict = {}
    for c in REGISTRY:
        try:
            res = c.collect()
            if res is not None:
                out[c.tool] = res
        except Exception as e:  # isolation: never let one tool break the rest
            warn(f"{c.tool} collector failed: {e}")
            errors[c.tool] = str(e)
    return out
