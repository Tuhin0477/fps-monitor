

import time
import collections
import tkinter as tk
from tkinter import font as tkfont
import sys
import os

# Try importing psutil for CPU/RAM stats; fallback gracefully if not installed
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Try importing ctypes for Windows-specific window transparency / click-through
try:
    import ctypes
    from ctypes import wintypes
    CTYPES_AVAILABLE = True
except ImportError:
    CTYPES_AVAILABLE = False


class FPSOverlay:
    def __init__(self):
        # 1. Initialize Root Window
        self.root = tk.Tk()
        self.root.title("FPS Overlay")

        # 2. Window Configurations (Frameless & Always-on-Top)
        self.root.overrideredirect(True)           # Remove borders/title bar
        self.root.wm_attributes("-topmost", True)  # Always stay on top of games/apps
        
        # Geometry & Default Position (Top-left corner of the screen)
        self.root.geometry("+30+30")
        
        # Transparent background color key (Windows DWM feature)
        self.trans_color = "#000001"
        self.root.configure(bg=self.trans_color)
        try:
            self.root.wm_attributes("-transparentcolor", self.trans_color)
        except Exception:
            # Fallback if transparent color is unsupported
            self.root.wm_attributes("-alpha", 0.85)

        # 3. Customization & State Variables
        self.show_system_stats = PSUTIL_AVAILABLE
        self.color_presets = {
            "Neon Green": "#00FF66",
            "Cyan": "#00E5FF",
            "Yellow": "#FFEA00",
            "Magenta": "#FF007F",
            "White": "#FFFFFF"
        }
        self.current_text_color = "#00FF66"
        self.bg_badge_color = "#111111"
        self.show_badge_bg = True
        self.is_click_through = False

        # Dragging support
        self._drag_start_x = 0
        self._drag_start_y = 0

        # FPS Calculation Variables (Moving average over last 30 frames)
        self.frame_times = collections.deque(maxlen=30)
        self.last_frame_time = time.perf_counter()
        self.fps_display_value = 0.0
        self.last_text_update = 0

        # 4. Build UI Elements
        self._create_widgets()
        self._setup_bindings()
        self._create_context_menu()

        # 5. Start Render / Measurement Loop
        self._measure_and_update()

    def _create_widgets(self):
        """Builds the compact HUD label."""
        # Use a clean, bold monospace font for stable number widths
        self.custom_font = tkfont.Font(family="Consolas", size=13, weight="bold")

        # Container Frame (Dark semi-transparent badge or fully transparent)
        self.badge_frame = tk.Frame(
            self.root,
            bg=self.bg_badge_color if self.show_badge_bg else self.trans_color,
            padx=10,
            pady=5,
            highlightthickness=1,
            highlightbackground="#2A2A2A" if self.show_badge_bg else self.trans_color
        )
        self.badge_frame.pack()

        # Label displaying FPS and stats
        self.stats_label = tk.Label(
            self.badge_frame,
            text="FPS: --",
            font=self.custom_font,
            fg=self.current_text_color,
            bg=self.bg_badge_color if self.show_badge_bg else self.trans_color,
            justify=tk.LEFT
        )
        self.stats_label.pack()

    def _setup_bindings(self):
        """Allows dragging the overlay with left mouse click and opening menu on right click."""
        for widget in (self.root, self.badge_frame, self.stats_label):
            widget.bind("<Button-1>", self._on_drag_start)
            widget.bind("<B1-Motion>", self._on_drag_motion)
            widget.bind("<Button-3>", self._show_context_menu)

    def _on_drag_start(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag_motion(self, event):
        # Calculate new window position based on mouse delta
        delta_x = event.x - self._drag_start_x
        delta_y = event.y - self._drag_start_y
        new_x = self.root.winfo_x() + delta_x
        new_y = self.root.winfo_y() + delta_y
        self.root.geometry(f"+{new_x}+{new_y}")

    def _create_context_menu(self):
        """Builds a right-click popup menu for settings and exit."""
        self.menu = tk.Menu(self.root, tearoff=0, bg="#1E1E1E", fg="#FFFFFF", activebackground="#007ACC")

        # Color sub-menu
        color_menu = tk.Menu(self.menu, tearoff=0, bg="#1E1E1E", fg="#FFFFFF", activebackground="#007ACC")
        for name, hex_code in self.color_presets.items():
            color_menu.add_command(
                label=name,
                command=lambda c=hex_code: self._set_text_color(c)
            )
        self.menu.add_cascade(label="🎨 Text Color", menu=color_menu)

        # Toggle Background Badge
        self.menu.add_command(label="🔳 Toggle Dark Badge", command=self._toggle_badge_bg)

        # Toggle Extra Stats (CPU/RAM)
        if PSUTIL_AVAILABLE:
            self.menu.add_command(label="📊 Toggle CPU/RAM Stats", command=self._toggle_system_stats)

        # Toggle Click-Through (Clicks pass through overlay)
        if CTYPES_AVAILABLE and sys.platform == "win32":
            self.menu.add_command(label="🖱️ Toggle Click-Through Mode", command=self._toggle_click_through)

        self.menu.add_separator()
        self.menu.add_command(label="❌ Exit Overlay", command=self.root.destroy)

    def _show_context_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def _set_text_color(self, color):
        self.current_text_color = color
        self.stats_label.configure(fg=self.current_text_color)

    def _toggle_badge_bg(self):
        self.show_badge_bg = not self.show_badge_bg
        target_bg = self.bg_badge_color if self.show_badge_bg else self.trans_color
        self.badge_frame.configure(
            bg=target_bg,
            highlightbackground="#2A2A2A" if self.show_badge_bg else self.trans_color
        )
        self.stats_label.configure(bg=target_bg)

    def _toggle_system_stats(self):
        self.show_system_stats = not self.show_system_stats

    def _toggle_click_through(self):
        """Toggles click-through behavior using Windows Win32 API."""
        if not CTYPES_AVAILABLE or sys.platform != "win32":
            return
        
        self.is_click_through = not self.is_click_through
        hwnd = self.root.winfo_id()
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_LAYERED = 0x00080000

        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

        if self.is_click_through:
            # Enable click-through
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
        else:
            # Disable click-through
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT)

    def _measure_and_update(self):
        """
        High-precision frame rate timing loop.
        Calculates time delta between frames using time.perf_counter().
        """
        now = time.perf_counter()
        delta = now - self.last_frame_time
        self.last_frame_time = now

        if delta > 0:
            self.frame_times.append(1.0 / delta)

        # Update the UI text every 250ms for readability (prevents flashing numbers)
        if now - self.last_text_update >= 0.25:
            if self.frame_times:
                self.fps_display_value = sum(self.frame_times) / len(self.frame_times)

            display_text = f"FPS: {int(round(self.fps_display_value))}"

            # Append CPU & RAM if enabled
            if self.show_system_stats and PSUTIL_AVAILABLE:
                try:
                    cpu = psutil.cpu_percent(interval=None)
                    ram = psutil.virtual_memory().percent
                    display_text += f" | CPU: {cpu:.0f}% | RAM: {ram:.0f}%"
                except Exception:
                    pass

            self.stats_label.configure(text=display_text)
            self.last_text_update = now

        # Schedule next tick with low-latency (e.g. ~16ms for 60Hz tick / update)
        self.root.after(16, self._measure_and_update)

    def run(self):
        """Starts the Tkinter main loop."""
        self.root.mainloop()


if __name__ == "__main__":
    app = FPSOverlay()
    app.run()
