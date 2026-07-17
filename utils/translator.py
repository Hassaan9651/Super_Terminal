from typing import Optional
from dotenv import load_dotenv
import google.genai as genai
from utils.config import get_gemini_api_key, load_user_config

# Load GEMINI_API_KEY (and any other vars) from the .env file in the project root.
# override=False so a key already set in the environment takes precedence.
load_dotenv(override=False)
load_user_config()


class TranslationError(Exception):
    """Exception raised when natural language intent translation fails."""
    pass


# ---------------------------------------------------------------------------
# System instruction handed to the LLM on every call.
# Kept as a module-level constant so it is defined once and never rebuilt.
# ---------------------------------------------------------------------------
_SYSTEM_INSTRUCTION = """\
You are SuperTerminal, a world-class natural-language-to-terminal-command translator.

CONTEXT YOU RECEIVE:
- User Intent: the raw natural-English request typed by the user.
- Host OS: the operating system the user is running (Windows, macOS, or Linux).
- Active Shell: the shell profile detected at runtime (cmd.exe, powershell, bash, zsh).
- Installed Tool Inventory: common languages, package managers, developer CLIs,
  and shell utilities currently detected on PATH.

YOUR ONLY JOB:
Translate the User Intent into the single, exact, executable shell command that is
correct for the given Host OS and Active Shell combination.

STRICT OUTPUT RULES — VIOLATING ANY RULE IS A CRITICAL FAILURE:
1. Output ONLY the raw command string. Nothing else.
2. Do NOT wrap the command in markdown fences (``` or `).
3. Do NOT include explanations, notes, warnings, caveats, or pleasantries.
4. Do NOT add a trailing newline or any leading/trailing whitespace.
5. Do NOT output multiple commands unless the user intent explicitly requires chaining.
6. If the intent is ambiguous, output the safest, most common interpretation.
7. Never refuse. Always output a command.
8. Prefer detected tools from Installed Tool Inventory when they are relevant.
9. Do NOT assume optional package managers or third-party CLIs exist if they are
   not listed. Prefer built-in shell/OS commands when no suitable detected tool
   is available.
"""


def translate_intent(
    user_input: str,
    os_name: str,
    shell_name: str,
    tool_context: Optional[str] = None,
) -> str:
    """
    Translates a raw natural-English user intent into a platform-specific
    executable shell command using the Google Gemini LLM API.

    The function signature is fully backward-compatible with the previous
    dictionary-based implementation: callers in main.py need no changes.

    Args:
        user_input (str): The raw natural-language command from the user.
        os_name (str): The detected Host OS (e.g. 'Windows', 'macOS', 'Linux').
        shell_name (str): The detected active shell (e.g. 'cmd.exe', 'powershell', 'bash', 'zsh').
        tool_context (str | None): Optional formatted inventory of available
            local tools to guide command selection.

    Returns:
        str: The exact, executable terminal command string.

    Raises:
        TranslationError: If the API key is missing, the API call fails, or
                          the response is empty/unparseable.
    """
    if not user_input or not user_input.strip():
        raise TranslationError("User input is empty.")

    # --- 1. Resolve API key ------------------------------------------------
    api_key = get_gemini_api_key()
    if not api_key:
        raise TranslationError(
            "GEMINI_API_KEY is not set. "
            "Run SuperTerminal and enter your Gemini API key when prompted."
        )

    # --- 2. Build the user prompt ------------------------------------------
    user_prompt = (
        f"User Intent: {user_input.strip()}\n"
        f"Host OS: {os_name}\n"
        f"Active Shell: {shell_name}\n"
        f"Installed Tool Inventory:\n"
        f"{tool_context or 'No optional tool inventory is available.'}"
    )

    # --- 3. Call the Gemini API --------------------------------------------
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            config=genai.types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                temperature=0.0,        # Deterministic output for command translation
                max_output_tokens=256,  # Commands are short; cap prevents runaway responses
            ),
            contents=user_prompt,
        )

        # --- 4. Extract and sanitise the command ----------------------------
        raw = response.text

        if not raw or not raw.strip():
            raise TranslationError(
                f"LLM returned an empty response for intent: '{user_input}'"
            )

        # Strip any residual markdown fences or surrounding whitespace the
        # model may have included despite the system instruction.
        command = raw.strip().strip("`").strip()

        # Remove a leading language tag a model sometimes emits (e.g. "bash\nls")
        lines = command.splitlines()
        if len(lines) > 1 and not lines[0].strip().startswith(("-", "/", ".", "$")):
            first = lines[0].strip().lower()
            if first in ("bash", "zsh", "sh", "powershell", "cmd", "shell"):
                command = "\n".join(lines[1:]).strip()

        if not command:
            raise TranslationError(
                f"LLM response was unusable after sanitisation for intent: '{user_input}'"
            )

        return command

    except TranslationError:
        # Re-raise our own errors without wrapping them
        raise
    except Exception as exc:
        raise TranslationError(
            f"Gemini API call failed: {exc}"
        ) from exc
