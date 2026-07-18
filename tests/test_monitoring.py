import json
import tempfile
import unittest
from pathlib import Path

from utils.monitoring import (
    ReadOnlyObservation,
    ReadOnlyRetryMonitor,
    classify_retry_signal,
    intent_similarity,
)


class TestReadOnlyRetryMonitoring(unittest.TestCase):
    def make_observation(self, user_input, command):
        return ReadOnlyObservation(
            user_input=user_input,
            translated_command=command,
            os_name="macOS",
            shell_name="zsh",
            cwd="/Users/me/project",
        )

    def test_classifies_exact_retry(self):
        previous = self.make_observation("show python files", "find . -name '*.py'")
        current = self.make_observation("show python files", "find . -name '*.py'")

        self.assertEqual(
            classify_retry_signal(previous, current),
            "exact_readonly_retry",
        )

    def test_classifies_same_command_rephrase(self):
        previous = self.make_observation("show python files", "find . -name '*.py'")
        current = self.make_observation("list py files", "find . -name '*.py'")

        self.assertEqual(
            classify_retry_signal(previous, current),
            "same_command_rephrase",
        )

    def test_classifies_similar_readonly_rephrase(self):
        previous = self.make_observation("show hidden files here", "ls -a")
        current = self.make_observation("show hidden files in this folder", "find . -maxdepth 1")

        self.assertEqual(
            classify_retry_signal(previous, current),
            "similar_readonly_rephrase",
        )
        self.assertGreaterEqual(
            intent_similarity(previous.user_input, current.user_input),
            0.72,
        )

    def test_ignores_unrelated_readonly_queries(self):
        previous = self.make_observation("show hidden files", "ls -a")
        current = self.make_observation("print current directory", "pwd")

        self.assertIsNone(classify_retry_signal(previous, current))

    def test_monitor_writes_retry_event_as_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "read_only_retries.jsonl"
            personality_file = Path(tmpdir) / "skills" / "personality.md"
            monitor = ReadOnlyRetryMonitor(
                log_file=log_file,
                session_id="test-session",
                personality_file=personality_file,
            )

            self.assertFalse(
                monitor.observe("show python files", "find . -name '*.py'", "macOS", "zsh", "/tmp")
            )
            self.assertTrue(
                monitor.observe("list py files", "find . -name '*.py'", "macOS", "zsh", "/tmp")
            )

            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]
            personality_content = personality_file.read_text(encoding="utf-8")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "read_only_retry_signal")
        self.assertEqual(events[0]["signal"], "same_command_rephrase")
        self.assertEqual(events[0]["session_id"], "test-session")
        self.assertEqual(events[0]["current"]["user_input"], "list py files")
        self.assertIn("list py files", personality_content)


if __name__ == "__main__":
    unittest.main()
