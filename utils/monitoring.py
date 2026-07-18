import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional
from uuid import uuid4

from utils.config import get_config_dir
from utils.personality import append_retry_learning


READ_ONLY_RETRY_LOG_NAME = "read_only_retries.jsonl"
SIMILAR_QUERY_THRESHOLD = 0.72


@dataclass
class ReadOnlyObservation:
    user_input: str
    translated_command: str
    os_name: str
    shell_name: str
    cwd: str


def get_readonly_retry_log_file() -> Path:
    return get_config_dir() / READ_ONLY_RETRY_LOG_NAME


def normalize_intent(text: str) -> str:
    words = re.findall(r"[a-z0-9~/._-]+", (text or "").lower())
    return " ".join(words)


def normalize_command(command: str) -> str:
    return " ".join((command or "").strip().lower().split())


def intent_similarity(left: str, right: str) -> float:
    left_norm = normalize_intent(left)
    right_norm = normalize_intent(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def classify_retry_signal(
    previous: ReadOnlyObservation,
    current: ReadOnlyObservation,
) -> Optional[str]:
    previous_intent = normalize_intent(previous.user_input)
    current_intent = normalize_intent(current.user_input)
    previous_command = normalize_command(previous.translated_command)
    current_command = normalize_command(current.translated_command)

    if previous_intent and previous_intent == current_intent:
        return "exact_readonly_retry"

    if previous_command and previous_command == current_command:
        return "same_command_rephrase"

    if intent_similarity(previous.user_input, current.user_input) >= SIMILAR_QUERY_THRESHOLD:
        return "similar_readonly_rephrase"

    return None


class ReadOnlyRetryMonitor:
    def __init__(
        self,
        log_file: Path = None,
        session_id: str = None,
        personality_file: Path = None,
    ):
        self.log_file = log_file or get_readonly_retry_log_file()
        self.personality_file = personality_file
        self.session_id = session_id or uuid4().hex
        self.previous_observation = None

    def observe(
        self,
        user_input: str,
        translated_command: str,
        os_name: str,
        shell_name: str,
        cwd: str,
    ) -> bool:
        current = ReadOnlyObservation(
            user_input=user_input,
            translated_command=translated_command,
            os_name=os_name,
            shell_name=shell_name,
            cwd=cwd,
        )

        wrote_event = False
        if self.previous_observation is not None:
            signal = classify_retry_signal(self.previous_observation, current)
            if signal:
                wrote_event = self._write_event(signal, self.previous_observation, current)
                append_retry_learning(
                    signal,
                    self.previous_observation,
                    current,
                    self.personality_file,
                )

        self.previous_observation = current
        return wrote_event

    def _write_event(
        self,
        signal: str,
        previous: ReadOnlyObservation,
        current: ReadOnlyObservation,
    ) -> bool:
        event = {
            "event": "read_only_retry_signal",
            "signal": signal,
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "similarity": round(intent_similarity(previous.user_input, current.user_input), 3),
            "previous": {
                "user_input": previous.user_input,
                "translated_command": previous.translated_command,
                "cwd": previous.cwd,
            },
            "current": {
                "user_input": current.user_input,
                "translated_command": current.translated_command,
                "cwd": current.cwd,
            },
            "environment": {
                "os": current.os_name,
                "shell": current.shell_name,
            },
        }

        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.log_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
            try:
                self.log_file.chmod(0o600)
            except OSError:
                pass
            return True
        except OSError:
            return False
