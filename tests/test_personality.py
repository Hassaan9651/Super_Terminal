import tempfile
import unittest
from pathlib import Path

from utils.monitoring import ReadOnlyObservation
from utils.personality import (
    append_retry_learning,
    ensure_personality_file,
    load_personality_context,
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

    def test_ensure_personality_file_creates_markdown_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            personality_file = Path(tmpdir) / "skills" / "personality.md"

            ensure_personality_file(personality_file)

            content = personality_file.read_text(encoding="utf-8")
            self.assertIn("# SuperTerminal User Adaptation", content)
            self.assertIn("## Learned Read-Only Retry Patterns", content)

    def test_append_retry_learning_records_compact_lesson(self):
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
            self.assertIn("show python files", content)
            self.assertIn("list py files", content)
            self.assertIn("find . -name '*.py'", content)

    def test_load_personality_context_omits_empty_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            personality_file = Path(tmpdir) / "skills" / "personality.md"

            ensure_personality_file(personality_file)

            self.assertEqual(load_personality_context(personality_file), "")


if __name__ == "__main__":
    unittest.main()
