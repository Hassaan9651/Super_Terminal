import unittest
from unittest.mock import patch, MagicMock

from utils.transcriber import (
    TranscriptionError,
    transcribe_to_shell_command,
    transcribe_wav_bytes,
)

FAKE_WAV = b"RIFF....WAVEfmt fake-wav-bytes"


def _make_mock_response(text: str) -> MagicMock:
    """Helper: build a mock Gemini response object with a .text attribute."""
    mock_response = MagicMock()
    mock_response.text = text
    return mock_response


class TestTranscriber(unittest.TestCase):

    def setUp(self):
        import utils.transcriber
        utils.transcriber._client = None

    @patch("utils.transcriber.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_transcribes_audio_to_text(self, mock_client_cls):
        """WAV bytes are transcribed to the returned transcript text."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("list all files sorted by size")
        )
        result = transcribe_wav_bytes(FAKE_WAV)
        self.assertEqual(result, "list all files sorted by size")

    @patch("utils.transcriber.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_strips_surrounding_whitespace(self, mock_client_cls):
        """Whitespace around the transcript is stripped."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("  show git status \n")
        )
        result = transcribe_wav_bytes(FAKE_WAV)
        self.assertEqual(result, "show git status")

    @patch("utils.transcriber.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_audio_sent_with_wav_mime_type(self, mock_client_cls):
        """The WAV bytes must be sent as an audio/wav Part."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("pwd")
        )
        with patch("utils.transcriber.genai.types.Part.from_bytes") as mock_from_bytes:
            transcribe_wav_bytes(FAKE_WAV)
        mock_from_bytes.assert_called_once_with(data=FAKE_WAV, mime_type="audio/wav")

    @patch("utils.transcriber.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_unintelligible_audio_returns_empty_string(self, mock_client_cls):
        """Silence/no speech yields an empty transcript, not an error."""
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("")
        )
        result = transcribe_wav_bytes(FAKE_WAV)
        self.assertEqual(result, "")

    def test_empty_audio_raises(self):
        """Empty audio bytes must raise TranscriptionError immediately."""
        with self.assertRaises(TranscriptionError):
            transcribe_wav_bytes(b"")

    @patch("utils.transcriber.get_gemini_api_key", return_value="")
    def test_missing_api_key_raises(self, mock_get_key):
        """Missing GEMINI_API_KEY must raise TranscriptionError before any API call."""
        with self.assertRaises(TranscriptionError) as ctx:
            transcribe_wav_bytes(FAKE_WAV)
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))
        mock_get_key.assert_called_once()

    @patch("utils.transcriber.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_api_exception_wraps_as_transcription_error(self, mock_client_cls):
        """Network / API exceptions must be caught and re-raised as TranscriptionError."""
        mock_client_cls.return_value.models.generate_content.side_effect = (
            ConnectionError("network failure")
        )
        with self.assertRaises(TranscriptionError) as ctx:
            transcribe_wav_bytes(FAKE_WAV)
        self.assertIn("Gemini transcription failed", str(ctx.exception))


class TestTranscribeToShellCommand(unittest.TestCase):

    def setUp(self):
        import utils.transcriber
        utils.transcriber._client = None

    @patch("utils.transcriber.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_translates_speech_to_command(self, mock_client_cls):
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("ls -laS")
        )
        result = transcribe_to_shell_command(FAKE_WAV, "macOS", "zsh", "- Tools: ls")
        self.assertEqual(result, "ls -laS")

        call_kwargs = mock_client_cls.return_value.models.generate_content.call_args.kwargs
        self.assertIn("Host OS: macOS", call_kwargs["contents"][1])
        self.assertIn("Active Shell: zsh", call_kwargs["contents"][1])

    @patch("utils.transcriber._client", None)
    @patch("utils.transcriber.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_strips_markdown_fences_from_command(self, mock_client_cls):
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("```bash\nls -la\n```")
        )
        result = transcribe_to_shell_command(FAKE_WAV, "Linux", "bash")
        self.assertEqual(result, "ls -la")

    @patch("utils.transcriber._client", None)
    @patch("utils.transcriber.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_unintelligible_audio_returns_empty_command(self, mock_client_cls):
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("")
        )
        self.assertEqual(transcribe_to_shell_command(FAKE_WAV, "macOS", "zsh"), "")

    def test_empty_audio_raises(self):
        with self.assertRaises(TranscriptionError):
            transcribe_to_shell_command(b"", "macOS", "zsh")

    @patch("utils.transcriber._client", None)
    @patch("utils.transcriber.genai.Client")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzattttttttttttttttttttttttttttttttttt"})
    def test_client_is_reused_across_calls(self, mock_client_cls):
        mock_client_cls.return_value.models.generate_content.return_value = (
            _make_mock_response("pwd")
        )
        transcribe_to_shell_command(FAKE_WAV, "macOS", "zsh")
        transcribe_to_shell_command(FAKE_WAV, "macOS", "zsh")
        self.assertEqual(mock_client_cls.call_count, 1)


if __name__ == "__main__":
    unittest.main()
