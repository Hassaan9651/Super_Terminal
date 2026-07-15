import unittest
from unittest.mock import patch, MagicMock
import sys
import io

from utils.executor import execute_readonly_command
from utils.injector import handle_modifying_command


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
            execute_readonly_command("ls")

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
            execute_readonly_command("ls non_existent")

        self.assertIn("cannot access", captured_err.getvalue())
        mock_run.assert_called_once_with("ls non_existent", shell=True, text=True, capture_output=True)

    @patch("subprocess.run")
    @patch("builtins.input", return_value="y")
    def test_handle_modifying_command_confirmed(self, mock_input, mock_run):
        # Capture console outputs
        captured_out = io.StringIO()
        with patch("sys.stdout", captured_out):
            handle_modifying_command("mkdir new_dir", "bash")

        # Verify command was executed
        mock_run.assert_called_once_with("mkdir new_dir", shell=True, text=True)
        self.assertIn("Security Warning", captured_out.getvalue())
        self.assertIn("Proposed Command: mkdir new_dir", captured_out.getvalue())

    @patch("subprocess.run")
    @patch("builtins.input", return_value="n")
    def test_handle_modifying_command_cancelled(self, mock_input, mock_run):
        # Capture console outputs
        captured_out = io.StringIO()
        with patch("sys.stdout", captured_out):
            handle_modifying_command("rm -rf /", "bash")

        # Verify command was NOT executed
        mock_run.assert_not_called()
        self.assertIn("Command canceled by user", captured_out.getvalue())

    @patch("subprocess.run")
    @patch("builtins.input", return_value="invalid")
    def test_handle_modifying_command_invalid_input(self, mock_input, mock_run):
        # Capture console outputs
        captured_out = io.StringIO()
        with patch("sys.stdout", captured_out):
            handle_modifying_command("rmdir temp", "bash")

        # Verify command was NOT executed on invalid input (failsafe to cancel)
        mock_run.assert_not_called()
        self.assertIn("Command canceled by user", captured_out.getvalue())


if __name__ == "__main__":
    unittest.main()
