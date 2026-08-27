"""Engine entrypoint: build the registry, run collectors, emit the contract.

The Tauri tray app calls ``python -m engine --json``. The result is a flat dict
keyed by tool name; each tool holds a ``ranges`` map (today/yesterday/week/
last_week/month/year/all) of token buckets and may expose provider-authored
``quota`` metadata. Metadata keys begin with ``_``:
``_pricing`` is the price table, ``_daily`` is the rolling chart series, and
``_projects`` is a privacy-preserving project summary.
"""
from __future__ import annotations

import importlib
import json
import os
import pkgutil
import sys

from datetime import date, timedelta
from .collectors import base as _base
from .core import pricing
from .contract import to_jsonable
from .core.log import log
from .core.ranges import empty_ranges
from .core.usage import merge_token_day


def _discover_collectors():
    """Import every collector module so it self-registers into the registry."""
    import engine.collectors as pkg
    for mod in pkgutil.iter_modules(pkg.__path__):
        name = mod.name
        if name in ("base", "jsonl", "sqlite", "__init__"):
            continue
        try:
            importlib.import_module(f"{pkg.__name__}.{name}")
        except Exception as e:  # a broken collector module must not kill the engine
            log(f"collector module '{name}' failed to import: {e}")


def _empty_daily(days: int) -> dict:
    """Return a fixed rolling window, oldest first, including zero-use days."""
    today = date.today()
    return {
        (today - timedelta(days=offset)).isoformat(): {
            "in": 0, "out": 0, "cr": 0, "cw": 0, "reason": 0,
            "cost": 0.0, "models": {},
        }
        for offset in range(days - 1, -1, -1)
    }


def _merge_daily(target: dict, source: dict, window_start: str | None) -> None:
    for day, usage in (source or {}).items():
        if window_start is not None and day < window_start:
            continue
        bucket = target.setdefault(
            day,
            {"in": 0, "out": 0, "cr": 0, "cw": 0, "reason": 0,
             "cost": 0.0, "models": {}},
        )
        merge_token_day(bucket, usage)


def _merge_projects(target: dict, source: dict) -> None:
    for project, project_data in (source or {}).items():
        merged = target.setdefault(
            project, {"ranges": empty_ranges(), "tools": set(), "last": None}
        )
        merged["tools"].update(project_data.get("tools", []))
        last = project_data.get("last")
        if last and (merged["last"] is None or last > merged["last"]):
            merged["last"] = last
        for range_name, source_bucket in project_data.get("ranges", {}).items():
            if range_name not in merged["ranges"]:
                continue
            target_bucket = merged["ranges"][range_name]
            merge_token_day(target_bucket, source_bucket)
            sessions = source_bucket.get("sessions")
            if isinstance(sessions, (set, list, tuple)):
                target_bucket["sessions"].update(sessions)


def _day_diff(previous: str, current: str) -> int:
    return (date.fromisoformat(current) - date.fromisoformat(previous)).days


def build_wrapped(payload: dict) -> dict:
    """Build a compact, deterministic summary for the Wrapped view."""
    tools = {key: value for key, value in payload.items()
             if not key.startswith("_")}
    totals = {key: 0 for key in ("in", "out", "cr", "cw", "reason")}
    total_cost = 0.0
    tool_cost: dict[str, float] = {}
    model_cost: dict[str, float] = {}
    for tool_name, tool_data in tools.items():
        all_usage = (tool_data.get("ranges") or {}).get("all") or {}
        for field in totals:
            totals[field] += int(all_usage.get(field, 0) or 0)
        cost = float(all_usage.get("cost", 0.0) or 0.0)
        total_cost += cost
        tool_cost[tool_name] = cost
        for model, model_usage in (all_usage.get("models") or {}).items():
            model_cost[model] = model_cost.get(model, 0.0) + float(
                model_usage.get("cost", 0.0) or 0.0
            )

    daily = payload.get("_daily") or {}
    active_days = sorted(
        day for day, usage in daily.items()
        if (usage.get("cost", 0.0) or 0.0) > 0
        or sum(int(usage.get(k, 0) or 0) for k in totals) > 0
    )
    longest_streak = current_streak = 0
    previous = None
    for day in active_days:
        current_streak = current_streak + 1 if (
            previous is not None and _day_diff(previous, day) == 1
        ) else 1
        longest_streak = max(longest_streak, current_streak)
        previous = day

    return {
        "total_tokens": sum(totals.values()),
        "tot_in": totals["in"], "tot_out": totals["out"],
        "tot_cr": totals["cr"], "tot_cw": totals["cw"],
        "tot_reason": totals["reason"], "total_cost": total_cost,
        "active_tools": sum(1 for value in tool_cost.values() if value > 0),
        "top_tools": [
            {"tool": tool, "cost": cost}
            for tool, cost in sorted(tool_cost.items(), key=lambda item: item[1],
                                     reverse=True)[:5]
        ],
        "top_models": [
            {"model": model, "cost": cost}
            for model, cost in sorted(model_cost.items(), key=lambda item: item[1],
                                      reverse=True)[:5]
        ],
        "top_days": [
            {"date": day, "cost": float(usage.get("cost", 0.0) or 0.0)}
            for day, usage in sorted(
                daily.items(),
                key=lambda item: float(item[1].get("cost", 0.0) or 0.0),
                reverse=True,
            )[:5]
        ],
        "longest_streak": longest_streak,
        "span_days": len(daily),
    }


def build_payload() -> dict:
    _discover_collectors()
    errors: dict = {}
    tools = _base.run_all(errors)
    payload = dict(tools)
    payload["_pricing"] = {
        "models": {**pricing._PRICING_DB, **pricing._OV_MODELS},
        "aliases": pricing._OV_ALIASES,
    }
    daily = _empty_daily(30)
    window_start = min(daily) if daily else None
    projects = {}
    for tool_name, tool_data in tools.items():
        if tool_name.startswith("_"):
            continue
        _merge_daily(daily, tool_data.get("daily", {}), window_start)
        _merge_projects(projects, tool_data.get("projects", {}))
    payload["_daily"] = daily
    payload["_projects"] = projects
    if errors:
        payload["_errors"] = errors
    return payload


def emit(payload: dict):
    json.dump(to_jsonable(payload), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


# --------------------------------------------------------------------------
# Subcommands
# --------------------------------------------------------------------------

def cmd_json(_args):
    emit(build_payload())


def cmd_projects(_args):
    payload = build_payload()
    emit({"projects": payload.get("_projects", {})})


def cmd_daily_costs(_args):
    payload = build_payload()
    emit({"daily": payload.get("_daily", {})})


def cmd_dashboard(_args):
    payload = build_payload()
    emit(payload)


def cmd_wrapped(_args):
    payload = build_payload()
    emit(build_wrapped(payload))


def cmd_quota_detail(_args):
    payload = build_payload()
    grok = payload.get("grok") or {}
    local = grok.get("ranges", {})
    if os.environ.get("TALLY_GROK_QUOTA") != "1":
        emit({
            "live": False,
            "note": "实时配额未开启；当前仅显示本机日志统计。",
            "local": local,
        })
        return
    api_key = os.environ.get("TALLY_GROK_API_KEY") or os.environ.get("XAI_API_KEY")
    if not api_key:
        emit({"live": False, "note": "未配置 xAI API 密钥，回退本机统计。",
              "local": local})
        return
    import urllib.request

    url = os.environ.get("TALLY_GROK_QUOTA_URL", "https://api.x.ai/v1/usage")
    try:
        request = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {api_key}"}
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            remote = json.loads(response.read().decode("utf-8"))
        emit({"live": True, "remote": remote, "local": local})
    except Exception as exc:
        log(f"grok quota fetch failed: {exc}")
        emit({"live": False, "note": "实时配额获取失败，已回退本机统计。",
              "local": local})


def cmd_update_prices(_args):
    """Refresh pricing.json from OpenRouter (network). Best-effort."""
    import urllib.request

    url = "https://openrouter.ai/api/v1/models"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log(f"update-prices failed: {e}")
        sys.exit(1)
    models = {}
    for m in data.get("data", []):
        id_ = m.get("id")
        if not id_:
            continue
        snap = m.get("pricing") or {}
        try:
            models[id_] = {
                "in": float(snap.get("prompt", 0)) * 1_000_000,
                "out": float(snap.get("completion", 0)) * 1_000_000,
                "cache_read": float(snap.get("input_cache_read", 0)) * 1_000_000,
                "cache_write": float(snap.get("input_cache_write", 0)) * 1_000_000,
            }
        except (TypeError, ValueError):
            continue
    from .core.io_util import atomic_write_json
    import os
    from pathlib import Path

    out_path = Path(__file__).resolve().parent.parent / "pricing.json"
    atomic_write_json(str(out_path), {"models": models})
    log(f"wrote {len(models)} models to {out_path}")
