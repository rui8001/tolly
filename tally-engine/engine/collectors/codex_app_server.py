"""Read the account-wide Codex quota through the local Codex app server.

This module deliberately uses the app server's read-only JSON-RPC method.  It
does not inspect ``auth.json`` or browser cookies.  The integration is best
effort because older Codex installations may not expose this experimental
method yet.
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path


def _find_codex_executable() -> str | None:
    configured = os.environ.get("TALLY_CODEX_BIN", "").strip()
    if configured and Path(configured).is_file():
        return configured

    discovered = shutil.which("codex") or shutil.which("codex.exe")
    if discovered:
        return discovered

    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_app_data:
        return None
    install_root = Path(local_app_data) / "OpenAI" / "Codex" / "bin"
    try:
        candidates = sorted(
            install_root.glob("*/codex.exe"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    return str(candidates[0]) if candidates else None


def _account_snapshot(result: dict) -> dict | None:
    """Select only the general ``codex`` bucket, never a model bucket."""
    buckets = result.get("rateLimitsByLimitId")
    if isinstance(buckets, dict):
        snapshot = buckets.get("codex")
        if isinstance(snapshot, dict):
            return snapshot

    # Compatibility with app-server versions that only return one snapshot.
    snapshot = result.get("rateLimits")
    if isinstance(snapshot, dict) and snapshot.get("limitId") == "codex":
        return snapshot
    return None


def _write_message(process, message: dict) -> None:
    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()


def _wait_for_response(
    responses: queue.Queue, request_id: int, deadline: float
) -> dict | None:
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        try:
            line = responses.get(timeout=remaining)
        except queue.Empty:
            return None
        if line is None:
            return None
        try:
            response = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            continue
        if response.get("id") == request_id:
            return response


def _query_app_server(executable: str, timeout: float) -> dict | None:
    """Perform the required two-phase app-server initialization handshake."""
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            [executable, "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )
    except OSError:
        return None

    responses = queue.Queue()

    def read_stdout():
        try:
            for line in process.stdout:
                responses.put(line)
        finally:
            responses.put(None)

    threading.Thread(target=read_stdout, daemon=True).start()
    deadline = time.monotonic() + timeout
    try:
        _write_message(process, {
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {"name": "tolly", "version": "1.2.0"},
                "capabilities": {"experimentalApi": True},
            },
        })
        initialized = _wait_for_response(responses, 1, deadline)
        if not initialized or "result" not in initialized:
            return None
        _write_message(process, {"method": "initialized"})
        _write_message(process, {
            "id": 2,
            "method": "account/rateLimits/read",
            "params": None,
        })
        return _wait_for_response(responses, 2, deadline)
    except (OSError, ValueError, BrokenPipeError):
        return None
    finally:
        try:
            process.terminate()
            process.wait(timeout=1)
        except (OSError, subprocess.SubprocessError):
            try:
                process.kill()
            except OSError:
                pass


def read_account_rate_limits(timeout: float = 6.0) -> dict | None:
    """Return the current account-wide Codex snapshot, or ``None`` on failure."""
    executable = _find_codex_executable()
    if not executable:
        return None
    response = _query_app_server(executable, timeout)
    if not isinstance(response, dict) or not isinstance(response.get("result"), dict):
        return None
    return _account_snapshot(response["result"])
