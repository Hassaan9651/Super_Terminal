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


class TestConfig(unittest.TestCase):

    def test_save_gemini_api_key_writes_user_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {CONFIG_DIR_ENV: tmpdir}, clear=False):
                os.environ.pop(GEMINI_API_KEY_NAME, None)

                config_file = save_gemini_api_key("test-gemini-key")

                self.assertEqual(config_file, Path(tmpdir) / ".env")
                self.assertIn("GEMINI_API_KEY=test-gemini-key", config_file.read_text())
                self.assertEqual(os.environ[GEMINI_API_KEY_NAME], "test-gemini-key")

    def test_get_gemini_api_key_prefers_environment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(
                os.environ,
                {
                    CONFIG_DIR_ENV: tmpdir,
                    GEMINI_API_KEY_NAME: "env-key",
                },
                clear=False,
            ):
                get_config_file().write_text("GEMINI_API_KEY=file-key\n")

                self.assertEqual(get_gemini_api_key(), "env-key")

    @patch("utils.config.getpass.getpass", return_value="prompted-key")
    def test_ensure_gemini_api_key_prompts_and_saves_when_missing(self, mock_getpass):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {CONFIG_DIR_ENV: tmpdir}, clear=False):
                os.environ.pop(GEMINI_API_KEY_NAME, None)

                key = ensure_gemini_api_key()

                self.assertEqual(key, "prompted-key")
                self.assertEqual(get_gemini_api_key(), "prompted-key")
                mock_getpass.assert_called_once()


if __name__ == "__main__":
    unittest.main()
