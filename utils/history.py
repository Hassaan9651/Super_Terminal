import atexit
from pathlib import Path

from utils.config import get_config_dir

try:
    import readline
except ImportError:
    readline = None


HISTORY_FILE_NAME = "history"
DEFAULT_HISTORY_LENGTH = 1000


def get_history_file() -> Path:
    return get_config_dir() / HISTORY_FILE_NAME


def load_history(history_file: Path = None) -> bool:
    if readline is None:
        return False

    target = history_file or get_history_file()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            readline.read_history_file(str(target))
        readline.set_history_length(DEFAULT_HISTORY_LENGTH)
        return True
    except OSError:
        return False


def save_history(history_file: Path = None) -> bool:
    if readline is None:
        return False

    target = history_file or get_history_file()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        readline.write_history_file(str(target))
        try:
            target.chmod(0o600)
        except OSError:
            pass
        return True
    except OSError:
        return False


def enable_persistent_history() -> bool:
    loaded = load_history()
    if loaded:
        atexit.register(save_history)
    return loaded
