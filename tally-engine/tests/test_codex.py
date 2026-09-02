import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from engine.collectors.codex import CodexCollector
from engine.collectors.codex_app_server import _account_snapshot, read_account_rate_limits


class FixtureCodexCollector(CodexCollector):
    def __init__(self, root):
        super().__init__()
        self.root = str(root)

    def candidate_dirs(self):
        return [self.root]

    def _read_live_account_quota(self):
        return None


class CodexCollectorTests(unittest.TestCase):
    def test_cached_input_is_split_from_inclusive_input_total(self):
        collector = CodexCollector()
        record = collector.parse_record({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 1000,
                        "cached_input_tokens": 800,
                        "output_tokens": 100,
                    },
                    "total_token_usage": {
                        "input_tokens": 1000,
                        "cached_input_tokens": 800,
                        "output_tokens": 100,
                        "reasoning_output_tokens": 0,
                    },
                },
            },
        }, "rollout.jsonl")

        self.assertEqual(200, record["in"])
        self.assertEqual(800, record["cr"])
        self.assertEqual(100, record["out"])

    def test_project_comes_from_session_working_directory_not_date_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dated = root / "2026" / "09" / "02"
            dated.mkdir(parents=True)
            now = datetime.now(timezone.utc).isoformat()
            records = [
                {
                    "timestamp": now,
                    "type": "session_meta",
                    "payload": {"cwd": "D:\\GitHub项目\\tolly", "model": "gpt-5.5"},
                },
                {
                    "timestamp": now,
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "last_token_usage": {
                                "input_tokens": 10,
                                "cached_input_tokens": 0,
                                "output_tokens": 5,
                            },
                            "total_token_usage": {
                                "input_tokens": 10,
                                "cached_input_tokens": 0,
                                "output_tokens": 5,
                                "reasoning_output_tokens": 0,
                            },
                        },
                    },
                },
            ]
            (dated / "rollout.jsonl").write_text(
                "\n".join(json.dumps(item) for item in records), encoding="utf-8"
            )

            result = FixtureCodexCollector(root).collect()

            self.assertIn("D:\\GitHub项目\\tolly", result["projects"])
            self.assertNotIn("02", result["projects"])

    def test_latest_weekly_quota_is_exposed_without_inventing_credits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            now = datetime.now(timezone.utc)
            records = []
            for offset, used in ((-10, 63.0), (0, 27.5)):
                records.append({
                    "timestamp": (now + timedelta(minutes=offset)).isoformat(),
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {"last_token_usage": None},
                        "rate_limits": {
                            "limit_id": "codex",
                            "limit_name": "Codex",
                            "primary": {
                                "used_percent": 10,
                                "window_minutes": 300,
                            },
                            "secondary": {
                                "used_percent": used,
                                "window_minutes": 10080,
                                "resets_at": 1_800_000_000,
                            },
                            "credits": {
                                "has_credits": False,
                                "unlimited": False,
                                "balance": "0",
                            },
                        },
                    },
                })
            (root / "rollout.jsonl").write_text(
                "\n".join(json.dumps(item) for item in records),
                encoding="utf-8",
            )

            result = FixtureCodexCollector(root).collect()

            self.assertEqual(27.5, result["quota"]["weekly"]["used_percent"])
            self.assertEqual(72.5, result["quota"]["weekly"]["remaining_percent"])
            self.assertNotIn("credits", result["quota"])

    def test_credits_are_available_as_fallback_when_provider_reports_them(self):
        quota = CodexCollector._quota_from_rate_limits({
            "credits": {
                "has_credits": True,
                "unlimited": False,
                "balance": "12.50",
            },
        })

        self.assertEqual(12.5, quota["credits"]["remaining"])

    def test_weekly_window_can_be_in_primary_slot(self):
        quota = CodexCollector._quota_from_rate_limits({
            "primary": {
                "used_percent": 31,
                "window_minutes": 10080,
                "resets_at": 1_900_000_000,
            },
            "secondary": {"used_percent": 2, "window_minutes": 300},
        })

        self.assertEqual(69, quota["weekly"]["remaining_percent"])

    def test_account_limit_beats_newer_model_specific_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            now = datetime.now(timezone.utc)
            def event(offset, limit_id, name, used):
                return {
                    "timestamp": (now + timedelta(minutes=offset)).isoformat(),
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {"last_token_usage": None},
                        "rate_limits": {
                            "limit_id": limit_id,
                            "limit_name": name,
                            "primary": {
                                "used_percent": used,
                                "window_minutes": 10080,
                                "resets_at": 1_900_000_000,
                            },
                        },
                    },
                }
            records = [
                event(-5, "codex", "Codex", 42),
                event(0, "codex_bengalfox", "GPT-5.3-Codex-Spark", 0),
            ]
            (root / "rollout.jsonl").write_text(
                "\n".join(json.dumps(item) for item in records), encoding="utf-8"
            )

            result = FixtureCodexCollector(root).collect()

            self.assertEqual("codex", result["quota"]["limit_id"])
            self.assertEqual(58, result["quota"]["weekly"]["remaining_percent"])

    def test_model_limit_never_replaces_expired_account_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            now = datetime.now(timezone.utc)
            records = []
            for offset, limit_id, name, reset in (
                (-5, "codex", "Codex", int(now.timestamp()) - 60),
                (0, "codex_bengalfox", "GPT-5.3-Codex-Spark", int(now.timestamp()) + 3600),
            ):
                records.append({
                    "timestamp": (now + timedelta(minutes=offset)).isoformat(),
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {"last_token_usage": None},
                        "rate_limits": {
                            "limit_id": limit_id,
                            "limit_name": name,
                            "primary": {
                                "used_percent": 8,
                                "window_minutes": 10080,
                                "resets_at": reset,
                            },
                        },
                    },
                })
            (root / "rollout.jsonl").write_text(
                "\n".join(json.dumps(item) for item in records), encoding="utf-8"
            )

            result = FixtureCodexCollector(root).collect()

            self.assertNotIn("quota", result)

    def test_live_account_quota_beats_local_log(self):
        with tempfile.TemporaryDirectory() as temporary:
            collector = FixtureCodexCollector(temporary)
            collector._read_live_account_quota = lambda: {
                "source": "codex_app_server",
                "limit_id": "codex",
                "weekly": {
                    "used_percent": 49,
                    "remaining_percent": 51,
                    "window_minutes": 10080,
                    "resets_at": 1_900_000_000,
                },
            }

            result = collector.collect()

            self.assertEqual(51, result["quota"]["weekly"]["remaining_percent"])
            self.assertEqual("codex_app_server", result["quota"]["source"])

    def test_app_server_selects_general_bucket_not_model_bucket(self):
        snapshot = _account_snapshot({
            "rateLimits": {
                "limitId": "codex_bengalfox",
                "limitName": "GPT-5.3-Codex-Spark",
            },
            "rateLimitsByLimitId": {
                "codex_bengalfox": {"limitId": "codex_bengalfox"},
                "codex": {
                    "limitId": "codex",
                    "limitName": "Codex",
                    "primary": {
                        "usedPercent": 49,
                        "windowDurationMins": 10080,
                        "resetsAt": 1_900_000_000,
                    },
                },
            },
        })

        self.assertEqual("codex", snapshot["limitId"])
        quota = CodexCollector._quota_from_rate_limits(snapshot, "codex_app_server")
        self.assertEqual(51, quota["weekly"]["remaining_percent"])

    def test_app_server_rejects_model_only_response(self):
        self.assertIsNone(_account_snapshot({
            "rateLimits": {"limitId": "codex_bengalfox"},
            "rateLimitsByLimitId": {
                "codex_bengalfox": {"limitId": "codex_bengalfox"},
            },
        }))

    @patch("engine.collectors.codex_app_server._find_codex_executable")
    @patch("engine.collectors.codex_app_server._query_app_server")
    def test_app_server_protocol_parses_general_quota(self, query, find_executable):
        find_executable.return_value = "codex.exe"
        query.return_value = {
            "id": 2,
            "result": {
                "rateLimitsByLimitId": {
                    "codex": {"limitId": "codex", "primary": {"usedPercent": 49}}
                }
            },
        }

        result = read_account_rate_limits()

        self.assertEqual("codex", result["limitId"])
        query.assert_called_once_with("codex.exe", 6.0)


if __name__ == "__main__":
    unittest.main()
