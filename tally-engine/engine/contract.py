"""Output contract serialization.

The engine builds nested dicts that contain ``set`` objects (sessions) and
``datetime`` values. This module converts them to plain JSON-compatible data
before emission, so callers (the Tauri tray app) always receive lists/strings.
"""
from __future__ import annotations

import datetime


def _jsonable(v):
    if isinstance(v, set):
        return sorted(v)
    if isinstance(v, dict):
        return {k: _jsonable(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, datetime.datetime):
        return v.isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    return v


def to_jsonable(result):
    """Recursively convert a result tree into JSON-safe structures."""
    return _jsonable(result)
