import tempfile
import unittest
from pathlib import Path

from utils.monitoring import ReadOnlyObservation
from utils.personality import (
    append_modifying_edit_learning,
    append_retry_learning,
    ensure_personality_file,
    load_personality_context,
    observe_user_expression,
)


class TestPersonalityProfile(unittest.TestCase):
    def make_observation(self, user_input, command):
        return ReadOnlyObservation(
            user_input=user_input,
            translated_command=command,
            os_name="Linux",
            shell_name="bash",
            cwd="/tmp/project",
        )

    def test_ensure_personality_file_creates_summary_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            personality_file = Path(tmpdir) / "skills" / "personality.md"

            ensure_personality_file(personality_file)

            content = personality_file.read_text(encoding="utf-8")
            self.assertIn("# SuperTerminal User Adaptation", content)
            self.assertIn("## Communication Style", content)
            self.assertIn("## Language Hints", content)
            self.assertIn("## Command Translation Preferences", content)

    def test_observe_user_expression_learns_style_without_correction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            personality_file = Path(tmpdir) / "skills" / "personality.md"

            self.assertTrue(
                observe_user_expression(
                    "show py files here",
                    "find . -name '*.py'",
                    personality_file,
                )
            )

            content = personality_file.read_text(encoding="utf-8")
            self.assertIn("short, direct terminal requests", content)
            self.assertIn("action-first phrasing", content)
            self.assertIn("implicit local context", content)
            self.assertIn("Treat `py`", content)

    def test_profile_deduplicates_repeated_style_observations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            personality_file = Path(tmpdir) / "skills" / "personality.md"

            observe_user_expression("show py files", "find . -name '*.py'", personality_file)
            observe_user_expression("list py files", "find . -name '*.py'", personality_file)

            content = personality_file.read_text(encoding="utf-8")
            self.assertEqual(content.count("Treat `py`"), 1)

    def test_append_retry_learning_records_preference_not_raw_event_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            personality_file = Path(tmpdir) / "skills" / "personality.md"
            previous = self.make_observation("show python files", "ls")
            current = self.make_observation("list py files", "find . -name '*.py'")

            self.assertTrue(
                append_retry_learning(
                    "similar_readonly_rephrase",
                    previous,
                    current,
                    personality_file,
                )
            )

            content = personality_file.read_text(encoding="utf-8")
            self.assertIn("prefer the command shape", content)
            self.assertIn("find . -name '*.py'", content)
            self.assertNotIn("similar_readonly_rephrase", content)

    def test_append_modifying_edit_learning_records_preference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            personality_file = Path(tmpdir) / "skills" / "personality.md"

            self.assertTrue(
                append_modifying_edit_learning(
                    "make a folder called reports",
                    "mkdir reports",
                    "mkdir -p reports",
                    personality_file,
                )
            )

            content = personality_file.read_text(encoding="utf-8")
            self.assertIn("make a folder called reports", content)
            self.assertIn("prefer `mkdir -p reports`", content)
            self.assertIn("over `mkdir reports`", content)

    def test_load_personality_context_omits_empty_profile_and_internal_markers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            personality_file = Path(tmpdir) / "skills" / "personality.md"

            ensure_personality_file(personality_file)
            self.assertEqual(load_personality_context(personality_file), "")

            observe_user_expression("show py files", "find . -name '*.py'", personality_file)
            context = load_personality_context(personality_file)

            self.assertIn("Treat `py`", context)
            self.assertNotIn("<!-- st:", context)


if __name__ == "__main__":
    unittest.main()
