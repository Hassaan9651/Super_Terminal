import unittest
from unittest.mock import patch, MagicMock

from utils.translator import translate_intent, TranslationError


def _make_mock_response(text: str) -> MagicMock:
    """Helper: build a mock Gemini response object with a .text attribute."""
    mock_response = MagicMock()
    mock_response.text = text
    return mock_response


def _make_parts_response(*parts: MagicMock) -> MagicMock:
    """Helper: build a mock Gemini response with candidate content parts."""
    mock_response = MagicMock()
    mock_response.candidates = [
        MagicMock(content=MagicMock(parts=list(parts)))
    ]
    type(mock_response).text = property(
        lambda self: (_ for _ in ()).throw(AssertionError("response.text accessed"))
    )
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
    def test_translate_cd_home_relative_path(self, mock_client_cls):
        """Home-folder directory changes should keep ~ in the generated command."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("cd ~/Downloads")
        )
        result = translate_intent("go to downloads", "macOS", "zsh")
        self.assertEqual(result, "cd ~/Downloads")

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

    @patch("utils.translator.load_personality_context", return_value="- Treat `py` as Python files.")
    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_translate_includes_personality_profile(self, mock_client_cls, mock_load_context):
        """Compact local adaptation profile is included in the LLM prompt."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("find . -name '*.py'")
        )

        result = translate_intent("show py files", "macOS", "zsh")

        self.assertEqual(result, "find . -name '*.py'")
        call_kwargs = mock_client_cls.return_value.models.generate_content.call_args.kwargs
        self.assertIn("User Adaptation Profile:", call_kwargs["contents"])
        self.assertIn("Treat `py` as Python files", call_kwargs["contents"])
        mock_load_context.assert_called_once()

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

    @patch("utils.translator.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_extracts_text_parts_without_response_text_warning(self, mock_client_cls):
        """Non-text response parts are ignored without touching response.text."""
        text_part = MagicMock(text="mkdir demo")
        thought_part = MagicMock()
        del thought_part.text
        thought_part.thought_signature = "opaque"
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_parts_response(thought_part, text_part)
        )

        result = translate_intent("make a folder called demo", "Linux", "bash")

        self.assertEqual(result, "mkdir demo")

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
