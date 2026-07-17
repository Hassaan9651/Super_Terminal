import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.history import (
    DEFAULT_HISTORY_LENGTH,
    enable_persistent_history,
    load_history,
    save_history,
)


class TestHistory(unittest.TestCase):

    @patch("utils.history.readline")
    def test_load_history_reads_existing_file_and_sets_length(self, mock_readline):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history"
            history_file.write_text("list files\n", encoding="utf-8")

            self.assertTrue(load_history(history_file))

            mock_readline.read_history_file.assert_called_once_with(str(history_file))
            mock_readline.set_history_length.assert_called_once_with(DEFAULT_HISTORY_LENGTH)

    @patch("utils.history.readline")
    def test_load_history_creates_parent_without_reading_missing_file(self, mock_readline):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "nested" / "history"

            self.assertTrue(load_history(history_file))

            self.assertTrue(history_file.parent.exists())
            mock_readline.read_history_file.assert_not_called()
            mock_readline.set_history_length.assert_called_once_with(DEFAULT_HISTORY_LENGTH)

    @patch("utils.history.readline")
    def test_save_history_writes_history_file(self, mock_readline):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history"

            self.assertTrue(save_history(history_file))

            mock_readline.write_history_file.assert_called_once_with(str(history_file))

    @patch("utils.history.atexit.register")
    @patch("utils.history.readline")
    def test_enable_persistent_history_registers_save_on_success(self, mock_readline, mock_register):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history"
            with patch("utils.history.get_history_file", return_value=history_file):
                self.assertTrue(enable_persistent_history())

            mock_register.assert_called_once_with(save_history)

    @patch("utils.history.readline", None)
    def test_history_returns_false_without_readline(self):
        self.assertFalse(load_history())
        self.assertFalse(save_history())
        self.assertFalse(enable_persistent_history())


if __name__ == "__main__":
    unittest.main()
