import unittest
from unittest.mock import patch, MagicMock

from utils.translator import translate_intent, TranslationError


def _make_mock_response(text: str) -> MagicMock:
    """Helper: build a mock Gemini response object with a .text attribute."""
    mock_response = MagicMock()
    mock_response.text = text
    return mock_response


class TestTranslator(unittest.TestCase):

    # ------------------------------------------------------------------
    # Core translation happy-paths
    # ------------------------------------------------------------------

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_translate_list_files_cmd(self, mock_client_cls):
        """Windows CMD: list files -> dir"""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("dir")
        )
        result = translate_intent("list files", "Windows", "cmd.exe")
        self.assertEqual(result, "dir")

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_translate_list_files_powershell(self, mock_client_cls):
        """Windows PowerShell: list files -> Get-ChildItem"""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("Get-ChildItem")
        )
        result = translate_intent("list files", "Windows", "powershell")
        self.assertEqual(result, "Get-ChildItem")

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_translate_list_files_bash(self, mock_client_cls):
        """Linux bash: list files -> ls"""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("ls")
        )
        result = translate_intent("list files", "Linux", "bash")
        self.assertEqual(result, "ls")

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_translate_show_path_zsh(self, mock_client_cls):
        """macOS zsh: where am i -> pwd"""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("pwd")
        )
        result = translate_intent("where am i", "macOS", "zsh")
        self.assertEqual(result, "pwd")

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_translate_create_folder(self, mock_client_cls):
        """Create folder command is passed through correctly."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("mkdir my-project")
        )
        result = translate_intent("create folder called my-project", "Linux", "bash")
        self.assertEqual(result, "mkdir my-project")

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_translate_includes_tool_inventory_context(self, mock_client_cls):
        """Installed tools are included in the LLM prompt for command selection."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("rg TODO")
        )

        result = translate_intent(
            "find TODO comments",
            "macOS",
            "zsh",
            "- Shell Utilities: rg, grep, find",
        )

        self.assertEqual(result, "rg TODO")
        call_kwargs = mock_client_cls.return_value.models.generate_content.call_args.kwargs
        self.assertIn("Installed Tool Inventory:", call_kwargs["contents"])
        self.assertIn("- Shell Utilities: rg, grep, find", call_kwargs["contents"])

    # ------------------------------------------------------------------
    # Response sanitisation
    # ------------------------------------------------------------------

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_strips_markdown_backticks(self, mock_client_cls):
        """Backtick-wrapped responses are stripped cleanly."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("```ls -la```")
        )
        result = translate_intent("list all files with details", "Linux", "bash")
        self.assertEqual(result, "ls -la")

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_strips_language_tag_prefix(self, mock_client_cls):
        """A 'bash\\n<cmd>' prefix is trimmed to just the command."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("bash\nls -la")
        )
        result = translate_intent("list files in detail", "Linux", "bash")
        self.assertEqual(result, "ls -la")

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_strips_leading_trailing_whitespace(self, mock_client_cls):
        """Whitespace around the response is always stripped."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("  dir  \n")
        )
        result = translate_intent("show directory", "Windows", "cmd.exe")
        self.assertEqual(result, "dir")

    # ------------------------------------------------------------------
    # Error / exception paths
    # ------------------------------------------------------------------

    def test_empty_input_raises(self):
        """Empty user input must raise TranslationError immediately."""
        with self.assertRaises(TranslationError):
            translate_intent("", "Windows", "cmd.exe")

    def test_whitespace_only_input_raises(self):
        """Whitespace-only input must raise TranslationError."""
        with self.assertRaises(TranslationError):
            translate_intent("   ", "Linux", "bash")

    @patch("utils.translator.get_gemini_api_key", return_value="")
    def test_missing_api_key_raises(self, mock_get_key):
        """Missing GEMINI_API_KEY must raise TranslationError before any API call."""
        with self.assertRaises(TranslationError) as ctx:
            translate_intent("list files", "Windows", "cmd.exe")
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))
        mock_get_key.assert_called_once()

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_empty_llm_response_raises(self, mock_client_cls):
        """An empty LLM response must raise TranslationError."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("")
        )
        with self.assertRaises(TranslationError) as ctx:
            translate_intent("list files", "Linux", "bash")
        self.assertIn("empty response", str(ctx.exception))

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_api_exception_wraps_as_translation_error(self, mock_client_cls):
        """Network / API exceptions must be caught and re-raised as TranslationError."""
        mock_client_cls.return_value.models.generate_content.side_effect = (
            ConnectionError("network failure")
        )
        with self.assertRaises(TranslationError) as ctx:
            translate_intent("list files", "Linux", "bash")
        self.assertIn("Gemini API call failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
