"""QwenWork (千问办公) local transcript collector.

The desktop app stores Qoder-compatible JSONL transcripts under
``~/.qwenworkcn/projects``. Those records do not expose provider token
accounting, so values are explicitly marked as local estimates.
"""
from __future__ import annotations

import json as _json
import http.client
import math
import os
import re
from urllib.parse import urlsplit

from .base import register
from .jsonl import JsonlCollector
from .qodercli import _est_tokens
from ..core.paths import HOME, discover_dirs
from ..core.ranges import parse_ts

_CONFIG_MAX_BYTES = 16 * 1024
_RESPONSE_MAX_BYTES = 1024 * 1024
_TOKEN_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(number, 0.0) if math.isfinite(number) else None


def _read_mcp_config(path):
    try:
        if os.path.islink(path) or not os.path.isfile(path):
            return None
        if not 0 < os.path.getsize(path) <= _CONFIG_MAX_BYTES:
            return None
        with open(path, "r", encoding="utf-8") as handle:
            config = _json.load(handle)
    except (OSError, ValueError, _json.JSONDecodeError):
        return None
    if not isinstance(config, dict):
        return None
    url, token = config.get("url"), config.get("token")
    if not isinstance(url, str) or not isinstance(token, str):
        return None
    try:
        parsed = urlsplit(url.strip())
        port = parsed.port
    except ValueError:
        return None
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or parsed.username is not None or parsed.password is not None
            or port is None or not 1 <= port <= 65535
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        return None
    token = token.strip()
    return {"port": port, "token": token} if _TOKEN_RE.fullmatch(token) else None


def _mcp_usage_data(payload):
    if not isinstance(payload, dict):
        return None
    result = payload.get("result")
    if not isinstance(result, dict):
        return None
    envelope = result.get("structuredContent")
    if not isinstance(envelope, dict):
        for item in result.get("content") or []:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str):
                continue
            try:
                candidate = _json.loads(item["text"])
            except (TypeError, ValueError, _json.JSONDecodeError):
                continue
            if isinstance(candidate, dict):
                envelope = candidate
                break
    if (not isinstance(envelope, dict) or envelope.get("ok") is False
            or envelope.get("key") not in (None, "qwenwork.usage")):
        return None
    data = envelope.get("data")
    return data if isinstance(data, dict) else None


def _quota_from_mcp_usage(data):
    if not isinstance(data, dict) or data.get("available") is False:
        return None
    segments = data.get("segments")
    if not isinstance(segments, list):
        segments = [data.get("planCredits"), data.get("addOnCredits")]
    balances = []
    totals = []
    resets = []
    for segment in segments[:8]:
        if not isinstance(segment, dict):
            continue
        unit = str(segment.get("unit") or "").lower()
        kind = str(segment.get("kind") or "").lower()
        if unit not in ("credit", "credits") and "credit" not in kind:
            continue
        remaining = _number(segment.get("remaining"))
        total = _number(segment.get("total"))
        if remaining is not None:
            balances.append(remaining)
        if total is not None and total > 0:
            totals.append(total)
        reset = _number(segment.get("renewsAt", segment.get("renews_at")))
        if reset is not None:
            resets.append(reset / 1000 if reset > 1_000_000_000_000 else reset)
    if not balances:
        fallback = _number(data.get("remaining", data.get("balance")))
        if fallback is not None:
            balances.append(fallback)
    if not balances:
        return None
    credits = {"remaining": sum(balances)}
    if totals:
        credits["total"] = sum(totals)
    if resets:
        credits["resets_at"] = min(resets)
    return {"source": "qwenwork_mcp", "credits": credits}


def _fetch_mcp_quota(config):
    body = _json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "qw_query", "arguments": {"key": "qwenwork.usage"}},
    }, separators=(",", ":")).encode("utf-8")
    connection = http.client.HTTPConnection("127.0.0.1", config["port"], timeout=3)
    try:
        connection.request("POST", "/", body=body, headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": "Tolly",
            "x-api-key": config["token"],
        })
        response = connection.getresponse()
        if response.status != 200:
            return None
        raw = response.read(_RESPONSE_MAX_BYTES + 1)
        if len(raw) > _RESPONSE_MAX_BYTES:
            return None
        text = raw.decode("utf-8")
        if "text/event-stream" in (response.getheader("Content-Type") or "").lower():
            candidates = [line[5:].strip() for line in text.splitlines()
                          if line.startswith("data:") and line[5:].strip()]
            payload = _json.loads(candidates[0]) if candidates else None
        else:
            payload = _json.loads(text)
        return _quota_from_mcp_usage(_mcp_usage_data(payload))
    except (OSError, ValueError, _json.JSONDecodeError):
        return None
    finally:
        connection.close()


class QwenWorkCollector(JsonlCollector):
    tool = "qwenwork"
    recursive = True

    def __init__(self):
        super().__init__()
        self._model_by_path: dict[str, str] = {}

    def candidate_dirs(self):
        return discover_dirs(
            "TALLY_QWENWORK_DIR", os.path.join(HOME, ".qwenworkcn", "projects")
        )

    def collect(self):
        roots = self.candidate_dirs()
        result = super().collect()
        result["estimated"] = True
        result["detected"] = bool(roots)
        result["note"] = "Token 来自本地对话文本估算，不是服务商账单"
        if os.environ.get("TALLY_QWENWORK_QUOTA") == "1":
            config = _read_mcp_config(os.path.join(HOME, ".qwenworkcn", "mcp-adaptor.config"))
            quota = _fetch_mcp_quota(config) if config else None
            if quota:
                result["quota"] = quota
        return result

    def parse_record(self, obj, path):
        if not isinstance(obj, dict):
            return None
        typ = obj.get("type")
        if typ == "runtime-config":
            model = obj.get("model")
            if model:
                self._model_by_path[path] = str(model)
            return None
        if typ not in ("user", "assistant"):
            return None

        dt = parse_ts(obj.get("timestamp") or "")
        if dt is None:
            return None
        content = (obj.get("message") or {}).get("content")
        estimated = 0.0
        if typ == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type")
                if block_type == "tool_use":
                    try:
                        estimated += _est_tokens(_json.dumps(
                            block.get("input") or {}, ensure_ascii=False
                        ))
                    except (TypeError, ValueError):
                        pass
                elif block_type in ("text", "thinking"):
                    estimated += _est_tokens(block.get(block_type))
        elif typ == "user" and not obj.get("isMeta") and not obj.get("isSidechain"):
            if isinstance(content, str) and content and not content.startswith("<"):
                estimated += _est_tokens(content)

        if estimated <= 0:
            return None
        return {
            "dt": dt.astimezone(),
            "in": int(round(estimated)),
            "out": 0,
            "cr": 0,
            "cw": 0,
            "reason": 0,
            "cost": 0.0,
            "model": self._model_by_path.get(path) or "qwenwork",
            "session": path,
            "project": obj.get("cwd"),
        }


register(QwenWorkCollector())
