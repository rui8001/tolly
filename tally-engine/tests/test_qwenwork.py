import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from engine.collectors.qwenwork import QwenWorkCollector, _quota_from_mcp_usage


class FixtureQwenWorkCollector(QwenWorkCollector):
    def __init__(self, root):
        super().__init__()
        self.root = str(root)

    def candidate_dirs(self):
        return [self.root]


class QwenWorkCollectorTests(unittest.TestCase):
    def test_real_credit_segments_are_normalized_without_alias_double_count(self):
        quota = _quota_from_mcp_usage({
            "available": True,
            "segments": [{
                "id": "plan", "kind": "plan_credits", "total": 0,
                "used": 0, "remaining": 2100, "unit": "credits",
            }],
            "planCredits": {"remaining": 2100, "unit": "credits"},
        })

        self.assertEqual(2100, quota["credits"]["remaining"])
        self.assertNotIn("total", quota["credits"])

    def test_transcript_is_estimated_and_labeled(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "project" / "chat.jsonl"
            path.parent.mkdir()
            timestamp = datetime.now().astimezone().isoformat()
            records = [
                {"type": "runtime-config", "model": "qmodel_latest"},
                {"type": "user", "timestamp": timestamp,
                 "message": {"content": "帮我整理今天的会议纪要"}},
                {"type": "assistant", "timestamp": timestamp,
                 "message": {"content": [{"type": "text", "text": "好的，我来整理。"}]}},
            ]
            path.write_text("\n".join(json.dumps(item, ensure_ascii=False)
                                      for item in records), encoding="utf-8")

            result = FixtureQwenWorkCollector(temporary).collect()

            self.assertTrue(result["estimated"])
            self.assertTrue(result["detected"])
            self.assertGreater(result["ranges"]["today"]["in"], 0)
            self.assertIn("qmodel_latest", result["ranges"]["today"]["models"])


if __name__ == "__main__":
    unittest.main()
