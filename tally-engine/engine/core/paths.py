"""Cross-platform path discovery.

Uses environment-variable overrides plus per-platform candidate lists. Every
collector builds its own candidate list and calls ``discover_dirs`` /
``discover_file``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HOME = str(Path.home())
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def _expand(path):
    if not path:
        return None
    value = os.fspath(path).strip()
    if not value:
        return None
    return os.path.abspath(os.path.expandvars(os.path.expanduser(value)))


def path_candidates(env_name, *defaults):
    """Return deduplicated, expanded candidate paths.

    ``env_name`` (if set) is a ``pathsep``-separated list of overrides that
    takes precedence over ``defaults``.
    """
    values = []
    configured = os.environ.get(env_name, "")
    if configured:
        values.extend(configured.split(os.pathsep))
    values.extend(defaults)
    result = []
    seen = set()
    for value in values:
        path = _expand(value)
        if not path:
            continue
        key = os.path.normcase(os.path.realpath(path))
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def first_existing_file(paths):
    for p in paths:
        if os.path.isfile(p):
            return p
    return None


def existing_dirs(paths):
    result = []
    seen = set()
    for p in paths:
        if not os.path.isdir(p):
            continue
        real = os.path.realpath(p)
        key = os.path.normcase(real)
        if key not in seen:
            seen.add(key)
            result.append(real)
    return result


def discover_dirs(env_name, *defaults):
    """All existing directories from the candidate list."""
    return existing_dirs(path_candidates(env_name, *defaults))


def discover_file(env_name, *defaults):
    return first_existing_file(path_candidates(env_name, *defaults))


def app_support_dir(*sub):
    """Cross-platform config base: APPDATA / ~/Library/Application Support / XDG."""
    if IS_WIN:
        base = os.environ.get("APPDATA", "")
    elif IS_MAC:
        base = os.path.join(HOME, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
    return os.path.join(base, *sub) if sub else base


def local_data_dir(*sub):
    """Cross-platform local-data base: LOCALAPPDATA / ~/Library/Application Support / XDG."""
    if IS_WIN:
        base = os.environ.get("LOCALAPPDATA", "")
    elif IS_MAC:
        base = os.path.join(HOME, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(HOME, ".local", "share")
    return os.path.join(base, *sub) if sub else base
