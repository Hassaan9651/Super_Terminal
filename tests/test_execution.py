import unittest
from unittest.mock import patch, MagicMock
import sys
import io

from main import INTERRUPTED_MESSAGE, execute_command
from utils.executor import execute_readonly_command
from utils.injector import handle_modifying_command, prefill_next_input, read_editable_command


class TestExecution(unittest.TestCase):

    @patch("subprocess.run")
    def test_execute_readonly_command_success(self, mock_run):
        # Configure mock response
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "mocked_file.txt\nanother_file.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Capture output
        captured_out = io.StringIO()
        with patch("sys.stdout", captured_out):
            completed = execute_readonly_command("ls")

        self.assertTrue(completed)
        self.assertIn("mocked_file.txt", captured_out.getvalue())
        mock_run.assert_called_once_with("ls", shell=True, text=True, capture_output=True)

    @patch("subprocess.run")
    def test_execute_readonly_command_failure(self, mock_run):
        # Configure mock response for error
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = ""
        mock_result.stderr = "ls: cannot access 'non_existent': No such file or directory\n"
        mock_run.return_value = mock_result

        # Capture error output
        captured_err = io.StringIO()
        with patch("sys.stderr", captured_err):
            completed = execute_readonly_command("ls non_existent")

        self.assertTrue(completed)
        self.assertIn("cannot access", captured_err.getvalue())
        mock_run.assert_called_once_with("ls non_existent", shell=True, text=True, capture_output=True)

    @patch("subprocess.run", side_effect=KeyboardInterrupt)
    def test_execute_readonly_command_interrupt_does_not_raise(self, mock_run):
        captured_out = io.StringIO()

        with patch("sys.stdout", captured_out):
            completed = execute_readonly_command("ls")

        self.assertFalse(completed)
        self.assertIn("Command execution interrupted by user.", captured_out.getvalue())
        mock_run.assert_called_once_with("ls", shell=True, text=True, capture_output=True)

    @patch("main.execute_readonly_command")
    def test_execute_command_prints_readonly_banner(self, mock_execute_readonly):
        mock_execute_readonly.return_value = True
        captured_out = io.StringIO()

        with patch("sys.stdout", captured_out):
            completed = execute_command("ls", "bash")

        self.assertTrue(completed)
        self.assertIn("Executing read-only command: ls", captured_out.getvalue())
        mock_execute_readonly.assert_called_once_with("ls", "bash")

    @patch("main.subprocess.run", side_effect=KeyboardInterrupt)
    def test_execute_command_interrupt_does_not_raise(self, mock_run):
        captured_out = io.StringIO()

        with patch("sys.stdout", captured_out):
            completed = execute_command("mkdir notes", "bash")

        self.assertFalse(completed)
        self.assertIn(INTERRUPTED_MESSAGE, captured_out.getvalue())
        mock_run.assert_called_once_with("mkdir notes", shell=True)

    @patch("utils.injector.prefill_next_input", return_value=True)
    def test_handle_modifying_command_prefills_next_prompt(self, mock_prefill):
        # Capture console outputs
        captured_out = io.StringIO()
        with patch("sys.stdout", captured_out):
            handle_modifying_command("mkdir new_dir", "bash")

        mock_prefill.assert_called_once_with("mkdir new_dir")
        self.assertIn("Modifying command detected!", captured_out.getvalue())

    @patch("utils.injector.read_editable_command", return_value="mkdir edited")
    def test_handle_modifying_command_returns_edited_prompt_command(self, mock_read):
        captured_out = io.StringIO()
        with patch("sys.stdout", captured_out):
            result = handle_modifying_command("mkdir new_dir", "bash", "SuperTerminal > ")

        self.assertEqual(result, "mkdir edited")
        mock_read.assert_called_once_with("SuperTerminal > ", "mkdir new_dir", None)
        self.assertIn("Modifying command detected!", captured_out.getvalue())

    @patch("utils.injector.editable_prompt", return_value="mkdir toolkit")
    def test_read_editable_command_uses_prompt_toolkit_default(self, mock_prompt):
        prompt_fragments = [
            ("ansired", "SuperTerminal"),
            ("", " > "),
        ]
        result = read_editable_command(prompt_fragments, "mkdir generated")

        self.assertEqual(result, "mkdir toolkit")
        mock_prompt.assert_called_once_with(prompt_fragments, default="mkdir generated")

    @patch("utils.injector.prefill_next_input", return_value=False)
    def test_handle_modifying_command_prints_fallback_when_prefill_fails(self, mock_prefill):
        # Capture console outputs
        captured_out = io.StringIO()
        with patch("sys.stdout", captured_out):
            handle_modifying_command("rm -rf /", "bash")

        mock_prefill.assert_called_once_with("rm -rf /")
        self.assertIn("Modifying command detected!", captured_out.getvalue())
        self.assertIn("rm -rf /", captured_out.getvalue())

    @patch("utils.injector.readline", None)
    @patch("utils.injector.inject_string_to_stdin", return_value=True)
    def test_prefill_next_input_falls_back_to_console_injection(self, mock_inject):
        self.assertTrue(prefill_next_input("rmdir temp"))
        mock_inject.assert_called_once_with("rmdir temp")

    @patch("utils.injector.sys.platform", "win32")
    @patch("utils.injector.inject_string_to_stdin", return_value=True)
    def test_prefill_next_input_prefers_windows_console_injection(self, mock_inject):
        self.assertTrue(prefill_next_input("mkdir win"))
        mock_inject.assert_called_once_with("mkdir win")

    @patch("utils.injector.readline")
    def test_prefill_next_input_redisplays_prefilled_text(self, mock_readline):
        hook_holder = {}

        def set_pre_input_hook(hook):
            hook_holder["hook"] = hook

        mock_readline.set_pre_input_hook.side_effect = set_pre_input_hook

        self.assertTrue(prefill_next_input("mkdir hi"))
        hook_holder["hook"]()

        mock_readline.insert_text.assert_called_once_with("mkdir hi")
        mock_readline.redisplay.assert_called_once_with()

    @patch("utils.injector.readline")
    def test_prefill_next_input_returns_false_when_readline_hook_setup_fails(self, mock_readline):
        mock_readline.set_pre_input_hook.side_effect = RuntimeError("unsupported")

        self.assertFalse(prefill_next_input("mkdir nope"))

    @patch("utils.injector.readline")
    def test_prefill_next_input_uses_startup_hook_for_libedit(self, mock_readline):
        hook_holder = {}
        mock_readline.__doc__ = "EditLine wrapper for libedit"

        def set_startup_hook(hook):
            hook_holder["hook"] = hook

        mock_readline.set_startup_hook.side_effect = set_startup_hook

        self.assertTrue(prefill_next_input("mkdir mac"))
        startup_hook = hook_holder["hook"]
        hook_holder["hook"]()

        mock_readline.set_startup_hook.assert_any_call(startup_hook)
        mock_readline.insert_text.assert_called_once_with("mkdir mac")
        mock_readline.set_startup_hook.assert_any_call(None)
        mock_readline.set_pre_input_hook.assert_not_called()


if __name__ == "__main__":
    unittest.main()
