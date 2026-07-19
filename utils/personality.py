import re
from pathlib import Path


PERSONALITY_DIR_NAME = "skills"
PERSONALITY_FILE_NAME = "personality.md"
MAX_PROFILE_BULLETS_PER_SECTION = 20
MAX_PROMPT_CHARS = 2500

SECTION_TITLES = [
    "Communication Style",
    "Language Hints",
    "Command Translation Preferences",
]

PERSONALITY_HEADER = """# SuperTerminal User Adaptation

This file is maintained locally by SuperTerminal.
It stores compact, deduplicated preferences learned from natural-language
phrasing, retries, rephrases, and command edits. It describes the user's style
and expectations instead of archiving every command.
"""

ACTION_WORDS = {
    "show",
    "list",
    "find",
    "make",
    "create",
    "delete",
    "remove",
    "go",
    "open",
    "move",
    "copy",
    "compress",
    "zip",
    "install",
    "run",
}

LOCALITY_WORDS = {
    "here",
    "this",
    "current",
    "inside",
    "folder",
    "directory",
    "dir",
}

SHORTHAND_HINTS = {
    "py": ("Python files", (".py", "*.py", "python")),
    "js": ("JavaScript files", (".js", "*.js", "javascript")),
    "ts": ("TypeScript files", (".ts", "*.ts", "typescript")),
    "jsn": ("JSON files", (".json", "*.json", "json")),
    "json": ("JSON files", (".json", "*.json", "json")),
    "csv": ("CSV files", (".csv", "*.csv")),
    "md": ("Markdown files", (".md", "*.md", "markdown")),
}


def get_personality_file() -> Path:
    return get_project_dir() / PERSONALITY_DIR_NAME / PERSONALITY_FILE_NAME


def get_project_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def build_empty_profile() -> str:
    sections = []
    for title in SECTION_TITLES:
        sections.append(f"## {title}\n- No stable preferences learned yet.")
    return PERSONALITY_HEADER.rstrip() + "\n\n" + "\n\n".join(sections) + "\n"


def ensure_personality_file(personality_file: Path = None) -> Path:
    target = personality_file or get_personality_file()
    if target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_empty_profile(), encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass
    return target


def normalize_for_profile(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def extract_words(text: str) -> list:
    return re.findall(r"[a-z0-9_-]+", (text or "").lower())


def command_mentions_any(command: str, needles: tuple) -> bool:
    command_norm = (command or "").lower()
    return any(needle in command_norm for needle in needles)


def strip_profile_marker(bullet: str) -> str:
    return re.sub(r"<!--\s*st:[^>]+-->\s*$", "", bullet or "").strip()


def strip_profile_markers(text: str) -> str:
    return re.sub(r"\s*<!--\s*st:[^>]+-->", "", text or "")


def extract_profile_marker(bullet: str) -> str:
    match = re.search(r"<!--\s*st:([^>]+)-->\s*$", bullet or "")
    return match.group(1).strip() if match else ""


def dedupe_bullets(bullets: list) -> list:
    seen = set()
    unique = []
    for bullet in bullets:
        key = extract_profile_marker(bullet) or normalize_for_profile(strip_profile_marker(bullet))
        if key in seen:
            continue
        seen.add(key)
        unique.append(bullet)
    return unique


def read_profile_sections(personality_file: Path) -> dict:
    sections = {title: [] for title in SECTION_TITLES}
    if not personality_file.exists():
        return sections

    current_title = None
    for line in personality_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            current_title = title if title in sections else None
            continue
        if current_title and line.startswith("- "):
            bullet = line.strip()
            if bullet != "- No stable preferences learned yet.":
                sections[current_title].append(bullet)
    return sections


def write_profile_sections(personality_file: Path, sections: dict) -> None:
    parts = [PERSONALITY_HEADER.rstrip()]
    for title in SECTION_TITLES:
        bullets = dedupe_bullets(sections.get(title, []))[-MAX_PROFILE_BULLETS_PER_SECTION:]
        if not bullets:
            bullets = ["- No stable preferences learned yet."]
        parts.append(f"## {title}\n" + "\n".join(bullets))

    personality_file.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    try:
        personality_file.chmod(0o600)
    except OSError:
        pass


def upsert_bullet(existing: list, bullet: str) -> list:
    marker = extract_profile_marker(bullet)
    if marker:
        return [
            candidate
            for candidate in existing
            if extract_profile_marker(candidate) != marker
        ] + [bullet]

    normalized = normalize_for_profile(strip_profile_marker(bullet))
    return [
        candidate
        for candidate in existing
        if normalize_for_profile(strip_profile_marker(candidate)) != normalized
    ] + [bullet]


def upsert_profile_bullets(personality_file: Path, updates: dict) -> bool:
    target = personality_file or get_personality_file()
    try:
        ensure_personality_file(target)
        sections = read_profile_sections(target)
        for title, bullets in updates.items():
            existing = sections.setdefault(title, [])
            for bullet in bullets:
                existing = upsert_bullet(existing, bullet)
            sections[title] = existing
        write_profile_sections(target, sections)
        return True
    except OSError:
        return False


def infer_style_bullets(user_input: str, translated_command: str = "") -> dict:
    words = extract_words(user_input)
    if not words:
        return {}

    updates = {
        "Communication Style": [],
        "Language Hints": [],
    }

    if len(words) <= 7:
        updates["Communication Style"].append(
            "- User often uses short, direct terminal requests; infer the practical CLI intent from concise wording. <!-- st:style:concise -->"
        )

    if words[0] in ACTION_WORDS:
        updates["Communication Style"].append(
            "- User often uses action-first phrasing, so the first verb is usually the command goal. <!-- st:style:action-first -->"
        )

    if any(word in LOCALITY_WORDS for word in words):
        updates["Communication Style"].append(
            "- User often relies on implicit local context; words like here, this folder, current, or inside usually refer to the current working directory. <!-- st:style:implicit-locality -->"
        )

    for token, (meaning, command_needles) in SHORTHAND_HINTS.items():
        if token in words and command_mentions_any(translated_command, command_needles):
            updates["Language Hints"].append(
                f"- Treat `{token}` in file-oriented requests as {meaning}. <!-- st:hint:{token} -->"
            )

    return {title: bullets for title, bullets in updates.items() if bullets}


def observe_user_expression(
    user_input: str,
    translated_command: str = "",
    personality_file: Path = None,
) -> bool:
    updates = infer_style_bullets(user_input, translated_command)
    if not updates:
        return False
    return upsert_profile_bullets(personality_file or get_personality_file(), updates)


def append_retry_learning(
    signal: str,
    previous,
    current,
    personality_file: Path = None,
) -> bool:
    command_key = normalize_for_profile(current.translated_command)
    return upsert_profile_bullets(
        personality_file or get_personality_file(),
        {
            "Command Translation Preferences": [
                (
                    f"- When similar read-only wording appears, prefer the command shape "
                    f"`{current.translated_command}`. <!-- st:retry:{command_key} -->"
                )
            ]
        },
    )


def append_modifying_edit_learning(
    user_input: str,
    suggested_command: str,
    approved_command: str,
    personality_file: Path = None,
) -> bool:
    user_key = normalize_for_profile(user_input)
    return upsert_profile_bullets(
        personality_file or get_personality_file(),
        {
            "Command Translation Preferences": [
                (
                    f"- For wording like \"{user_input}\", prefer `{approved_command}` "
                    f"over `{suggested_command}` when generating a modifying command. "
                    f"<!-- st:edit:{user_key} -->"
                )
            ]
        },
    )


def load_personality_context(personality_file: Path = None) -> str:
    target = personality_file or get_personality_file()
    try:
        if not target.exists():
            return ""
        content = target.read_text(encoding="utf-8").strip()
    except OSError:
        return ""

    if not content or content == build_empty_profile().strip():
        return ""

    context = strip_profile_markers(content)
    return context[-MAX_PROMPT_CHARS:]
