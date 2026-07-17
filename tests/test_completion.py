import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.completion import _complete_path_prefix, enable_path_completion, path_completer


class TestCompletion(unittest.TestCase):

    def test_complete_path_prefix_returns_files_and_directory_slashes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "alpha.txt").write_text("")
            (root / "alpha-dir").mkdir()

            matches = _complete_path_prefix(str(root / "alp"))

            self.assertIn(str(root / "alpha.txt"), matches)
            self.assertIn(str(root / "alpha-dir") + os.sep, matches)

    def test_path_completer_returns_stateful_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "first.txt").write_text("")
            (root / "second.txt").write_text("")

            prefix = str(root) + os.sep

            self.assertEqual(path_completer(prefix, 0), str(root / "first.txt"))
            self.assertEqual(path_completer(prefix, 1), str(root / "second.txt"))
            self.assertIsNone(path_completer(prefix, 2))

    def test_nested_completion_matches_basename_substring(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nested = root / "tests"
            nested.mkdir()
            (nested / "test_capabilities.py").write_text("")

            matches = _complete_path_prefix(str(nested / "cap"))

            self.assertEqual(matches, [str(nested / "test_capabilities.py")])

    @patch("utils.completion.readline")
    def test_enable_path_completion_configures_readline(self, mock_readline):
        mock_readline.__doc__ = "GNU readline"

        self.assertTrue(enable_path_completion())

        mock_readline.set_completer.assert_called_once()
        mock_readline.set_completer_delims.assert_called_once_with(" \t\n;|&<>")
        mock_readline.set_completion_append_character.assert_called_once_with("")
        mock_readline.parse_and_bind.assert_called_once_with("tab: complete")

    @patch("utils.completion.readline", None)
    def test_enable_path_completion_returns_false_without_readline(self):
        self.assertFalse(enable_path_completion())


if __name__ == "__main__":
    unittest.main()
