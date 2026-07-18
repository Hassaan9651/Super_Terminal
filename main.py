import sys
import os
import re
import subprocess

try:
    import readline
except ImportError:
    readline = None

from utils.capabilities import detect_installed_tools, format_tool_context
from utils.completion import enable_path_completion
from utils.config import ConfigError, ensure_gemini_api_key, get_config_file
from utils.detector import detect_environment
from utils.history import enable_persistent_history
from utils.translator import translate_intent, TranslationError
from utils.classifier import classify_command
from utils.executor import execute_readonly_command
from utils.injector import handle_modifying_command
from utils.voice import create_voice_input, start_voice_overlay

READLINE_START_INVISIBLE = "\001"
READLINE_END_INVISIBLE = "\002"
ANSI_RED = "\033[31m"
ANSI_YELLOW = "\033[33m"
ANSI_DARK_GREEN = "\033[32;2m"
ANSI_RESET = "\033[0m"


def nonprinting(text: str) -> str:
    return f"{READLINE_START_INVISIBLE}{text}{READLINE_END_INVISIBLE}"


def supports_readline_invisible_markers() -> bool:
    if readline is None:
        return False
    return "libedit" not in getattr(readline, "__doc__", "").lower()


def prompt_control(text: str) -> str:
    if supports_readline_invisible_markers():
        return nonprinting(text)
    return text


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
        print_readonly_execution(command_str)
        execute_readonly_command(command_str, shell_name)
    elif sys.platform == "win32" and shell_name.lower() == "powershell":
        subprocess.run(["powershell.exe", "-Command", command_str])
    else:
        subprocess.run(command_str, shell=True)


def format_readonly_execution_line(command_str: str) -> str:
    return f"{ANSI_DARK_GREEN}Executing read-only command: {command_str}{ANSI_RESET}"


def print_readonly_execution(command_str: str) -> None:
    print(format_readonly_execution_line(command_str))


def parse_direct_command(user_input: str) -> str:
    normalized_input = (user_input or "").strip()
    if not normalized_input.startswith("!"):
        return ""
    return normalized_input[1:].strip()


def format_generated_command_for_review(command_str: str) -> str:
    command = (command_str or "").strip()
    if not command:
        return "!"
    if command.startswith("!"):
        return command
    return f"!{command}"


def parse_approved_modifying_command(approved_command: str) -> str:
    return parse_direct_command(approved_command)


def format_prompt() -> str:
    red = prompt_control(ANSI_RED)
    yellow = prompt_control(ANSI_YELLOW)
    reset = prompt_control(ANSI_RESET)
    return f"{red}SuperTerminal{reset} {yellow}({os.getcwd()}){reset} > "


def format_plain_prompt() -> str:
    return f"SuperTerminal ({os.getcwd()}) > "


def format_prompt_fragments() -> list:
    return [
        ("ansired", "SuperTerminal"),
        ("", " "),
        ("ansiyellow", f"({os.getcwd()})"),
        ("", " > "),
    ]


def main(enable_voice: bool = False):
    """
    Main application entry point. Initializes the environment detector,
    displays the activation greeting, and starts the interactive sub-shell loop.

    Voice mode (the floating mic overlay) is opt-in: launch with the
    `supervoice` command or pass `--voice`.
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
    print("👉 Prefix real shell commands with '!': !git status")
    print("👉 Type 'exit', 'quit', or 'leave' to return to your native shell.")
    print(f"👉 Gemini key loaded from environment")

    # 3. Core interactive sub-shell loop
    enable_persistent_history()
    enable_path_completion()

    # 4. Voice overlay: floating hold-to-talk mic button (opt-in via the
    #    `supervoice` command or --voice). When active, the prompt runs on
    #    prompt_toolkit so spoken commands can be submitted into it;
    #    otherwise the plain input() path is used.
    voice_input = None
    voice_manager = None
    if enable_voice or "--voice" in sys.argv[1:]:
        voice_input = create_voice_input()
        if voice_input is not None:
            voice_manager = start_voice_overlay(
                voice_input,
                os_name,
                shell_name,
                format_tool_context(detect_installed_tools()),
            )
        if voice_manager is None:
            voice_input = None
        else:
            print("👉 Voice: hold the floating mic button, speak a command, release.")

    try:
        while True:
            try:
                if voice_input is not None:
                    user_input = voice_input.prompt(format_prompt_fragments())
                else:
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

            direct_command = parse_direct_command(normalized_input)
            if direct_command or normalized_input.startswith("!"):
                if not direct_command:
                    continue
                if handle_directory_change(direct_command):
                    continue
                execute_command(direct_command, shell_name)
                continue

            # Otherwise, translate the natural English intent using the LLM.
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
                    print_readonly_execution(translated_cmd)
                    execute_readonly_command(translated_cmd, shell_name)
                else:
                    approved_cmd = handle_modifying_command(
                        format_generated_command_for_review(translated_cmd),
                        shell_name,
                        format_prompt_fragments(),
                        format_plain_prompt(),
                    )
                    if approved_cmd and approved_cmd.strip():
                        approved_direct_cmd = parse_approved_modifying_command(approved_cmd)
                        if not approved_direct_cmd:
                            print("Command not executed. Keep '!' at the start to run a real command.")
                            continue
                        if handle_directory_change(approved_direct_cmd):
                            continue
                        execute_command(approved_direct_cmd, shell_name)
            except TranslationError as e:
                print(f"Error: {e}")
            sys.stdout.flush()

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully without dumping a traceback stack
        print("\n👋 Deactivating Superterminal. Safe travels!")
        sys.exit(0)
    finally:
        if voice_manager is not None:
            voice_manager.stop()

def main_voice():
    """Entry point for the `supervoice` command: SuperTerminal + mic overlay."""
    main(enable_voice=True)


if __name__ == "__main__":
    main()
