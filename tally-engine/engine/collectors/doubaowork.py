"""Conservative DoubaoWork detector.

Current Windows builds leave local application data but no stable, documented
token or credit field that can be verified offline. Report detection only so
the UI is transparent instead of fabricating usage numbers.
"""
from __future__ import annotations

import os

from .base import Collector, register
from ..core.paths import discover_dirs, local_data_dir


class DoubaoWorkCollector(Collector):
    tool = "doubaowork"

    def collect(self):
        roots = discover_dirs("TALLY_DOUBAOWORK_DIR", local_data_dir("DoubaoWork"))
        if not roots:
            return None
        result = self.empty_result()
        result["detected"] = True
        result["note"] = "已检测到本地数据，但当前版本未发现可验证的 Token 或积分字段"
        return result


register(DoubaoWorkCollector())
