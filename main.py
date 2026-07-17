import sys
import os
import re
import subprocess
from utils.capabilities import detect_installed_tools, format_tool_context
from utils.completion import enable_path_completion
from utils.config import ConfigError, ensure_gemini_api_key, get_config_file
from utils.detector import detect_environment
from utils.history import enable_persistent_history
from utils.translator import translate_intent, TranslationError
from utils.classifier import classify_command
from utils.executor import execute_readonly_command
from utils.injector import handle_modifying_command

READLINE_START_INVISIBLE = "\001"
READLINE_END_INVISIBLE = "\002"
ANSI_RED = "\033[31m"
ANSI_YELLOW = "\033[33m"
ANSI_RESET = "\033[0m"


def nonprinting(text: str) -> str:
    return f"{READLINE_START_INVISIBLE}{text}{READLINE_END_INVISIBLE}"


def handle_directory_change(command_str: str) -> bool:
    """
    Intercepts and handles shell directory changes locally in the parent 
    Python process so that state (working directory) is preserved.
    """
    clean_cmd = command_str.strip()
    # Match patterns like: cd path, cd "path", Set-Location path, chdir path
    match = re.match(r'^(cd|chdir|set-location)\s+(.*)$', clean_cmd, re.IGNORECASE)
    if match:
        target_path = match.group(2).strip()
        # Strip outer quotes if they exist
        if (target_path.startswith('"') and target_path.endswith('"')) or \
           (target_path.startswith("'") and target_path.endswith("'")):
            target_path = target_path[1:-1]
        
        try:
            os.chdir(target_path)
            return True
        except Exception as e:
            print(f"Error changing directory: {e}")
            return True
            
    # Handle plain 'cd' (which usually prints or goes to home)
    if clean_cmd.lower() in ("cd", "chdir"):
        # On Windows, 'cd' with no arguments prints the current directory
        if sys.platform == "win32":
            print(os.getcwd())
        else:
            home = os.path.expanduser("~")
            try:
                os.chdir(home)
            except Exception as e:
                print(e)
        return True
        
    return False


def execute_command(command_str: str, shell_name: str) -> None:
    """Executes a user-approved shell command in the active shell context."""
    safety_classification = classify_command(command_str, shell_name)
    if safety_classification == "READ-ONLY":
        execute_readonly_command(command_str, shell_name)
    elif sys.platform == "win32" and shell_name.lower() == "powershell":
        subprocess.run(["powershell.exe", "-Command", command_str])
    else:
        subprocess.run(command_str, shell=True)


def format_prompt() -> str:
    red = nonprinting(ANSI_RED)
    yellow = nonprinting(ANSI_YELLOW)
    reset = nonprinting(ANSI_RESET)
    return f"{red}SuperTerminal{reset} {yellow}({os.getcwd()}){reset} > "


def format_plain_prompt() -> str:
    return f"SuperTerminal ({os.getcwd()}) > "


def main():
    """
    Main application entry point. Initializes the environment detector,
    displays the activation greeting, and starts the interactive sub-shell loop.
    """
    # Configure streams to support UTF-8 characters (emojis) on Windows terminals
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

    # 1. Detect Host OS and active shell
    os_name, shell_name = detect_environment()

    try:
        ensure_gemini_api_key()
    except (ConfigError, KeyboardInterrupt, EOFError) as exc:
        if isinstance(exc, KeyboardInterrupt):
            print("\nGemini API key setup cancelled.")
        else:
            print(f"Gemini API key setup failed: {exc}")
        sys.exit(1)

    # 2. Print activation and greeting message using exact formatting
    print(f"⚡ Superterminal Activated [Host: {os_name} | Shell: {shell_name}]")
    print("👉 Turn your natural English thoughts into executable terminal commands.")
    print("👉 Type 'exit', 'quit', or 'leave' to return to your native shell.")
    print(f"👉 Gemini key loaded from environment")

    # 3. Core interactive sub-shell loop
    enable_persistent_history()
    enable_path_completion()

    try:
        while True:
            try:
                user_input = input(format_prompt())
            except EOFError:
                # Handle Ctrl+D gracefully
                print("\n👋 Deactivating Superterminal. Safe travels!")
                break

            # String normalization: strip whitespaces
            normalized_input = user_input.strip()

            # Case-insensitive intercept trap for escape keywords
            if normalized_input.lower() in ("exit", "quit", "leave"):
                print("👋 Deactivating Superterminal. Safe travels!")
                break

            # Skip empty inputs
            if not normalized_input:
                continue

            # LOOP BREAK & STATE PRESERVATION FIX 1: Intercept directory change commands first!
            if handle_directory_change(normalized_input):
                continue

            # LOOP BREAK FIX 2: Check if this is already a native system command 
            # (i.e. the user just pressed Enter on our injected command)
            safety_classification = classify_command(normalized_input, shell_name)
            
            # If the user typed/entered something that is already a valid system terminal command
            # we execute it directly without sending it back to the LLM.
            is_probably_command = any(
                normalized_input.lower().startswith(prefix) for prefix in [
                    "mkdir", "rm", "del", "rmdir", "new-item", "git", "ls", "dir", "pwd", "get-childitem"
                ]
            )

            if is_probably_command:
                execute_command(normalized_input, shell_name)
                continue

            # Otherwise, translate the natural English intent using the LLM
            try:
                tool_context = format_tool_context(detect_installed_tools())
                translated_cmd = translate_intent(
                    user_input,
                    os_name,
                    shell_name,
                    tool_context,
                )
                safety_classification = classify_command(translated_cmd, shell_name)
                
                # Check directory change on translated commands too!
                if handle_directory_change(translated_cmd):
                    continue

                if safety_classification == "READ-ONLY":
                    # Pass both parameters to execute via powershell.exe on Windows
                    execute_readonly_command(translated_cmd, shell_name)
                else:
                    approved_cmd = handle_modifying_command(
                        translated_cmd,
                        shell_name,
                        format_plain_prompt(),
                    )
                    if approved_cmd and approved_cmd.strip():
                        if handle_directory_change(approved_cmd):
                            continue
                        execute_command(approved_cmd, shell_name)
            except TranslationError as e:
                print(f"Error: {e}")
            sys.stdout.flush()

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully without dumping a traceback stack
        print("\n👋 Deactivating Superterminal. Safe travels!")
        sys.exit(0)

if __name__ == "__main__":
    main()
