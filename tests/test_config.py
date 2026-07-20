import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.config import (
    ANSI_PINK,
    ANSI_RESET,
    CONFIG_DIR_ENV,
    GEMINI_API_KEY_NAME,
    ensure_gemini_api_key,
    format_secret_pasted_line,
    get_config_file,
    get_gemini_api_key,
    read_secret,
    save_gemini_api_key,
    update_gemini_api_key,
)


TEST_KEY = "test-gemini-key"
ENV_KEY = "env-key"
FILE_KEY = "file-key"
PROMPTED_KEY = "prompted-key"
UPDATED_KEY = "updated-key"


class TestConfig(unittest.TestCase):

    def test_save_gemini_api_key_writes_user_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {CONFIG_DIR_ENV: tmpdir}, clear=False):
                os.environ.pop(GEMINI_API_KEY_NAME, None)

                config_file = save_gemini_api_key(TEST_KEY)

                self.assertEqual(config_file, Path(tmpdir) / ".env")
                self.assertIn(f"GEMINI_API_KEY={TEST_KEY}", config_file.read_text())
                self.assertEqual(os.environ[GEMINI_API_KEY_NAME], TEST_KEY)

    def test_get_gemini_api_key_prefers_environment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(
                os.environ,
                {
                    CONFIG_DIR_ENV: tmpdir,
                    GEMINI_API_KEY_NAME: ENV_KEY,
                },
                clear=False,
            ):
                get_config_file().write_text(f"GEMINI_API_KEY={FILE_KEY}\n")

                self.assertEqual(get_gemini_api_key(), ENV_KEY)

    def test_any_non_empty_key_shape_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(
                os.environ,
                {
                    CONFIG_DIR_ENV: tmpdir,
                    GEMINI_API_KEY_NAME: "AQ.Ab8RN6LaDGfUF_UoCLaDgKgRrb94WP7tBaKytxGIOdX9rK6s5w",
                },
                clear=False,
            ):
                self.assertEqual(
                    get_gemini_api_key(),
                    "AQ.Ab8RN6LaDGfUF_UoCLaDgKgRrb94WP7tBaKytxGIOdX9rK6s5w",
                )

    def test_format_secret_pasted_line_masks_value_and_shows_length(self):
        formatted = format_secret_pasted_line("  secret-key  ")

        self.assertEqual(
            formatted,
            f"{ANSI_PINK}<secret pasted - length:10>{ANSI_RESET}",
        )
        self.assertNotIn("secret-key", formatted)

    @patch("utils.config.getpass.getpass", return_value=PROMPTED_KEY)
    @patch("utils.config.sys.stdin")
    @patch("utils.config.sys.stdout")
    def test_read_secret_falls_back_to_getpass_without_tty(self, mock_stdout, mock_stdin, mock_getpass):
        mock_stdin.isatty.return_value = False
        mock_stdout.isatty.return_value = True

        self.assertEqual(read_secret("Secret: "), PROMPTED_KEY)

        mock_getpass.assert_called_once_with("Secret: ")

    @patch("utils.config.read_secret", return_value=PROMPTED_KEY)
    @patch("utils.config.print")
    def test_ensure_gemini_api_key_prompts_and_saves_when_missing(self, mock_print, mock_read_secret):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {CONFIG_DIR_ENV: tmpdir}, clear=False):
                os.environ.pop(GEMINI_API_KEY_NAME, None)

                key = ensure_gemini_api_key()

                self.assertEqual(key, PROMPTED_KEY)
                self.assertEqual(get_gemini_api_key(), PROMPTED_KEY)
                mock_read_secret.assert_called_once_with("Enter your Gemini API key: ")
                printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
                self.assertNotIn(PROMPTED_KEY, printed)

    @patch("utils.config.read_secret", return_value=UPDATED_KEY)
    def test_update_gemini_api_key_overwrites_saved_key(self, mock_read_secret):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {CONFIG_DIR_ENV: tmpdir}, clear=False):
                os.environ.pop(GEMINI_API_KEY_NAME, None)
                save_gemini_api_key(PROMPTED_KEY)

                key = update_gemini_api_key()

                self.assertEqual(key, UPDATED_KEY)
                self.assertEqual(get_gemini_api_key(), UPDATED_KEY)
                self.assertIn(f"GEMINI_API_KEY={UPDATED_KEY}", get_config_file().read_text())
                mock_read_secret.assert_called_once_with("Enter your new Gemini API key: ")


if __name__ == "__main__":
    unittest.main()
