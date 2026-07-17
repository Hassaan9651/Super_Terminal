import sys
import time
import ctypes
from ctypes import wintypes

try:
    import readline
except ImportError:
    readline = None

# Win32 API Constants & Structures for input buffer injection
STD_INPUT_HANDLE = -10
KEY_EVENT = 0x0001

class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("bKeyDown", wintypes.BOOL),
        ("wRepeatCount", wintypes.WORD),
        ("wVirtualKeyCode", wintypes.WORD),
        ("wVirtualScanCode", wintypes.WORD),
        ("uChar", ctypes.c_ushort),  # Unicode character code
        ("dwControlKeyState", wintypes.DWORD)
    ]

class INPUT_RECORD_UNION(ctypes.Union):
    _fields_ = [
        ("KeyEvent", KEY_EVENT_RECORD),
        # Other event types are omitted as we only need KeyEvents
    ]

class INPUT_RECORD(ctypes.Structure):
    _fields_ = [
        ("EventType", wintypes.WORD),
        ("Event", INPUT_RECORD_UNION)
    ]

def inject_string_to_stdin(text: str) -> bool:
    """
    Directly injects a string into the native Windows Console input buffer.
    This mimics actual physical keystrokes so they sit on the input line.
    """
    try:
        kernel32 = ctypes.windll.kernel32
        h_stdin = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        
        # Build list of key events (both key-down and key-up for each character)
        records = []
        for char in text:
            char_code = ord(char)
            
            # Key Down Event
            rec_down = INPUT_RECORD()
            rec_down.EventType = KEY_EVENT
            rec_down.Event.KeyEvent.bKeyDown = True
            rec_down.Event.KeyEvent.wRepeatCount = 1
            rec_down.Event.KeyEvent.wVirtualKeyCode = 0
            rec_down.Event.KeyEvent.wVirtualScanCode = 0
            rec_down.Event.KeyEvent.uChar = char_code
            rec_down.Event.KeyEvent.dwControlKeyState = 0
            
            # Key Up Event
            rec_up = INPUT_RECORD()
            rec_up.EventType = KEY_EVENT
            rec_up.Event.KeyEvent.bKeyDown = False
            rec_up.Event.KeyEvent.wRepeatCount = 1
            rec_up.Event.KeyEvent.wVirtualKeyCode = 0
            rec_up.Event.KeyEvent.wVirtualScanCode = 0
            rec_up.Event.KeyEvent.uChar = char_code
            rec_up.Event.KeyEvent.dwControlKeyState = 0
            
            records.extend([rec_down, rec_up])
            
        # Allocate array and write events to console input buffer
        records_array = (INPUT_RECORD * len(records))(*records)
        events_written = wintypes.DWORD(0)
        
        success = kernel32.WriteConsoleInputW(
            h_stdin,
            records_array,
            len(records),
            ctypes.byref(events_written)
        )
        return bool(success)
    except Exception:
        return False


def prefill_next_input(text: str) -> bool:
    """
    Prefills the next Python input()/readline prompt with editable text.

    On Unix-like terminals, readline gives us a native editable command line.
    On Windows consoles, fall back to writing key events to the console input
    buffer so the next prompt receives the generated command as keystrokes.
    """
    if sys.platform == "win32":
        time.sleep(0.05)
        return inject_string_to_stdin(text)

    if readline is not None:
        is_libedit = "libedit" in getattr(readline, "__doc__", "").lower()

        def pre_input_hook() -> None:
            readline.insert_text(text)
            readline.redisplay()
            readline.set_pre_input_hook(None)

        def startup_hook() -> None:
            readline.insert_text(text)
            readline.set_startup_hook(None)

        try:
            if is_libedit and hasattr(readline, "set_startup_hook"):
                readline.set_startup_hook(startup_hook)
            elif hasattr(readline, "set_pre_input_hook"):
                readline.set_pre_input_hook(pre_input_hook)
            elif hasattr(readline, "set_startup_hook"):
                readline.set_startup_hook(startup_hook)
            else:
                return False
            return True
        except Exception:
            return False

    time.sleep(0.05)
    return inject_string_to_stdin(text)


def handle_modifying_command(translated_command: str, native_shell: str) -> None:
    """
    Handles modifying commands by writing 'Modifying command detected!', 
    injecting the translation into the active input stream, and letting 
    the user edit/confirm it natively in the command line loop.
    """
    print("Modifying command detected!")
    sys.stdout.flush()

    if not prefill_next_input(translated_command):
        print(translated_command)
