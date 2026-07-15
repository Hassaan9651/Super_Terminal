import os
import platform
import subprocess
import csv

def detect_environment():
    """
    Detects the Host OS (Windows, macOS, or Linux) and the active terminal shell
    currently executing the script (e.g., cmd.exe, powershell, bash, zsh).

    Returns:
        tuple: (os_name, shell_name) normalized clean strings.
    """
    # 1. Detect Host OS
    system = platform.system().lower()
    if "windows" in system:
        os_name = "Windows"
    elif "darwin" in system:
        os_name = "macOS"
    elif "linux" in system:
        os_name = "Linux"
    else:
        # Fallback to general system name
        os_name = platform.system() or "Unknown"

    # 2. Detect Active Shell
    shell_name = "Unknown"
    ppid = None
    
    # Attempt to get parent process ID
    if hasattr(os, "getppid"):
        try:
            ppid = os.getppid()
        except (AttributeError, OSError):
            pass

    parent_process = None
    if ppid:
        try:
            if os_name == "Windows":
                # Run tasklist to find parent process name
                # Output format: CSV, no headers
                cmd = ["tasklist", "/FI", f"PID eq {ppid}", "/FO", "CSV", "/NH"]
                
                # Prevent flash of command prompt window if executed from GUI context
                startupinfo = None
                if hasattr(subprocess, "STARTUPINFO"):
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                    startupinfo=startupinfo
                )
                
                # Parse CSV to get process name (first column)
                reader = csv.reader(result.stdout.strip().splitlines())
                for row in reader:
                    if row:
                        parent_process = row[0]
                        break
            else:
                # Try reading /proc (Linux)
                proc_comm = f"/proc/{ppid}/comm"
                if os.path.exists(proc_comm):
                    with open(proc_comm, "r") as f:
                        parent_process = f.read().strip()
                else:
                    # Fallback to ps command (macOS/Unix fallback)
                    cmd = ["ps", "-p", str(ppid), "-o", "comm="]
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True
                    )
                    parent_process = result.stdout.strip()
        except Exception:
            # Silently fallback to env vars if parent query fails
            pass

    # Normalize process name if resolved
    if parent_process:
        proc_lower = parent_process.lower()
        if proc_lower.endswith(".exe"):
            proc_lower = proc_lower[:-4]

        # Map parent process name to standard shells
        if "cmd" in proc_lower:
            shell_name = "cmd.exe"
        elif "powershell" in proc_lower or "pwsh" in proc_lower:
            shell_name = "powershell"
        elif "bash" in proc_lower or "git-bash" in proc_lower or proc_lower == "sh":
            shell_name = "bash"
        elif "zsh" in proc_lower:
            shell_name = "zsh"

    # Fallback/validation using environment variables
    if shell_name == "Unknown":
        # Check standard env vars for unix-like systems
        if os.environ.get("ZSH_VERSION"):
            shell_name = "zsh"
        elif os.environ.get("BASH_VERSION"):
            shell_name = "bash"
        else:
            shell_env = os.environ.get("SHELL", "")
            if shell_env:
                shell_lower = shell_env.lower()
                if "zsh" in shell_lower:
                    shell_name = "zsh"
                elif "bash" in shell_lower or "sh" in shell_lower:
                    shell_name = "bash"
                elif "powershell" in shell_lower or "pwsh" in shell_lower:
                    shell_name = "powershell"
            
            # Windows fallback
            if shell_name == "Unknown" and os_name == "Windows":
                # Check if running under Git Bash/MSYS2/Cygwin (which set specific env vars)
                if os.environ.get("MSYSTEM") or "xterm" in os.environ.get("TERM", "").lower():
                    shell_name = "bash"
                else:
                    # Default to cmd.exe on Windows
                    shell_name = "cmd.exe"

    return os_name, shell_name
