import subprocess
import sys

def execute_readonly_command(translated_command: str, shell_name: str = "powershell") -> None:
    """
    Executes a read-only shell command in a blocking background subprocess,
    captures its stdout and stderr streams, and prints the result cleanly.
    Ensures that if the detected shell is powershell on Windows, it runs via powershell.exe.

    Args:
        translated_command (str): The translated terminal command to run.
        shell_name (str): The active detected shell (e.g., 'powershell', 'cmd', 'bash').
    """
    try:
        # If we are on Windows and the shell is powershell, run it explicitly via powershell.exe
        if sys.platform == "win32" and shell_name.lower() == "powershell":
            # Passing the command through powershell's -Command parameter
            executable_args = ["powershell.exe", "-Command", translated_command]
            result = subprocess.run(
                executable_args,
                text=True,
                capture_output=True
            )
        else:
            # Fallback to default system shell behavior (CMD on Windows, Sh/Bash on Unix)
            result = subprocess.run(
                translated_command,
                shell=True,
                text=True,
                capture_output=True
            )

        # Print stdout to terminal screen on success or output existence
        if result.stdout:
            sys.stdout.write(result.stdout)
            sys.stdout.flush()

        # If execution fails (exit code != 0) and stderr exists, display it cleanly
        if result.returncode != 0 and result.stderr:
            sys.stderr.write(result.stderr)
            sys.stderr.flush()

    except KeyboardInterrupt:
        # Gracefully handle Ctrl+C interrupts during execution of sub-processes
        sys.stdout.write("\n⚠️ Command execution interrupted by user.\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stderr.write(f"Error executing command: {e}\n")
        sys.stderr.flush()