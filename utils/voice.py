"""
Parent-side voice support for SuperTerminal.

Spawns the floating mic overlay (utils/overlay.py) as a child process and
feeds the transcripts it emits into the interactive prompt as if the user
had typed them and pressed Enter.

Because macOS no longer permits TIOCSTI-style keystroke injection, voice
mode swaps the plain input() prompt for a prompt_toolkit PromptSession
(already a project dependency): transcripts are submitted into the live
prompt thread-safely via the application event loop. When voice is
disabled or unavailable, main.py keeps its original input() path.
"""

import atexit
import json
import os
import subprocess
import sys
import threading
from collections import deque
from pathlib import Path
from typing import Optional

try:
    import readline
except ImportError:
    readline = None

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.application import run_in_terminal
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import InMemoryHistory
except ImportError:
    PromptSession = None
    run_in_terminal = None
    Completer = object
    Completion = None
    InMemoryHistory = None

from utils.classifier import classify_command
from utils.completion import _complete_path_prefix

VOICE_DISABLE_ENV = "SUPERTERMINAL_VOICE"
VOICE_DISABLE_FLAG = "--no-voice"
OVERLAY_MODULE = "utils.overlay"
COMPLETER_DELIMS = " \t\n;|&<>"

ANSI_DIM = "\033[2m"
ANSI_RESET = "\033[0m"


def print_voice_notice(message: str) -> None:
    print(f"{ANSI_DIM}🎤 {message}{ANSI_RESET}")


def voice_explicitly_disabled(argv=None, environ=None) -> bool:
    argv = sys.argv[1:] if argv is None else argv
    environ = os.environ if environ is None else environ
    if VOICE_DISABLE_FLAG in argv:
        return True
    return environ.get(VOICE_DISABLE_ENV, "").strip().lower() in ("0", "false", "off", "no")


def display_available(platform: str = None, environ=None) -> bool:
    platform = platform or sys.platform
    environ = os.environ if environ is None else environ
    if platform == "win32" or platform == "darwin":
        return True
    return bool(environ.get("DISPLAY") or environ.get("WAYLAND_DISPLAY"))


def parse_overlay_message(line: str) -> Optional[dict]:
    """Parses one overlay stdout line; returns None for anything malformed."""
    try:
        message = json.loads(line)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        return None
    return message


class _PathCompleter(Completer):
    """prompt_toolkit adapter around the readline path completion logic."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        token_start = max(text.rfind(delim) for delim in COMPLETER_DELIMS) + 1
        token = text[token_start:]
        if not token:
            return
        for match in _complete_path_prefix(token):
            yield Completion(match, start_position=-len(token))


def _history_from_readline():
    """Seeds a prompt_toolkit history with the persisted readline history."""
    history = InMemoryHistory()
    if readline is not None:
        for index in range(1, readline.get_current_history_length() + 1):
            item = readline.get_history_item(index)
            if item:
                history.append_string(item)
    return history


class VoiceInput:
    """A prompt line that voice transcripts can be submitted into.

    prompt() behaves like input(): it blocks the calling (main) thread and
    returns the accepted line, raising EOFError/KeyboardInterrupt the same
    way. feed_transcript() may be called from any thread; if a prompt is
    active and empty the transcript is auto-submitted, if the user is
    mid-typing it is inserted without submitting, and if no prompt is
    active it is queued for the next one.
    """

    def __init__(self):
        if PromptSession is None:
            raise RuntimeError("prompt_toolkit is required for voice input.")
        self._session = PromptSession(
            history=_history_from_readline(),
            completer=_PathCompleter(),
            complete_while_typing=False,
        )
        self._pending = deque()
        self._lock = threading.Lock()

    def prompt(self, message) -> str:
        line = self._session.prompt(message, pre_run=self._drain_pending)
        # Mirror accepted lines into readline so the existing persistent
        # history (utils/history.py) keeps recording them.
        if readline is not None and line and line.strip():
            try:
                readline.add_history(line)
            except Exception:
                pass
        return line

    def feed_text(self, text: str, submit: bool = True) -> None:
        """Puts text on the prompt from any thread; submits it when asked."""
        cleaned = " ".join((text or "").split())
        if not cleaned:
            return
        app = self._session.app
        try:
            if app.is_running and app.loop is not None:
                app.loop.call_soon_threadsafe(self._insert_into_prompt, cleaned, submit)
                return
        except Exception:
            pass
        with self._lock:
            self._pending.append((cleaned, submit))

    def feed_transcript(self, text: str) -> None:
        self.feed_text(text, submit=True)

    def notify(self, message: str) -> None:
        """Prints a line without corrupting an active prompt. Thread-safe."""
        app = self._session.app
        try:
            if app.is_running and app.loop is not None:
                app.loop.call_soon_threadsafe(
                    lambda: run_in_terminal(lambda: print(message))
                )
                return
        except Exception:
            pass
        print(message)

    def _drain_pending(self) -> None:
        with self._lock:
            if not self._pending:
                return
            text, submit = self._pending.popleft()
        buffer = self._session.app.current_buffer
        buffer.insert_text(text)
        if submit:
            buffer.validate_and_handle()

    def _insert_into_prompt(self, text: str, submit: bool) -> None:
        app = self._session.app
        if not app.is_running:
            with self._lock:
                self._pending.append((text, submit))
            return
        buffer = app.current_buffer
        if buffer.text.strip():
            # The user is mid-typing: add the words but let them submit.
            buffer.insert_text(text)
            return
        buffer.insert_text(text)
        if submit:
            buffer.validate_and_handle()


class VoiceOverlayManager:
    """Owns the overlay child process and its stdout reader thread.

    The overlay translates speech straight into a shell command (one Gemini
    call). Read-only commands are auto-submitted as direct `!` commands;
    modifying commands are placed on the prompt unsubmitted so the user
    reviews them and presses Enter — the same gate typed input gets.
    """

    def __init__(self, voice_input: "VoiceInput", os_name: str = "",
                 shell_name: str = "", tool_context: str = ""):
        self._voice_input = voice_input
        self._os_name = os_name
        self._shell_name = shell_name
        self._tool_context = tool_context
        self._process = None
        self._stopped = False

    def start(self) -> bool:
        project_root = Path(__file__).resolve().parent.parent
        child_env = dict(os.environ)
        child_env["SUPERTERMINAL_VOICE_OS"] = self._os_name
        child_env["SUPERTERMINAL_VOICE_SHELL"] = self._shell_name
        child_env["SUPERTERMINAL_VOICE_TOOLS"] = self._tool_context
        try:
            self._process = subprocess.Popen(
                [sys.executable, "-m", OVERLAY_MODULE],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=str(project_root),
                env=child_env,
                text=True,
                encoding="utf-8",
            )
        except Exception:
            return False
        threading.Thread(target=self._reader_loop, daemon=True).start()
        return True

    def _handle_command(self, command: str) -> None:
        command = (command or "").strip()
        if not command:
            return
        direct_command = f"!{command}"
        if classify_command(command, self._shell_name) == "READ-ONLY":
            self._voice_input.feed_text(direct_command, submit=True)
        else:
            self._voice_input.notify("Modifying command detected!")
            self._voice_input.feed_text(direct_command, submit=False)

    def _notify(self, message: str) -> None:
        self._voice_input.notify(f"{ANSI_DIM}🎤 {message}{ANSI_RESET}")

    def _reader_loop(self) -> None:
        try:
            for line in self._process.stdout:
                message = parse_overlay_message(line)
                if message is None:
                    continue
                if message.get("type") == "command":
                    self._handle_command(message.get("text", ""))
                elif message.get("type") == "transcript":
                    self._voice_input.feed_text(message.get("text", ""), submit=True)
                elif message.get("type") == "error":
                    self._notify(f"Voice: {message.get('message', 'unknown error')}")
        except Exception:
            pass
        if not self._stopped:
            self._notify("Voice overlay stopped. Typed input keeps working as usual.")

    def stop(self) -> None:
        self._stopped = True
        process = self._process
        if process is None:
            return
        try:
            process.stdin.close()
        except Exception:
            pass
        try:
            process.terminate()
            process.wait(timeout=2)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass


def create_voice_input() -> Optional[VoiceInput]:
    try:
        return VoiceInput()
    except Exception:
        return None


def start_voice_overlay(
    voice_input: VoiceInput,
    os_name: str = "",
    shell_name: str = "",
    tool_context: str = "",
    argv=None,
    environ=None,
) -> Optional[VoiceOverlayManager]:
    """Spawns the mic overlay when the environment supports it.

    Returns the running manager, or None when voice is disabled/unavailable
    (in which case the caller should fall back to the plain input() prompt).
    """
    if voice_explicitly_disabled(argv, environ):
        return None
    if not display_available(environ=environ):
        return None
    try:
        # Piped/redirected sessions must keep the plain input() prompt.
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            return None
    except Exception:
        return None

    manager = VoiceOverlayManager(voice_input, os_name, shell_name, tool_context)
    if not manager.start():
        print_voice_notice("Voice overlay could not start. Continuing without voice input.")
        return None

    atexit.register(manager.stop)
    return manager
