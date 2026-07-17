import getpass
import os
import sys
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


CONFIG_DIR_ENV = "SUPERTERMINAL_CONFIG_DIR"
CONFIG_FILE_NAME = ".env"
GEMINI_API_KEY_NAME = "GEMINI_API_KEY"


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
    return get_stored_gemini_api_key()


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


def ensure_gemini_api_key() -> str:
    existing_key = get_gemini_api_key()
    if existing_key:
        os.environ[GEMINI_API_KEY_NAME] = existing_key
        return existing_key

    print("Gemini API key is required for SuperTerminal.")
    print("Get one from: https://aistudio.google.com/apikey")
    entered_key = getpass.getpass("Enter your Gemini API key: ").strip()
    save_gemini_api_key(entered_key)
    return entered_key
