"""Doubao Work local request collector.

Doubao Work does not currently expose stable token or credit accounting in its
local files. Its SDK log does, however, record a timestamped line whenever the
desktop client starts a ``/chat/completion`` request. We report those verified
local requests as calls and never relabel them as tokens or account credits.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime

from .base import Collector, register
from ..core.paths import discover_dirs, local_data_dir
from ..core.ranges import empty_ranges, range_bounds
from ..core.usage import bucket_record

_LOG_NAME_RE = re.compile(r"^saman_(?P<year>\d{4})\.(?P<month>\d{2})(?P<day>\d{2})(?:\.\d+)?\.log$")
_REQUEST_RE = re.compile(
    rb":(?P<month>\d{2})(?P<day>\d{2})/(?P<hour>\d{2})(?P<minute>\d{2})"
    rb"(?P<second>\d{2})\.(?P<millis>\d{3}):[^\]]*\].*?"
    rb"start request here: (?P<url>https://www\.doubao\.com/chat/completion\S*)"
)


class DoubaoWorkCollector(Collector):
    tool = "doubaowork"

    def candidate_roots(self):
        return discover_dirs("TALLY_DOUBAOWORK_DIR", local_data_dir("DoubaoWork"))

    @staticmethod
    def _log_dirs(roots):
        result = []
        seen = set()
        for root in roots:
            candidates = [
                root,
                os.path.join(root, "sdk_storage", "log"),
                os.path.join(root, "User Data", "sdk_storage", "log"),
            ]
            for candidate in candidates:
                if not os.path.isdir(candidate):
                    continue
                key = os.path.normcase(os.path.realpath(candidate))
                if key not in seen:
                    seen.add(key)
                    result.append(candidate)
        return result

    @staticmethod
    def _events(path, filename_match):
        year = int(filename_match.group("year"))
        file_month = int(filename_match.group("month"))
        file_day = int(filename_match.group("day"))
        try:
            with open(path, "rb") as handle:
                for line in handle:
                    if b"start request here: https://www.doubao.com/chat/completion" not in line:
                        continue
                    match = _REQUEST_RE.search(line)
                    if not match:
                        continue
                    month = int(match.group("month"))
                    day = int(match.group("day"))
                    if (month, day) != (file_month, file_day):
                        continue
                    try:
                        dt = datetime(
                            year, month, day,
                            int(match.group("hour")), int(match.group("minute")),
                            int(match.group("second")), int(match.group("millis")) * 1000,
                        ).astimezone()
                    except ValueError:
                        continue
                    # Hash only for in-memory replay de-duplication. The URL may
                    # contain private query values and is never returned or saved.
                    identity = (dt.isoformat(), hashlib.sha256(match.group("url")).digest())
                    yield dt, identity
        except OSError:
            return

    def collect(self):
        roots = self.candidate_roots()
        if not roots:
            return None
        ranges = empty_ranges(("calls",))
        daily = {}
        bounds = range_bounds()
        seen = set()
        for log_dir in self._log_dirs(roots):
            try:
                filenames = os.listdir(log_dir)
            except OSError:
                continue
            for filename in filenames:
                name_match = _LOG_NAME_RE.match(filename)
                if not name_match:
                    continue
                path = os.path.join(log_dir, filename)
                if not os.path.isfile(path) or os.path.islink(path):
                    continue
                for dt, identity in self._events(path, name_match):
                    if identity in seen:
                        continue
                    seen.add(identity)
                    bucket_record(
                        ranges, bounds, dt, daily=daily, extra={"calls": 1}
                    )
        return {
            "ranges": ranges,
            "daily": daily,
            "projects": {},
            "detected": True,
            "metric": "calls",
            "note": "按本地对话请求统计调用次数，不等同于 Token 或积分",
        }


register(DoubaoWorkCollector())
