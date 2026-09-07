import io
import json
import queue
import subprocess
import time
import unittest
from unittest.mock import MagicMock, patch

from engine.collectors import codex_app_server as server


class AppServerBoundaryTests(unittest.TestCase):
    def test_protocol_ignores_json_scalars_and_unrelated_notifications(self):
        messages = queue.Queue()
        for value in ['null', '[]', '123', 'not-json', '{"method":"notice"}', '{"id":2,"result":{}}']:
            messages.put(value)
        self.assertEqual(server._wait_for_response(messages, 2, time.monotonic()+1), {"id":2,"result":{}})

    def test_timeout_and_eof_return_no_snapshot(self):
        self.assertIsNone(server._wait_for_response(queue.Queue(), 2, time.monotonic()))
        messages = queue.Queue()
        messages.put(None)
        self.assertIsNone(server._wait_for_response(messages, 2, time.monotonic()+1))

    def test_initialization_precedes_read_and_process_is_terminated(self):
        process = MagicMock()
        process.stdin = io.StringIO()
        process.stdout = io.StringIO('{"id":1,"result":{}}\n{"id":2,"result":{"rateLimitsByLimitId":{}}}\n')
        with patch.object(server.subprocess, "Popen", return_value=process):
            response = server._query_app_server("synthetic-codex", 1)
        self.assertEqual(response["id"], 2)
        methods = [json.loads(line)["method"] for line in process.stdin.getvalue().splitlines()]
        self.assertEqual(methods, ["initialize", "initialized", "account/rateLimits/read"])
        process.terminate.assert_called_once()

    def test_launch_failure_is_unavailable_not_exception(self):
        with patch.object(server.subprocess, "Popen", side_effect=OSError("synthetic missing executable")):
            self.assertIsNone(server._query_app_server("missing", .01))

    def test_init_error_does_not_send_account_request(self):
        process = MagicMock()
        process.stdin = io.StringIO()
        process.stdout = io.StringIO('{"id":1,"error":{"code":-1}}\n')
        process.wait.side_effect = subprocess.TimeoutExpired("synthetic-codex", 1)
        with patch.object(server.subprocess, "Popen", return_value=process):
            self.assertIsNone(server._query_app_server("synthetic-codex", 1))
        self.assertNotIn("account/rateLimits/read", process.stdin.getvalue())
        process.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
