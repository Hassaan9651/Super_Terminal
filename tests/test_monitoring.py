import json
import tempfile
import unittest
from pathlib import Path

from utils.monitoring import (
    ModifyingCommandEditMonitor,
    ReadOnlyObservation,
    ReadOnlyRetryMonitor,
    classify_retry_signal,
    intent_similarity,
    was_modifying_command_edited,
)
from utils.system_log import SystemLogger


class TestMonitoring(unittest.TestCase):
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

    def test_monitor_writes_retry_event_and_compact_learning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "read_only_retries.jsonl"
            system_log_file = Path(tmpdir) / "system.log"
            personality_file = Path(tmpdir) / "skills" / "personality.md"
            system_logger = SystemLogger(log_file=system_log_file, session_id="test-session")
            monitor = ReadOnlyRetryMonitor(
                log_file=log_file,
                session_id="test-session",
                personality_file=personality_file,
                system_logger=system_logger,
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
            system_events = [
                json.loads(line)
                for line in system_log_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "read_only_retry_signal")
        self.assertEqual(events[0]["session_id"], "test-session")
        self.assertIn("prefer the command shape", personality_content)
        self.assertNotIn("show python files", personality_content)
        self.assertEqual(system_events[0]["event"], "read_only_retry_signal")
        self.assertEqual(system_events[0]["session_id"], "test-session")

    def test_detects_modifying_command_edit(self):
        self.assertTrue(
            was_modifying_command_edited(
                "mkdir notes",
                "mkdir -p notes",
            )
        )
        self.assertFalse(
            was_modifying_command_edited(
                "mkdir notes",
                "  mkdir   notes  ",
            )
        )

    def test_modifying_monitor_writes_edit_event_and_compact_learning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "modifying_command_edits.jsonl"
            system_log_file = Path(tmpdir) / "system.log"
            personality_file = Path(tmpdir) / "skills" / "personality.md"
            system_logger = SystemLogger(log_file=system_log_file, session_id="edit-session")
            monitor = ModifyingCommandEditMonitor(
                log_file=log_file,
                session_id="edit-session",
                personality_file=personality_file,
                system_logger=system_logger,
            )

            self.assertTrue(
                monitor.observe(
                    "make a notes folder",
                    "mkdir notes",
                    "mkdir -p notes",
                    "Linux",
                    "bash",
                    "/tmp/project",
                )
            )

            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]
            personality_content = personality_file.read_text(encoding="utf-8")
            system_events = [
                json.loads(line)
                for line in system_log_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "modifying_command_edit")
        self.assertEqual(events[0]["suggested_command"], "mkdir notes")
        self.assertEqual(events[0]["approved_command"], "mkdir -p notes")
        self.assertIn("make a notes folder", personality_content)
        self.assertIn("prefer `mkdir -p notes`", personality_content)
        self.assertEqual(system_events[0]["event"], "modifying_command_edit")
        self.assertEqual(system_events[0]["session_id"], "edit-session")

    def test_modifying_monitor_ignores_unedited_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "modifying_command_edits.jsonl"
            personality_file = Path(tmpdir) / "skills" / "personality.md"
            monitor = ModifyingCommandEditMonitor(
                log_file=log_file,
                session_id="edit-session",
                personality_file=personality_file,
            )

            self.assertFalse(
                monitor.observe(
                    "make a notes folder",
                    "mkdir notes",
                    "mkdir notes",
                    "Linux",
                    "bash",
                    "/tmp/project",
                )
            )

            self.assertFalse(log_file.exists())
            self.assertFalse(personality_file.exists())


if __name__ == "__main__":
    unittest.main()
