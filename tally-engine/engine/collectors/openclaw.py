"""OpenClaw collector.

Source: ``~/.openclaw/state/openclaw.sqlite`` (new) or
``~/.openclaw/tasks/runs.sqlite`` (old) (env ``TALLY_OPENCLAW_DB``).
Both DBs are unioned: each ``task_runs`` table contributes per-day task counts.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime

from .base import register
from .sqlite import SqliteCollector
from ..core.paths import HOME
from ..core.ranges import classify, empty_ranges, range_bounds
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


class OpenClawCollector(SqliteCollector):
    tool = "openclaw"

    def candidate_dbs(self):
        cands = []
        env = os.environ.get("TALLY_OPENCLAW_DB")
        if env:
            cands.append(os.path.expanduser(env))
        cands.append(os.path.expanduser(os.path.join(
            HOME, ".openclaw", "state", "openclaw.sqlite")))
        cands.append(os.path.expanduser(os.path.join(
            HOME, ".openclaw", "tasks", "runs.sqlite")))
        return cands

    def query(self, conn):
        ranges = empty_ranges(extra_keys=("tasks", "completed", "failed"))
        bounds = range_bounds()
        try:
            rows = conn.execute("""
                SELECT date(created_at/1000,'unixepoch','localtime') as day,
                       COUNT(*) as total,
                       SUM(CASE WHEN lower(status) IN ('completed','succeeded','success') THEN 1 ELSE 0 END),
                       SUM(CASE WHEN lower(status) IN ('failed','error') THEN 1 ELSE 0 END)
                FROM task_runs WHERE created_at > 0
                GROUP BY day
            """)
        except Exception:
            return {"ranges": ranges}
        for row in rows:
            dk, total, completed, failed = row
            if not dk:
                continue
            try:
                d = date.fromisoformat(dk)
            except ValueError:
                continue
            dt = datetime(d.year, d.month, d.day)
            for k in classify(dt, bounds):
                b = ranges[k]
                b["tasks"] += int(total or 0)
                b["completed"] += int(completed or 0)
                b["failed"] += int(failed or 0)
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
            return {"ranges": empty_ranges(extra_keys=("tasks", "completed", "failed"))}
        return merged


register(OpenClawCollector())
