"""File / IO helpers. Every text open is utf-8; atomic writes use os.replace."""
from __future__ import annotations

import json
import os
import tempfile


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def atomic_write_json(path, data):
    """Write JSON atomically (utf-8) via a temp file + os.replace.

    os.replace works on Windows even when the destination is read-only, so we
    deliberately avoid fcntl-based locking and chmod-then-rewrite patterns.
    """
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def read_text(path, errors="replace"):
    with open(path, "r", encoding="utf-8", errors=errors) as f:
        return f.read()


def sqlite_ro_uri(path):
    """Read-only SQLite URI that never locks the live database."""
    p = os.path.abspath(path)
    if not p.startswith("/"):
        p = "/" + p
    return "file:" + p + "?mode=ro&immutable=1"


def iter_jsonl_files(dirs, recursive=True, suffix=".jsonl"):
    """Yield absolute paths of every *suffix* file under *dirs*."""
    out = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        if recursive:
            for root, _dirs, files in os.walk(d):
                for fn in files:
                    if fn.endswith(suffix):
                        out.append(os.path.join(root, fn))
        else:
            for fn in os.listdir(d):
                if fn.endswith(suffix):
                    out.append(os.path.join(d, fn))
    return out


def iter_lines(path, errors="replace"):
    """Yield decoded, stripped, non-empty lines from a text file (utf-8)."""
    with open(path, "r", encoding="utf-8", errors=errors) as f:
        for line in f:
            line = line.strip()
            if line:
                yield line
