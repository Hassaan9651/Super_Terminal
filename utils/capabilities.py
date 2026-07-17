import shutil


TOOL_CATEGORIES = {
    "Languages/Runtimes": [
        "python",
        "python3",
        "node",
        "ruby",
        "go",
        "rustc",
        "java",
        "javac",
        "php",
        "perl",
        "lua",
        "dotnet",
    ],
    "Package Managers": [
        "pip",
        "pip3",
        "uv",
        "poetry",
        "npm",
        "yarn",
        "pnpm",
        "bun",
        "cargo",
        "gem",
        "composer",
        "brew",
        "apt",
        "apt-get",
        "dnf",
        "yum",
        "pacman",
        "apk",
        "winget",
        "choco",
        "scoop",
    ],
    "Developer CLIs": [
        "git",
        "gh",
        "docker",
        "docker-compose",
        "kubectl",
        "helm",
        "terraform",
        "aws",
        "gcloud",
        "az",
        "vercel",
        "netlify",
        "supabase",
        "firebase",
    ],
    "Shell Utilities": [
        "rg",
        "fd",
        "fzf",
        "jq",
        "yq",
        "curl",
        "wget",
        "tar",
        "zip",
        "unzip",
        "make",
        "cmake",
        "sed",
        "awk",
        "grep",
        "find",
        "xargs",
        "rsync",
        "ssh",
        "scp",
        "ffmpeg",
    ],
}


def detect_installed_tools() -> dict:
    """
    Detects common languages, package managers, and CLI tools available on PATH.

    The scan is intentionally shallow: it does not read project files, shell
    history, or run version commands. Presence is determined by shutil.which().
    """
    installed = {}
    for category, tool_names in TOOL_CATEGORIES.items():
        found = []
        for tool_name in tool_names:
            if shutil.which(tool_name):
                found.append(tool_name)
        installed[category] = found
    return installed


def format_tool_context(installed_tools: dict) -> str:
    """Formats detected tool availability for the translation prompt."""
    if not installed_tools:
        return "No optional tool inventory is available."

    lines = []
    for category, tool_names in installed_tools.items():
        value = ", ".join(tool_names) if tool_names else "none detected"
        lines.append(f"- {category}: {value}")
    return "\n".join(lines)
