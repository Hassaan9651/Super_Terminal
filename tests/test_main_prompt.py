import os
import unittest
from unittest.mock import patch

from main import (
    ANSI_BLUE,
    ANSI_DARK_GREEN,
    ANSI_RED,
    ANSI_RESET,
    ANSI_YELLOW,
    READLINE_END_INVISIBLE,
    READLINE_START_INVISIBLE,
    format_plain_prompt,
    format_generated_command_for_review,
    format_preference_remembered_line,
    format_prompt,
    format_prompt_fragments,
    format_readonly_execution_line,
    is_api_key_update_command,
    parse_approved_modifying_command,
    parse_direct_command,
    prompt_control,
)


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

    @patch("main.readline")
    def test_prompt_control_uses_readline_markers_for_gnu_readline(self, mock_readline):
        mock_readline.__doc__ = "GNU readline"

        self.assertEqual(
            prompt_control(ANSI_RED),
            f"{READLINE_START_INVISIBLE}{ANSI_RED}{READLINE_END_INVISIBLE}",
        )

    @patch("main.readline")
    def test_prompt_control_uses_raw_ansi_for_libedit(self, mock_readline):
        mock_readline.__doc__ = "EditLine wrapper for libedit"

        self.assertEqual(prompt_control(ANSI_RED), ANSI_RED)

    @patch("main.readline")
    @patch("main.os.getcwd", return_value=os.path.join("tmp", "project"))
    def test_format_prompt_uses_raw_ansi_on_libedit(self, mock_getcwd, mock_readline):
        mock_readline.__doc__ = "EditLine wrapper for libedit"

        self.assertEqual(
            format_prompt(),
            f"{ANSI_RED}SuperTerminal{ANSI_RESET} "
            f"{ANSI_YELLOW}({os.path.join('tmp', 'project')}){ANSI_RESET} > ",
        )

    def test_format_readonly_execution_line_uses_dark_green(self):
        self.assertEqual(
            format_readonly_execution_line("ls -la"),
            f"{ANSI_DARK_GREEN}Executing read-only command: ls -la{ANSI_RESET}",
        )

    def test_format_preference_remembered_line_uses_blue(self):
        self.assertEqual(
            format_preference_remembered_line(),
            f"{ANSI_BLUE}I'll remember your preference for this next time!{ANSI_RESET}",
        )

    def test_parse_direct_command_requires_bang_prefix(self):
        self.assertEqual(parse_direct_command("!git status"), "git status")
        self.assertEqual(parse_direct_command("  !ls -la  "), "ls -la")
        self.assertEqual(parse_direct_command("git status"), "")
        self.assertEqual(parse_direct_command("ls all files from yesterday"), "")

    def test_format_generated_command_for_review_adds_bang_prefix(self):
        self.assertEqual(format_generated_command_for_review("mkdir notes"), "!mkdir notes")
        self.assertEqual(format_generated_command_for_review("!rm temp"), "!rm temp")

    def test_parse_approved_modifying_command_requires_bang_prefix(self):
        self.assertEqual(parse_approved_modifying_command("!mkdir notes"), "mkdir notes")
        self.assertEqual(parse_approved_modifying_command("mkdir notes"), "")

    def test_api_key_update_command_aliases(self):
        self.assertTrue(is_api_key_update_command("key update"))
        self.assertTrue(is_api_key_update_command("update gemini key"))
        self.assertTrue(is_api_key_update_command("  API KEY UPDATE  "))
        self.assertFalse(is_api_key_update_command("update dependencies"))


if __name__ == "__main__":
    unittest.main()
