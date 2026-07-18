"""
Floating hold-to-talk microphone button for SuperTerminal.

Runs as a standalone child process (`python -m utils.overlay`) so tkinter
owns its own main thread (required on macOS) and a GUI/audio crash can
never take down the terminal session.

Protocol: newline-delimited JSON on stdout.
    {"type": "command", "text": "..."}      spoken request, already translated
                                            to a shell command (single Gemini
                                            call; host context arrives via the
                                            SUPERTERMINAL_VOICE_* env vars)
    {"type": "transcript", "text": "..."}   verbatim transcript (fallback mode
                                            when no host context env is set)
    {"type": "error", "message": "..."}     something went wrong
The process exits when stdin reaches EOF (the parent has exited).
"""

import io
import json
import math
import os
import struct
import sys
import threading
import time
import wave

try:
    import tkinter as tk
except Exception:  # ImportError, or TclError on headless systems
    tk = None

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # int16
MAX_RECORD_SECONDS = 30
MIN_HOLD_SECONDS = 0.3
DRAG_THRESHOLD_PX = 8

WINDOW_SIZE = 104
CENTER = WINDOW_SIZE // 2
BUTTON_RADIUS = 30
MAX_RIPPLE_RADIUS = CENTER - 3
FRAME_MS = 40  # ~25 fps

COLOR_BG = "#101014"
COLOR_BUTTON = "#17172b"
COLOR_BUTTON_RECORDING = "#241033"
COLOR_GLYPH = "#f5f5ff"
# Siri-style palette: cyan -> blue -> violet -> pink
SIRI_COLORS = ["#22d3ee", "#3b82f6", "#8b5cf6", "#ec4899"]


def send_message(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def frames_to_wav_bytes(frames: bytes, rate: int = SAMPLE_RATE) -> bytes:
    """Wraps raw int16 mono PCM frames into an in-memory WAV file."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(rate)
        wav_file.writeframes(frames)
    return buffer.getvalue()


def _chunk_level(chunk: bytes) -> float:
    """Rough 0..1 loudness of an int16 PCM chunk (sampled, no numpy)."""
    if len(chunk) < 2:
        return 0.0
    step = max(2, (len(chunk) // 2 // 64) * 2)  # ~64 samples per chunk
    peak = 0
    for offset in range(0, len(chunk) - 1, step):
        sample = struct.unpack_from("<h", chunk, offset)[0]
        peak = max(peak, abs(sample))
    return min(1.0, peak / 32768.0)


def record_audio(
    stop_event: threading.Event,
    max_seconds: int = MAX_RECORD_SECONDS,
    level_callback=None,
) -> bytes:
    """Records microphone audio until stop_event is set or max_seconds pass.

    level_callback, when given, receives a 0..1 loudness value per audio
    chunk so the UI can visualize the microphone level.
    """
    import sounddevice as sd

    chunks = []

    def callback(indata, frame_count, time_info, status):
        chunk = bytes(indata)
        chunks.append(chunk)
        if level_callback is not None:
            try:
                level_callback(_chunk_level(chunk))
            except Exception:
                pass

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        callback=callback,
    ):
        deadline = time.monotonic() + max_seconds
        while not stop_event.is_set() and time.monotonic() < deadline:
            time.sleep(0.05)

    return b"".join(chunks)


def describe_audio_error(exc: Exception) -> str:
    message = f"Could not record audio: {exc}"
    if sys.platform == "darwin":
        message += (
            " — check System Settings > Privacy & Security > Microphone"
            " and allow your terminal app."
        )
    return message


def _blend(color_a: str, color_b: str, t: float) -> str:
    """Linear blend between two #rrggbb colors, t in 0..1."""
    t = max(0.0, min(1.0, t))
    parts = []
    for i in (1, 3, 5):
        a = int(color_a[i:i + 2], 16)
        b = int(color_b[i:i + 2], 16)
        parts.append(round(a + (b - a) * t))
    return "#{:02x}{:02x}{:02x}".format(*parts)


class OverlayApp:
    """Borderless always-on-top Siri-style button. Hold to talk, release to send.

    Visual states (driven by a single ~25fps animation loop):
      idle       - dark circle with a slowly rotating cyan->pink gradient ring
                   and an "S" glyph
      recording  - ripple rings radiating outward, plus a ring that reacts to
                   the live microphone level
      processing - two bright arcs orbiting the button quickly

    Dragging the button (beyond a small threshold) moves it and cancels the
    in-progress recording. Holds shorter than MIN_HOLD_SECONDS are treated
    as accidental clicks and discarded.
    """

    def __init__(self, root):
        self.root = root
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)

        x = root.winfo_screenwidth() - WINDOW_SIZE - 30
        y = root.winfo_screenheight() - WINDOW_SIZE - 80
        root.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}+{x}+{y}")

        self.canvas = tk.Canvas(
            root, width=WINDOW_SIZE, height=WINDOW_SIZE,
            highlightthickness=0, bg=COLOR_BG,
        )
        self.canvas.pack()
        self._transparent = self._make_window_transparent()

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.state = "idle"
        self._tick = 0
        self._level = 0.0
        self._press_root = (0, 0)
        self._window_origin = (0, 0)
        self._press_time = 0.0
        self._dragging = False
        self._cancelled = False
        self._stop_event = None

        threading.Thread(target=self._watch_stdin, daemon=True).start()
        self._animate()

    def _make_window_transparent(self) -> bool:
        """Hides the square window corners so only the circle is visible."""
        try:
            if sys.platform == "darwin":
                self.root.wm_attributes("-transparent", True)
                self.root.config(bg="systemTransparent")
                self.canvas.config(bg="systemTransparent")
                return True
            if sys.platform == "win32":
                self.root.wm_attributes("-transparentcolor", COLOR_BG)
                return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Mouse handling (hold-to-talk + drag-to-move)
    # ------------------------------------------------------------------

    def _inside_button(self, event) -> bool:
        return math.hypot(event.x - CENTER, event.y - CENTER) <= BUTTON_RADIUS + 6

    def on_press(self, event):
        if self.state != "idle" or not self._inside_button(event):
            return
        self._press_root = (event.x_root, event.y_root)
        self._window_origin = (self.root.winfo_x(), self.root.winfo_y())
        self._press_time = time.monotonic()
        self._dragging = False
        self._start_recording()

    def on_motion(self, event):
        dx = event.x_root - self._press_root[0]
        dy = event.y_root - self._press_root[1]
        if not self._dragging and (abs(dx) > DRAG_THRESHOLD_PX or abs(dy) > DRAG_THRESHOLD_PX):
            self._dragging = True
            self._cancel_recording()
        if self._dragging:
            new_x = self._window_origin[0] + dx
            new_y = self._window_origin[1] + dy
            self.root.geometry(f"+{new_x}+{new_y}")

    def on_release(self, event):
        if self._dragging:
            self._dragging = False
            return
        if self.state != "recording":
            return
        if time.monotonic() - self._press_time < MIN_HOLD_SECONDS:
            self._cancel_recording()
            return
        # Release ends the recording; the worker thread owns the
        # processing -> idle state transitions from here.
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Recording / transcription worker
    # ------------------------------------------------------------------

    def _start_recording(self):
        self.set_state("recording")
        self._cancelled = False
        self._level = 0.0
        self._stop_event = threading.Event()
        worker = threading.Thread(
            target=self._capture_and_transcribe, args=(self._stop_event,), daemon=True
        )
        worker.start()

    def _cancel_recording(self):
        self._cancelled = True
        if self._stop_event is not None:
            self._stop_event.set()
        self.set_state("idle")

    def _on_level(self, level: float) -> None:
        # Fast attack, slow decay, so the ring follows speech naturally.
        self._level = max(level, self._level * 0.85)

    def _capture_and_transcribe(self, stop_event):
        try:
            frames = record_audio(stop_event, level_callback=self._on_level)
        except Exception as exc:
            send_message({"type": "error", "message": describe_audio_error(exc)})
            self._set_state_threadsafe("idle")
            return

        if self._cancelled:
            return

        self._set_state_threadsafe("processing")
        try:
            wav_bytes = frames_to_wav_bytes(frames)
            os_name = os.environ.get("SUPERTERMINAL_VOICE_OS", "")
            shell_name = os.environ.get("SUPERTERMINAL_VOICE_SHELL", "")

            if os_name and shell_name:
                from utils.transcriber import transcribe_to_shell_command

                command = transcribe_to_shell_command(
                    wav_bytes,
                    os_name,
                    shell_name,
                    os.environ.get("SUPERTERMINAL_VOICE_TOOLS", ""),
                )
                if command.strip():
                    send_message({"type": "command", "text": command})
                else:
                    send_message({"type": "error", "message": "Didn't catch that — try again."})
            else:
                from utils.transcriber import transcribe_wav_bytes

                text = transcribe_wav_bytes(wav_bytes)
                if text.strip():
                    send_message({"type": "transcript", "text": text})
                else:
                    send_message({"type": "error", "message": "Didn't catch that — try again."})
        except Exception as exc:
            send_message({"type": "error", "message": str(exc)})
        finally:
            self._set_state_threadsafe("idle")

    # ------------------------------------------------------------------
    # Animation / drawing
    # ------------------------------------------------------------------

    def set_state(self, state: str):
        self.state = state

    def _set_state_threadsafe(self, state: str):
        try:
            self.root.after(0, lambda: self.set_state(state))
        except Exception:
            pass  # window already destroyed

    def _animate(self):
        self._tick += 1
        try:
            self._render()
        except Exception:
            return  # canvas destroyed
        self.root.after(FRAME_MS, self._animate)

    def _render(self):
        c = self.canvas
        c.delete("all")
        if self.state == "recording":
            self._render_recording(c)
        elif self.state == "processing":
            self._render_processing(c)
        else:
            self._render_idle(c)

    def _draw_button(self, c, fill, glow=0.0):
        """The core circle with its 'S' glyph; glow expands a soft halo."""
        if glow > 0:
            for i in range(3, 0, -1):
                radius = BUTTON_RADIUS + i * 3 * glow
                halo = _blend(SIRI_COLORS[2], COLOR_BG, 0.55 + i * 0.15)
                c.create_oval(
                    CENTER - radius, CENTER - radius,
                    CENTER + radius, CENTER + radius,
                    fill="", outline=halo, width=2,
                )
        c.create_oval(
            CENTER - BUTTON_RADIUS, CENTER - BUTTON_RADIUS,
            CENTER + BUTTON_RADIUS, CENTER + BUTTON_RADIUS,
            fill=fill, outline="",
        )
        c.create_text(
            CENTER, CENTER, text="S",
            font=("Helvetica", 26, "bold italic"),
            fill=COLOR_GLYPH,
        )

    def _draw_gradient_ring(self, c, radius, width, offset_deg, brightness=0.0):
        """A rotating multi-color ring built from short colored arcs."""
        segments = 24
        span = 360 / segments
        for seg in range(segments):
            t = seg / segments
            palette_pos = t * (len(SIRI_COLORS) - 1)
            idx = int(palette_pos)
            frac = palette_pos - idx
            color = _blend(
                SIRI_COLORS[idx],
                SIRI_COLORS[min(idx + 1, len(SIRI_COLORS) - 1)],
                frac,
            )
            if brightness < 1.0:
                color = _blend(COLOR_BG, color, 0.35 + 0.65 * brightness)
            c.create_arc(
                CENTER - radius, CENTER - radius,
                CENTER + radius, CENTER + radius,
                start=offset_deg + seg * span, extent=span + 1,
                style="arc", outline=color, width=width,
            )

    def _render_idle(self, c):
        # Gentle breathing + slow rotation so the button feels alive.
        breath = 0.5 + 0.5 * math.sin(self._tick / 30)
        self._draw_gradient_ring(
            c, BUTTON_RADIUS + 4, 3,
            offset_deg=self._tick * 1.2,
            brightness=0.35 + 0.4 * breath,
        )
        self._draw_button(c, COLOR_BUTTON)

    def _render_recording(self, c):
        # Ripple rings radiate from the button edge to the window edge.
        span = MAX_RIPPLE_RADIUS - BUTTON_RADIUS
        for i in range(3):
            progress = ((self._tick * 1.6 + i * span / 3) % span) / span
            radius = BUTTON_RADIUS + progress * span
            color_idx = i % len(SIRI_COLORS)
            color = _blend(SIRI_COLORS[color_idx], COLOR_BG, 0.15 + 0.8 * progress)
            c.create_oval(
                CENTER - radius, CENTER - radius,
                CENTER + radius, CENTER + radius,
                fill="", outline=color, width=2,
            )
        # A ring hugging the button follows the live microphone level.
        level_radius = BUTTON_RADIUS + 3 + self._level * 9
        c.create_oval(
            CENTER - level_radius, CENTER - level_radius,
            CENTER + level_radius, CENTER + level_radius,
            fill="", outline=_blend(SIRI_COLORS[3], SIRI_COLORS[1], self._level),
            width=3,
        )
        self._draw_button(c, COLOR_BUTTON_RECORDING, glow=0.5 + 0.5 * self._level)

    def _render_processing(self, c):
        # Two bright arcs orbiting fast: unmistakably "working on it".
        radius = BUTTON_RADIUS + 7
        angle = -(self._tick * 14) % 360
        for offset, color in ((0, SIRI_COLORS[1]), (180, SIRI_COLORS[3])):
            c.create_arc(
                CENTER - radius, CENTER - radius,
                CENTER + radius, CENTER + radius,
                start=angle + offset, extent=110,
                style="arc", outline=color, width=4,
            )
        # Dim, slowly-pulsing button face while thinking.
        pulse = 0.5 + 0.5 * math.sin(self._tick / 6)
        face = _blend(COLOR_BUTTON, COLOR_BUTTON_RECORDING, pulse)
        self._draw_button(c, face)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _watch_stdin(self):
        """Exits the overlay when the parent process closes our stdin."""
        try:
            sys.stdin.buffer.read()
        except Exception:
            pass
        try:
            self.root.after(0, self.root.destroy)
        except Exception:
            pass


def main() -> int:
    if tk is None:
        send_message({"type": "error", "message": "tkinter is not available."})
        return 3

    try:
        import sounddevice  # noqa: F401
    except Exception as exc:
        send_message({
            "type": "error",
            "message": (
                f"sounddevice is not available ({exc}). "
                "Install voice support with: pip install sounddevice"
            ),
        })
        return 3

    try:
        root = tk.Tk()
    except Exception as exc:
        send_message({"type": "error", "message": f"Could not open overlay window: {exc}"})
        return 3

    # Warm up the Gemini client in the background so the first voice
    # command doesn't also pay the SDK/connection setup cost.
    def _warm_up():
        try:
            from utils.transcriber import warm_up_client

            warm_up_client()
        except Exception:
            pass

    threading.Thread(target=_warm_up, daemon=True).start()

    OverlayApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
