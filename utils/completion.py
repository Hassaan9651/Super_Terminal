import glob
import os

try:
    import readline
except ImportError:
    readline = None


def _quote_if_needed(path: str) -> str:
    if any(char.isspace() for char in path):
        return f'"{path}"'
    return path


def _complete_path_prefix(prefix: str) -> list:
    expanded_prefix = os.path.expanduser(prefix)
    matches = []

    direct_matches = glob.glob(expanded_prefix + "*")
    candidate_matches = direct_matches

    if not candidate_matches:
        parent_dir, basename_prefix = os.path.split(expanded_prefix)
        search_dir = parent_dir or "."
        candidate_matches = [
            match for match in glob.glob(os.path.join(search_dir, "*"))
            if basename_prefix.lower() in os.path.basename(match).lower()
        ]

    for match in candidate_matches:
        display_match = match
        if prefix.startswith("~"):
            home = os.path.expanduser("~")
            if match == home:
                display_match = "~"
            elif match.startswith(home + os.sep):
                display_match = "~" + match[len(home):]

        if os.path.isdir(match):
            display_match += os.sep

        matches.append(_quote_if_needed(display_match))

    return sorted(matches)


def path_completer(text: str, state: int):
    matches = _complete_path_prefix(text)
    if state < len(matches):
        return matches[state]
    return None


def enable_path_completion() -> bool:
    if readline is None:
        return False

    readline.set_completer(path_completer)
    readline.set_completer_delims(" \t\n;|&<>")
    if hasattr(readline, "set_completion_append_character"):
        readline.set_completion_append_character("")

    # libedit, used by macOS Python builds, expects this binding.
    if "libedit" in getattr(readline, "__doc__", "").lower():
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    return True
