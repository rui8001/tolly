"""QoderWork collector.

The stable tool key is ``qoderwork``.

Source: ``~/Library/Application Support/QoderWork/data/agents.db``
(env ``TALLY_QODERWORK_DB``). Token counts come from ``messages.metadata``
(JSON, epoch-second ``created_at``); sub-agent counts and context-usage
percentages come from ``sub_chats``.
"""
from __future__ import annotations

import os
from datetime import date, datetime

from .base import register
from .sqlite import SqliteCollector
from ..core.paths import HOME, IS_WIN, app_support_dir
from ..core.ranges import classify, empty_ranges, range_bounds


class QoderWorkCollector(SqliteCollector):
    tool = "qoderwork"

    def candidate_dbs(self):
        cands = []
        env = os.environ.get("TALLY_QODERWORK_DB")
        if env:
            cands.append(os.path.expanduser(env))
        cands.append(app_support_dir("QoderWork", "data", "agents.db"))
        if IS_WIN:
            cands.append(os.path.join(
                os.environ.get("APPDATA", ""), "QoderWork",
                "data", "agents.db"))
            cands.append(os.path.join(
                os.environ.get("LOCALAPPDATA", ""), "QoderWork",
                "data", "agents.db"))
        else:
            cands.append(os.path.expanduser(os.path.join(
                HOME, ".config", "QoderWork", "data", "agents.db")))
        return cands

    def query(self, conn):
        ranges = empty_ranges(extra_keys=(
            "calls", "sub_agents", "duration", "turns",
            "ctx_sum", "ctx_count"))
        bounds = range_bounds()
        days = {}
        try:
            for row in conn.execute("""
                SELECT date(created_at,'unixepoch','localtime') as day,
                       COUNT(*) as calls,
                       COUNT(DISTINCT chat_id) as sessions,
                       COALESCE(SUM(json_extract(metadata,'$.inputTokens')),0),
                       COALESCE(SUM(json_extract(metadata,'$.outputTokens')),0),
                       COALESCE(SUM(json_extract(metadata,'$.durationMs')),0),
                       COALESCE(SUM(json_extract(metadata,'$.numTurns')),0)
                FROM messages WHERE metadata!='{}' AND role='assistant'
                GROUP BY day
            """):
                dk, calls, _sessions, ti, to_, dur, turns = row
                if not dk:
                    continue
                days[dk] = {
                    "in": int(ti or 0), "out": int(to_ or 0),
                    "duration": int(dur or 0), "turns": int(turns or 0),
                    "calls": int(calls or 0),
                    "session_ids": set(), "ctx_sum": 0.0, "ctx_count": 0}

            sub_chat_days = {}
            for row in conn.execute("""
                SELECT date(created_at,'unixepoch','localtime') as day, COUNT(*)
                FROM sub_chats WHERE created_at IS NOT NULL
                GROUP BY day
            """):
                if row[0]:
                    sub_chat_days[row[0]] = int(row[1])

            for row in conn.execute("""
                SELECT date(created_at,'unixepoch','localtime') as day,
                       AVG(CASE WHEN json_extract(ext,'$.contextUsageSnapshot.percentage')>0
                                THEN json_extract(ext,'$.contextUsageSnapshot.percentage') END)
                FROM sub_chats
                WHERE ext IS NOT NULL AND ext != '{}'
                GROUP BY day
            """):
                dk, ctx_pct = row
                if dk and ctx_pct and dk in days:
                    days[dk]["ctx_sum"] = float(ctx_pct) * days[dk]["calls"]
                    days[dk]["ctx_count"] = days[dk]["calls"]

            for row in conn.execute("""
                SELECT date(created_at,'unixepoch','localtime') as day, chat_id
                FROM messages WHERE metadata!='{}' AND role='assistant'
                GROUP BY day, chat_id
            """):
                dk, chat_id = row
                if dk and chat_id is not None and dk in days:
                    days[dk]["session_ids"].add(chat_id)
        except Exception:
            return {"ranges": ranges}

        for dk, day in days.items():
            try:
                d = date.fromisoformat(dk)
            except ValueError:
                continue
            dt = datetime(d.year, d.month, d.day)
            sub_agents = sub_chat_days.get(dk, 0)
            for k in classify(dt, bounds):
                b = ranges[k]
                b["in"] += day["in"]
                b["out"] += day["out"]
                b["duration"] += day["duration"]
                b["turns"] += day["turns"]
                b["calls"] += day["calls"]
                b["sub_agents"] += sub_agents
                b["ctx_sum"] += day["ctx_sum"]
                b["ctx_count"] += day["ctx_count"]
                b["sessions"].update(day["session_ids"])
        return {"ranges": ranges}


register(QoderWorkCollector())
