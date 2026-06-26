#
#  main.py
#  AskWindows
#
#  App entry point. Mirrors AskMacApp.swift.
#  Creates the window, loads settings, and switches between
#  WelcomeView and ChatView based on settings.is_set_up.
#

import customtkinter as ctk
from user_settings import UserSettings
from welcome_view import WelcomeView
from chat_view import ChatView

# tkinterdnd2 adds drag-and-drop to the root Tk window.
# We mix it into AskWindowsApp so every widget in the app can be
# a drop target. If the package is missing we fall back gracefully.
try:
    from tkinterdnd2 import TkinterDnD as _TkDnD
    _dnd_base   = _TkDnD.DnDWrapper
    _dnd_avail  = True
except ImportError:
    _dnd_base   = object
    _dnd_avail  = False


APP_TITLE  = "Ask Windows"
WIN_WIDTH  = 640
WIN_HEIGHT = 700
MIN_WIDTH  = 520
MIN_HEIGHT = 560


class AskWindowsApp(ctk.CTk, _dnd_base):

    def __init__(self):
        super().__init__()

        # Load the tkdnd Tcl extension so every widget in the app
        # gets drop_target_register / dnd_bind methods.
        if _dnd_avail:
            self.TkdndVersion = _TkDnD._require(self)

        self._settings = UserSettings()

        self.title(APP_TITLE)

        # Size and place the window so it always fits the usable screen area
        # (the screen minus the taskbar), regardless of resolution or DPI
        # scaling. winfo_screenheight() reports the FULL physical height and
        # ignores the taskbar, which is why the window could previously hang
        # off the bottom — so we measure the actual work area instead.
        self.update_idletasks()
        try:
            # Tk knows the maximised inner size, which equals the work area
            # (screen minus taskbar). This is the reliable usable height.
            work_w = self.winfo_screenwidth()
            work_h = self.winfo_height() if self.state() == "zoomed" else 0
            if not work_h:
                # Query the work area via the window manager's maxsize, which
                # Tk derives from the usable desktop rectangle.
                work_w, work_h = self.maxsize()
        except Exception:
            work_w, work_h = self.winfo_screenwidth(), self.winfo_screenheight()

        # Leave a small margin so the title bar and a bottom gap stay visible.
        usable_h = max(MIN_HEIGHT, work_h - 60)
        win_h = min(WIN_HEIGHT, usable_h)
        win_w = WIN_WIDTH

        # Centre horizontally; pin near the top so the bottom never clips.
        x = max(0, (work_w - win_w) // 2)
        y = 20
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.minsize(MIN_WIDTH, MIN_HEIGHT)

        # Use system default appearance (respects Windows dark/light mode).
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self._current_view = None
        self._show_appropriate_view()

    def _show_appropriate_view(self):
        if self._current_view:
            # Give ChatView a chance to clean up threads before destroying.
            if hasattr(self._current_view, "cleanup"):
                self._current_view.cleanup()
            self._current_view.destroy()
            self._current_view = None

        if self._settings.is_set_up:
            self._current_view = ChatView(
                self,
                settings=self._settings,
                on_reset=self._on_reset,
            )
        else:
            self._current_view = WelcomeView(
                self,
                settings=self._settings,
                on_complete=self._on_setup_complete,
            )

        self._current_view.pack(fill="both", expand=True)

    def _on_setup_complete(self):
        """Called by WelcomeView when the user taps Continue."""
        self._show_appropriate_view()

    def _on_reset(self):
        """Called by SettingsSheet when the user taps 'Start over'."""
        self._show_appropriate_view()


def main():
    app = AskWindowsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
