READ_ONLY_PREFIXES = [
    "dir", "ls", "cd", "pwd", "get-location", "get-childitem",
    "git status", "cat", "type"
]

MODIFYING_KEYWORDS = [
    "mkdir", "rm", "del", "rmdir", "new-item", "git clone"
]


def split_compound_command(command: str) -> list:
    """
    Splits a command string into individual sub-commands based on shell delimiters
    (|, ;, &&, ||, &) while respecting single and double quotes.

    Args:
        command (str): The raw command line string.

    Returns:
        list: A list of individual command strings.
    """
    parts = []
    current = []
    in_double_quote = False
    in_single_quote = False
    i = 0
    n = len(command)

    while i < n:
        c = command[i]
        if c == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(c)
        elif c == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current.append(c)
        elif not in_double_quote and not in_single_quote:
            # Check for double-character delimiters: &&, ||
            if i + 1 < n and command[i:i+2] in ("&&", "||"):
                parts.append("".join(current).strip())
                current = []
                i += 1  # Skip the second character of the delimiter
            # Check for single-character delimiters: ;, |, &
            elif c in (";", "|", "&"):
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(c)
        else:
            current.append(c)
        i += 1

    if current:
        parts.append("".join(current).strip())

    return [p for p in parts if p]


def contains_modifying_operator(part: str) -> bool:
    """
    Checks if a command part contains modifying output redirectors (e.g. '>')
    outside of quotes.

    Args:
        part (str): The command part to inspect.

    Returns:
        bool: True if a raw '>' redirector is found, False otherwise.
    """
    in_double_quote = False
    in_single_quote = False
    i = 0
    n = len(part)

    while i < n:
        c = part[i]
        if c == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif c == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif not in_double_quote and not in_single_quote:
            if c == '>':
                return True
        i += 1

    return False


def is_part_read_only(part: str) -> bool:
    """
    Validates if a single command component is strictly read-only.

    Args:
        part (str): A single parsed shell command component.

    Returns:
        bool: True if the command is recognized as read-only and safe, False otherwise.
    """
    part_norm = part.strip().lower()
    if not part_norm:
        return False

    # 1. Verify starts with a recognized read-only prefix
    starts_with_ro = False
    for prefix in READ_ONLY_PREFIXES:
        if part_norm == prefix:
            starts_with_ro = True
            break
        if part_norm.startswith(prefix + " "):
            starts_with_ro = True
            break
        # Support common Windows command syntax variations: e.g. dir/w, cd..
        if prefix in ("dir", "cd") and part_norm.startswith(prefix + "/"):
            starts_with_ro = True
            break
        if prefix == "cd" and part_norm.startswith("cd.."):
            starts_with_ro = True
            break

    if not starts_with_ro:
        return False

    # 2. Safety filter: check for modifying keywords (word-bounded)
    tokens = part_norm.split()
    for token in tokens:
        if token in MODIFYING_KEYWORDS:
            return False

    # Check multi-word modifying keywords (e.g., "git clone")
    if "git clone" in part_norm:
        idx = part_norm.find("git clone")
        before_ok = (idx == 0 or part_norm[idx-1].isspace())
        after_ok = (idx + len("git clone") == len(part_norm) or part_norm[idx + len("git clone")].isspace())
        if before_ok and after_ok:
            return False

    return True


def classify_command(translated_command: str, shell_name: str) -> str:
    """
    Evaluates safety profiles of translated shell commands.

    Args:
        translated_command (str): The generated terminal syntax.
        shell_name (str): The active environment shell name.

    Returns:
        str: 'READ-ONLY' or 'MODIFYING'.
    """
    cmd = (translated_command or "").strip()
    if not cmd:
        return "MODIFYING"

    parts = split_compound_command(cmd)
    if not parts:
        return "MODIFYING"

    for part in parts:
        # A component is modifying if it contains raw redirection operators
        if contains_modifying_operator(part):
            return "MODIFYING"

        # A component is modifying if it fails the read-only checks
        if not is_part_read_only(part):
            return "MODIFYING"

    return "READ-ONLY"
