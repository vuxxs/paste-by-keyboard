import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
import logging

import clipboard
import keyboard
import pyautogui

DEFAULT_HOTKEY = "F12"
EXIT_HOTKEY = "ctrl+shift+q"
VERSION = "4.0"

CONFIG_DIR = Path.home() / ".paste-by-keyboard"
CONFIG_FILE = CONFIG_DIR / "settings.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


class PasteByKeyboard:
    def __init__(self, root: tk.Tk):
        self.root = root

        self.paste_hotkey = DEFAULT_HOTKEY
        self.hotkey_handler = None
        self.exit_handler = None
        self.capture_hook = None

        self.captured_modifiers = set()
        self.capture_keys = set()
        self.is_capturing = False

        self.root.title("tool")
        self.root.geometry("240x140")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self.load_settings()
        self.create_ui()
        self.register_hotkeys()

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        logger.info("Paste by Keyboard started")

    def load_settings(self):
        """Load persisted settings, falling back to defaults."""
        try:
            if CONFIG_FILE.exists():
                settings = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

                self.paste_hotkey = settings.get("paste_hotkey", DEFAULT_HOTKEY)

            logger.info("Loaded hotkey: %s", self.paste_hotkey)

        except (OSError, json.JSONDecodeError, TypeError) as error:
            logger.warning("Could not load settings: %s", error)
            self.paste_hotkey = DEFAULT_HOTKEY

    def save_settings(self):
        """Persist settings as JSON."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        settings = {"paste_hotkey": self.paste_hotkey}

        CONFIG_FILE.write_text(
            json.dumps(settings, indent=4),
            encoding="utf-8",
        )

        logger.info("Settings saved: %s", self.paste_hotkey)

    def create_ui(self):
        """Build the application interface."""
        container = tk.Frame(self.root, padx=20, pady=12)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text=f"Paste by Keyboard {VERSION}",
            font=("Arial", 11, "bold"),
        ).pack(pady=(0, 5))

        self.hotkey_button = tk.Button(
            container,
            text=f"Paste hotkey: {self.paste_hotkey.upper()} (click to change)",
            font=("Arial", 9),
            command=self.start_hotkey_capture,
            cursor="hand2",
            width=17,
            height=3,
            wraplength=125,
        )
        self.hotkey_button.pack(anchor="center", pady=(0, 5))

        tk.Label(
            container,
            text="Exit anytime with Ctrl + Shift + Q",
            font=("Arial", 8),
            fg="gray",
        ).pack(side="bottom")

    def register_hotkeys(self):
        """Register global keyboard shortcuts."""
        self.hotkey_handler = keyboard.add_hotkey(
            self.paste_hotkey,
            self.paste_clipboard,
            suppress=True,
        )

        def exit_callback():
            self.root.after(0, self.close)

        self.exit_handler = keyboard.add_hotkey(
            EXIT_HOTKEY,
            exit_callback,
            suppress=True,
        )

        logger.info("Listening for %s", self.paste_hotkey)
        logger.info("Exit hotkey: %s", EXIT_HOTKEY)

    def start_hotkey_capture(self):
        """Start listening for a new hotkey combination."""
        if self.is_capturing:
            return

        self.is_capturing = True
        self.captured_modifiers.clear()
        self.capture_keys.clear()

        self.hotkey_button.config(
            text="Press a key combination... (Esc to cancel)",
            state="disabled",
        )

        self.capture_hook = keyboard.hook(self.handle_hotkey_capture)

    def handle_hotkey_capture(self, event):
        """Capture modifier keys and the final key."""
        if not self.is_capturing:
            return

        modifiers = {
            "ctrl": {"ctrl", "left ctrl", "right ctrl"},
            "alt": {"alt", "left alt", "right alt"},
            "shift": {"shift", "left shift", "right shift"},
            "windows": {"windows", "left windows", "right windows"},
        }

        modifier_name = next(
            (name for name, aliases in modifiers.items() if event.name in aliases),
            None,
        )

        if event.event_type == "down":
            if event.name == "esc":
                self.root.after(
                    0,
                    self.cancel_hotkey_capture,
                )
                return

            if modifier_name:
                self.captured_modifiers.add(modifier_name)
                return

            self.capture_keys.add(event.name)

            # Wait until all keys are released before finalizing.
            return

        if event.event_type == "up":
            if modifier_name:
                self.captured_modifiers.discard(modifier_name)

            # Finalize after the primary key is released.
            if event.name in self.capture_keys:
                self.capture_keys.discard(event.name)

                new_hotkey = "+".join(sorted(self.captured_modifiers) + [event.name])

                self.root.after(
                    0,
                    lambda hotkey=new_hotkey: self.update_hotkey(hotkey),
                )

    def cancel_hotkey_capture(self):
        """Cancel capture and restore the existing hotkey."""
        if not self.is_capturing:
            return

        self.stop_hotkey_capture()

        self.hotkey_button.config(
            text=f"Current hotkey: {self.paste_hotkey}",
            state="normal",
        )

    def stop_hotkey_capture(self):
        """Remove the temporary keyboard hook."""
        self.is_capturing = False

        if self.capture_hook is not None:
            keyboard.unhook(self.capture_hook)
            self.capture_hook = None

        self.captured_modifiers.clear()
        self.capture_keys.clear()

    def update_hotkey(self, new_hotkey):
        """Register and persist a newly captured hotkey."""
        self.stop_hotkey_capture()

        new_hotkey = new_hotkey.lower()

        if new_hotkey == EXIT_HOTKEY:
            messagebox.showerror(
                "Invalid hotkey",
                "The paste hotkey cannot be the exit hotkey.",
            )
            self.cancel_hotkey_capture()
            return

        old_hotkey = self.paste_hotkey
        old_handler = self.hotkey_handler

        new_handler = None

        try:
            new_handler = keyboard.add_hotkey(
                new_hotkey,
                self.paste_clipboard,
                suppress=True,
            )

            self.paste_hotkey = new_hotkey

            try:
                self.save_settings()
            except Exception:
                self.paste_hotkey = old_hotkey
                keyboard.remove_hotkey(new_handler)
                raise

            if old_handler is not None:
                keyboard.remove_hotkey(old_handler)

            self.hotkey_handler = new_handler

            self.hotkey_button.config(
                text=f"Current hotkey: {new_hotkey}",
                state="normal",
            )

            logger.info("Hotkey changed to %s", new_hotkey)

        except Exception as error:
            logger.exception("Failed to update hotkey")

            self.paste_hotkey = old_hotkey

            if new_handler is not None:
                try:
                    keyboard.remove_hotkey(new_handler)
                except Exception:
                    logger.exception("Could not remove new hotkey")

            self.hotkey_button.config(
                text=f"Current hotkey: {old_hotkey}",
                state="normal",
            )

            messagebox.showerror(
                "Hotkey error",
                f"Could not register or save this hotkey:\n{error}",
            )

    def paste_clipboard(self):
        """Type the current clipboard contents."""
        try:
            text = clipboard.paste()

            if text:
                pyautogui.typewrite(text, interval=0)

        except Exception:
            logger.exception("Failed to paste clipboard contents")

    def close(self):
        """Cleanly shut down the application."""
        logger.info("Shutting down application")

        if self.is_capturing:
            try:
                self.stop_hotkey_capture()
            except Exception:
                logger.exception("Error stopping capture hook")

        for handler in (self.hotkey_handler, self.exit_handler):
            if handler is not None:
                try:
                    keyboard.remove_hotkey(handler)
                except (KeyError, ValueError):
                    logger.debug("Hotkey was already removed")
                except Exception:
                    logger.exception("Error removing hotkey")

        self.hotkey_handler = None
        self.exit_handler = None

        self.root.destroy()


def main():
    logger.info("Welcome to Paste by Keyboard")

    root = tk.Tk()
    PasteByKeyboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
