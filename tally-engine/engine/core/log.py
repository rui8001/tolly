"""Lightweight logging to stderr only (never pollute the stdout JSON stream)."""
from __future__ import annotations

import sys


def log(msg):
    try:
        print(f"[tally] {msg}", file=sys.stderr)
    except Exception:
        pass


def warn(msg):
    try:
        print(f"[tally][warn] {msg}", file=sys.stderr)
    except Exception:
        pass
