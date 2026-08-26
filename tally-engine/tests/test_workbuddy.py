import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from engine.collectors.workbuddy import WorkBuddyCollector


class FixtureWorkBuddyCollector(WorkBuddyCollector):
    def __init__(self, root):
        self.root = str(root)

    def candidate_dirs(self):
        return [self.root]


class WorkBuddyCollectorTests(unittest.TestCase):
    def test_replayed_message_is_counted_once_and_cache_is_split(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "demo-project"
            project.mkdir()
            record = {
                "id": "message-1",
                "sessionId": "session-1",
                "timestamp": datetime.now().astimezone().isoformat(),
                "message": {
                    "model": "claude-sonnet-4",
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 500,
                        "total_tokens": 1500,
                        "cache_read_input_tokens": 200,
                        "cache_creation_input_tokens": 100,
                    },
                },
            }
            session = project / "session.jsonl"
            session.write_text(
                json.dumps(record) + "\n" + json.dumps(record) + "\n",
                encoding="utf-8",
            )

            result = FixtureWorkBuddyCollector(temporary).collect()
            all_usage = result["ranges"]["all"]
            self.assertEqual(700, all_usage["in"])
            self.assertEqual(500, all_usage["out"])
            self.assertEqual(200, all_usage["cr"])
            self.assertEqual(100, all_usage["cw"])
            self.assertEqual(1, len(all_usage["sessions"]))

            project_usage = result["projects"]["demo-project"]["ranges"]["all"]
            self.assertEqual(1500, project_usage["in"] + project_usage["out"]
                             + project_usage["cr"] + project_usage["cw"])
            self.assertEqual(1, len(project_usage["sessions"]))
            self.assertEqual(1, len(result["daily"]))


if __name__ == "__main__":
    unittest.main()
