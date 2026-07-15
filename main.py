import sys
import os
import re
from utils.detector import detect_environment
from utils.translator import translate_intent, TranslationError
from utils.classifier import classify_command
from utils.executor import execute_readonly_command
from utils.injector import handle_modifying_command

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

    # 2. Print activation and greeting message using exact formatting
    print(f"⚡ Superterminal Activated [Host: {os_name} | Shell: {shell_name}]")
    print("👉 Turn your natural English thoughts into executable terminal commands.")
    print("👉 Type 'exit', 'quit', or 'leave' to return to your native shell.")

    # 3. Core interactive sub-shell loop
    try:
        while True:
            try:
                # Prompt token must strictly display: "Super > "
                user_input = input("Super > ")
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
                if safety_classification == "READ-ONLY":
                    execute_readonly_command(normalized_input, shell_name)
                else:
                    import subprocess
                    if sys.platform == "win32" and shell_name.lower() == "powershell":
                        subprocess.run(["powershell.exe", "-Command", normalized_input])
                    else:
                        subprocess.run(normalized_input, shell=True)
                continue

            # Otherwise, translate the natural English intent using the LLM
            try:
                translated_cmd = translate_intent(user_input, os_name, shell_name)
                safety_classification = classify_command(translated_cmd, shell_name)
                
                # Check directory change on translated commands too!
                if handle_directory_change(translated_cmd):
                    continue

                if safety_classification == "READ-ONLY":
                    # Pass both parameters to execute via powershell.exe on Windows
                    execute_readonly_command(translated_cmd, shell_name)
                else:
                    # Input-inject modifying commands safely
                    handle_modifying_command(translated_cmd, shell_name)
            except TranslationError as e:
                print(f"Error: {e}")
            sys.stdout.flush()

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully without dumping a traceback stack
        print("\n👋 Deactivating Superterminal. Safe travels!")
        sys.exit(0)

if __name__ == "__main__":
    main()