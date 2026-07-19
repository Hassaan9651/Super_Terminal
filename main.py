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
from utils.monitoring import ModifyingCommandEditMonitor, ReadOnlyRetryMonitor
from utils.personality import observe_user_expression
from utils.system_log import SystemLogger
from utils.translator import translate_intent, TranslationError
from utils.classifier import classify_command
from utils.executor import execute_readonly_command
from utils.injector import handle_modifying_command

READLINE_START_INVISIBLE = "\001"
READLINE_END_INVISIBLE = "\002"
ANSI_RED = "\033[31m"
ANSI_YELLOW = "\033[33m"
ANSI_DARK_GREEN = "\033[32;2m"
ANSI_BLUE = "\033[34m"
ANSI_RESET = "\033[0m"
PREFERENCE_REMEMBERED_MESSAGE = "I'll remember your preference for this next time!"


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
    match = re.match(r'^(cd|chdir|set-location)\s+(.*)$', clean_cmd, re.IGNORECASE)
    if match:
        target_path = match.group(2).strip()
        if (target_path.startswith('"') and target_path.endswith('"')) or \
           (target_path.startswith("'") and target_path.endswith("'")):
            target_path = target_path[1:-1]

        try:
            os.chdir(target_path)
            return True
        except Exception as e:
            print(f"Error changing directory: {e}")
            return True

    if clean_cmd.lower() in ("cd", "chdir"):
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


def format_preference_remembered_line() -> str:
    return f"{ANSI_BLUE}{PREFERENCE_REMEMBERED_MESSAGE}{ANSI_RESET}"


def print_preference_remembered() -> None:
    print(format_preference_remembered_line())


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


def main():
    """
    Main application entry point. Initializes the environment detector,
    displays the activation greeting, and starts the interactive sub-shell loop.
    """
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

    os_name, shell_name = detect_environment()

    try:
        ensure_gemini_api_key()
    except (ConfigError, KeyboardInterrupt, EOFError) as exc:
        if isinstance(exc, KeyboardInterrupt):
            print("\nGemini API key setup cancelled.")
        else:
            print(f"Gemini API key setup failed: {exc}")
        sys.exit(1)

    print(f"⚡ Superterminal Activated [Host: {os_name} | Shell: {shell_name}]")
    print("👉 Turn your natural English thoughts into executable terminal commands.")
    print("👉 Prefix real shell commands with '!': !git status")
    print("👉 Type 'exit', 'quit', or 'leave' to return to your native shell.")
    print(f"👉 Gemini key loaded from environment")

    enable_persistent_history()
    enable_path_completion()
    system_logger = SystemLogger()
    system_logger.log(
        "session_start",
        os_name=os_name,
        shell_name=shell_name,
        cwd=os.getcwd(),
    )
    read_only_retry_monitor = ReadOnlyRetryMonitor(
        session_id=system_logger.session_id,
        system_logger=system_logger,
    )
    modifying_edit_monitor = ModifyingCommandEditMonitor(
        session_id=system_logger.session_id,
        system_logger=system_logger,
    )

    try:
        while True:
            try:
                user_input = input(format_prompt())
            except EOFError:
                print("\n👋 Deactivating Superterminal. Safe travels!")
                break

            normalized_input = user_input.strip()

            if normalized_input.lower() in ("exit", "quit", "leave"):
                print("👋 Deactivating Superterminal. Safe travels!")
                break

            if not normalized_input:
                continue

            direct_command = parse_direct_command(normalized_input)
            if direct_command or normalized_input.startswith("!"):
                if not direct_command:
                    continue
                system_logger.log(
                    "direct_command_received",
                    command=direct_command,
                    cwd=os.getcwd(),
                    os_name=os_name,
                    shell_name=shell_name,
                )
                if handle_directory_change(direct_command):
                    system_logger.log(
                        "directory_changed",
                        command=direct_command,
                        cwd=os.getcwd(),
                        source="direct_command",
                    )
                    continue
                execute_command(direct_command, shell_name)
                system_logger.log(
                    "direct_command_executed",
                    command=direct_command,
                    cwd=os.getcwd(),
                    os_name=os_name,
                    shell_name=shell_name,
                )
                continue

            try:
                tool_context = format_tool_context(detect_installed_tools())
                translated_cmd = translate_intent(
                    user_input,
                    os_name,
                    shell_name,
                    tool_context,
                )
                safety_classification = classify_command(translated_cmd, shell_name)
                system_logger.log(
                    "natural_language_translated",
                    user_input=user_input,
                    translated_command=translated_cmd,
                    safety_classification=safety_classification,
                    cwd=os.getcwd(),
                    os_name=os_name,
                    shell_name=shell_name,
                )
                if observe_user_expression(user_input, translated_cmd):
                    system_logger.log(
                        "personality_profile_updated",
                        reason="passive_expression_observation",
                        user_input=user_input,
                        translated_command=translated_cmd,
                        cwd=os.getcwd(),
                    )

                if handle_directory_change(translated_cmd):
                    system_logger.log(
                        "directory_changed",
                        command=translated_cmd,
                        cwd=os.getcwd(),
                        source="translated_command",
                    )
                    continue

                if safety_classification == "READ-ONLY":
                    read_only_retry_monitor.observe(
                        user_input,
                        translated_cmd,
                        os_name,
                        shell_name,
                        os.getcwd(),
                    )
                    system_logger.log(
                        "read_only_command_executing",
                        user_input=user_input,
                        command=translated_cmd,
                        cwd=os.getcwd(),
                        os_name=os_name,
                        shell_name=shell_name,
                    )
                    print_readonly_execution(translated_cmd)
                    execute_readonly_command(translated_cmd, shell_name)
                else:
                    system_logger.log(
                        "modifying_command_review_started",
                        user_input=user_input,
                        suggested_command=translated_cmd,
                        cwd=os.getcwd(),
                        os_name=os_name,
                        shell_name=shell_name,
                    )
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
                            system_logger.log(
                                "modifying_command_rejected",
                                user_input=user_input,
                                suggested_command=translated_cmd,
                                approved_input=approved_cmd,
                                reason="missing_bang_prefix",
                                cwd=os.getcwd(),
                            )
                            continue
                        if modifying_edit_monitor.observe(
                            user_input,
                            translated_cmd,
                            approved_direct_cmd,
                            os_name,
                            shell_name,
                            os.getcwd(),
                        ):
                            print_preference_remembered()
                        system_logger.log(
                            "modifying_command_approved",
                            user_input=user_input,
                            suggested_command=translated_cmd,
                            approved_command=approved_direct_cmd,
                            cwd=os.getcwd(),
                            os_name=os_name,
                            shell_name=shell_name,
                        )
                        if handle_directory_change(approved_direct_cmd):
                            system_logger.log(
                                "directory_changed",
                                command=approved_direct_cmd,
                                cwd=os.getcwd(),
                                source="approved_modifying_command",
                            )
                            continue
                        execute_command(approved_direct_cmd, shell_name)
                        system_logger.log(
                            "modifying_command_executed",
                            user_input=user_input,
                            command=approved_direct_cmd,
                            cwd=os.getcwd(),
                            os_name=os_name,
                            shell_name=shell_name,
                        )
            except TranslationError as e:
                print(f"Error: {e}")
                system_logger.log(
                    "translation_error",
                    user_input=user_input,
                    error=str(e),
                    cwd=os.getcwd(),
                    os_name=os_name,
                    shell_name=shell_name,
                )
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n👋 Deactivating Superterminal. Safe travels!")
        sys.exit(0)
    finally:
        system_logger.log(
            "session_end",
            os_name=os_name,
            shell_name=shell_name,
            cwd=os.getcwd(),
        )


if __name__ == "__main__":
    main()
