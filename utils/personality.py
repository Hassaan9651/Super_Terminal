from datetime import datetime, timezone
from pathlib import Path

from utils.config import get_config_dir


PERSONALITY_DIR_NAME = "skills"
PERSONALITY_FILE_NAME = "personality.md"
MAX_LEARNED_NOTES = 40
MAX_PROMPT_CHARS = 4000

PERSONALITY_HEADER = """# SuperTerminal User Adaptation

This file is maintained locally by SuperTerminal.
It stores compact lessons from read-only retries and rephrases so future command
translation can better match the user's wording and expectations.

## Learned Read-Only Retry Patterns
"""


def get_personality_file() -> Path:
    return get_config_dir() / PERSONALITY_DIR_NAME / PERSONALITY_FILE_NAME


def ensure_personality_file(personality_file: Path = None) -> Path:
    target = personality_file or get_personality_file()
    if target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(PERSONALITY_HEADER, encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass
    return target


def build_retry_learning_note(signal: str, previous, current) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    return (
        f"- {timestamp} [{signal}] When the user rephrased "
        f"\"{previous.user_input}\" as \"{current.user_input}\", the expected "
        f"read-only command shape was `{current.translated_command}`."
    )


def append_retry_learning(
    signal: str,
    previous,
    current,
    personality_file: Path = None,
) -> bool:
    target = personality_file or get_personality_file()
    try:
        ensure_personality_file(target)
        existing = target.read_text(encoding="utf-8")
        notes = [
            line
            for line in existing.splitlines()
            if line.startswith("- ")
        ]
        notes.append(build_retry_learning_note(signal, previous, current))
        notes = notes[-MAX_LEARNED_NOTES:]
        content = PERSONALITY_HEADER.rstrip() + "\n" + "\n".join(notes) + "\n"
        target.write_text(content, encoding="utf-8")
        try:
            target.chmod(0o600)
        except OSError:
            pass
        return True
    except OSError:
        return False


def load_personality_context(personality_file: Path = None) -> str:
    target = personality_file or get_personality_file()
    try:
        if not target.exists():
            return ""
        content = target.read_text(encoding="utf-8").strip()
    except OSError:
        return ""

    if not content or content == PERSONALITY_HEADER.strip():
        return ""

    return content[-MAX_PROMPT_CHARS:]
