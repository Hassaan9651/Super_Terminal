import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.config import (
    CONFIG_DIR_ENV,
    GEMINI_API_KEY_NAME,
    ensure_gemini_api_key,
    get_config_file,
    get_gemini_api_key,
    save_gemini_api_key,
)


TEST_KEY = "test-gemini-key"
ENV_KEY = "env-key"
FILE_KEY = "file-key"
PROMPTED_KEY = "prompted-key"


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

    @patch("utils.config.getpass.getpass", return_value=PROMPTED_KEY)
    def test_ensure_gemini_api_key_prompts_and_saves_when_missing(self, mock_getpass):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {CONFIG_DIR_ENV: tmpdir}, clear=False):
                os.environ.pop(GEMINI_API_KEY_NAME, None)

                key = ensure_gemini_api_key()

                self.assertEqual(key, PROMPTED_KEY)
                self.assertEqual(get_gemini_api_key(), PROMPTED_KEY)
                mock_getpass.assert_called_once()


if __name__ == "__main__":
    unittest.main()
