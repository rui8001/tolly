"""Hermes collector.

Source: ``~/.hermes/state.db`` (env ``TALLY_HERMES_DB``) plus every
``~/.hermes/profiles/*/state.db``. Several DBs are unioned: each is scanned
independently and the resulting ranges are merged.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime

from .base import register
from .sqlite import SqliteCollector
from ..core.paths import HOME
from ..core.ranges import classify, empty_ranges, range_bounds
from ..core.usage import add_model_usage
from ..core.io_util import sqlite_ro_uri


def _merge_ranges(dst, src):
    dr = dst["ranges"]
    sr = src.get("ranges", {})
    for k in dr:
        sb = sr.get(k)
        if not sb:
            continue
        db = dr[k]
        for f in ("in", "out", "cr", "cw", "reason", "cost",
                  "tasks", "completed", "failed", "calls",
                  "sub_agents", "duration", "turns", "ctx_sum", "ctx_count"):
            if f in sb:
                db[f] = db.get(f, 0) + sb[f]
        for mn, mv in (sb.get("models") or {}).items():
            mm = db["models"].setdefault(
                mn, {"in": 0, "out": 0, "cr": 0, "cw": 0, "reason": 0, "cost": 0.0})
            for f in ("in", "out", "cr", "cw", "reason", "cost"):
                mm[f] += mv.get(f, 0)
        s = db.get("sessions")
        if isinstance(s, set):
            s.update(sb.get("sessions") or [])
        elif isinstance(s, (int, float)):
            db["sessions"] = s + (sb.get("sessions") or 0)
    return dst


class HermesCollector(SqliteCollector):
    tool = "hermes"

    def candidate_dbs(self):
        cands = []
        env = os.environ.get("TALLY_HERMES_DB")
        if env:
            cands.append(os.path.expanduser(env))
        cands.append(os.path.expanduser(
            os.path.join(HOME, ".hermes", "state.db")))
        prof = os.path.join(HOME, ".hermes", "profiles")
        if os.path.isdir(prof):
            for p in os.listdir(prof):
                db = os.path.join(prof, p, "state.db")
                if os.path.isfile(db):
                    cands.append(db)
        return cands

    def query(self, conn):
        ranges = empty_ranges()
        bounds = range_bounds()
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "sessions" not in tables:
            return {"ranges": ranges}

        def columns(table):
            return {row[1] for row in conn.execute(
                f'PRAGMA table_info("{table}")')}

        def expr(alias, available, name, fallback="0"):
            return f'{alias}."{name}"' if name in available else fallback

        session_columns = columns("sessions")
        session_query = f"""
            SELECT s.id AS session_id,
                   {expr('s', session_columns, 'started_at')} AS started_at,
                   {expr('s', session_columns, 'model', "''")} AS model,
                   {expr('s', session_columns, 'input_tokens')} AS input_tokens,
                   {expr('s', session_columns, 'output_tokens')} AS output_tokens,
                   {expr('s', session_columns, 'cache_read_tokens')} AS cache_read_tokens,
                   {expr('s', session_columns, 'cache_write_tokens')} AS cache_write_tokens,
                   {expr('s', session_columns, 'reasoning_tokens')} AS reasoning_tokens,
                   {expr('s', session_columns, 'estimated_cost_usd')} AS estimated_cost_usd,
                   {expr('s', session_columns, 'actual_cost_usd', 'NULL')} AS actual_cost_usd
            FROM sessions s
        """
        sessions = {row["session_id"]: dict(row)
                    for row in conn.execute(session_query)}

        usage_rows = {}
        for table in ("session_model_usage_v21", "session_model_usage"):
            if table not in tables:
                continue
            usage_columns = columns(table)
            if "session_id" not in usage_columns:
                continue
            usage_query = f"""
                SELECT u.session_id AS session_id,
                       {expr('u', usage_columns, 'model', "''")} AS model,
                       {expr('u', usage_columns, 'billing_provider', "''")} AS billing_provider,
                       {expr('u', usage_columns, 'billing_base_url', "''")} AS billing_base_url,
                       {expr('u', usage_columns, 'billing_mode', "''")} AS billing_mode,
                       {expr('u', usage_columns, 'task', "''")} AS task,
                       {expr('u', usage_columns, 'input_tokens')} AS input_tokens,
                       {expr('u', usage_columns, 'output_tokens')} AS output_tokens,
                       {expr('u', usage_columns, 'cache_read_tokens')} AS cache_read_tokens,
                       {expr('u', usage_columns, 'cache_write_tokens')} AS cache_write_tokens,
                       {expr('u', usage_columns, 'reasoning_tokens')} AS reasoning_tokens,
                       {expr('u', usage_columns, 'estimated_cost_usd')} AS estimated_cost_usd,
                       {expr('u', usage_columns, 'actual_cost_usd', 'NULL')} AS actual_cost_usd,
                       {expr('u', usage_columns, 'first_seen', 'NULL')} AS first_seen,
                       {expr('u', usage_columns, 'last_seen', 'NULL')} AS last_seen
                FROM "{table}" u
            """
            for row in conn.execute(usage_query):
                item = dict(row)
                key = tuple(item.get(name) or "" for name in (
                    "session_id", "model", "billing_provider", "billing_base_url",
                    "billing_mode", "task"))
                previous = usage_rows.get(key)
                if previous and _token_total({
                        "in": previous.get("input_tokens", 0),
                        "out": previous.get("output_tokens", 0),
                        "cr": previous.get("cache_read_tokens", 0),
                        "cw": previous.get("cache_write_tokens", 0),
                        "reason": previous.get("reasoning_tokens", 0),
                }) > _token_total({
                        "in": item.get("input_tokens", 0),
                        "out": item.get("output_tokens", 0),
                        "cr": item.get("cache_read_tokens", 0),
                        "cw": item.get("cache_write_tokens", 0),
                        "reason": item.get("reasoning_tokens", 0),
                }):
                    continue
                usage_rows[key] = item

        records = list(usage_rows.values())
        main_usage_sessions = {
            row.get("session_id") for row in records if not (row.get("task") or "")}

        for session_id, session in sessions.items():
            if session_id in main_usage_sessions:
                continue
            records.append({
                **session,
                "task": "",
                "first_seen": session.get("started_at"),
                "last_seen": session.get("started_at"),
            })

        def row_cost(row):
            actual = row.get("actual_cost_usd")
            return float(actual if actual is not None
                         else row.get("estimated_cost_usd", 0) or 0)

        records_by_session = {}
        for row in records:
            records_by_session.setdefault(row.get("session_id"), []).append(row)
        for session_id, session_records in records_by_session.items():
            session = sessions.get(session_id)
            if not session or any(row_cost(row) for row in session_records):
                continue
            fallback_cost = row_cost(session)
            if not fallback_cost:
                continue
            main_records = [row for row in session_records
                            if not (row.get("task") or "")]
            if not main_records:
                continue
            target = next(
                (row for row in main_records
                 if row.get("model") == session.get("model")),
                main_records[0])
            target["actual_cost_usd"] = session.get("actual_cost_usd")
            target["estimated_cost_usd"] = session.get("estimated_cost_usd")

        session_first_seen = {}
        for row in records:
            session_id = row.get("session_id")
            if not session_id:
                continue
            session = sessions.get(session_id) or {}
            timestamp = (session.get("started_at")
                         or row.get("first_seen") or row.get("last_seen"))
            try:
                timestamp = float(timestamp)
                if timestamp > 100_000_000_000:
                    timestamp /= 1000.0
            except (TypeError, ValueError):
                continue
            if timestamp <= 0:
                continue
            session_first_seen[session_id] = min(
                timestamp, session_first_seen.get(session_id, timestamp))

        days = {}
        day_sessions = {}
        for row in records:
            session_id = row.get("session_id")
            timestamp = session_first_seen.get(session_id)
            if timestamp is None:
                continue
            local_dt = datetime.fromtimestamp(timestamp).astimezone()
            dk = local_dt.date().isoformat()
            day = days.setdefault(dk, {"in": 0, "out": 0, "cr": 0, "cw": 0,
                                       "reason": 0, "cost": 0.0, "models": {}})
            inp = int(row.get("input_tokens") or 0)
            out = int(row.get("output_tokens") or 0)
            cr = int(row.get("cache_read_tokens") or 0)
            cw = int(row.get("cache_write_tokens") or 0)
            reason = int(row.get("reasoning_tokens") or 0)
            cost = row_cost(row)
            model = row.get("model")
            day["in"] += inp
            day["out"] += out
            day["cr"] += cr
            day["cw"] += cw
            day["reason"] += reason
            day["cost"] += cost
            if model:
                add_model_usage(day["models"], model, inp, out, cr, cw, reason, cost)
            if session_id in sessions:
                day_sessions.setdefault(dk, set()).add(session_id)

        for dk, day in days.items():
            try:
                d = date.fromisoformat(dk)
            except ValueError:
                continue
            dt = datetime(d.year, d.month, d.day)
            for k in classify(dt, bounds):
                b = ranges[k]
                b["in"] += day["in"]
                b["out"] += day["out"]
                b["cr"] += day["cr"]
                b["cw"] += day["cw"]
                b["reason"] += day["reason"]
                b["cost"] += day["cost"]
                b["sessions"].update(day_sessions.get(dk, set()))
                for mn, mv in day["models"].items():
                    add_model_usage(b["models"], mn, mv["in"], mv["out"],
                                    mv["cr"], mv["cw"], mv["reason"], mv["cost"])
        return {"ranges": ranges}

    def collect(self):
        merged = None
        for db in self.candidate_dbs():
            if not db or not os.path.isfile(db):
                continue
            uri = sqlite_ro_uri(db)
            conn = None
            try:
                conn = sqlite3.connect(uri, timeout=5)
                conn.row_factory = sqlite3.Row
            except Exception:
                continue
            try:
                res = self.query(conn)
            except Exception:
                res = None
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
            if res is None:
                continue
            merged = res if merged is None else _merge_ranges(merged, res)
        if merged is None:
            return self.empty_result()
        return merged


def _token_total(d):
    return sum(d.get(k, 0) for k in ("in", "out", "cr", "cw", "reason"))


register(HermesCollector())
