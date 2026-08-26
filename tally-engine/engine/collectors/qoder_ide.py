"""Qoder IDE collector.

Source: ``~/Library/Application Support/Qoder/SharedClientCache/cache/db/local.db``
(env ``TALLY_QODER_IDE_DB``). The ``chat_message`` table carries token usage in a
JSON ``token_info`` column (epoch-millisecond ``gmt_create``); session type
distinguishes sub-agent sessions.
"""
from __future__ import annotations

import os
from datetime import date, datetime

from .base import register
from .sqlite import SqliteCollector
from ..core.paths import HOME, IS_WIN, app_support_dir
from ..core.ranges import classify, empty_ranges, range_bounds


class QoderIdeCollector(SqliteCollector):
    tool = "qoder_ide"

    def candidate_dbs(self):
        cands = []
        env = os.environ.get("TALLY_QODER_IDE_DB")
        if env:
            cands.append(os.path.expanduser(env))
        cands.append(app_support_dir(
            "Qoder", "SharedClientCache", "cache", "db", "local.db"))
        if IS_WIN:
            cands.append(os.path.join(
                os.environ.get("APPDATA", ""), "Qoder",
                "SharedClientCache", "cache", "db", "local.db"))
            cands.append(os.path.join(
                os.environ.get("LOCALAPPDATA", ""), "Qoder",
                "SharedClientCache", "cache", "db", "local.db"))
        else:
            cands.append(os.path.expanduser(os.path.join(
                HOME, ".config", "Qoder", "SharedClientCache",
                "cache", "db", "local.db")))
        return cands

    def query(self, conn):
        ranges = empty_ranges(extra_keys=(
            "sub_agents", "calls", "messages", "duration"))
        bounds = range_bounds()
        days = {}
        try:
            for row in conn.execute("""
                SELECT date(gmt_create/1000, 'unixepoch', 'localtime') as day,
                       COALESCE(SUM(json_extract(token_info, '$.prompt_tokens')), 0),
                       COALESCE(SUM(json_extract(token_info, '$.completion_tokens')), 0),
                       COALESCE(SUM(json_extract(token_info, '$.cached_tokens')), 0),
                       COUNT(DISTINCT request_id),
                       COUNT(*)
                FROM chat_message
                WHERE token_info IS NOT NULL AND token_info != ''
                GROUP BY day
            """):
                dk, ti, to_, cached, calls, msgs = row
                if not dk:
                    continue
                days[dk] = {
                    "in": int(ti or 0), "out": int(to_ or 0),
                    "cr": int(cached or 0), "calls": int(calls or 0),
                    "messages": int(msgs or 0), "duration": 0,
                    "session_ids": set(), "sub_agent_ids": set()}

            sub_agent_sids = set()
            try:
                for row in conn.execute(
                        "SELECT session_id FROM chat_session "
                        "WHERE session_type LIKE 'agent_sub_%'"):
                    sub_agent_sids.add(row[0])
            except Exception:
                pass

            for row in conn.execute("""
                SELECT date(gmt_create/1000, 'unixepoch', 'localtime') as day,
                       session_id
                FROM chat_message
                WHERE token_info IS NOT NULL AND token_info != ''
                GROUP BY day, session_id
            """):
                dk, sid = row
                if dk and dk in days and sid:
                    if sid in sub_agent_sids:
                        days[dk]["sub_agent_ids"].add(sid)
                    else:
                        days[dk]["session_ids"].add(sid)

            for row in conn.execute("""
                SELECT date(min_ts/1000, 'unixepoch', 'localtime') as day,
                       SUM(max_ts - min_ts) / 1000 as dur_sec
                FROM (SELECT request_id, MIN(gmt_create) as min_ts,
                             MAX(gmt_create) as max_ts
                      FROM chat_message GROUP BY request_id HAVING COUNT(*) > 1) sub
                GROUP BY day
            """):
                dk, dur = row
                if dk and dk in days:
                    days[dk]["duration"] = int(dur or 0)
        except Exception:
            return {"ranges": ranges}

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
                b["calls"] += day["calls"]
                b["messages"] += day["messages"]
                b["duration"] += day["duration"]
                b["sessions"].update(day["session_ids"])
                b["sub_agents"] += len(day["sub_agent_ids"])
        return {"ranges": ranges}


register(QoderIdeCollector())
