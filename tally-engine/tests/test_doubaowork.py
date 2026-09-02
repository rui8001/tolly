import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from engine.collectors.doubaowork import DoubaoWorkCollector


class FixtureDoubaoWorkCollector(DoubaoWorkCollector):
    def __init__(self, root):
        self.root = str(root)

    def candidate_roots(self):
        return [self.root]


class DoubaoWorkCollectorTests(unittest.TestCase):
    def test_counts_verified_completion_requests_without_inventing_tokens(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            today = datetime.now().astimezone()
            filename = f"saman_{today.year}.{today.month:02d}{today.day:02d}.0.log"
            prefix = f"[1:2:{today.month:02d}{today.day:02d}/120000."
            lines = [
                prefix + "001:INFO:x] start request here: https://www.doubao.com/chat/completion?a=1",
                prefix + "002:INFO:x] unrelated request",
                prefix + "003:INFO:x] start request here: https://www.doubao.com/chat/completion?a=2",
            ]
            (root / filename).write_text("\n".join(lines), encoding="utf-8")

            result = FixtureDoubaoWorkCollector(root).collect()

            self.assertEqual(2, result["ranges"]["today"]["calls"])
            self.assertEqual(2, result["ranges"]["all"]["calls"])
            self.assertEqual(0, result["ranges"]["all"]["in"])
            self.assertEqual("calls", result["metric"])
            self.assertNotIn("quota", result)

    def test_duplicate_log_event_is_counted_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            today = datetime.now().astimezone()
            filename = f"saman_{today.year}.{today.month:02d}{today.day:02d}.0.log"
            line = (
                f"[1:2:{today.month:02d}{today.day:02d}/120000.001:INFO:x] "
                "start request here: https://www.doubao.com/chat/completion?a=1"
            )
            (root / filename).write_text(f"{line}\n{line}\n", encoding="utf-8")

            result = FixtureDoubaoWorkCollector(root).collect()

            self.assertEqual(1, result["ranges"]["all"]["calls"])


if __name__ == "__main__":
    unittest.main()
