import os
import unittest
from unittest.mock import patch

from main import ANSI_DARK_GREEN, ANSI_RESET, format_plain_prompt, format_prompt_fragments, format_readonly_execution_line


class TestMainPrompt(unittest.TestCase):

    @patch("main.os.getcwd", return_value=os.path.join("tmp", "project"))
    def test_format_prompt_fragments_use_prompt_toolkit_colors(self, mock_getcwd):
        self.assertEqual(
            format_prompt_fragments(),
            [
                ("ansired", "SuperTerminal"),
                ("", " "),
                ("ansiyellow", f"({os.path.join('tmp', 'project')})"),
                ("", " > "),
            ],
        )

    @patch("main.os.getcwd", return_value=os.path.join("tmp", "project"))
    def test_format_plain_prompt_has_same_text_without_color(self, mock_getcwd):
        self.assertEqual(
            format_plain_prompt(),
            f"SuperTerminal ({os.path.join('tmp', 'project')}) > ",
        )

    def test_format_readonly_execution_line_uses_dark_green(self):
        self.assertEqual(
            format_readonly_execution_line("ls -la"),
            f"{ANSI_DARK_GREEN}Executing read-only command: ls -la{ANSI_RESET}",
        )


if __name__ == "__main__":
    unittest.main()
