"""Base collector for SQLite-backed tools (Qoder, Hermes, OpenCode, ZCode, ...).

Connects read-only (``mode=ro&immutable=1``) so the live database is never
locked. Subclasses implement :meth:`candidate_dbs` and :meth:`query`.
"""
from __future__ import annotations

import sqlite3

from .base import Collector
from ..core.io_util import sqlite_ro_uri
from ..core.log import warn


class SqliteCollector(Collector):
    def candidate_dbs(self) -> list[str]:
        raise NotImplementedError

    def query(self, conn: sqlite3.Connection) -> dict:
        raise NotImplementedError

    def empty_result(self, extra=None):
        from ..core.ranges import empty_ranges
        return {"ranges": empty_ranges(extra)}

    def collect(self) -> dict:
        for db in self.candidate_dbs():
            if not db or not __import__("os").path.isfile(db):
                continue
            uri = sqlite_ro_uri(db)
            try:
                conn = sqlite3.connect(uri, timeout=5)
                conn.row_factory = sqlite3.Row
            except Exception as e:
                warn(f"{self.tool}: cannot open {db}: {e}")
                continue
            try:
                return self.query(conn)
            except Exception as e:
                warn(f"{self.tool}: query failed on {db}: {e}")
                continue
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        return self.empty_result()
