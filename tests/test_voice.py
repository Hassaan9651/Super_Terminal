import unittest
from unittest.mock import patch, MagicMock

from utils.voice import (
    VoiceOverlayManager,
    display_available,
    parse_overlay_message,
    voice_explicitly_disabled,
)


class TestParseOverlayMessage(unittest.TestCase):

    def test_parses_transcript_message(self):
        message = parse_overlay_message('{"type": "transcript", "text": "list files"}')
        self.assertEqual(message, {"type": "transcript", "text": "list files"})

    def test_parses_error_message(self):
        message = parse_overlay_message('{"type": "error", "message": "mic denied"}')
        self.assertEqual(message["type"], "error")

    def test_rejects_non_json_line(self):
        self.assertIsNone(parse_overlay_message("Fontconfig warning: blah"))

    def test_rejects_json_without_type(self):
        self.assertIsNone(parse_overlay_message('{"text": "hello"}'))

    def test_rejects_non_dict_json(self):
        self.assertIsNone(parse_overlay_message('["transcript", "hello"]'))

    def test_rejects_non_string_type(self):
        self.assertIsNone(parse_overlay_message('{"type": 42}'))


class TestVoiceGates(unittest.TestCase):

    def test_disabled_by_flag(self):
        self.assertTrue(voice_explicitly_disabled(["--no-voice"], {}))

    def test_disabled_by_env_values(self):
        for value in ("0", "false", "off", "no", "FALSE", " Off "):
            with self.subTest(value=value):
                self.assertTrue(
                    voice_explicitly_disabled([], {"SUPERTERMINAL_VOICE": value})
                )

    def test_enabled_by_default(self):
        self.assertFalse(voice_explicitly_disabled([], {}))

    def test_enabled_when_env_truthy(self):
        self.assertFalse(voice_explicitly_disabled([], {"SUPERTERMINAL_VOICE": "1"}))

    def test_display_always_available_on_macos_and_windows(self):
        self.assertTrue(display_available("darwin", {}))
        self.assertTrue(display_available("win32", {}))

    def test_display_requires_x11_or_wayland_on_linux(self):
        self.assertFalse(display_available("linux", {}))
        self.assertTrue(display_available("linux", {"DISPLAY": ":0"}))
        self.assertTrue(display_available("linux", {"WAYLAND_DISPLAY": "wayland-0"}))


class TestVoiceOverlayManager(unittest.TestCase):

    @patch("utils.voice.subprocess.Popen", side_effect=OSError("spawn failed"))
    def test_start_returns_false_when_spawn_fails(self, mock_popen):
        manager = VoiceOverlayManager(MagicMock())
        self.assertFalse(manager.start())

    @patch("utils.voice.subprocess.Popen")
    def test_reader_dispatches_transcripts_to_voice_input(self, mock_popen):
        voice_input = MagicMock()
        process = MagicMock()
        process.stdout = iter([
            '{"type": "transcript", "text": "show git status"}\n',
            "garbage line\n",
            '{"type": "transcript", "text": "list files"}\n',
        ])
        mock_popen.return_value = process

        manager = VoiceOverlayManager(voice_input)
        manager._stopped = True  # silence the "overlay stopped" notice
        self.assertTrue(manager.start())
        manager._reader_loop()

        voice_input.feed_text.assert_any_call("show git status", submit=True)
        voice_input.feed_text.assert_any_call("list files", submit=True)

    def test_readonly_command_is_auto_submitted_as_direct_command(self):
        voice_input = MagicMock()
        manager = VoiceOverlayManager(voice_input, "macOS", "zsh")

        manager._handle_command("ls -la")

        voice_input.feed_text.assert_called_once_with("!ls -la", submit=True)
        voice_input.notify.assert_not_called()

    def test_modifying_command_waits_for_user_confirmation(self):
        voice_input = MagicMock()
        manager = VoiceOverlayManager(voice_input, "macOS", "zsh")

        manager._handle_command("rm -rf build")

        voice_input.feed_text.assert_called_once_with("!rm -rf build", submit=False)
        voice_input.notify.assert_called_once()

    def test_child_env_carries_host_context(self):
        with patch("utils.voice.subprocess.Popen") as mock_popen:
            manager = VoiceOverlayManager(MagicMock(), "macOS", "zsh", "- Tools: git")
            manager.start()
        child_env = mock_popen.call_args.kwargs["env"]
        self.assertEqual(child_env["SUPERTERMINAL_VOICE_OS"], "macOS")
        self.assertEqual(child_env["SUPERTERMINAL_VOICE_SHELL"], "zsh")
        self.assertEqual(child_env["SUPERTERMINAL_VOICE_TOOLS"], "- Tools: git")

    @patch("utils.voice.subprocess.Popen")
    def test_stop_terminates_child(self, mock_popen):
        process = MagicMock()
        mock_popen.return_value = process

        manager = VoiceOverlayManager(MagicMock())
        manager.start()
        manager.stop()

        process.stdin.close.assert_called_once()
        process.terminate.assert_called_once()


class TestVoiceInputTranscriptHandling(unittest.TestCase):

    def _make_voice_input(self):
        from utils.voice import VoiceInput

        with patch("utils.voice.PromptSession") as mock_session_cls:
            voice_input = VoiceInput()
        voice_input._session = mock_session_cls.return_value
        return voice_input

    def test_transcript_queued_when_no_prompt_active(self):
        voice_input = self._make_voice_input()
        voice_input._session.app.is_running = False

        voice_input.feed_transcript("  list   files \n")

        self.assertEqual(list(voice_input._pending), [("list files", True)])

    def test_transcript_submitted_into_running_prompt(self):
        voice_input = self._make_voice_input()
        app = voice_input._session.app
        app.is_running = True
        app.loop.call_soon_threadsafe = lambda fn, *args: fn(*args)
        app.current_buffer.text = ""

        voice_input.feed_transcript("show git status")

        app.current_buffer.insert_text.assert_called_once_with("show git status")
        app.current_buffer.validate_and_handle.assert_called_once()

    def test_transcript_not_submitted_while_user_is_typing(self):
        voice_input = self._make_voice_input()
        app = voice_input._session.app
        app.is_running = True
        app.loop.call_soon_threadsafe = lambda fn, *args: fn(*args)
        app.current_buffer.text = "git sta"

        voice_input.feed_transcript("show git status")

        app.current_buffer.insert_text.assert_called_once_with("show git status")
        app.current_buffer.validate_and_handle.assert_not_called()

    def test_empty_transcript_is_dropped(self):
        voice_input = self._make_voice_input()
        voice_input._session.app.is_running = False

        voice_input.feed_transcript("   \n ")

        self.assertEqual(len(voice_input._pending), 0)


if __name__ == "__main__":
    unittest.main()
