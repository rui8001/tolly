"""Model-name normalization and price resolution.

Local model names are normalized to canonical ids, then priced from
(in priority order) local overrides,
the OpenRouter ``pricing.json`` baseline, and a small built-in fallback table.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

_HERE = Path(__file__).resolve().parent
PRICING_FILE = os.environ.get("TALLY_PRICING_FILE") or str(_HERE.parent.parent / "pricing.json")
OVERRIDES_FILE = os.environ.get("TALLY_PRICING_OVERRIDES") or str(_HERE.parent.parent / "pricing_overrides.json")

# Built-in fallback so the engine prices known models even with no pricing.json.
_DEFAULT_PRICES = {
    "anthropic/claude-opus-4.8":     {"in": 5.0,   "out": 25.0, "cache_read": 0.5,    "cache_write": 6.25},
    "anthropic/claude-sonnet-4.6":   {"in": 3.0,   "out": 15.0, "cache_read": 0.3,    "cache_write": 3.75},
    "anthropic/claude-haiku-4.5":    {"in": 1.0,   "out": 5.0,  "cache_read": 0.1,    "cache_write": 1.25},
    "openai/gpt-5.5":                {"in": 5.0,   "out": 30.0, "cache_read": 0.5,    "cache_write": 0.0},
    "qwen/qwen3.7-max":              {"in": 1.25,  "out": 3.75, "cache_read": 0.25,   "cache_write": 1.5625},
    "deepseek/deepseek-v4-pro":      {"in": 0.435, "out": 0.87, "cache_read": 0.0036, "cache_write": 0.0},
    "google/gemini-3.5-flash":       {"in": 1.5,   "out": 9.0,  "cache_read": 0.15,   "cache_write": 0.0833},
    "google/gemini-3.1-pro-preview": {"in": 2.0,   "out": 12.0, "cache_read": 0.2,    "cache_write": 0.375},
    "x-ai/grok-4.5":                 {"in": 2.0,   "out": 6.0,  "cache_read": 0.3,    "cache_write": 0.0},
    "tencent/hy3":                   {"in": 0.14,  "out": 0.58, "cache_read": 0.035,  "cache_write": 0.0},
    "tencent/hy3-preview":           {"in": 0.063, "out": 0.21, "cache_read": 0.021,  "cache_write": 0.0},
}

# DeepSeek Harness routes via official direct prices, not OpenRouter channel prices.
_DEEPSEEK_OFFICIAL_PRICES = {
    "deepseek-v4-pro":   {"in": 0.435, "out": 0.87, "cache_read": 0.003625, "cache_write": 0.0},
    "deepseek-v4-flash": {"in": 0.14,  "out": 0.28, "cache_read": 0.0028,   "cache_write": 0.0},
}

# Family keyword -> representative canonical id (fallback when exact match fails).
_FAMILY = [
    ("opus",     "anthropic/claude-opus-4.8"),
    ("sonnet",   "anthropic/claude-sonnet-4.6"),
    ("haiku",    "anthropic/claude-haiku-4.5"),
    ("gpt-5",    "openai/gpt-5.5"),
    ("qwen",     "qwen/qwen3.7-max"),
    ("deepseek", "deepseek/deepseek-v4-pro"),
    ("glm",      "z-ai/glm-5.2"),
    ("mimo",     "xiaomi/mimo-v2.5-pro"),
    ("hy3",      "tencent/hy3"),
]


def _deepseek_official_price(model):
    normalized = normalize(model) or ""
    model_id = normalized.rsplit("/", 1)[-1]
    price = _DEEPSEEK_OFFICIAL_PRICES.get(model_id)
    return dict(price) if price else None


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


_PRICING_DB = _load_json(PRICING_FILE, {}).get("models", {})
_OVERRIDES = _load_json(OVERRIDES_FILE, {})
_OV_MODELS = _OVERRIDES.get("models", {})
_OV_ALIASES = _OVERRIDES.get("aliases", {})


def normalize(model: str):
    """Local model name -> OpenRouter canonical id. Free tier ':free' priced as base."""
    m = (model or "").strip().lower()
    if not m or m == "<synthetic>":
        return None
    m = re.sub(r"\s+", "-", m)
    m = re.sub(r"[:\-]free$", "", m)
    if "/" in m:
        return m
    if m.startswith("claude"):
        m = re.sub(r"-(\d+)-(\d+)$", r"-\1.\2", m)
        return "anthropic/" + m
    if re.match(r"(gpt|o\d|chatgpt)", m):
        return "openai/" + m
    if m.startswith("gemini"):
        return "google/" + m
    if m.startswith("grok"):
        return "x-ai/" + m
    if m.startswith("qwen"):
        return "qwen/" + m
    if m.startswith("deepseek"):
        return "deepseek/" + m
    if m.startswith("glm"):
        return "z-ai/" + m
    if m.startswith("mimo"):
        return "xiaomi/" + m
    if m == "hy3":
        return "tencent/hy3"
    if m in ("hy3-preview", "hy3 preview"):
        return "tencent/hy3-preview"
    return m


def _resolve_id(model: str):
    """Resolve to a canonical id; unknown falls back to opus (conservative)."""
    s = (model or "").strip()
    if not s or s.lower() == "<synthetic>":
        return None
    if s in _OV_ALIASES:
        return _OV_ALIASES[s]
    norm = normalize(model)
    if norm and (norm in _OV_MODELS or norm in _PRICING_DB or norm in _DEFAULT_PRICES):
        return norm
    low = s.lower()
    if "gemini" in low:
        return "google/gemini-3.1-pro-preview" if "pro" in low else "google/gemini-3.5-flash"
    for kw, rep in _FAMILY:
        if kw in low:
            return rep
    return "anthropic/claude-opus-4.8"


def _known_id_or_raw(model: str):
    """Canonical priced id when known, preserving unknown raw names otherwise."""
    s = (model or "").strip()
    if not s or s.lower() == "<synthetic>":
        return None
    if s in _OV_ALIASES:
        return _OV_ALIASES[s]
    norm = normalize(s)
    if norm and (norm in _OV_MODELS or norm in _PRICING_DB or norm in _DEFAULT_PRICES):
        return norm
    low = s.lower()
    if "gemini" in low:
        return "google/gemini-3.1-pro-preview" if "pro" in low else "google/gemini-3.5-flash"
    for keyword, representative in _FAMILY:
        if keyword in low:
            return representative
    return s


def _has_known_price(model: str):
    return pricing_id(model) is not None


def pricing_id(model: str):
    canonical = _known_id_or_raw(model)
    if canonical and (canonical in _OV_MODELS or canonical in _PRICING_DB or canonical in _DEFAULT_PRICES):
        return canonical
    normalized = normalize(model)
    if normalized == "z-ai/glm-5.2" and "z-ai/glm-5.1" in _PRICING_DB:
        return "z-ai/glm-5.1"
    return None


def _raw_price(model: str):
    """Unified price lookup -> {in,out,cache_read,cache_write,write1h?}. <synthetic> -> zeros."""
    cid = _resolve_id(model)
    if cid is None:
        return {"in": 0.0, "out": 0.0, "cache_read": 0.0, "cache_write": 0.0}
    p = dict(_DEFAULT_PRICES.get(cid, {}))
    p.update(_PRICING_DB.get(cid, {}))
    p.update(_OV_MODELS.get(cid, {}))
    out = {"in": p.get("in", 0.0), "out": p.get("out", 0.0),
           "cache_read": p.get("cache_read", 0.0), "cache_write": p.get("cache_write", 0.0)}
    if "write1h" in p:
        out["write1h"] = p["write1h"]
    elif cid.startswith("anthropic/"):
        out["write1h"] = out["in"] * 2
    return out


def price_for(model: str):
    """Claude cost: adds write5m (=cache_write) and write1h tiers."""
    p = _raw_price(model)
    return {"in": p["in"], "out": p["out"], "cache_read": p["cache_read"],
            "write5m": p["cache_write"], "write1h": p.get("write1h", p["cache_write"])}


def gemini_price(model: str):
    """Gemini cost: unified lookup (OpenRouter is versioned, more accurate than regex)."""
    return _raw_price(model)


def nice_model(m: str) -> str:
    """claude-opus-4-7 -> Opus 4.7; <synthetic> -> 合成; strips prefix/-free/-preview."""
    if not m or m == "<synthetic>":
        return "合成"
    if m == "unknown":
        return "未知"
    s = m.lower()
    for key, disp in (("opus", "Opus"), ("sonnet", "Sonnet"), ("haiku", "Haiku")):
        if key in s:
            mt = re.search(r"(\d+)-(\d+)", s)
            return f"{disp} {mt.group(1)}.{mt.group(2)}" if mt else disp
    if "gpt" in s:
        mt = re.search(r"gpt[- ]?(\d+(?:\.\d+)?)", s)
        version = mt.group(1) if mt else ""
        variant_labels = []
        for token, label in (("sol", "Sol"), ("luna", "Luna"), ("terra", "Terra"),
                             ("mini", "Mini"), ("pro", "Pro")):
            if re.search(rf"(?:^|[-_/ ]){token}(?:$|[-_/ ])", s):
                variant_labels.append(label)
        suffix = f" {' '.join(variant_labels)}" if variant_labels else ""
        return f"GPT-{version}{suffix}" if version else "GPT"
    if "mimo" in s:
        name = m.split("/")[-1]
        version = re.sub(r"^mimo[- ]?v?", "", name, flags=re.I).strip()
        parts = [part for part in version.split("-") if part]
        if not parts:
            return "MiMo"
        head = "MiMo-V" + parts[0] if parts[0][0].isdigit() else "MiMo-" + parts[0]
        return "-".join([head] + [part.capitalize() for part in parts[1:]])
    name = re.sub(r"[-:](free|preview|latest)$", "", m.split("/")[-1]).replace("-", " ")
    return " ".join(w[:1].upper() + w[1:] if w[:1].isalpha() else w
                    for w in name.split())
