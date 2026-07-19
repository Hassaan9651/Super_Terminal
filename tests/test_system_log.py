import json
import tempfile
import unittest
from pathlib import Path

from utils.system_log import SystemLogger, write_system_log_record


class TestSystemLog(unittest.TestCase):
    def test_system_logger_writes_timestamped_session_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "system.log"
            logger = SystemLogger(log_file=log_file, session_id="session-123")

            self.assertTrue(logger.log("session_start", shell_name="bash", cwd="/tmp"))

            records = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event"], "session_start")
        self.assertEqual(records[0]["session_id"], "session-123")
        self.assertEqual(records[0]["shell_name"], "bash")
        self.assertIn("timestamp", records[0])

    def test_write_system_log_record_appends_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "system.log"

            self.assertTrue(write_system_log_record(log_file, {"event": "one"}))
            self.assertTrue(write_system_log_record(log_file, {"event": "two"}))

            records = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual([record["event"] for record in records], ["one", "two"])


if __name__ == "__main__":
    unittest.main()
