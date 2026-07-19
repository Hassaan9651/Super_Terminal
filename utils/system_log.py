import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from utils.config import get_config_dir


SYSTEM_LOG_NAME = "system.log"


def get_system_log_file() -> Path:
    return get_config_dir() / SYSTEM_LOG_NAME


class SystemLogger:
    def __init__(self, log_file: Path = None, session_id: str = None):
        self.log_file = log_file or get_system_log_file()
        self.session_id = session_id or uuid4().hex

    def log(self, event: str, **fields) -> bool:
        record = {
            "event": event,
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        record.update(fields)
        return write_system_log_record(self.log_file, record)


def write_system_log_record(log_file: Path, record: dict) -> bool:
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        try:
            log_file.chmod(0o600)
        except OSError:
            pass
        return True
    except OSError:
        return False
