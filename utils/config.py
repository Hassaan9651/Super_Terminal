import getpass
import os
import select
import sys
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

try:
    import termios
    import tty
except ImportError:
    termios = None
    tty = None


CONFIG_DIR_ENV = "SUPERTERMINAL_CONFIG_DIR"
CONFIG_FILE_NAME = ".env"
GEMINI_API_KEY_NAME = "GEMINI_API_KEY"
ANSI_PINK = "\033[95m"
ANSI_RESET = "\033[0m"
BRACKETED_PASTE_START = "\x1b[200~"
BRACKETED_PASTE_END = "\x1b[201~"
ENABLE_BRACKETED_PASTE = "\x1b[?2004h"
DISABLE_BRACKETED_PASTE = "\x1b[?2004l"


class ConfigError(Exception):
    """Raised when SuperTerminal cannot read or write user configuration."""


def get_config_dir() -> Path:
    override = os.environ.get(CONFIG_DIR_ENV)
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "SuperTerminal"
        return Path.home() / "AppData" / "Roaming" / "SuperTerminal"

    if sys_platform_is_macos():
        return Path.home() / "Library" / "Application Support" / "SuperTerminal"

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "superterminal"
    return Path.home() / ".config" / "superterminal"


def sys_platform_is_macos() -> bool:
    return sys.platform == "darwin"


def get_config_file() -> Path:
    return get_config_dir() / CONFIG_FILE_NAME


def load_user_config() -> None:
    load_dotenv(get_config_file(), override=False)


def get_stored_gemini_api_key() -> str:
    config_file = get_config_file()
    if not config_file.exists():
        return ""
    values = dotenv_values(config_file)
    return (values.get(GEMINI_API_KEY_NAME) or "").strip()


def get_gemini_api_key() -> str:
    env_key = os.environ.get(GEMINI_API_KEY_NAME, "").strip()
    if env_key:
        return env_key

    stored_key = get_stored_gemini_api_key()
    if stored_key:
        return stored_key
    return ""


def save_gemini_api_key(api_key: str) -> Path:
    cleaned_key = (api_key or "").strip()
    if not cleaned_key:
        raise ConfigError("Gemini API key cannot be empty.")

    config_dir = get_config_dir()
    config_file = get_config_file()
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(f"{GEMINI_API_KEY_NAME}={cleaned_key}\n", encoding="utf-8")
        try:
            config_file.chmod(0o600)
        except OSError:
            pass
    except OSError as exc:
        raise ConfigError(f"Could not save Gemini API key: {exc}") from exc

    os.environ[GEMINI_API_KEY_NAME] = cleaned_key
    return config_file


def format_secret_pasted_line(secret: str) -> str:
    secret_length = len((secret or "").strip())
    return f"{ANSI_PINK}<secret pasted - length:{secret_length}>{ANSI_RESET}"


def print_secret_pasted(secret: str) -> None:
    print(format_secret_pasted_line(secret))


def read_secret(prompt_text: str) -> str:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return getpass.getpass(prompt_text)

    if os.name == "nt" or termios is None or tty is None:
        return getpass.getpass(prompt_text)

    return read_secret_with_paste_detection(prompt_text)


def read_secret_with_paste_detection(prompt_text: str) -> str:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    buffer = []
    try:
        sys.stdout.write(ENABLE_BRACKETED_PASTE)
        sys.stdout.write(prompt_text)
        sys.stdout.flush()
        tty.setraw(fd)

        while True:
            char = sys.stdin.read(1)
            if char in ("\r", "\n"):
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                return "".join(buffer)
            if char == "\x03":
                raise KeyboardInterrupt
            if char in ("\x7f", "\b"):
                if buffer:
                    buffer.pop()
                continue
            if char == "\x1b":
                sequence = read_escape_sequence(char)
                if sequence == BRACKETED_PASTE_START:
                    pasted_text = read_until(BRACKETED_PASTE_END)
                    buffer.extend(pasted_text)
                    sys.stdout.write("\r\033[2K")
                    sys.stdout.write(prompt_text)
                    sys.stdout.write(format_secret_pasted_line("".join(buffer)))
                    sys.stdout.flush()
                continue
            buffer.append(char)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write(DISABLE_BRACKETED_PASTE)
        sys.stdout.flush()


def read_escape_sequence(first_char: str) -> str:
    sequence = first_char
    while len(sequence) < len(BRACKETED_PASTE_START):
        readable, _, _ = select.select([sys.stdin], [], [], 0.05)
        if not readable:
            break
        sequence += sys.stdin.read(1)
        if sequence.endswith("~"):
            break
    return sequence


def read_until(terminator: str) -> str:
    text = ""
    while terminator not in text:
        text += sys.stdin.read(1)
    pasted_text, _, _ = text.partition(terminator)
    return pasted_text


def ensure_gemini_api_key() -> str:
    existing_key = get_gemini_api_key()
    if existing_key:
        os.environ[GEMINI_API_KEY_NAME] = existing_key
        return existing_key

    print("Gemini API key is required for SuperTerminal.")
    print("Get one from: https://aistudio.google.com/apikey")
    entered_key = read_secret("Enter your Gemini API key: ").strip()
    save_gemini_api_key(entered_key)
    return entered_key


def update_gemini_api_key() -> str:
    entered_key = read_secret("Enter your new Gemini API key: ").strip()
    save_gemini_api_key(entered_key)
    return entered_key
