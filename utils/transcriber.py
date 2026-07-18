import os

from dotenv import load_dotenv
import google.genai as genai
from utils.config import get_gemini_api_key, load_user_config

# Load GEMINI_API_KEY (and any other vars) from the .env file in the project root.
# override=False so a key already set in the environment takes precedence.
load_dotenv(override=False)
load_user_config()


class TranscriptionError(Exception):
    """Exception raised when speech-to-text transcription fails."""
    pass


# gemini-3.5-flash handles audio 2-4x faster than the flash-lite tier
# (measured ~3s vs 6-14s per request). Override with SUPERTERMINAL_VOICE_MODEL.
_STT_MODEL = os.environ.get("SUPERTERMINAL_VOICE_MODEL", "gemini-3.5-flash")

# Reused across calls: creating a genai.Client per request adds a full
# connection setup to every voice command's latency.
_client = None


def _get_client(api_key: str):
    global _client
    if _client is None:
        _client = genai.Client(api_key=api_key)
    return _client


def warm_up_client() -> None:
    """Pre-creates the API client so the first voice command is faster."""
    api_key = get_gemini_api_key()
    if api_key:
        try:
            _get_client(api_key)
        except Exception:
            pass


_STT_INSTRUCTION = """\
You are a speech-to-text engine for a terminal assistant.

YOUR ONLY JOB:
Transcribe the spoken audio into plain text, verbatim.

STRICT OUTPUT RULES — VIOLATING ANY RULE IS A CRITICAL FAILURE:
1. Output ONLY the transcript text. Nothing else.
2. Do NOT add explanations, labels, quotes, or markdown formatting.
3. Do NOT add trailing punctuation the speaker did not clearly dictate.
4. Do NOT attempt to answer or act on the request — only transcribe it.
5. If the audio contains no intelligible speech, output nothing at all.
"""

_SPEECH_TO_COMMAND_INSTRUCTION = """\
You are SuperTerminal, a world-class natural-language-to-terminal-command translator.
The user's request arrives as SPOKEN AUDIO instead of typed text.

CONTEXT YOU RECEIVE:
- Spoken audio: the user's natural-English request.
- Host OS: the operating system the user is running (Windows, macOS, or Linux).
- Active Shell: the shell profile detected at runtime (cmd.exe, powershell, bash, zsh).
- Installed Tool Inventory: common languages, package managers, developer CLIs,
  and shell utilities currently detected on PATH.

YOUR ONLY JOB:
Understand the spoken request and translate it into the single, exact,
executable shell command that is correct for the given Host OS and Active
Shell combination.

STRICT OUTPUT RULES — VIOLATING ANY RULE IS A CRITICAL FAILURE:
1. Output ONLY the raw command string. Nothing else.
2. Do NOT wrap the command in markdown fences (``` or `).
3. Do NOT include explanations, notes, warnings, caveats, or pleasantries.
4. Do NOT add a trailing newline or any leading/trailing whitespace.
5. Do NOT output multiple commands unless the spoken request explicitly requires chaining.
6. If the request is ambiguous, output the safest, most common interpretation.
7. Prefer detected tools from Installed Tool Inventory when they are relevant.
8. Do NOT assume optional package managers or third-party CLIs exist if they are
   not listed. Prefer built-in shell/OS commands when no suitable detected tool
   is available.
9. If the audio contains no intelligible spoken request, output nothing at all.
"""


def _extract_text_response(response) -> str:
    """
    Extracts only text parts from a Gemini response.

    The SDK's response.text convenience property can warn when a response also
    contains non-text parts such as thought_signature metadata.
    """
    text_parts = []
    candidates = getattr(response, "candidates", None) or []

    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                text_parts.append(text)

    if text_parts:
        return "".join(text_parts)

    return getattr(response, "text", "") or ""


def transcribe_wav_bytes(wav_bytes: bytes) -> str:
    """
    Transcribes in-memory WAV audio into plain text using the Gemini API.

    Args:
        wav_bytes (bytes): A complete WAV file (header + frames) in memory.

    Returns:
        str: The verbatim transcript, stripped of surrounding whitespace.
             Empty string when the audio contained no intelligible speech.

    Raises:
        TranscriptionError: If the API key is missing, the audio is empty,
                            or the API call fails.
    """
    if not wav_bytes:
        raise TranscriptionError("No audio data to transcribe.")

    api_key = get_gemini_api_key()
    if not api_key:
        raise TranscriptionError(
            "GEMINI_API_KEY is not set. "
            "Run SuperTerminal and enter your Gemini API key when prompted."
        )

    try:
        client = _get_client(api_key)

        response = client.models.generate_content(
            model=_STT_MODEL,
            config=genai.types.GenerateContentConfig(
                system_instruction=_STT_INSTRUCTION,
                temperature=0.0,        # Deterministic output for transcription
                max_output_tokens=256,  # Spoken commands are short
            ),
            contents=[
                genai.types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"),
                "Transcribe this audio.",
            ],
        )

        return _extract_text_response(response).strip()

    except TranscriptionError:
        raise
    except Exception as exc:
        raise TranscriptionError(f"Gemini transcription failed: {exc}") from exc


def _sanitize_command(raw: str) -> str:
    """Strips markdown fences and language-tag prefixes, like the translator."""
    command = (raw or "").strip().strip("`").strip()
    lines = command.splitlines()
    if len(lines) > 1 and not lines[0].strip().startswith(("-", "/", ".", "$")):
        first = lines[0].strip().lower()
        if first in ("bash", "zsh", "sh", "powershell", "cmd", "shell"):
            command = "\n".join(lines[1:]).strip()
    return command


def transcribe_to_shell_command(
    wav_bytes: bytes,
    os_name: str,
    shell_name: str,
    tool_context: str = "",
) -> str:
    """
    Translates spoken audio directly into a shell command in ONE Gemini call
    (instead of transcribe + translate), halving voice-command latency.

    Returns an empty string when the audio contained no intelligible request.

    Raises:
        TranscriptionError: If the API key is missing, the audio is empty,
                            or the API call fails.
    """
    if not wav_bytes:
        raise TranscriptionError("No audio data to transcribe.")

    api_key = get_gemini_api_key()
    if not api_key:
        raise TranscriptionError(
            "GEMINI_API_KEY is not set. "
            "Run SuperTerminal and enter your Gemini API key when prompted."
        )

    context_prompt = (
        f"Host OS: {os_name}\n"
        f"Active Shell: {shell_name}\n"
        f"Installed Tool Inventory:\n"
        f"{tool_context or 'No optional tool inventory is available.'}"
    )

    try:
        client = _get_client(api_key)

        response = client.models.generate_content(
            model=_STT_MODEL,
            config=genai.types.GenerateContentConfig(
                system_instruction=_SPEECH_TO_COMMAND_INSTRUCTION,
                temperature=0.0,
                max_output_tokens=256,
            ),
            contents=[
                genai.types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"),
                context_prompt,
            ],
        )

        return _sanitize_command(_extract_text_response(response))

    except TranscriptionError:
        raise
    except Exception as exc:
        raise TranscriptionError(f"Gemini transcription failed: {exc}") from exc
