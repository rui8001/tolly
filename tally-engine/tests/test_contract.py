import json
import unittest

from engine.contract import to_jsonable
from engine.main import build_wrapped


class ContractTests(unittest.TestCase):
    def test_sets_are_stably_serialized(self):
        value = to_jsonable({"sessions": {"b", "a"}})
        self.assertEqual(["a", "b"], value["sessions"])
        json.dumps(value)

    def test_wrapped_ignores_metadata_and_reports_dates(self):
        empty = {
            "in": 0, "out": 0, "cr": 0, "cw": 0, "reason": 0,
            "cost": 0.0, "models": {}, "sessions": set(),
        }
        all_usage = dict(empty)
        all_usage.update({
            "in": 100, "out": 20, "cost": 1.25,
            "models": {"demo/model": {"cost": 1.25}},
        })
        payload = {
            "demo": {"ranges": {"all": all_usage}},
            "_pricing": {"ranges": {"all": {"cost": 999}}},
            "_daily": {
                "2026-08-24": {"cost": 1.0, "in": 1},
                "2026-08-25": {"cost": 2.0, "in": 1},
                "2026-08-26": {"cost": 0.0, "in": 0},
            },
        }

        wrapped = build_wrapped(payload)
        self.assertEqual(120, wrapped["total_tokens"])
        self.assertEqual(1.25, wrapped["total_cost"])
        self.assertEqual(2, wrapped["longest_streak"])
        self.assertEqual("2026-08-25", wrapped["top_days"][0]["date"])
        self.assertEqual("demo", wrapped["top_tools"][0]["tool"])


if __name__ == "__main__":
    unittest.main()
